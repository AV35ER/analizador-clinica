"""Compara los algoritmos de ambos lenguajes y un build sin archivos locales."""
import json
import os
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import subprocess
import sys
from threading import Thread
from tempfile import TemporaryDirectory
import unittest
from urllib.request import urlopen
from xml.etree import ElementTree

import app
import automatas
from test_interfaz_generada import LeerHTML, texto


@unittest.skipUnless(shutil.which("node"), "La paridad JavaScript requiere Node")
class ParidadTests(unittest.TestCase):
    def ejecutar_node(self, codigo, datos):
        resultado = subprocess.run(["node", "-e", codigo], input=json.dumps(datos),
                                   text=True, encoding="utf-8", capture_output=True, timeout=60)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        return json.loads(resultado.stdout)

    def test_modelos_tablas_y_quintuplas_identicos(self):
        expresiones = list(automatas.EXPRESIONES.values()) + [
            "a+", "a*", "(a|b)*abb", "a?b{1,3}", "[a-c]{0,2}", "x{2,}", "", "a|", r"\+", "(ab|c)+"]
        datos = self.ejecutar_node("""
            const fs = require('node:fs'), m = require('./netlify-public/motor.js');
            const patrones = JSON.parse(fs.readFileSync(0, 'utf8'));
            console.log(JSON.stringify(patrones.map(p => {
                const afnd=m.crearAFND(p), afd=m.convertirAFD(afnd), minimo=m.minimizarAFD(afd);
                return [afnd,afd,minimo].map((a,i) => [a,m.quintupla(a),m.tabla(a),m.tablaVisual(a,i===0)]);
            })));
        """, expresiones)
        for patron, resultado in zip(expresiones, datos):
            afnd = automatas.crear_afnd(patron)
            afd = automatas.convertir_afd(afnd)
            for i, a in enumerate([afnd, afd, automatas.minimizar_afd(afd)]):
                with self.subTest(patron=patron, tipo=i):
                    esperado = [a, automatas.generar_quintupla(a), automatas.generar_tabla(a), app.preparar_tabla(a, i == 0)]
                    self.assertEqual(resultado[i], json.loads(json.dumps(esperado)))

    def test_lexico_y_simulacion_identicos(self):
        programas = [app.EJEMPLO, "G00 X02 Y03;\nG01 X10 Y15;\nG28;", "", "   ",
                     "G02 X01 Y20;", "G01 Y20 X01;", "G28 X01;", "G01 X01 Y20", "G00 X01 Y20 F5;",
                     "G28;G28;", "G01 X99 Y00 F999;\rG28;", "😀 G28;", "G28;\u0085G28;", "G28;\x1cG28;", "\x1fG28;", "G28;\ufeffG28;"]
        for validos, invalidos in automatas.EJEMPLOS.values():
            programas.extend(validos + invalidos)
        datos = self.ejecutar_node("""
            const fs=require('node:fs'), m=require('./netlify-public/motor.js');
            const datos=JSON.parse(fs.readFileSync(0,'utf8'));
            console.log(JSON.stringify(datos.programas.map(p=>m.compilar(p,datos))));
        """, {"programas": programas, "expresiones": automatas.EXPRESIONES})
        for programa, resultado in zip(programas, datos):
            tokens, errores = app.analizar(programa)
            traduccion, errores_instruccion = ([], []) if errores else app.interpretar(tokens)
            with self.subTest(programa=programa):
                self.assertEqual(resultado, dict(tokens=tokens, errores=errores, traduccion=traduccion, errores_instruccion=errores_instruccion))

    def test_html_estatico_graficos_tablas_quintuplas(self):
        datos = self.ejecutar_node("""
            const fs=require('node:fs'), m=require('./netlify-public/motor.js'), v=require('./netlify-public/vistas.js');
            const config=JSON.parse(fs.readFileSync(0,'utf8'));
            const automatas=m.generarTodos(config);
            console.log(JSON.stringify({html:v.renderizar(m.compilar('G28;',config),automatas),automatas}));
        """, {"expresiones": automatas.EXPRESIONES, "ejemplos": automatas.EJEMPLOS})
        pagina = LeerHTML(datos["html"]).raiz
        graficos = re.findall(r"<svg\b.*?</svg>", datos["html"], re.DOTALL)
        self.assertEqual(len(graficos), 15)
        for grafico in graficos:
            ElementTree.fromstring(grafico)
        for nombre, modelos in datos["automatas"].items():
            for tipo in ("afnd", "afd", "afd_minimo"):
                with self.subTest(token=nombre, tipo=tipo):
                    modelo = modelos[tipo]
                    panel = pagina.find(f'.//div[@id="token-{nombre}"]')
                    vista = panel.find(f'.//div[@data-tipo="{tipo}"]')
                    self.assertEqual("hidden" in vista.attrib, tipo != "afnd")
                    quint = [texto(n) for n in vista.find('.//div[@class="quintupla"]').findall("div")]
                    q = modelos["quintupla_" + tipo]
                    self.assertEqual(quint, [", ".join(q["Q"]), ", ".join(q["Sigma"]), "Ver tabla de transiciones.", q["q0"], ", ".join(q["F"])])
                    tabla = vista.find('.//div[@class="transiciones"]//table')
                    visual = modelos["tabla_visual_" + tipo]
                    self.assertEqual([texto(n) for n in tabla.findall("thead/tr/th")], ["Estado", *visual["alfabeto"]])
                    filas = tabla.findall("tbody/tr")
                    self.assertEqual(len(filas), len(visual["filas"]))
                    for fila, esperada in zip(filas, visual["filas"]):
                        self.assertEqual([texto(n) for n in fila.findall("td")][1:], list(esperada["destinos"].values()))
                    svg = vista.find(".//svg")
                    # Además de leer HTML, el SVG debe ser XML válido.
                    ElementTree.fromstring(ElementTree.tostring(svg, encoding="unicode"))
                    estados = svg.findall('.//g[@class="estado"]')
                    self.assertEqual([n.get("data-estado") for n in estados], modelo["estados"])
                    self.assertEqual([n.get("data-estado") for n in estados if n.get("data-inicial") == "true"], [modelo["inicial"]])
                    self.assertEqual([n.get("data-estado") for n in estados if n.get("data-final") == "true"], modelo["finales"])
                    aristas = []
                    for arista in svg.findall('.//g[@class="arista"]'):
                        simbolos = json.loads(arista.get("data-simbolos"))
                        self.assertEqual(texto(arista.find("text")), automatas.etiqueta_simbolos(simbolos))
                        self.assertTrue(arista.find("path").get("d"))
                        aristas.extend((arista.get("data-origen"), s, arista.get("data-destino")) for s in simbolos)
                    self.assertCountEqual(aristas, [(t["origen"], t["simbolo"], t["destino"]) for t in modelo["transiciones"]])

    def test_copia_limpia_build_y_flujo_generado_sin_red(self):
        with TemporaryDirectory() as carpeta:
            destino = Path(carpeta)
            # Solamente las fuentes del build y sus pruebas: sin .venv, Git ni HTML previo.
            for nombre in ("app.py", "automatas.py", "generar_frontend.py", "test_cliente.cjs"):
                shutil.copyfile(nombre, destino / nombre)
            shutil.copytree("templates", destino / "templates")
            (destino / "netlify-public").mkdir()
            for nombre in ("motor.js", "vistas.js", "cliente.js"):
                shutil.copyfile(Path("netlify-public", nombre), destino / "netlify-public" / nombre)
            env = {**os.environ, "NETLIFY": "true", "RENDER_API_URL": "", "PYTHONUTF8": "1"}
            build = subprocess.run([sys.executable, "generar_frontend.py"], cwd=destino, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(build.returncode, 0, build.stderr)
            self.assertTrue((destino / "netlify-public/index.html").is_file())
            class ServidorSilencioso(SimpleHTTPRequestHandler):
                def log_message(self, formato, *args):
                    pass
            servidor = ThreadingHTTPServer(("127.0.0.1", 0), partial(ServidorSilencioso, directory=str(destino / "netlify-public")))
            hilo = Thread(target=servidor.serve_forever, daemon=True)
            hilo.start()
            try:
                for recurso in ("index.html", "motor.js", "vistas.js", "cliente.js"):
                    with urlopen(f"http://127.0.0.1:{servidor.server_port}/{recurso}", timeout=5) as respuesta:
                        self.assertEqual(respuesta.status, 200)
                        self.assertIn("html" if recurso.endswith(".html") else "javascript", respuesta.headers["Content-Type"])
                        self.assertEqual(respuesta.read(), (destino / "netlify-public" / recurso).read_bytes())
            finally:
                servidor.shutdown()
                servidor.server_close()
                hilo.join()
            pruebas = subprocess.run(["node", "--test", "test_cliente.cjs"], cwd=destino, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60)
            self.assertEqual(pruebas.returncode, 0, pruebas.stdout + pruebas.stderr)


if __name__ == "__main__":
    unittest.main()

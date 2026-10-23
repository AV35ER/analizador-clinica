import io
import itertools
import re
import unittest
from collections import deque
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

import app
import automatas as au


def avanzar(automata, estados, simbolo):
    destinos = set()
    for transicion in automata["transiciones"]:
        coincide = simbolo in au.expandir_simbolo(transicion["simbolo"])
        if transicion["origen"] in estados and coincide:
            destinos.add(transicion["destino"])
    return au.cierre_epsilon(destinos, automata["transiciones"])


def acepta(automata, texto):
    estados = au.cierre_epsilon([automata["inicial"]], automata["transiciones"])
    for simbolo in texto:
        estados = avanzar(automata, estados, simbolo)
    return bool(set(estados) & set(automata["finales"]))


class ProyectoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        au.generar_token.cache_clear()
        cls.datos = au.generar_todos()
        cls.cliente = app.app.test_client()

    def test_entrada_valida(self):
        tokens, errores = app.analizar(app.EJEMPLO)
        self.assertEqual([t["token"] for t in tokens], list(au.EXPRESIONES))
        self.assertEqual(errores, [])

    def test_error_completo(self):
        tokens, errores = app.analizar(app.EJEMPLO.replace("74839261", "7483926"))
        self.assertEqual(len(tokens), 4)
        self.assertEqual(errores, [{"linea": 1, "columna": 18, "lexema": "7483926", "detalle": "No corresponde a DNI"}])

    def test_limites_regex_y_automatas(self):
        casos = au.EJEMPLOS
        for token, (validos, invalidos) in casos.items():
            muestras = set(validos + invalidos)
            muestras.update("".join(p) for n in range(4) for p in itertools.product("01LU;", repeat=n))
            for valido in validos:
                for i in range(len(valido)):
                    muestras.add(valido[:i] + valido[i + 1:])
                for extra in "0L; ":
                    muestras.add(valido + extra)
                    muestras.add(extra + valido)
            for texto in muestras:
                esperado = re.fullmatch(au.EXPRESIONES[token], texto) is not None
                for tipo in ("afnd", "afd"):
                    self.assertEqual(acepta(self.datos[token][tipo], texto), esperado, (token, tipo, texto))
            for texto in validos:
                self.assertTrue(re.fullmatch(au.EXPRESIONES[token], texto))
            for texto in invalidos:
                self.assertIsNone(re.fullmatch(au.EXPRESIONES[token], texto))

    def test_equivalencia_todos_estados_alcanzables(self):
        for datos in self.datos.values():
            afnd, afd = datos["afnd"], datos["afd"]
            inicial = au.cierre_epsilon([afnd["inicial"]], afnd["transiciones"])
            pendientes = deque([(inicial, afd["inicial"])])
            vistos = set()
            while pendientes:
                conjunto, estado = pendientes.popleft()
                if (conjunto, estado) in vistos:
                    continue
                vistos.add((conjunto, estado))
                self.assertEqual(set(afd["equivalencias"][estado]), set(conjunto))
                self.assertEqual(bool(set(conjunto) & set(afnd["finales"])), estado in afd["finales"])
                for simbolo in au.obtener_alfabeto(afnd):
                    destinos = [t["destino"] for t in afd["transiciones"] if t["origen"] == estado and t["simbolo"] == simbolo]
                    self.assertEqual(len(destinos), 1)
                    pendientes.append((avanzar(afnd, conjunto, simbolo), destinos[0]))
            self.assertEqual({e for _, e in vistos}, set(afd["estados"]))

    def test_epsilon_ciclos_y_estrella(self):
        transiciones = [
            {"origen": "q0", "simbolo": "ε", "destino": "q1"},
            {"origen": "q1", "simbolo": "ε", "destino": "q0"}
        ]
        self.assertEqual(au.cierre_epsilon(["q0"], transiciones), frozenset(["q0", "q1"]))
        for automata in (au.crear_afnd("[0-9]*"), au.convertir_afd(au.crear_afnd("[0-9]*"))):
            for texto in ("", "0", "007", "123"):
                self.assertTrue(acepta(automata, texto))
            self.assertFalse(acepta(automata, "L"))

    def test_tablas_quintuplas_y_svg(self):
        ns = {"s": "http://www.w3.org/2000/svg"}
        for datos in self.datos.values():
            for tipo in ("afnd", "afd"):
                automata = datos[tipo]
                quint = datos["quintupla_" + tipo]
                self.assertEqual(quint["Q"], automata["estados"])
                self.assertEqual(quint["Sigma"], au.obtener_alfabeto(automata))
                self.assertNotIn("ε", quint["Sigma"])
                self.assertEqual(quint["delta"], automata["transiciones"])
                self.assertEqual(quint["q0"], automata["inicial"])
                self.assertEqual(quint["F"], automata["finales"])
                visual = app.preparar_tabla(automata, tipo == "afnd")
                tabla = {f["estado"]: f for f in datos["tabla_" + tipo]}
                for fila in visual["filas"]:
                    for etiqueta, simbolos in visual["grupos"]:
                        for simbolo in simbolos:
                            esperado = {t["destino"] for t in automata["transiciones"]
                                        if t["origen"] == fila["estado"] and
                                        (t["simbolo"] == simbolo or simbolo in au.expandir_simbolo(t["simbolo"]))}
                            self.assertEqual(set(tabla[fila["estado"]].get(simbolo, [])), esperado)
                            self.assertEqual(set(fila["destinos"][etiqueta].split(", ")) if esperado else set(), esperado)
                raiz = ElementTree.fromstring(datos["imagen_" + tipo])
                nodos = raiz.findall('.//s:g[@class="node"]', ns)
                self.assertEqual({n.find("s:title", ns).text for n in nodos}, set(automata["estados"]) | {"inicio"})
                aristas = raiz.findall('.//s:g[@class="edge"]', ns)
                grupos = {}
                for t in automata["transiciones"]:
                    grupos.setdefault((t["origen"], t["destino"]), []).append(t["simbolo"])
                esperadas = [(a + "->" + b, au.etiqueta_simbolos(valores)) for (a, b), valores in grupos.items()]
                reales = [(e.find("s:title", ns).text, e.find("s:text", ns).text) for e in aristas if e.find("s:text", ns) is not None]
                self.assertCountEqual(reales, esperadas)
                for nodo in nodos:
                    nombre = nodo.find("s:title", ns).text
                    if nombre != "inicio":
                        self.assertEqual(len(nodo.findall("s:ellipse", ns)), 2 if nombre in automata["finales"] else 1)

    def test_web_y_seleccion(self):
        self.assertEqual(self.cliente.get("/").status_code, 200)
        respuesta = self.cliente.post("/", data={"texto": app.EJEMPLO})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data.count(b"<svg"), 10)
        self.assertNotIn(b"static/img", respuesta.data)
        self.assertNotIn(b"<footer", respuesta.data)
        # Los cinco tokens se consultan incluso si no aparecen en la entrada.
        respuesta = self.cliente.post("/", data={"texto": "???"})
        self.assertEqual(respuesta.data.count(b"<svg"), 10)
        self.assertIn(b"seleccionarTipo", respuesta.data)

    def test_txt_multilinea_y_campos(self):
        texto = app.EJEMPLO + "\n" + app.EJEMPLO
        tokens, errores = app.analizar(texto)
        self.assertEqual(len(tokens), 10)
        self.assertEqual(errores, [])
        self.assertEqual((tokens[5]["linea"], tokens[5]["columna"]), (2, 1))
        respuesta = self.cliente.post("/", data={"texto": "ignorado", "archivo": (io.BytesIO(b"\xef\xbb\xbf" + texto.encode()), "entrada.TXT")})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data.count(b"<svg"), 10)
        for contenido, nombre, mensaje in [(b"abc", "a.csv", b"Selecciona"), (b"\xff", "a.txt", b"UTF-8")]:
            self.assertIn(mensaje, self.cliente.post("/", data={"archivo": (io.BytesIO(contenido), nombre)}).data)
        respuesta = self.cliente.post("/", data={"archivo": (io.BytesIO(b"x" * (1024 * 1024 + 1)), "a.txt")})
        self.assertEqual(respuesta.status_code, 413)
        respuesta.request.close()
        respuesta.request.environ["wsgi.input"].close()

    def test_cache_y_sin_archivos(self):
        antes = {p.relative_to(Path.cwd()) for p in Path.cwd().rglob("*") if p.is_file() and p.suffix in (".svg", ".png", ".gv")}
        au.generar_token.cache_clear()
        with patch.object(au.Digraph, "render", side_effect=AssertionError("No escribir imágenes")):
            primero = au.generar_todos(["DNI"])
            with patch.object(au.Digraph, "pipe", side_effect=AssertionError("No regenerar")):
                self.assertIs(primero["DNI"], au.generar_todos(["DNI"])["DNI"])
        despues = {p.relative_to(Path.cwd()) for p in Path.cwd().rglob("*") if p.is_file() and p.suffix in (".svg", ".png", ".gv")}
        self.assertEqual(antes, despues)

    def test_graphviz_ausente(self):
        with patch.object(app, "preparar_resultados", side_effect=app.ExecutableNotFound(["dot"])):
            respuesta = self.cliente.post("/", data={"texto": app.EJEMPLO})
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(b"PATH", respuesta.data)

    def test_parser_general_y_errores(self):
        for expresion in ("(a|b)+c?", "[A-Cx-z]{2,3}", "a{0}", "(ab){1,}", "(a|)b", "[12][0-9]", "a*", r"a\+b"):
            afnd = au.crear_afnd(expresion)
            afd = au.convertir_afd(afnd)
            for n in range(5):
                for partes in itertools.product("abc+", repeat=n):
                    texto = "".join(partes)
                    esperado = re.fullmatch(expresion, texto) is not None
                    self.assertEqual(acepta(afnd, texto), esperado, (expresion, texto))
                    self.assertEqual(acepta(afd, texto), esperado, (expresion, texto))
        for expresion in ("[z-a]", "[", "(a", "a{3,2}", "a{a}", "a{2", "*a", "a)", "[^a]", r"\d", r"[\d]"):
            with self.assertRaises(ValueError, msg=expresion):
                au.crear_afnd(expresion)

    def test_campos_nombre_y_limitaciones(self):
        for texto, lexema in ((app.EJEMPLO.replace("Joaquin Esquivez", "Joaquin"), "Joaquin"),
                              (app.EJEMPLO.replace("Joaquin", "José"), "José Esquivez"),
                              (app.EJEMPLO.replace("10:30", "24:00"), "24:00")):
            _, errores = app.analizar(texto)
            self.assertIn(lexema, [e["lexema"] for e in errores])
        self.assertTrue(acepta(self.datos["FECHA"]["afnd"], "31/02/2026"))


if __name__ == "__main__":
    unittest.main()

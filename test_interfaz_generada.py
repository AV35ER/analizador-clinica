"""Comprueba el HTML entregado por Flask, sin simular una revisión visual."""
import re
import unittest
from html.parser import HTMLParser
from xml.etree.ElementTree import Element, SubElement

import app
import automatas


class LeerHTML(HTMLParser):
    def __init__(self, contenido):
        super().__init__(convert_charrefs=True)
        self.raiz = Element("documento")
        self.pila = [self.raiz]
        self.feed(contenido)

    def handle_starttag(self, tag, attrs):
        nodo = SubElement(self.pila[-1], tag, dict((k, v or "") for k, v in attrs))
        if tag not in {"meta", "input", "br", "hr", "link", "img"}:
            self.pila.append(nodo)

    def handle_startendtag(self, tag, attrs):
        SubElement(self.pila[-1], tag, dict((k, v or "") for k, v in attrs))

    def handle_endtag(self, tag):
        for i in range(len(self.pila) - 1, 0, -1):
            if self.pila[i].tag == tag:
                del self.pila[i:]
                break

    def handle_data(self, data):
        nodo = self.pila[-1]
        if len(nodo):
            nodo[-1].tail = (nodo[-1].tail or "") + data
        else:
            nodo.text = (nodo.text or "") + data


def texto(nodo):
    return "".join(nodo.itertext()).strip()


def simbolos_etiqueta(etiqueta, alfabeto):
    """Decodifica las etiquetas visibles sin usar el agrupador del programa."""
    resultado = set()
    for parte in etiqueta.split(", "):
        if parte == "␠":
            resultado.add(" ")
        elif parte.startswith("["):
            resultado.update(c for c in alfabeto if re.fullmatch(parte, c))
        else:
            resultado.add(parte)
    return resultado


class InterfazGeneradaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.datos = automatas.generar_todos()
        cliente = app.app.test_client()
        respuesta = cliente.post("/", data={"texto": app.EJEMPLO})
        assert respuesta.status_code == 200
        cls.pagina = LeerHTML(respuesta.get_data(as_text=True)).raiz

    def test_cinco_expresiones_originales_y_selectores(self):
        originales = {
            "NOMBRE_PACIENTE": "[A-Za-z]+( [A-Za-z]+)+",
            "DNI": "[0-9]{8}",
            "FECHA": "(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/[0-9]{4}",
            "HORA": "([01][0-9]|2[0-3]):[0-5][0-9]",
            "ESPECIALIDAD": "[A-Za-z]+"
        }
        self.assertEqual(automatas.EXPRESIONES, originales)
        botones = self.pagina.findall('.//button[@class="boton-token"]')
        self.assertEqual([b.get("data-token") for b in botones], list(originales))
        for nombre, expresion in originales.items():
            panel = self.pagina.find('.//div[@id="token-' + nombre + '"]')
            self.assertEqual(texto(panel.find(".//code")), expresion)
            self.assertEqual([o.get("value") for o in panel.findall(".//select/option")], ["afnd", "afd"])
            for grupo in automatas.EJEMPLOS[nombre]:
                for ejemplo in grupo:
                    self.assertIn(ejemplo, texto(panel))

    def test_diez_graficos_tablas_y_quintuplas_del_html(self):
        for nombre, datos in self.datos.items():
            panel = self.pagina.find('.//div[@id="token-' + nombre + '"]')
            for tipo in ("afnd", "afd"):
                with self.subTest(token=nombre, tipo=tipo):
                    modelo = datos[tipo]
                    vista = panel.find('.//div[@data-tipo="' + tipo + '"]')
                    self.assertEqual("hidden" in vista.attrib, tipo == "afd")
                    quint = vista.find('.//div[@class="quintupla"]')
                    valores = [texto(n) for n in quint.findall("div")]
                    self.assertEqual(valores[0], ", ".join(modelo["estados"]))
                    self.assertEqual(valores[1], ", ".join(automatas.obtener_alfabeto(modelo)).strip())
                    self.assertEqual(valores[3], modelo["inicial"])
                    self.assertEqual(valores[4], ", ".join(modelo["finales"]))
                    alfabeto = set(automatas.obtener_alfabeto(modelo)) | {"ε"}
                    esperadas = set()
                    for t in modelo["transiciones"]:
                        for simbolo in simbolos_etiqueta(t["simbolo"], alfabeto):
                            esperadas.add((t["origen"], simbolo, t["destino"]))

                    svg = vista.find(".//svg")
                    nodos = svg.findall('.//g[@class="node"]')
                    self.assertEqual({texto(n.find("title")) for n in nodos}, set(modelo["estados"]) | {"inicio"})
                    for nodo in nodos:
                        estado = texto(nodo.find("title"))
                        if estado != "inicio":
                            self.assertEqual(len(nodo.findall("ellipse")), 2 if estado in modelo["finales"] else 1)
                    aristas = set()
                    iniciales = []
                    for arista in svg.findall('.//g[@class="edge"]'):
                        origen, destino = texto(arista.find("title")).split("->")
                        etiqueta = arista.find("text")
                        if etiqueta is None:
                            iniciales.append((origen, destino))
                        else:
                            for simbolo in simbolos_etiqueta(texto(etiqueta), alfabeto):
                                aristas.add((origen, simbolo, destino))
                    self.assertEqual(iniciales, [("inicio", modelo["inicial"])])
                    self.assertEqual(aristas, esperadas)

                    tabla = vista.find('.//div[@class="tabla-contenedor transiciones"]/table')
                    columnas = [texto(n) for n in tabla.findall("thead/tr/th")][1:]
                    filas = tabla.findall("tbody/tr")
                    self.assertEqual(len(filas), len(modelo["estados"]))
                    celdas_transiciones = set()
                    for fila, estado in zip(filas, modelo["estados"]):
                        celdas = [texto(n) for n in fila.findall("td")]
                        self.assertEqual(celdas[0].replace("→", "").replace("*", "").strip(), estado)
                        self.assertEqual("→" in celdas[0], estado == modelo["inicial"])
                        self.assertEqual("*" in celdas[0], estado in modelo["finales"])
                        for columna, celda in zip(columnas, celdas[1:]):
                            if celda != "∅":
                                for simbolo in simbolos_etiqueta(columna, alfabeto):
                                    for destino in celda.split(", "):
                                        celdas_transiciones.add((estado, simbolo, destino))
                    self.assertEqual(celdas_transiciones, esperadas)


if __name__ == "__main__":
    unittest.main()


import os
import re
from graphviz import ExecutableNotFound, CalledProcessError
from flask import Flask, abort, render_template, request
from automatas import EXPRESIONES, EJEMPLOS, generar_todos, generar_tabla, agrupar_columnas

app = Flask(__name__)
LIMITE_ENTRADA = 1024 * 1024
app.config.update(
    MAX_CONTENT_LENGTH=2 * LIMITE_ENTRADA + 64 * 1024,
    MAX_FORM_MEMORY_SIZE=LIMITE_ENTRADA + 64 * 1024,
    MAX_FORM_PARTS=10
)

REGLAS = [
    (nombre, re.compile(patron))
    for nombre, patron in EXPRESIONES.items()
]

EJEMPLO = "G01 X01 Y20 F120;"
CODIGOS = {
    "G00": "Mover directamente a X e Y en el simulador.",
    "G01": "Mover en línea recta a X e Y; F indica velocidad, por defecto 100.",
    "G28": "Regresar al origen (0, 0)."
}


def analizar(texto):
    tokens = []
    errores = []

    for numero, linea in enumerate(texto.splitlines(), start=1):
        for coincidencia in re.finditer(r";|[^\s;]+", linea):
            lexema = coincidencia.group()
            elemento = {"linea": numero, "columna": coincidencia.start() + 1, "lexema": lexema}
            for nombre, patron in REGLAS:
                if patron.fullmatch(lexema):
                    tokens.append({**elemento, "token": nombre})
                    break
            else:
                errores.append({**elemento, "detalle": "Lexema no reconocido"})

    return tokens, errores


def interpretar(tokens):
    """Reconoce tres formatos regulares y traduce sin AST ni analisis LR.

    El programa se valida completo antes de devolver una simulacion; si alguna
    linea falla, no se presenta como ejecutado un programa parcial.
    """
    lineas = {}
    for token in tokens:
        lineas.setdefault(token["linea"], []).append(token)
    resultado, errores = [], []
    posicion = [0, 0]
    for numero, elementos in lineas.items():
        tipos = [t["token"] for t in elementos]
        codigo = elementos[0]["lexema"]
        formatos = [["COMANDO", "COORDENADA_X", "COORDENADA_Y", "FIN_INSTRUCCION"],
                    ["COMANDO", "COORDENADA_X", "COORDENADA_Y", "VELOCIDAD", "FIN_INSTRUCCION"]]
        valido = (codigo == "G28" and tipos == ["COMANDO", "FIN_INSTRUCCION"]) or (
            codigo in ("G00", "G01") and tipos in formatos and
            (codigo == "G01" or "VELOCIDAD" not in tipos))
        if not valido:
            errores.append({"linea": numero, "detalle": "Formato de instrucción incorrecto; consulta el diccionario."})
            continue
        destino = [0, 0] if codigo == "G28" else [int(t["lexema"][1:]) for t in elementos[1:3]]
        paso = {"linea": numero, "codigo": codigo, "desde": posicion[:], "hasta": destino}
        if codigo == "G01":
            paso["velocidad"] = int(elementos[3]["lexema"][1:]) if "VELOCIDAD" in tipos else 100
        resultado.append(paso)
        posicion = destino
    return ([], errores) if errores else (resultado, [])


def preparar_tabla(automata, es_afnd, tabla=None):
    if tabla is None:
        tabla = generar_tabla(automata)
    grupos = agrupar_columnas(automata, es_afnd, tabla)
    filas = []
    for fila in tabla:
        estado = fila["estado"]
        filas.append({
            "estado": estado,
            "inicial": estado == automata["inicial"],
            "final": estado in automata["finales"],
            "destinos": {
                etiqueta: ", ".join(fila.get(simbolos[0], [])) or "∅"
                for etiqueta, simbolos in grupos
            }
        })
    return {"alfabeto": [g[0] for g in grupos], "grupos": grupos, "filas": filas}


def preparar_resultados():
    resultados = {}
    for nombre, datos in generar_todos().items():
        resultados[nombre] = {
            **datos,
            "tabla_visual_afnd": preparar_tabla(datos["afnd"], True, datos["tabla_afnd"]),
            "tabla_visual_afd": preparar_tabla(datos["afd"], False, datos["tabla_afd"]),
            "tabla_visual_afd_minimo": preparar_tabla(datos["afd_minimo"], False, datos["tabla_afd_minimo"])
        }

    return resultados


@app.route("/", methods=["GET", "POST"])
@app.route("/api/analizar", methods=["POST"])
def inicio():
    texto = EJEMPLO
    tokens = []
    errores = []
    mensaje = ""
    analizado = False
    resultados = {}
    traduccion, errores_instruccion = [], []

    if request.method == "POST":
        texto = request.form.get("texto", "")
        archivo = request.files.get("archivo")

        if archivo and archivo.filename:
            if not archivo.filename.lower().endswith(".txt"):
                mensaje = "Selecciona un archivo TXT."
            else:
                try:
                    contenido = archivo.read(LIMITE_ENTRADA + 1)
                    if len(contenido) > LIMITE_ENTRADA:
                        abort(413)
                    texto = contenido.decode("utf-8-sig")
                except UnicodeDecodeError:
                    mensaje = "El archivo debe estar guardado en UTF-8."

        if not mensaje:
            if len(texto.encode("utf-8")) > LIMITE_ENTRADA:
                abort(413)
            if texto.strip():
                tokens, errores = analizar(texto)
                if not errores:
                    traduccion, errores_instruccion = interpretar(tokens)
                analizado = True
                try:
                    resultados = preparar_resultados()
                except (ExecutableNotFound, CalledProcessError):
                    mensaje = (
                        "No se pudieron generar los gráficos. Comprueba que Graphviz "
                        "esté instalado y que el comando dot esté disponible en PATH."
                    )
            else:
                mensaje = "Escribe instrucciones o carga un archivo."

    if request.path == "/api/analizar":
        return {
            "html": render_template(
                "resultados.html", tokens=tokens, errores=errores,
                analizado=analizado, resultados=resultados,
                traduccion=traduccion, errores_instruccion=errores_instruccion
            ),
            "mensaje": mensaje,
            "texto": texto,
            "tokens": tokens,
            "errores": errores,
            "traduccion": traduccion, "errores_instruccion": errores_instruccion
        }, 503 if analizado and mensaje else 400 if mensaje else 200

    return render_template(
        "index.html",
        texto=texto,
        tokens=tokens,
        errores=errores,
        mensaje=mensaje,
        analizado=analizado,
        resultados=resultados,
        expresiones=EXPRESIONES, ejemplos=EJEMPLOS, codigos=CODIGOS,
        traduccion=traduccion, errores_instruccion=errores_instruccion
    )


@app.get("/healthz")
def salud():
    return {"status": "ok"}


@app.after_request
def configurar_cache(respuesta):
    if request.endpoint != "static":
        respuesta.headers["Cache-Control"] = "no-store"
    origen = request.headers.get("Origin")
    permitidos = {valor.strip() for valor in os.environ.get("CORS_ORIGINS", "").split(",") if valor.strip()}
    if request.path in ("/api/analizar", "/healthz"):
        respuesta.vary.add("Origin")
        if origen in permitidos:
            respuesta.headers["Access-Control-Allow-Origin"] = origen
            respuesta.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            respuesta.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return respuesta


@app.errorhandler(413)
def archivo_grande(error):
    if request.path == "/api/analizar":
        return {"mensaje": "La entrada supera el máximo de 1 MiB."}, 413
    return "El archivo supera el maximo de 1 MB.", 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))

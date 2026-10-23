
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

EJEMPLO = "Joaquin Esquivez 74839261 25/09/2026 10:30 Cardiologia"


def analizar(texto):
    tokens = []
    errores = []

    # Un registro por línea: los cuatro últimos campos son simples;
    # el prefijo conserva los espacios internos del nombre compuesto.
    for numero, linea in enumerate(texto.splitlines(), start=1):
        partes = list(re.finditer(r"[^\s]+", linea))
        if not partes:
            continue
        if len(partes) < 5:
            errores.append({"linea": numero, "columna": partes[0].start() + 1,
                            "lexema": linea.strip(),
                            "detalle": "Se requieren nombre, DNI, fecha, hora y especialidad."})
            continue
        inicio, fin = partes[0].start(), partes[-5].end()
        campos = [(inicio, linea[inicio:fin])]
        campos.extend((p.start(), p.group()) for p in partes[-4:])
        for (nombre, patron), (columna, lexema) in zip(REGLAS, campos):
            elemento = {"linea": numero, "columna": columna + 1, "lexema": lexema}
            if patron.fullmatch(lexema):
                tokens.append({**elemento, "token": nombre})
            else:
                errores.append({**elemento, "detalle": "No corresponde a " + nombre})

    return tokens, errores


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
            "tabla_visual_afd": preparar_tabla(datos["afd"], False, datos["tabla_afd"])
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
                analizado = True
                try:
                    resultados = preparar_resultados()
                except (ExecutableNotFound, CalledProcessError):
                    mensaje = (
                        "No se pudieron generar los gráficos. Comprueba que Graphviz "
                        "esté instalado y que el comando dot esté disponible en PATH."
                    )
            else:
                mensaje = "Escribe un registro o carga un archivo."

    if request.path == "/api/analizar":
        return {
            "html": render_template(
                "resultados.html", tokens=tokens, errores=errores,
                analizado=analizado, resultados=resultados
            ),
            "mensaje": mensaje,
            "texto": texto,
            "tokens": tokens,
            "errores": errores
        }, 503 if analizado and mensaje else 400 if mensaje else 200

    return render_template(
        "index.html",
        texto=texto,
        tokens=tokens,
        errores=errores,
        mensaje=mensaje,
        analizado=analizado,
        resultados=resultados,
        expresiones=EXPRESIONES, ejemplos=EJEMPLOS
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

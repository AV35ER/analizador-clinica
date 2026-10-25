import shutil
from pathlib import Path

from flask import render_template
from app import app, EJEMPLO, EXPRESIONES, EJEMPLOS, CODIGOS, LIMITE_ENTRADA


def generar(destino=Path("netlify-public")):
    destino.mkdir(parents=True, exist_ok=True)
    with app.test_request_context("/"):
        pagina = render_template(
            "index.html", texto=EJEMPLO, tokens=[], errores=[], mensaje="",
            analizado=False, resultados={}, expresiones=EXPRESIONES, ejemplos=EJEMPLOS,
            modo_estatico=True, codigos=CODIGOS, traduccion=[], errores_instruccion=[],
            configuracion_simulador={"expresiones": EXPRESIONES, "ejemplos": EJEMPLOS,
                                     "codigos": CODIGOS, "limite": LIMITE_ENTRADA}
        )
    (destino / "index.html").write_text(pagina, encoding="utf-8")
    origen = Path(__file__).resolve().parent / "netlify-public"
    for nombre in ("motor.js", "vistas.js", "cliente.js"):
        if (origen / nombre).resolve() != (destino / nombre).resolve():
            shutil.copyfile(origen / nombre, destino / nombre)


if __name__ == "__main__":
    generar()

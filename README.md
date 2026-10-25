# Simulador de instrucciones de movimiento 2D

Proyecto de Teoría de la Computación, etapa 2. Reconoce un minilenguaje, construye autómatas y traduce instrucciones a una secuencia de movimientos en JSON. No controla hardware ni implementa un compilador completo.

## Enfoque y materiales revisados

Se revisaron en el Escritorio `70. 5 Tips proyecto Compiladores.pptx`, `11.4.-Borrador inicial del proyecto_TCOM(1).docx` y las dos copias de `S06 - Avance 01 TEO COMPU`. El PowerPoint distingue recibir/validar datos de interpretar instrucciones con significado; el avance anterior describe registros médicos y no contiene aprobación explícita. El usuario confirmó que no tiene constancia de aprobación y autorizó adaptar el tema. Se reutilizan la web, Flask, TXT, Thompson, subconjuntos, tablas, quíntuplas, gráficos y zoom.

Los significados siguientes son decisiones didácticas del proyecto, no definiciones atribuidas al profesor ni una implementación industrial de G-code. No se añaden gramáticas libres de contexto, análisis LR ni árboles sintácticos de instrucciones. El árbol interno del parser de expresiones regulares solo sirve para construir autómatas.

## Lenguaje

Una instrucción por línea, en mayúsculas, con espacios entre códigos y punto y coma final. Posición inicial (0, 0).

| Instrucción | Significado del proyecto |
| --- | --- |
| `G00 X01 Y20;` | Mover directamente a (1, 20) |
| `G01 X10 Y15 F120;` | Movimiento lineal a (10, 15), velocidad 120 unidades/minuto |
| `G01 X10 Y15;` | Igual, con velocidad predeterminada 100 |
| `G28;` | Regresar a (0, 0), sin parámetros |

No se simula el tiempo físico: se genera una lista de origen, destino, código y velocidad cuando corresponde. Si cualquier línea contiene errores, no se devuelve una ejecución parcial. Ejemplos inválidos: `G02 X01 Y20;` (código desconocido), `G01 Y20 X01;` (orden incorrecto), `G28 X01;` (parámetro sobrante) y `G01 X01 Y20` (sin terminador).

| Token | Expresión regular |
| --- | --- |
| COMANDO | `G(0[01]|28)` |
| COORDENADA_X | `X[0-9]{2}` |
| COORDENADA_Y | `Y[0-9]{2}` |
| VELOCIDAD | `F[1-9][0-9]{0,2}` |
| FIN_INSTRUCCION | `;` |

X e Y admiten 00–99; F admite 1–999, sin ceros iniciales. Es un lenguaje deliberadamente acotado; no admite números negativos, decimales, comentarios o instrucciones fuera del diccionario.

## Ejecutar y verificar

Requisitos: Python 3.11+, el ejecutable [Graphviz](https://graphviz.org/download/) en PATH (`dot -V`) y Node para pruebas JavaScript. El paquete Python graphviz no instala el ejecutable. Docker configura Python 3.13; esta revisión local usa Python 3.14.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe generar_frontend.py
.\.venv\Scripts\python.exe -m unittest discover -v
node --test test_cliente.cjs
.\.venv\Scripts\python.exe app.py
```

Abre `http://127.0.0.1:5000`. Si `py` falla, crea el entorno con `& "RUTA_COMPLETA_PYTHON.exe" -m venv .venv`. No es necesario activar el entorno. Para otro puerto, establece `$env:PORT="5057"` antes de iniciar Flask.

Entrada completa de ejemplo: `G01 X01 Y20 F120;`. El TXT debe ser UTF-8, máximo 1 MiB, y reemplaza el texto escrito. Con Flask iniciado, en otra terminal:

```powershell
.\.venv\Scripts\python.exe verificar_http.py http://127.0.0.1:5000
.\.venv\Scripts\python.exe exportar_avance.py
```

Las pruebas comprueban lexemas válidos/inválidos, formatos de instrucciones, traducción y rechazo atómico, cierre ε, equivalencia AFND/AFD, optimización de `+`, minimización, quince gráficos/tablas/quíntuplas del HTML, API, TXT, límites y caché. `test_paridad.py` compara Python con JavaScript, comprueba los gráficos dinámicos y genera el frontend desde fuentes limpias. Node ejecuta los scripts reales del HTML generado con un DOM simulado y toda llamada de red bloqueada; no sustituye una inspección visual. Genera primero el HTML antes de ejecutar Node por separado. La prueba de Gunicorn requiere Unix y se omite en Windows; las comparaciones entre lenguajes requieren Node y se omiten donde no esté instalado. CI también ejecuta paridad en el host con Node y pruebas Flask en Docker/Linux; ese workflow no se ha ejecutado aquí.

## Componentes

- `automatas.py`: reglas y ejemplos, parser regex, Thompson, subconjuntos, refinamiento de particiones, tablas, quíntuplas y SVG en memoria. La caché evita regenerarlos en cada petición.
- `app.py`: tokenización, reconocimiento directo de tres formatos regulares, traducción didáctica, TXT, API, límites y CORS.
- `templates/`: interfaz compartida; AFND, AFD original y AFD mínimo, con sus tablas, quíntuplas, equivalencias y zoom.
- `generar_frontend.py`: genera HTML y copia los tres scripts necesarios. Inserta únicamente las reglas, ejemplos y límite desde Python; no precalcula resultados ni autómatas.
- `netlify-public/motor.js`: parser regex, Thompson, subconjuntos, minimización, tablas, quíntuplas y simulación en el navegador. `vistas.js` genera HTML y SVG desde esos modelos; `cliente.js` conecta el formulario y lee TXT, sin usar red. Los autómatas se calculan una vez por carga y se reutilizan.
- `exportar_avance.py`: regenera el avance académico y quince SVG en `docs/`. No edita los originales Word del Escritorio.
- `test_*.py`, `test_cliente.cjs`, `verificar_http.py`: pruebas automatizadas y comprobación HTTP real.

El parser regex admite clases positivas/rangos, concatenación, grupos, alternativas, `*`, `+`, `?`, `{n}`, `{m,n}` y `{m,}`. No admite clases negadas, comodines, anclas ni `\d`; los escapes son para signos literales.

Se corrigió `r+`: una copia y un bucle ε sustituyen las dos copias de `r·r*`. El AFD original conserva cada subconjunto AFND; el mínimo agrupa estados AFD equivalentes mediante refinamiento finales/no finales hasta estabilizar sus destinos. No se impone un número de estados ni se elimina un sumidero necesario. Tablas, quíntuplas y SVG proceden del mismo modelo; las columnas solo se agrupan si tienen idénticos destinos en todos los estados. `␠` representa espacio; ε no pertenece a Σ.

## Netlify sin backend

Netlify publica la versión JavaScript: al pulsar Compilar se analiza e interpreta dentro del navegador, sin Render, Flask, CORS ni llamadas de salud. Los SVG se dibujan desde las transiciones calculadas; Graphviz sigue usándose en la versión Python local. Se ha eliminado `config.js`, cuya única función era configurar la API remota. `RENDER_API_URL` ya no se lee, aunque permanezca en el panel de Netlify.

Para revisar la versión estática, con Flask detenido:

```powershell
.\.venv\Scripts\python.exe generar_frontend.py
node --test test_cliente.cjs
.\.venv\Scripts\python.exe -m http.server 8080 --bind 127.0.0.1 --directory netlify-public
```

Abre `http://127.0.0.1:8080`. La primera carga necesita obtener HTML y scripts; después, compilar y cargar TXT no requiere red. No se añade un service worker: abrir de nuevo la URL sin conexión no está garantizado.

Cuando autorices publicar:

1. Incluye las fuentes, plantillas, tres scripts de `netlify-public/`, pruebas, documentación, dependencias y configuraciones en GitHub. No incluyas `.venv`, `.env`, cachés, claves ni `index.html` generado; el build lo crea.
2. En el proyecto Netlify existente usa la raíz del repositorio como base, comando `python generar_frontend.py`, carpeta publicada `netlify-public` y `PYTHON_VERSION=3.13`, tal como indica `netlify.toml`. No necesitas configurar una API. Elimina la variable obsoleta `RENDER_API_URL` para evitar confusión.
3. Tras subir los cambios con tu autorización, ejecuta un nuevo deploy. Comprueba el log de build y que publique `index.html`, `motor.js`, `vistas.js` y `cliente.js`. Netlify instala `requirements.txt`; el ejecutable Graphviz no es necesario para este build. Véase [dependencias Python](https://docs.netlify.com/build/configure-builds/manage-dependencies/) y [configuración por archivo](https://docs.netlify.com/build/configure-builds/file-based-configuration/).
4. Abre `https://clinicateo.netlify.app/` y recarga sin caché. En DevTools → Network comprueba los cuatro recursos con respuesta 200 y Console sin errores. Compila `G01 X01 Y20 F120;`: cinco tokens, posición final (1, 20), velocidad 120 y quince vistas. Al compilar no debe aparecer ninguna petición a Render, `/healthz` o `/api/analizar`.
5. Con la página ya cargada, selecciona Offline en Network y compila `G28;`, un programa multilínea, uno inválido y un TXT. Deben seguir funcionando los cinco selectores, tres tipos, tablas, quíntuplas y zoom. Repite el recorrido de `docs/verificacion-etapa-2.md`.

El dominio publicado sigue sin verificarse con esta versión: no se ha hecho commit, push ni despliegue. Las pruebas locales no demuestran que el sitio remoto esté actualizado.

## Flask y Render opcional

Python/Flask conserva sus rutas y algoritmos. Render puede seguir ofreciendo esa versión independiente, pero la página estática no la consulta ni la usa como alternativa. No es necesario desplegar Render para publicar Netlify.

Si decides mantenerlo, `render.yaml` y Dockerfile conservan Graphviz, dependencias, pruebas y arranque `gunicorn --config gunicorn.conf.py app:app` sin privilegios. Gunicorn escucha `0.0.0.0:$PORT` (10000 por defecto), precalienta los gráficos y expone `/healthz`. `CORS_ORIGINS` solo afecta a consumidores directos de la API Flask. Docker/Gunicorn/Linux y el servicio remoto requieren su propia verificación.

## Documentación y pendientes

El [avance editable](docs/avance-etapa-2.md) contiene los resultados reales para la etapa 2. El [recorrido manual](docs/verificacion-etapa-2.md) permite comprobar las vistas y controles. Los originales Word y la plantilla encontrados en el Escritorio se conservan sin cambios: falta incorporar los apartados 4–9 preservando su estructura y revisar su renderizado. El avance médico anterior también debe revisarse en coherencia con el nuevo enfoque; no se presenta como un informe ya actualizado del simulador.

Pendientes: revisión visual en navegador (la herramienta no pudo identificar con confianza la URL de Brave ni Chrome en Windows), integración Word con verificación de páginas, Linux/Docker/Gunicorn y compilación en el dominio público después del despliegue autorizado. `.gitignore` excluye `.venv/`, cachés, `.env`, claves, temporales, `.ai/` e `index.html` generado. Revisa `git status` y `git diff`; incluye los archivos nuevos de documentación/pruebas, sin secretos.

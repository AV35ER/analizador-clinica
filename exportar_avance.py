"""Exporta resultados reales de etapa 2 para incorporarlos al Word original."""
from pathlib import Path

from app import EJEMPLO, CODIGOS, preparar_tabla
from automatas import EXPRESIONES, generar_todos


def exportar():
    carpeta = Path('docs')
    figuras = carpeta / 'figuras'
    figuras.mkdir(parents=True, exist_ok=True)
    lineas = [
        '# Avance verificado de la etapa 2: simulador de movimiento 2D', '',
        'Material para incorporar al Word original. No sustituye su estructura ni presume revisar los documentos académicos ausentes.', '',
        '## Alcance implementado', '',
        'El PowerPoint de clase requiere instrucciones con significado. El avance anterior describia registros medicos y no contiene aprobacion explicita. El proyecto se adapta a un minilenguaje didactico de movimiento 2D. Los significados de G00, G01 y G28 son decisiones del proyecto, no una norma ni una atribucion al docente.', '',
        'El parser produce un árbol de alternativas, concatenaciones, repeticiones y símbolos. Thompson genera los fragmentos con estados independientes y transiciones ε. La conversión calcula el cierre ε inicial y, por cada símbolo de Σ, el cierre ε del movimiento desde cada subconjunto. Un subconjunto es final si contiene algún estado final del AFND. El subconjunto vacío se conserva como sumidero. Se conserva el AFD original y se obtiene un AFD mínimo por refinamiento de particiones, sin cambiar su lenguaje.', '',
        'El gráfico, la quíntupla y la tabla se obtienen del mismo autómata. Las columnas agrupan caracteres solo si coinciden sus destinos en todos los estados; las aristas agrupan etiquetas por origen y destino. ␠ representa espacio literal.', '',
        '## Entrada y limitaciones conservadas', '',
        '`' + EJEMPLO + '`', '',
        'Una instruccion por linea terminada en punto y coma. G00 Xnn Ynn; mueve directamente. G01 Xnn Ynn Fv; mueve en linea recta; F es opcional y vale 100 por defecto. G28; vuelve al origen. X e Y van de 00 a 99; F de 1 a 999. El programa se traduce a JSON con posiciones de origen/destino y velocidad. Si hay un error no se devuelve una ejecucion parcial. No controla hardware ni implementa analisis LR.', '',
        '## Diccionario de codigos', '',
        *['- ' + codigo + ': ' + significado for codigo, significado in CODIGOS.items()], '',
        '## Resultados generados', ''
    ]
    for nombre, datos in generar_todos().items():
        lineas += ['### ' + nombre, '', '`' + EXPRESIONES[nombre] + '`', '',
                   'Ejemplos válidos: ' + '; '.join('`' + x + '`' for x in datos['ejemplos'][0]) + '.', '',
                   'Ejemplos inválidos: ' + '; '.join('`' + x + '`' for x in datos['ejemplos'][1]) + '.', '']
        for tipo in ('afnd', 'afd', 'afd_minimo'):
            titulo = 'AFD mínimo' if tipo == 'afd_minimo' else tipo.upper()
            automata = datos[tipo]
            quint = datos['quintupla_' + tipo]
            archivo = nombre.lower() + '-' + tipo + '.svg'
            (figuras / archivo).write_text(datos['imagen_' + tipo].replace('\r\n', '\n'), encoding='utf-8', newline='\n')
            lineas += ['#### ' + titulo, '',
                       '![' + nombre + ' ' + titulo + '](figuras/' + archivo + ')', '',
                       'M = (Q, Σ, δ, q₀, F)', '',
                       '- Q = {' + ', '.join(quint['Q']) + '}',
                       '- Σ = {' + ', '.join('␠' if c == ' ' else c for c in quint['Sigma']) + '}',
                       '- q₀ = ' + quint['q0'],
                       '- F = {' + ', '.join(quint['F']) + '}',
                       '- δ: tabla siguiente; ε no pertenece a Σ.', '']
            tabla = preparar_tabla(automata, tipo == 'afnd')
            encabezado = ['Estado'] + tabla['alfabeto']
            lineas += ['| ' + ' | '.join(encabezado) + ' |', '| ' + ' | '.join(['---'] * len(encabezado)) + ' |']
            for fila in tabla['filas']:
                marca = ('→' if fila['inicial'] else '') + ('*' if fila['final'] else '')
                lineas.append('| ' + ' | '.join([marca + fila['estado']] + [fila['destinos'][c] for c in tabla['alfabeto']]) + ' |')
            lineas += ['', '→ inicial; * aceptación; ∅ sin destinos.', '']
            if tipo != 'afnd':
                lineas += ['Estados AFD agrupados:' if tipo == 'afd_minimo' else 'Subconjuntos del AFND:', '']
                lineas += ['- ' + e + ' = {' + ', '.join(conjunto) + '}' for e, conjunto in automata['equivalencias'].items()]
                lineas += ['']
    lineas += ['## Validación reproducible', '',
               'Ejecutar primero `python generar_frontend.py`, después `python -m unittest discover -v`, `node --test test_cliente.cjs` y, con Flask iniciado, `python verificar_http.py http://127.0.0.1:5000`. Las pruebas comparan lexemas con las expresiones originales, recorren todos los subconjuntos alcanzables y comprueban tablas, quíntuplas, SVG, API, TXT, límites y CORS. `test_paridad.py` compara los modelos Python/JavaScript y ejecuta un build limpio sin backend. La comprobación de Gunicorn se omite en Windows y debe ejecutarse en Linux/Docker.', '',
               'Los dominios remotos son conocidos, pero sigue pendiente aplicar la configuracion y comprobar una compilacion desde Netlify. Los documentos originales se localizaron en el Escritorio y se revisaron; no se han modificado. Este material contiene resultados editables para incorporarlos a la etapa 2.', '']
    (carpeta / 'avance-etapa-2.md').write_text('\n'.join(lineas), encoding='utf-8')


if __name__ == '__main__':
    exportar()

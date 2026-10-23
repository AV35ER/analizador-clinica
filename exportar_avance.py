"""Exporta resultados reales de etapa 2 para incorporarlos al Word original."""
from pathlib import Path

from app import EJEMPLO, preparar_tabla
from automatas import EXPRESIONES, generar_todos


def exportar():
    carpeta = Path('docs')
    figuras = carpeta / 'figuras'
    figuras.mkdir(parents=True, exist_ok=True)
    lineas = [
        '# Avance verificado de la etapa 2: citas médicas', '',
        'Material para incorporar al Word original. No sustituye su estructura ni presume revisar los documentos académicos ausentes.', '',
        '## Alcance implementado', '',
        'Se conservaron Flask, Graphviz, la conversión por subconjuntos, el cliente y el despliegue. Se amplió el parser de expresiones regulares y se adaptaron los cinco tokens al registro de citas médicas.', '',
        'El parser produce un árbol de alternativas, concatenaciones, repeticiones y símbolos. Thompson genera los fragmentos con estados independientes y transiciones ε. La conversión calcula el cierre ε inicial y, por cada símbolo de Σ, el cierre ε del movimiento desde cada subconjunto. Un subconjunto es final si contiene algún estado final del AFND. El subconjunto vacío se conserva como sumidero. No se aplica minimización.', '',
        'El gráfico, la quíntupla y la tabla se obtienen del mismo autómata. Las columnas agrupan caracteres solo si coinciden sus destinos en todos los estados; las aristas agrupan etiquetas por origen y destino. ␠ representa espacio literal.', '',
        '## Entrada y limitaciones conservadas', '',
        '`' + EJEMPLO + '`', '',
        'Un registro por línea. Los cuatro últimos campos son DNI, fecha, hora y especialidad; el prefijo completo es el nombre. Se informa línea, columna y campo inválido. Se conservan las expresiones originales: letras ASCII sin tildes ni ñ y especialidad de una palabra. FECHA reconoce formato y rangos básicos; 31/02/2026 es un lexema reconocido aunque no exista en el calendario. No se comprueban identidad, disponibilidad ni citas reales. La gramática sintáctica completa de la etapa 3 queda pendiente.', '',
        '## Resultados generados', ''
    ]
    for nombre, datos in generar_todos().items():
        lineas += ['### ' + nombre, '', '`' + EXPRESIONES[nombre] + '`', '',
                   'Ejemplos válidos: ' + '; '.join('`' + x + '`' for x in datos['ejemplos'][0]) + '.', '',
                   'Ejemplos inválidos: ' + '; '.join('`' + x + '`' for x in datos['ejemplos'][1]) + '.', '']
        for tipo in ('afnd', 'afd'):
            automata = datos[tipo]
            quint = datos['quintupla_' + tipo]
            archivo = nombre.lower() + '-' + tipo + '.svg'
            (figuras / archivo).write_text(datos['imagen_' + tipo], encoding='utf-8')
            lineas += ['#### ' + tipo.upper(), '',
                       '![' + nombre + ' ' + tipo.upper() + '](figuras/' + archivo + ')', '',
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
            if tipo == 'afd':
                lineas += ['Subconjuntos del AFND:', '']
                lineas += ['- ' + e + ' = {' + ', '.join(conjunto) + '}' for e, conjunto in automata['equivalencias'].items()]
                lineas += ['']
    lineas += ['## Validación reproducible', '',
               'Ejecutar `python -m unittest discover -v`, `node --test test_cliente.cjs` y, con Flask iniciado, `python verificar_http.py http://127.0.0.1:5000`. Las pruebas comparan lexemas con las expresiones originales, recorren todos los subconjuntos alcanzables y comprueban tablas, quíntuplas, SVG, API, TXT, límites y CORS. La comprobación de Gunicorn se omite en Windows y debe ejecutarse en Linux/Docker.', '',
               'La publicación remota y la edición de los dos Word originales siguen pendientes: no se dispone aquí de sus cuentas/dominios ni de esos documentos.', '']
    (carpeta / 'avance-etapa-2.md').write_text('\n'.join(lineas), encoding='utf-8')


if __name__ == '__main__':
    exportar()

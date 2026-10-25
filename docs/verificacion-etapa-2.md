# Comprobacion manual del simulador 2D

Las casillas son tareas de revision visual, no resultados ejecutados. Consulta README para instalacion y despliegue.

## Entrada y traduccion

- [ ] Compilar `G01 X01 Y20 F120;`: cinco tokens, sin errores; JSON de (0,0) a (1,20), velocidad 120.
- [ ] Compilar `G00 X02 Y03;`, `G01 X10 Y15;` y `G28;` en tres lineas: el segundo movimiento parte de (2,3), usa velocidad 100 y el tercero termina en (0,0).
- [ ] `G02 X01 Y20;` produce error lexico; `G01 Y20 X01;`, `G28 X01;` y `G01 X01 Y20` producen error de formato. No se simula un programa parcial.
- [ ] Cargar TXT UTF-8 multilinea: reemplaza el texto; conserva numeros de linea y columnas. Comprobar errores de extension, codificacion y tamano superior a 1 MiB.

## Quince vistas

- [ ] Seleccionar cada token y alternar AFND, AFD y AFD minimo. Cambian juntos grafico, quintupla y tabla.
- [ ] En AFD, revisar los subconjuntos AFND; en minimo, los bloques de estados AFD originales. No confundir ambas correspondencias.
- [ ] Verificar flecha inicial, dobles circulos finales, epsilon solo en AFND y coincidencia de todas las celdas de la tabla con las flechas.
- [ ] Acercar, alejar y restablecer cada grafico; probar desplazamiento horizontal/vertical y tablas en pantalla estrecha.
- [ ] Revisar navegacion con Tab/Enter y ausencia de errores en Console.

| Token | AFND cantidad / inicial / finales | AFD cantidad / inicial / finales | Minimo cantidad / inicial / finales |
| --- | --- | --- | --- |
| COMANDO | 12 / q0 / q3 | 7 / D0 / D5, D6 | 6 / M0 / M5 |
| COORDENADA_X | 6 / q0 / q5 | 5 / D0 / D4 | 5 / M0 / M4 |
| COORDENADA_Y | 6 / q0 / q5 | 5 / D0 / D4 | 5 / M0 / M4 |
| VELOCIDAD | 12 / q0 / q11 | 6 / D0 / D3, D4, D5 | 6 / M0 / M3, M4, M5 |
| FIN_INSTRUCCION | 2 / q0 / q1 | 3 / D0 / D1 | 3 / M0 / M1 |

## Frontend estatico

- [ ] Generar con `python generar_frontend.py` y servir `netlify-public` en 8080 siguiendo README, con Flask detenido.
- [ ] En Network, comprobar respuestas 200 de index.html, motor.js, vistas.js y cliente.js. No hay config.js ni API obligatoria.
- [ ] Repetir traduccion, TXT, seleccion de las quince vistas y zoom tras insertar resultados por JavaScript.
- [ ] Con la página cargada, activar Offline en DevTools y repetir compilación válida, inválida, TXT y zoom: deben funcionar sin esperar a Render.
- [ ] Comprobar que Compilar no genera peticiones a Render, /healthz o /api/analizar. Los errores deben permitir corregir la entrada y volver a compilar.
- [ ] Repetir desde el dominio Netlify real cuando se autorice el despliegue; una prueba local no verifica el dominio publicado.

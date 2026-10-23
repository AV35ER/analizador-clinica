# Comprobación manual de la interfaz

Las pruebas automatizadas y las instrucciones de instalación/publicación están en el [README](../README.md). Este documento conserva el recorrido manual y sus resultados esperados. Las casillas pendientes no afirman una inspección visual en navegador.

## Procedimiento manual de la página local

Sigue la instalación del README, inicia `.\.venv\Scripts\python.exe app.py` y abre `http://127.0.0.1:5000`. Usa los ejemplos académicos siguientes, sin datos reales de pacientes. Marca estas casillas solo después de comprobarlas en tu navegador.

- [ ] La página abre sin errores de consola y muestra clínica privada, explicación del proyecto, las cinco reglas y ejemplos. Comprueba tildes, ε, Σ, ∅ y los controles; no debe aparecer el lenguaje anterior de biblioteca.
- [ ] Pulsa **Compilar** con `Joaquin Esquivez 74839261 25/09/2026 10:30 Cardiologia`. Debe haber cinco tokens, cero errores y nombre compuesto en una sola fila. DNI empieza en columna 18.
- [ ] Pulsa cada uno de los cinco botones de token. Se activa únicamente el panel correspondiente y su regla coincide literalmente con la tabla siguiente.
- [ ] En cada token alterna **AFND → AFD → AFND**. Cambian juntos gráfico, quíntupla y tabla. Los subconjuntos se muestran solo para AFD. Al regresar a un token, su selección y representación deben ser coherentes.

| Token | Expresión exacta |
| --- | --- |
| NOMBRE_PACIENTE | `[A-Za-z]+( [A-Za-z]+)+` |
| DNI | `[0-9]{8}` |
| FECHA | `(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/[0-9]{4}` |
| HORA | `([01][0-9]|2[0-3]):[0-5][0-9]` |
| ESPECIALIDAD | `[A-Za-z]+` |

Repite las siguientes comprobaciones para **las diez vistas**, no únicamente para DNI:

- [ ] La cantidad de estados y los identificadores iniciales/finales coinciden con la tabla inferior. La flecha sin origen señala el inicial; cada final tiene doble círculo.
- [ ] La quíntupla contiene exactamente los estados del gráfico; Σ excluye ε. En NOMBRE_PACIENTE existe además un espacio literal en Σ, que puede verse como un hueco al estar unido con comas. En etiquetas y tablas se representa como `␠`.
- [ ] Para cada fila y columna de la tabla, comprueba las flechas equivalentes. Una celda puede representar varios caracteres; todos deben tener los mismos destinos. En AFND puede haber ε y varios destinos; en AFD hay un destino por símbolo de Σ y no hay ε.
- [ ] Comprueba los subconjuntos vacíos indicados: son estados sumidero reales. ESPECIALIDAD no necesita sumidero dentro de su alfabeto de letras; un carácter externo a Σ se rechaza sin transición.
- [ ] Pulsa **Acercar**, **Alejar** y **Restablecer**. Cambia el tamaño del SVG; restablecer recupera el tamaño inicial y lleva las barras de desplazamiento al origen. Desplázate horizontal y verticalmente cuando el gráfico exceda su contenedor. El desplazamiento disponible usa las barras del contenedor; no se promete arrastre para mover el lienzo.
- [ ] Revisa flechas, textos y círculos al ampliar. Ningún gráfico debe estar vacío. Comprueba lectura en escritorio y ventana estrecha; las tablas deben permitir desplazamiento horizontal y los botones seguir accesibles.

Los identificadores siguientes corresponden al algoritmo actual, sin minimización:

| Token | AFND: cantidad / inicial / finales | AFD: cantidad / inicial / finales | Sumidero AFD |
| --- | --- | --- | --- |
| NOMBRE_PACIENTE | 24 / q0 / q23 | 10 / D0 / D5, D7, D8, D9 | D1 |
| DNI | 16 / q0 / q15 | 10 / D0 / D8 | D9 |
| FECHA | 36 / q0 / q35 | 18 / D0 / D17 | D1 |
| HORA | 16 / q0 / q15 | 9 / D0 / D8 | D3 |
| ESPECIALIDAD | 6 / q0 / q5 | 3 / D0 / D1, D2 | No necesario en Σ |

Ejemplo concreto para contrastar gráfico y tabla: en AFND de DNI, `q0 --[0-9]→ q1 --ε→ q2`; la fila q0 debe mandar todos los dígitos a q1 y la fila q1 debe mandar ε a q2. En AFD de DNI, ocho dígitos recorren D0 hasta D8; un noveno lleva a D9, que conserva todos los dígitos en D9.

## Casos de entrada y errores desde la interfaz

En cada caso parte del registro válido anterior, cambia **solo** el campo indicado y pulsa Compilar:

| Caso | Sustitución | Resultado esperado |
| --- | --- | --- |
| Nombre válido compuesto | `Maria Lopez` | Cinco tokens, sin errores |
| Nombre incompleto | `Joaquin` | Error NOMBRE_PACIENTE; cuatro tokens |
| Nombre con tilde | `José Esquivez` | Error NOMBRE_PACIENTE; cuatro tokens |
| DNI inválido | `7483926` | Error DNI; cuatro tokens |
| Fecha inválida | `25/13/2026` | Error FECHA; cuatro tokens |
| Hora inválida | `24:00` | Error HORA; cuatro tokens |
| Especialidad inválida | `Cardiología` | Error ESPECIALIDAD; cuatro tokens |
| Fecha inexistente pero reconocida | `31/02/2026` | Cinco tokens, sin error léxico: limitación de la regla original |

- [ ] Verifica todos los casos de la tabla. La interfaz muestra línea, columna, lexema y campo incorrecto. Los cinco autómatas siguen consultables aunque haya errores.
- [ ] Con `???` debe aparecer error de campos insuficientes y ningún token reconocido; los autómatas siguen disponibles. Con texto vacío debe pedirse entrada y no anunciar análisis correcto.
- [ ] Crea un TXT UTF-8 con dos registros válidos, uno por línea. Selecciónalo y compila: diez tokens con líneas 1 y 2. El archivo reemplaza al texto del formulario. Después limpia la selección del archivo para volver a probar el textarea.
- [ ] Prueba TXT con bytes no UTF-8: debe avisar sobre UTF-8. Un archivo con otra extensión debe rechazarse si el selector permite elegirlo. Un archivo mayor de 1 MiB se rechaza; en Flask local el límite puede mostrarse como respuesta HTTP 413, sin la presentación dinámica de Netlify.
- [ ] Prueba la navegación por teclado con Tab y Enter, y revisa que no haya errores JavaScript al cambiar token o autómata.

## Procedimiento manual del frontend estático

Este recorrido comprueba el flujo que usará Netlify. El modo Flask local anterior no carga `cliente.js` ni utiliza espera/cancelación.

1. Detén Flask con Ctrl+C. En esa terminal configura `$env:CORS_ORIGINS="http://127.0.0.1:8080"` y vuelve a iniciar Flask.
2. En otra terminal ejecuta `.\.venv\Scripts\python.exe generar_frontend.py` y `.\.venv\Scripts\python.exe -m http.server 8080 --directory netlify-public`.
3. Para esta prueba guarda una copia del contenido de `netlify-public/config.js` y cambia temporalmente su contenido por `window.CLINICA_API = "http://127.0.0.1:5000";`. No publiques esa dirección local.
4. Abre exactamente `http://127.0.0.1:8080`, recarga y abre las herramientas de desarrollo, pestañas Console y Network.

- [ ] La página estática abre incluso con Flask detenido; no solicita `/healthz` hasta pulsar Compilar.
- [ ] Con Flask iniciado, Compilar produce `/healthz` y después un POST `/api/analizar`; aparece el mismo resultado de cinco tokens y diez vistas. No hay error de CORS ni peticiones Flask al puerto 8080.
- [ ] Repite selección de tokens, AFND/AFD, zoom, tablas y TXT en esta página, porque los resultados se insertan dinámicamente.
- [ ] Detén Flask y pulsa Compilar. Aparece la espera, Compilar queda deshabilitado y **Cancelar espera** queda disponible. Cancela: se conserva texto/archivo y Compilar vuelve a habilitarse.
- [ ] Reintenta sin Flask: al agotarse la espera debe mostrarse el error y conservarse la entrada. Inicia Flask y vuelve a compilar: debe recuperarse. Comprueba en Network que, una vez cancelado o terminado, no se inicia sondeo periódico en reposo.
- [ ] Restaura el contenido original de `config.js`, detén ambos servidores y revisa `git diff -- netlify-public/config.js` para no subir la URL de prueba.

## Publicación

Completa los recorridos local y estático antes de verificar las mismas funciones en el dominio público. Sigue la lista de publicación del README; la existencia de Docker y del workflow no acredita su ejecución ni un despliegue real.

(function (global) {
    "use strict";
    const motor = typeof module !== "undefined" && module.exports ? require("./motor.js") : global.Motor2D;
    const e = motor.escapar;
    const tipos = {afnd: "AFND", afd: "AFD", afd_minimo: "AFD mínimo"};
    const celdas = (valores, etiqueta = "td") => valores.map(v => `<${etiqueta}>${e(v)}</${etiqueta}>`).join("");
    const tablaHTML = (cabecera, filas) => `<div class="tabla-contenedor"><table><thead><tr>${celdas(cabecera, "th")}</tr></thead><tbody>${filas.map(f => `<tr>${celdas(f)}</tr>`).join("")}</tbody></table></div>`;

    function dibujar(a, id) {
        // Capas por distancia desde el inicio; se conservan todas las aristas.
        const niveles = new Map([[a.inicial, 0]]), pendientes = [a.inicial];
        for (let i = 0; i < pendientes.length; i++) {
            for (const t of a.transiciones) if (t.origen === pendientes[i] && !niveles.has(t.destino)) {
                niveles.set(t.destino, niveles.get(t.origen) + 1); pendientes.push(t.destino);
            }
        }
        const capas = new Map();
        for (const estado of a.estados) {
            const nivel = niveles.get(estado) || 0;
            if (!capas.has(nivel)) capas.set(nivel, []);
            capas.get(nivel).push(estado);
        }
        const alto = Math.max(260, Math.max(...[...capas.values()].map(g => g.length)) * 150 + 120);
        const ancho = Math.max(360, capas.size * 190 + 80), puntos = new Map();
        for (const [nivel, grupo] of capas) grupo.forEach((estado, i) => puntos.set(estado, [80 + nivel * 190, (i + 1) * alto / (grupo.length + 1)]));
        const grupos = new Map();
        for (const t of a.transiciones) {
            const clave = JSON.stringify([t.origen, t.destino]);
            if (!grupos.has(clave)) grupos.set(clave, []);
            grupos.get(clave).push(t.simbolo);
        }
        let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${ancho} ${alto}" width="${ancho}" height="${alto}" role="img" aria-label="Autómata ${e(id)}"><defs><marker id="flecha-${e(id)}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 Z" fill="#444"/></marker></defs>`;
        const flecha = `fill="none" stroke="#444" stroke-width="1.2" marker-end="url(#flecha-${e(id)})"`;
        const [ix, iy] = puntos.get(a.inicial);
        svg += `<path d="M${ix - 60} ${iy} H${ix - 25}" ${flecha}/>`;
        for (const [clave, simbolos] of grupos) {
            const [origen, destino] = JSON.parse(clave), [x1, y1] = puntos.get(origen), [x2, y2] = puntos.get(destino);
            let camino, tx, ty;
            if (origen === destino) {
                camino = `M${x1 - 15} ${y1 - 20} C${x1 - 80} ${y1 - 100} ${x1 + 80} ${y1 - 100} ${x1 + 15} ${y1 - 20}`;
                tx = x1; ty = y1 - 80;
            } else {
                const dx = x2 - x1, dy = y2 - y1, distancia = Math.hypot(dx, dy);
                const curva = 30 + Math.min(45, Math.abs(dx) / 10);
                const cx = (x1 + x2) / 2 - dy / distancia * curva, cy = (y1 + y2) / 2 + dx / distancia * curva;
                const d1 = Math.hypot(cx - x1, cy - y1), d2 = Math.hypot(cx - x2, cy - y2);
                camino = `M${x1 + (cx - x1) / d1 * 25} ${y1 + (cy - y1) / d1 * 25} Q${cx} ${cy} ${x2 + (cx - x2) / d2 * 25} ${y2 + (cy - y2) / d2 * 25}`;
                tx = (x1 + 2 * cx + x2) / 4; ty = (y1 + 2 * cy + y2) / 4 - 8;
            }
            const etiqueta = motor.etiqueta(simbolos);
            svg += `<g class="arista" data-origen="${e(origen)}" data-destino="${e(destino)}" data-simbolos="${e(JSON.stringify(simbolos))}"><title>${e(origen)} → ${e(destino)}: ${e(etiqueta)}</title><path d="${camino}" ${flecha}/><text x="${tx}" y="${ty}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" stroke="white" stroke-width="4" paint-order="stroke" fill="#222">${e(etiqueta)}</text></g>`;
        }
        for (const estado of a.estados) {
            const [x, y] = puntos.get(estado), final = a.finales.includes(estado);
            svg += `<g class="estado" data-estado="${e(estado)}" data-inicial="${estado === a.inicial}" data-final="${final}"><circle cx="${x}" cy="${y}" r="24" fill="white" stroke="#333"/>${final ? `<circle cx="${x}" cy="${y}" r="20" fill="none" stroke="#333"/>` : ""}<text x="${x}" y="${y + 5}" text-anchor="middle" font-family="Arial, sans-serif" font-size="14">${e(estado)}</text></g>`;
        }
        return svg + "</svg>";
    }

    function panelAutomata(nombre, tipo, datos) {
        const a = datos[tipo], q = datos["quintupla_" + tipo], tabla = datos["tabla_visual_" + tipo];
        const id = "grafico-" + nombre + "-" + tipo;
        let html = `<div class="panel panel-automata" data-tipo="${tipo}" ${tipo !== "afnd" ? "hidden" : ""}><h3>${tipos[tipo]}</h3><p>M = (Q, Σ, δ, q₀, F)</p><div class="controles"><button type="button" onclick="cambiarZoom('${id}', 1.25)">Acercar +</button><button type="button" onclick="cambiarZoom('${id}', 0.8)">Alejar −</button><button type="button" onclick="reiniciarZoom('${id}')">Restablecer</button></div><div class="grafico" id="${id}">${dibujar(a, id)}</div><h3>Quíntupla</h3><div class="quintupla"><strong>Q</strong><div>${e(q.Q.join(", "))}</div><strong>Σ</strong><div>${e(q.Sigma.join(", "))}</div><strong>δ</strong><div>Ver tabla de transiciones.</div><strong>q₀</strong><div>${e(q.q0)}</div><strong>F</strong><div>${e(q.F.join(", "))}</div></div>`;
        if (tipo !== "afnd") {
            html += `<h3>${tipo === "afd" ? "Estados equivalentes del AFND" : "Estados del AFD agrupados"}</h3>`;
            html += tablaHTML([tipos[tipo], tipo === "afd" ? "Conjunto de estados AFND" : "Estados AFD originales"], Object.entries(a.equivalencias).map(([estado, conjunto]) => [estado, conjunto.join(", ") || "∅ (sumidero)"]));
        }
        html += `<h3>Tabla de transiciones</h3><div class="transiciones">${tablaHTML(["Estado", ...tabla.alfabeto], tabla.filas.map(f => [(f.inicial ? "→" : "") + (f.final ? "*" : "") + f.estado, ...tabla.alfabeto.map(s => f.destinos[s])]))}</div><p class="nota">→ Inicial. * Aceptación. ∅ Sin transición. ␠ Espacio. Los símbolos agrupados comparten destinos. El subconjunto vacío del AFD es el sumidero.</p></div>`;
        return html;
    }
    function renderizar(resultado, automatas) {
        const {tokens, errores, traduccion, errores_instruccion} = resultado;
        let html = "<section><h2>Resultado del análisis léxico</h2>";
        if (tokens.length) html += tablaHTML(["Línea", "Columna", "Lexema", "Token"], tokens.map(t => [t.linea, t.columna, t.lexema, t.token]));
        if (errores.length) html += '<h3 class="error">Errores léxicos</h3>' + errores.map(t => `<p>Línea ${t.linea}, columna ${t.columna}: <strong>${e(t.lexema)}</strong> ${e(t.detalle)}</p>`).join("");
        else html += '<p class="correcto">Análisis léxico completado sin errores.</p>';
        if (!tokens.length) html += "<p>No se reconocieron tokens válidos.</p>";
        html += "</section><section><h2>Traducción del programa</h2>";
        if (errores.length || errores_instruccion.length) html += '<p class="error">No se simula el programa mientras existan errores.</p>' + errores_instruccion.map(t => `<p>Línea ${t.linea}: ${e(t.detalle)}</p>`).join("");
        else if (traduccion.length) html += `<p>Posición inicial (0, 0). Resultado en JSON:</p><pre style="overflow-x:auto">${e(JSON.stringify(traduccion, null, 2))}</pre><p>Posición final: (${traduccion.at(-1).hasta.join(", ")}).</p>`;
        html += '</section><section><h2>Generación de autómatas</h2><p>Selecciona un token y el tipo de autómata para consultar su gráfico, quíntupla y tabla de transiciones.</p><div class="selector">';
        for (const nombre of Object.keys(automatas)) html += `<button type="button" class="boton-token" data-token="${nombre}" onclick="seleccionarToken('${nombre}')">${nombre}</button>`;
        html += "</div>";
        for (const [nombre, datos] of Object.entries(automatas)) {
            html += `<div class="panel-token" id="token-${nombre}"><div class="panel"><h3>${nombre}</h3><p><strong>Expresión regular:</strong> <code>${e(datos.expresion)}</code></p><p>${Object.entries(tipos).map(([t, titulo]) => `<span class="etiqueta">${titulo}: ${datos[t].estados.length} estados</span>`).join(" ")}</p></div><p>Válidos: ${e(datos.ejemplos[0].join(" / "))}. Inválidos: ${e(datos.ejemplos[1].join(" / "))}.</p><label>Autómata <select onchange="seleccionarTipo('${nombre}', this.value)">${Object.entries(tipos).map(([t, titulo]) => `<option value="${t}">${titulo}</option>`).join("")}</select></label>`;
            for (const tipo of Object.keys(tipos)) html += panelAutomata(nombre, tipo, datos);
            html += "</div>";
        }
        return html + "</section>";
    }
    const vistas = {dibujar, renderizar};
    if (typeof module !== "undefined" && module.exports) module.exports = vistas;
    else global.Vistas2D = vistas;
})(globalThis);

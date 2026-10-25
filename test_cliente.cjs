const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const {test} = require("node:test");
const motor = require("./netlify-public/motor.js");
const vistas = require("./netlify-public/vistas.js");
const carpeta = path.resolve("netlify-public");
const pagina = fs.readFileSync(path.join(carpeta, "index.html"), "utf8");
const config = JSON.parse(pagina.match(/<script id="lenguaje-config" type="application\/json">([\s\S]*?)<\/script>/)[1]);
const automatas = motor.generarTodos(config);

function clases() {
    const valores = new Set();
    return {add: v => valores.add(v), remove: v => valores.delete(v), contains: v => valores.has(v)};
}

// DOM acotado a los controles existentes. Se ejecutan los scripts reales del build.
function entorno() {
    const eventos = {}, boton = {disabled: false}, estado = {};
    const entrada = {texto: pagina.match(/<textarea[^>]*>([\s\S]*?)<\/textarea>/)[1], archivo: null};
    let graficos = [], botones = [], paneles = [], html = "", peticiones = 0;
    const texto = {get value() {return entrada.texto;}, set value(v) {entrada.texto = v;}};
    const resultados = {
        get innerHTML() {return html;},
        set innerHTML(v) {
            html = v;
            graficos = [...v.matchAll(/class="grafico" id="([^"]+)"[^>]*><svg[^>]*viewBox="0 0 ([\d.]+) ([\d.]+)"/g)].map(m => {
                const imagen = {dataset: {}, style: {}, viewBox: {baseVal: {width: Number(m[2]), height: Number(m[3])}}};
                return {id: m[1], scrollLeft: 0, scrollTop: 0, querySelector: () => imagen};
            });
            botones = [...v.matchAll(/class="boton-token" data-token="([^"]+)"/g)].map(m => ({dataset: {token: m[1]}, classList: clases()}));
            paneles = [...v.matchAll(/class="panel-token" id="([^"]+)"/g)].map(m => ({id: m[1], classList: clases(), automatas: ["afnd", "afd", "afd_minimo"].map(tipo => ({dataset: {tipo}, hidden: tipo !== "afnd"}))}));
        }
    };
    const formulario = {querySelector: () => boton, addEventListener: (nombre, fn) => eventos[nombre] = fn};
    const document = {
        getElementById(id) {
            if (id === "lenguaje-config") return {textContent: JSON.stringify(config)};
            if (id === "texto") return texto;
            if (id === "resultados") return resultados;
            if (id === "estado-conexion") return estado;
            return [...graficos, ...paneles].find(n => n.id === id);
        },
        querySelector(selector) {
            if (selector === "form") return formulario;
            if (selector === ".boton-token") return botones[0];
            return botones.find(b => selector.includes('"' + b.dataset.token + '"'));
        },
        querySelectorAll(selector) {
            if (selector === ".grafico") return graficos;
            if (selector === ".panel-token") return paneles;
            if (selector === ".boton-token") return botones;
            if (selector.includes(".panel-automata")) return paneles.find(p => selector.startsWith("#" + p.id + " ")).automatas;
            throw new Error("Selector inesperado: " + selector);
        }
    };
    const sinRed = () => {peticiones++; throw new Error("Red bloqueada en esta prueba");};
    const contexto = {document, FormData: class {get(nombre) {return entrada[nombre];}}, TextEncoder, TextDecoder,
        fetch: sinRed, XMLHttpRequest: sinRed, WebSocket: sinRed, console};
    contexto.window = contexto;
    vm.createContext(contexto);
    for (const script of pagina.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)) {
        if (script[1].includes('type="application/json"')) continue;
        const src = script[1].match(/src="([^"]+)"/);
        if (src) {
            assert.match(src[1], /^\/[a-z]+\.js$/);
            vm.runInContext(fs.readFileSync(path.join(carpeta, src[1].slice(1)), "utf8"), contexto, {filename: src[1]});
        } else vm.runInContext(script[2], contexto);
    }
    return {contexto, eventos, boton, estado, resultados, entrada, document, peticiones: () => peticiones};
}
const compilar = entorno => entorno.eventos.submit({preventDefault() {}});
const archivo = (name, contenido) => {
    const bytes = typeof contenido === "string" ? new TextEncoder().encode(contenido) : contenido;
    return {name, size: bytes.byteLength, arrayBuffer: async () => bytes.buffer};
};

test("HTML generado carga todos los scripts y compila sin backend ni red", async () => {
    const t = entorno();
    await compilar(t);
    assert.equal(t.peticiones(), 0);
    assert.equal(t.boton.disabled, false);
    assert.match(t.estado.textContent, /completado en este navegador/);
    assert.match(t.resultados.innerHTML, /Posición final: \(1, 20\)/);
    assert.equal(t.document.querySelectorAll(".grafico").length, 15);
    assert.equal(t.document.querySelectorAll(".boton-token").length, 5);
    for (const g of t.document.querySelectorAll(".grafico")) {
        const imagen = g.querySelector("svg");
        assert.equal(imagen.style.width, imagen.viewBox.baseVal.width + "px");
    }
});

test("G00, G01 sin F y G28 simulan el programa completo", async () => {
    const t = entorno();
    t.entrada.texto = "G00 X02 Y03;\nG01 X10 Y15;\nG28;";
    await compilar(t);
    const json = t.resultados.innerHTML.match(/<pre[^>]*>([\s\S]*?)<\/pre>/)[1].replaceAll("&quot;", '"');
    const pasos = JSON.parse(json);
    assert.deepEqual(pasos.map(p => p.hasta), [[2, 3], [10, 15], [0, 0]]);
    assert.deepEqual(pasos[1].desde, [2, 3]);
    assert.equal(pasos[1].velocidad, 100);
    assert.equal(t.peticiones(), 0);
});

test("Errores léxicos y de formato rechazan la simulación completa", async () => {
    for (const instruccion of ["G02 X01 Y20;", "G01 Y20 X01;", "G28 X01;", "G01 X01 Y20", "G00 X01 Y20 F1;"]) {
        const t = entorno(); t.entrada.texto = "G28;\n" + instruccion;
        await compilar(t);
        assert.match(t.estado.textContent, /con errores/);
        assert.match(t.resultados.innerHTML, /No se simula el programa/);
        assert.doesNotMatch(t.resultados.innerHTML, /<pre/);
        assert.equal(t.document.querySelectorAll(".grafico").length, 15);
    }
});

test("TXT UTF-8 y BOM reemplazan el texto, con líneas y columnas reales", async () => {
    const t = entorno();
    t.entrada.archivo = archivo("movimientos.TXT", "\ufeffG28;\r\n  G00 X99 Y00;");
    await compilar(t);
    assert.equal(t.entrada.texto, "G28;\r\n  G00 X99 Y00;");
    assert.match(t.resultados.innerHTML, /Posición final: \(99, 0\)/);
    assert.match(t.resultados.innerHTML, /<td>2<\/td><td>3<\/td><td>G00<\/td>/);
    assert.equal(t.peticiones(), 0);
});

test("Extensión, UTF-8, tamaño y entrada vacía fallan sin borrar la entrada", async () => {
    const casos = [
        [archivo("a.csv", "G28;"), /TXT/],
        [archivo("a.txt", new Uint8Array([0xff, 0xfe])), /UTF-8/],
        [{name: "a.txt", size: config.limite + 1}, /1 MiB/],
        [null, /Introduce/]
    ];
    for (const [f, mensaje] of casos) {
        const t = entorno(); t.entrada.archivo = f; t.entrada.texto = "";
        await compilar(t);
        assert.match(t.estado.textContent, mensaje);
        assert.equal(t.entrada.archivo, f);
        assert.equal(t.boton.disabled, false);
        assert.equal(t.peticiones(), 0);
    }
    const t = entorno(); t.entrada.texto = "á".repeat(config.limite / 2 + 1);
    await compilar(t);
    assert.match(t.estado.textContent, /1 MiB/);
});

test("Una compilación nueva elimina resultados anteriores y permite corregir errores", async () => {
    const t = entorno(); await compilar(t);
    t.entrada.texto = ""; await compilar(t);
    assert.equal(t.resultados.innerHTML, "");
    t.entrada.texto = "G28;"; await compilar(t);
    assert.match(t.resultados.innerHTML, /Posición final: \(0, 0\)/);
});

test("Lexemas maliciosos se muestran como texto, sin HTML ejecutable", async () => {
    const t = entorno(); t.entrada.texto = '<img/src=x/onerror=alert(1)>;';
    await compilar(t);
    assert.doesNotMatch(t.resultados.innerHTML, /<img/);
    assert.match(t.resultados.innerHTML, /&lt;img/);
});

function acepta(a, cadena) {
    let estados = motor.cierre([a.inicial], a.transiciones);
    for (const c of cadena) estados = motor.cierre(a.transiciones.filter(t => estados.includes(t.origen) && motor.expandir(t.simbolo).includes(c)).map(t => t.destino), a.transiciones);
    return estados.some(e => a.finales.includes(e));
}

test("Todos los ejemplos y los límites numéricos concuerdan con regex, AFND, AFD y mínimo", () => {
    for (const [nombre, datos] of Object.entries(automatas)) {
        const patron = new RegExp("^(?:" + datos.expresion + ")$");
        const muestras = [...datos.ejemplos.flat(), "", "G29", "X100", "F1000", "F01"];
        for (let i = 0; i <= 1000; i++) muestras.push((nombre === "COORDENADA_Y" ? "Y" : nombre === "VELOCIDAD" ? "F" : "X") + String(i).padStart(2, "0"));
        for (const [i, grupo] of datos.ejemplos.entries()) for (const cadena of grupo) assert.equal(patron.test(cadena), i === 0);
        for (const cadena of muestras) for (const tipo of ["afnd", "afd", "afd_minimo"]) assert.equal(acepta(datos[tipo], cadena), patron.test(cadena), nombre + " " + tipo + " " + cadena);
    }
});

test("Equivalencia exacta AFND–AFD–mínimo mediante producto alcanzable", () => {
    for (const datos of Object.values(automatas)) for (const tipo of ["afd", "afd_minimo"]) {
        const a = datos.afnd, b = datos[tipo], pendientes = [[motor.cierre([a.inicial], a.transiciones), b.inicial]], vistos = new Set();
        for (let i = 0; i < pendientes.length; i++) {
            const [conjunto, estado] = pendientes[i], clave = JSON.stringify([conjunto, estado]);
            if (vistos.has(clave)) continue;
            vistos.add(clave);
            assert.equal(conjunto.some(e => a.finales.includes(e)), b.finales.includes(estado));
            for (const s of motor.alfabeto(a)) {
                const siguiente = motor.cierre(a.transiciones.filter(t => conjunto.includes(t.origen) && motor.expandir(t.simbolo).includes(s)).map(t => t.destino), a.transiciones);
                const t = b.transiciones.filter(t => t.origen === estado && t.simbolo === s);
                assert.equal(t.length, 1);
                pendientes.push([siguiente, t[0].destino]);
            }
        }
    }
});

test("Cada par de estados mínimos se distingue por alguna continuación", () => {
    for (const datos of Object.values(automatas)) {
        const a = datos.afd_minimo, simbolos = motor.alfabeto(a);
        const delta = (e, s) => a.transiciones.find(t => t.origen === e && t.simbolo === s).destino;
        for (let i = 0; i < a.estados.length; i++) for (let j = i + 1; j < a.estados.length; j++) {
            const pendientes = [[a.estados[i], a.estados[j]]], vistos = new Set(); let distintos = false;
            for (let k = 0; k < pendientes.length && !distintos; k++) {
                const [x, y] = pendientes[k], clave = x + ":" + y;
                if (vistos.has(clave)) continue;
                vistos.add(clave);
                distintos = a.finales.includes(x) !== a.finales.includes(y);
                if (!distintos) for (const s of simbolos) pendientes.push([delta(x, s), delta(y, s)]);
            }
            assert.equal(distintos, true);
        }
    }
});

test("Thompson genera expresiones nuevas y rechaza sintaxis no admitida", () => {
    const a = motor.crearAFND("Z(a|b)+[0-2]?");
    for (const s of ["Za", "Zabb2", "Zbbb0"]) assert.equal(acepta(a, s), true);
    for (const s of ["Z", "Za3", "Zc", "Zab00"]) assert.equal(acepta(a, s), false);
    for (const p of ["[z-a]", "[", "(a", "a{3,2}", "a{,2}", "a{1", "[^a]", "\\d", ".", "a**"]) assert.throws(() => motor.crearAFND(p));
    assert.match(vistas.dibujar(a, "nuevo"), /data-estado="q/);
});

test("Selección de los cinco tokens, tipos y zoom usan los controles originales", async () => {
    const t = entorno(); await compilar(t);
    for (const nombre of Object.keys(config.expresiones)) {
        t.contexto.seleccionarToken(nombre);
        assert.equal(t.document.getElementById("token-" + nombre).classList.contains("activo"), true);
        for (const tipo of ["afnd", "afd", "afd_minimo"]) {
            t.contexto.seleccionarTipo(nombre, tipo);
            const paneles = t.document.querySelectorAll("#token-" + nombre + " .panel-automata");
            assert.deepEqual(paneles.map(p => p.hidden), paneles.map(p => p.dataset.tipo !== tipo));
            const id = "grafico-" + nombre + "-" + tipo, g = t.document.getElementById(id), imagen = g.querySelector("svg");
            t.contexto.cambiarZoom(id, 1.25);
            assert.equal(imagen.style.width, imagen.viewBox.baseVal.width * 1.25 + "px");
            t.contexto.cambiarZoom(id, 0.8);
            assert.equal(imagen.style.width, imagen.viewBox.baseVal.width + "px");
            t.contexto.cambiarZoom(id, 100); assert.equal(imagen.dataset.escala, 4);
            t.contexto.cambiarZoom(id, 0.001); assert.equal(imagen.dataset.escala, 0.5);
            g.scrollLeft = 70; t.contexto.reiniciarZoom(id);
            assert.equal(imagen.dataset.escala, 1); assert.equal(g.scrollLeft, 0);
        }
    }
});

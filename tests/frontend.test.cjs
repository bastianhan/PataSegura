const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

class Elemento {
  constructor(tag = 'div') {
    this.tagName = tag; this.children = []; this.dataset = {}; this.listeners = {};
    this.classList = { add() {}, toggle() {} }; this.attributes = {};
  }
  set textContent(value) { this.text = String(value); }
  get textContent() { return (this.text || '') + this.children.map((c) => c.textContent).join(''); }
  setAttribute(k, v) { this.attributes[k] = String(v); }
  append(...children) { this.children.push(...children); }
  appendChild(child) { this.append(child); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(event, fn) { this.listeners[event] = fn; }
  insertAdjacentHTML() {}
  querySelectorAll(selector) { return selector === '.burbuja[data-id]' ? this.children.filter((c) => c.dataset.id) : []; }
  querySelector(selector) {
    const id = selector.match(/data-id="(\d+)"/);
    return id ? this.children.find((c) => String(c.dataset.id) === id[1]) : null;
  }
  focus() {}
  remove() {}
}
const codigo = (archivo) => fs.readFileSync(path.join(__dirname, '..', 'mascotas', 'static', 'mascotas', archivo), 'utf8');
const turno = () => new Promise((resolve) => setImmediate(resolve));

test('el nombre con comillas y HTML permanece en texto y en un único atributo alt', async () => {
  const nombres = ['mapa', 'panel-zona', 'panel-lista', 'panel-titulo', 'cerrar-panel', 'ver-hallazgos', 'buscar', 'leyenda', 'leyenda-toggle', 'ubicarme'];
  const nodos = Object.fromEntries(nombres.map((n) => [n, new Elemento()]));
  let pin;
  const grupo = { on() {}, clearLayers() {}, addLayers() {} };
  const L = { markerClusterGroup: () => grupo, marker: () => (pin = { on(_evento, cb) { this.click = cb; } }) };
  const nombre = 'Max" onmouseover="alert(1)<b>';
  const reporte = { id: 1, nombre, especie: 'perro', especie_texto: 'Perro', raza: '', zona: '', tipo: 'perdida', foto: '/foto.jpg', url: '/perdidas/1/', dias: 0, fecha_evento: '2026-11-05', coordenadas: { lat: -33, lng: -70 } };
  const document = { getElementById: (id) => nodos[id], createElement: (tag) => new Elemento(tag), createTextNode: (t) => { const n = new Elemento('#text'); n.textContent = t; return n; }, querySelectorAll: () => [], addEventListener() {} };
  const mapa = { addLayer() {}, getCenter: () => ({ lat: -33, lng: -70 }) };
  const PS = { crearMapa: () => mapa, iconoPin() {}, CENTRO_SANTIAGO: [], mostrarAviso() {} };
  vm.runInNewContext(codigo('mapa.js'), { document, L, window: { L, PataSegura: PS, innerWidth: 1000 }, fetch: async () => ({ json: async () => ({ reportes: [reporte] }) }), URLSearchParams, location: { search: '' }, setTimeout, clearTimeout });
  await turno(); await turno();
  pin.click();
  const fila = nodos['panel-lista'].children[0];
  assert.equal(fila.children[0].alt, `Foto de ${nombre}`);
  assert.equal(fila.children[0].attributes.onmouseover, undefined);
  assert.ok(fila.textContent.includes(nombre));
});

test('sincroniza el mensaje recibido antes del mensaje enviado, sin duplicados', async () => {
  const chat = new Elemento(); chat.dataset = { api: '/api', enviar: '/chat' };
  const caja = new Elemento();
  const form = new Elemento();
  const input = new Elemento(); input.dataset.max = '1000'; input.value = 'Respuesta';
  const boton = new Elemento();
  form.elements = { texto: input, csrfmiddlewaretoken: { value: 'token' } };
  form.querySelector = () => boton;
  const nodos = { chat, mensajes: caja, 'chat-form': form, 'contador-chat': new Elemento() };
  const document = { hidden: false, getElementById: (id) => nodos[id], createElement: (tag) => new Elemento(tag) };
  const mensajes = [{ id: 1, texto: 'Recibido', mio: false, hora: '12:00' }, { id: 2, texto: 'Respuesta', mio: true, hora: '12:01' }];
  const fetch = async (url) => url === '/chat' ? { ok: true, json: async () => ({ mensaje: mensajes[1] }) } : { ok: true, json: async () => ({ mensajes: mensajes.filter((m) => m.id > Number(url.split('=')[1])) }) };
  vm.runInNewContext(codigo('chat.js'), { document, window: { PataSegura: { mostrarAviso() {} } }, fetch, URLSearchParams, setInterval() {} });
  await form.listeners.submit({ preventDefault() {} });
  assert.deepEqual(caja.children.map((b) => b.dataset.id), [1, 2]);
  assert.deepEqual(caja.children.map((b) => b.children[0].textContent), ['Recibido', 'Respuesta']);
});

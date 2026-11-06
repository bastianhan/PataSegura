// =============================================================
//  chat.js — Enviar mensajes sin recargar la página y revisar
//  cada 4 segundos si llegaron mensajes nuevos.
// =============================================================
(function () {
  const chat = document.getElementById('chat');
  const caja = document.getElementById('mensajes');
  const form = document.getElementById('chat-form');
  const input = form.elements.texto;
  const csrf = form.elements.csrfmiddlewaretoken.value;
  const max = Number(input.dataset.max) || 1000;
  const contador = document.getElementById('contador-chat');
  const boton = form.querySelector('.boton-enviar');

  // 2.5: contador visible cuando el mensaje se acerca al límite
  input.addEventListener('input', () => {
    const n = input.value.length;
    contador.hidden = n < max * 0.8;
    contador.textContent = `${n} / ${max}`;
    contador.classList.toggle('excedido', n >= max);
  });

  const idsIniciales = [...caja.querySelectorAll('.burbuja[data-id]')].map((b) => Number(b.dataset.id));
  let cursor = Math.max(0, ...idsIniciales);
  let sondeo = null;
  const bajar = () => (caja.scrollTop = caja.scrollHeight);

  function agregar(m) {
    if (caja.querySelector(`.burbuja[data-id="${m.id}"]`)) return; // ya está
    document.getElementById('chat-vacio')?.remove();
    const div = document.createElement('div');
    div.className = `burbuja ${m.mio ? 'mia' : 'suya'}`;
    div.dataset.id = m.id;
    const p = document.createElement('p');
    p.textContent = m.texto; // textContent evita que se inyecte HTML
    const small = document.createElement('small');
    small.textContent = m.hora;
    if (m.mio) small.insertAdjacentHTML('beforeend', ' <span class="visto">✓✓</span>');
    div.append(p, small);
    caja.appendChild(div);
    bajar();
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const texto = input.value.trim();
    if (!texto) {
      // 2.3: mensaje en blanco
      window.PataSegura.mostrarAviso('No escribiste nada. El mensaje está en blanco y no se envió.', 'error');
      return;
    }
    if (boton.disabled) return; // evita enviar dos veces con doble clic
    boton.disabled = true;
    input.value = '';
    contador.hidden = true;
    try {
      const resp = await fetch(chat.dataset.enviar, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrf, 'X-Requested-With': 'fetch' },
        body: new URLSearchParams({ texto }),
      });
      const datos = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        input.value = texto;
        window.PataSegura.mostrarAviso(datos.error || 'No se pudo enviar el mensaje. Intenta de nuevo.', 'error');
      } else {
        await revisarNuevos(true);
        if (datos.aviso) window.PataSegura.mostrarAviso(datos.aviso, 'info');
      }
    } catch {
      input.value = texto;
      window.PataSegura.mostrarAviso('No se pudo enviar el mensaje. Revisa tu conexión.', 'error');
    }
    boton.disabled = false;
    input.focus();
  });

  async function revisarNuevos(forzar = false) {
    if (document.hidden && !forzar) return;
    if (sondeo) {
      await sondeo;
      if (forzar) return revisarNuevos(true);
      return;
    }
    sondeo = (async () => {
      try {
        let mensajes;
        do {
          const resp = await fetch(`${chat.dataset.api}?desde=${cursor}`);
          if (!resp.ok) return;
          mensajes = (await resp.json()).mensajes;
          for (const mensaje of mensajes) {
            agregar(mensaje);
            cursor = mensaje.id;
          }
        } while (mensajes.length === 200);
      } catch { /* sin conexión: se reintenta en el próximo ciclo */ }
    })();
    try {
      await sondeo;
    } finally {
      sondeo = null;
    }
  }

  bajar();
  input.focus();
  setInterval(revisarNuevos, 4000);
})();

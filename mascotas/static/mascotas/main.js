// =============================================================
//  main.js — Código JavaScript que se carga en TODAS las páginas
// =============================================================

// ---------- Avisos (mensajes de Django) se esconden solos ----------
document.querySelectorAll('.aviso').forEach((aviso, i) => {
  setTimeout(() => aviso.classList.add('saliendo'), 4500 + i * 400);
  setTimeout(() => aviso.remove(), 5000 + i * 400);
});

// ---------- Botón "ojo" para ver/ocultar la contraseña ----------
document.querySelectorAll('.ver-clave').forEach((boton) => {
  boton.addEventListener('click', () => {
    const input = boton.parentElement.querySelector('input');
    const visible = input.type === 'text';
    input.type = visible ? 'password' : 'text';
    boton.setAttribute('aria-label', visible ? 'Mostrar contraseña' : 'Ocultar contraseña');
  });
});

// ---------- Enlaces de funciones que todavía no existen ----------
document.querySelectorAll('[data-proximamente]').forEach((el) => {
  el.addEventListener('click', (e) => {
    e.preventDefault();
    mostrarAviso(el.dataset.proximamente, 'info');
  });
});

function mostrarAviso(texto, tipo = 'success') {
  let caja = document.querySelector('.avisos');
  if (!caja) {
    caja = document.createElement('div');
    caja.className = 'avisos';
    caja.setAttribute('role', 'status');
    document.body.appendChild(caja);
  }
  const aviso = document.createElement('div');
  aviso.className = `aviso aviso-${tipo}`;
  aviso.textContent = texto;
  caja.appendChild(aviso);
  setTimeout(() => aviso.classList.add('saliendo'), 3500);
  setTimeout(() => aviso.remove(), 4000);
}

// ---------- Ayudas para los mapas (solo si la página cargó Leaflet) ----------
const CENTRO_SANTIAGO = [-33.4489, -70.6393];

const HUELLA_SVG =
  '<svg width="16" height="16" viewBox="0 0 24 24" fill="#fff" aria-hidden="true">' +
  '<ellipse cx="6" cy="9.5" rx="2.1" ry="2.7" transform="rotate(-18 6 9.5)"/><ellipse cx="10" cy="5.6" rx="2.1" ry="2.8"/>' +
  '<ellipse cx="14.6" cy="5.6" rx="2.1" ry="2.8"/><ellipse cx="18.4" cy="9.6" rx="2.1" ry="2.7" transform="rotate(18 18.4 9.6)"/>' +
  '<path d="M12.3 11.2c2.6 0 5.6 3.6 5.6 6.1 0 1.8-1.4 2.6-2.9 2.6-1.2 0-1.8-.6-2.7-.6s-1.6.6-2.8.6c-1.5 0-2.9-.8-2.9-2.6 0-2.5 3.1-6.1 5.7-6.1Z"/></svg>';

window.PataSegura = {
  mostrarAviso,
  CENTRO_SANTIAGO,

  crearMapa(elemento, centro = CENTRO_SANTIAGO, zoom = 12) {
    const mapa = L.map(elemento, { zoomControl: false }).setView(centro, zoom);
    L.control.zoom({ position: 'bottomleft' }).addTo(mapa);
    // Mapa base de OpenStreetMap con estilo "Voyager" de CARTO (gratis, sin clave)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      subdomains: 'abcd',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    }).addTo(mapa);
    return mapa;
  },

  // Pin con huella: verde = perdida, azul = hallazgo
  iconoPin(tipo = 'perdida') {
    return L.divIcon({
      className: '',
      html: `<div class="pin pin-${tipo}">${HUELLA_SVG}</div>`,
      iconSize: [34, 34],
      iconAnchor: [17, 17],
    });
  },

  // Pide la ubicación al navegador. Devuelve [lat, lng] o null.
  obtenerUbicacion() {
    return new Promise((resolve) => {
      if (!navigator.geolocation) return resolve(null);
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve([pos.coords.latitude, pos.coords.longitude]),
        () => resolve(null),
        { enableHighAccuracy: true, timeout: 8000 }
      );
    });
  },
};

// =============================================================
//  mapa.js — Mapa interactivo de mascotas perdidas y hallazgos
// -------------------------------------------------------------
//  1. Pide los reportes al servidor (/api/reportes/) en JSON
//  2. Pone un pin por cada uno usando sus coordenadas
//  3. Agrupa los pines cercanos en círculos de colores según la
//     cantidad (verde 1, amarillo 2-3, naranjo 4-5, rojo +5)
//  4. Al hacer clic en un círculo, muestra la lista de esa zona
// =============================================================
(function () {
  const PS = window.PataSegura;
  const caja = document.getElementById('mapa');

  if (!window.L || !L.markerClusterGroup) {
    caja.innerHTML = '<p class="mapa-error">No se pudo cargar el mapa. Revisa tu conexión a internet y recarga la página.</p>';
    return;
  }

  const mapa = PS.crearMapa(caja, PS.CENTRO_SANTIAGO, 12);
  const panel = document.getElementById('panel-zona');
  const lista = document.getElementById('panel-lista');
  const tituloPanel = document.getElementById('panel-titulo');

  let reportes = [];
  let filtroEspecie = 'todos';
  let verHallazgos = true;
  let textoBusqueda = '';
  let miUbicacion = null; // [lat, lng] si el usuario la comparte
  const marcadores = new Map(); // id → marcador

  // ---------- Grupo de pines con colores por rango ----------
  function claseRango(n) {
    if (n <= 1) return 'rango-1';
    if (n <= 3) return 'rango-2';
    if (n <= 5) return 'rango-3';
    return 'rango-4';
  }

  const grupo = L.markerClusterGroup({
    maxClusterRadius: 70,
    showCoverageOnHover: false,
    zoomToBoundsOnClick: false, // al hacer clic mostramos la lista, no hacemos zoom
    spiderfyOnMaxZoom: false,
    iconCreateFunction(cluster) {
      const n = cluster.getChildCount();
      return L.divIcon({
        className: '',
        html: `<div class="cluster ${claseRango(n)}"><span>${n}</span></div>`,
        iconSize: [52, 52],
        iconAnchor: [26, 26],
      });
    },
  });
  mapa.addLayer(grupo);

  grupo.on('clusterclick', (e) => {
    const ids = e.layer.getAllChildMarkers().map((m) => m.options.idReporte);
    abrirPanel(reportes.filter((r) => ids.includes(r.id)));
  });

  // ---------- Dibujar los pines según los filtros ----------
  function pasaFiltros(r) {
    if (r.tipo === 'hallazgo' && !verHallazgos) return false;
    if (filtroEspecie !== 'todos' && r.especie !== filtroEspecie) return false;
    if (textoBusqueda) {
      const texto = `${r.nombre} ${r.raza} ${r.zona} ${r.especie_texto}`.toLowerCase();
      if (!texto.includes(textoBusqueda)) return false;
    }
    return true;
  }

  function dibujar() {
    grupo.clearLayers();
    marcadores.clear();
    const visibles = reportes.filter(pasaFiltros);
    for (const r of visibles) {
      const m = L.marker([r.coordenadas.lat, r.coordenadas.lng], {
        icon: PS.iconoPin(r.tipo),
        idReporte: r.id,
        title: r.nombre,
      });
      m.on('click', () => abrirPanel([r]));
      marcadores.set(r.id, m);
    }
    grupo.addLayers([...marcadores.values()]);
    return visibles;
  }

  // ---------- Panel con la lista de mascotas de la zona ----------
  const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
  const EMOJI = { perro: '🐶', gato: '🐱', otro: '🐾' };

  function elemento(tag, clase, texto) {
    const nodo = document.createElement(tag);
    if (clase) nodo.className = clase;
    if (texto != null) nodo.textContent = texto;
    return nodo;
  }
  function fechaLarga(iso) {
    const [a, m, d] = iso.split('-').map(Number);
    return `${d} de ${MESES[m - 1]} de ${a}`;
  }
  function haceDias(n) {
    return n === 0 ? 'Hoy' : n === 1 ? 'Hace 1 día' : `Hace ${n} días`;
  }
  function claseUrgencia(n) {
    return n <= 2 ? 'badge-rojo' : n <= 5 ? 'badge-ambar' : 'badge-verde';
  }
  // Distancia en km entre dos puntos (fórmula de Haversine)
  function distanciaKm([lat1, lng1], [lat2, lng2]) {
    const rad = (x) => (x * Math.PI) / 180;
    const h = Math.sin(rad(lat2 - lat1) / 2) ** 2 +
      Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(rad(lng2 - lng1) / 2) ** 2;
    return 2 * 6371 * Math.asin(Math.sqrt(h));
  }
  function textoDistancia(r) {
    const origen = miUbicacion || [mapa.getCenter().lat, mapa.getCenter().lng];
    const km = distanciaKm(origen, [r.coordenadas.lat, r.coordenadas.lng]);
    const valor = km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1).replace('.', ',')} km`;
    return `A ${valor} ${miUbicacion ? 'de tu ubicación' : 'del centro del mapa'}`;
  }

  function abrirPanel(items) {
    const perdidas = items.filter((r) => r.tipo === 'perdida').length;
    const hallazgos = items.length - perdidas;
    tituloPanel.textContent = hallazgos && !perdidas
      ? `Hallazgos en esta zona (${items.length})`
      : `Mascotas perdidas en esta zona (${items.length})`;

    items.sort((a, b) => a.dias - b.dias);
    lista.replaceChildren();
    for (const r of items) {
      const fila = elemento('a', 'fila-reporte');
      fila.href = r.url;
      let foto;
      if (r.foto) {
        foto = elemento('img', 'foto-mascota mediana');
        foto.src = r.foto;
        foto.alt = `Foto de ${r.nombre}`;
      } else {
        foto = elemento('div', `foto-mascota mediana sin-foto sin-foto-${r.especie}`, EMOJI[r.especie] || '🐾');
        foto.setAttribute('role', 'img');
        foto.setAttribute('aria-label', r.especie_texto);
      }
      const texto = elemento('div', 'fila-texto');
      const titulo = elemento('div', 'fila-titulo');
      titulo.append(elemento('b', '', r.nombre), elemento('span', `badge ${claseUrgencia(r.dias)}`, haceDias(r.dias)));
      const especie = elemento('p', '', `${r.especie_texto}${r.raza ? ' · ' + r.raza : ''}`);
      if (r.tipo === 'hallazgo') especie.append(document.createTextNode(' · '), elemento('b', 'txt-hallazgo', 'Hallazgo'));
      texto.append(titulo, especie,
        elemento('p', 'text-muted', `${r.tipo === 'hallazgo' ? 'Encontrado' : 'Perdido'} el ${fechaLarga(r.fecha_evento)}`),
        elemento('p', 'text-muted', `📍 ${textoDistancia(r)}`));
      fila.append(foto, texto, elemento('span', 'chevron', '›'));
      lista.append(fila);
    }

    panel.classList.add('abierto');
    caja.classList.add('con-panel');
    panel.setAttribute('aria-hidden', 'false');
    lista.scrollTop = 0;
  }

  function cerrarPanel() {
    panel.classList.remove('abierto');
    caja.classList.remove('con-panel');
    panel.setAttribute('aria-hidden', 'true');
  }
  document.getElementById('cerrar-panel').addEventListener('click', cerrarPanel);
  document.addEventListener('keydown', (e) => e.key === 'Escape' && cerrarPanel());

  // ---------- Controles ----------
  document.querySelectorAll('.filtros-especie button').forEach((b) =>
    b.addEventListener('click', () => {
      filtroEspecie = b.dataset.especie;
      document.querySelectorAll('.filtros-especie button').forEach((x) => x.classList.toggle('activo', x === b));
      dibujar();
      cerrarPanel();
    })
  );

  document.getElementById('ver-hallazgos').addEventListener('change', (e) => {
    verHallazgos = e.target.checked;
    dibujar();
    cerrarPanel();
  });

  let espera;
  document.getElementById('buscar').addEventListener('input', (e) => {
    clearTimeout(espera);
    espera = setTimeout(() => {
      textoBusqueda = e.target.value.trim().toLowerCase();
      const visibles = dibujar();
      if (textoBusqueda && visibles.length) {
        mapa.fitBounds(L.latLngBounds(visibles.map((r) => [r.coordenadas.lat, r.coordenadas.lng])), { padding: [60, 60], maxZoom: 15 });
        abrirPanel(visibles);
      } else if (textoBusqueda) {
        PS.mostrarAviso('No hay mascotas que coincidan con la búsqueda.', 'info');
      }
    }, 350);
  });

  const leyenda = document.getElementById('leyenda');
  document.getElementById('leyenda-toggle').addEventListener('click', (e) => {
    const abierta = leyenda.classList.toggle('cerrada') === false;
    e.currentTarget.setAttribute('aria-expanded', String(abierta));
  });
  if (window.innerWidth < 700) leyenda.classList.add('cerrada');

  let pinYo = null;
  document.getElementById('ubicarme').addEventListener('click', async (e) => {
    const boton = e.currentTarget;
    boton.disabled = true;
    const pos = await PS.obtenerUbicacion();
    boton.disabled = false;
    if (!pos) return PS.mostrarAviso('No pudimos obtener tu ubicación. Revisa los permisos del navegador.', 'error');
    miUbicacion = pos;
    mapa.setView(pos, 15);
    if (pinYo) pinYo.setLatLng(pos);
    else pinYo = L.circleMarker(pos, { radius: 9, color: '#fff', weight: 3, fillColor: '#2f7de1', fillOpacity: 1 }).addTo(mapa).bindTooltip('Estás aquí');
  });

  // ---------- Cargar datos ----------
  fetch(caja.dataset.api)
    .then((r) => r.json())
    .then((datos) => {
      reportes = datos.reportes;
      dibujar();

      // Si venimos desde "Ver en mapa" (?ver=ID), centramos en esa mascota
      const ver = Number(new URLSearchParams(location.search).get('ver'));
      const objetivo = reportes.find((r) => r.id === ver);
      if (objetivo) {
        mapa.setView([objetivo.coordenadas.lat, objetivo.coordenadas.lng], 17);
        abrirPanel([objetivo]);
      }
    })
    .catch(() => PS.mostrarAviso('No se pudieron cargar los reportes.', 'error'));
})();

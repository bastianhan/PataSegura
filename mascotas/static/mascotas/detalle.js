// Mapa pequeño en la página de detalle de una mascota
(function () {
  const caja = document.getElementById('mapa-detalle');
  if (!caja || !window.L) return;
  const pos = [parseFloat(caja.dataset.lat), parseFloat(caja.dataset.lng)];
  const mapa = window.PataSegura.crearMapa(caja, pos, 15);
  L.marker(pos, { icon: window.PataSegura.iconoPin(caja.dataset.tipo) }).addTo(mapa);
  L.circle(pos, { radius: 300, color: '#2d5c53', weight: 1, fillOpacity: 0.08 }).addTo(mapa);
})();

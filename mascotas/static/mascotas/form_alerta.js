// =============================================================
//  form_alerta.js — Formulario "Crear Alerta"
//  1. Mapa donde el usuario hace clic para marcar la ubicación
//     (llena los campos ocultos latitud y longitud)
//  2. Vista previa de la foto
//  3. Validación en el navegador antes de enviar
// =============================================================
(function () {
  const PS = window.PataSegura;
  const form = document.getElementById('form-alerta');
  const cajaMapa = document.getElementById('mapa-form');
  const inputLat = document.getElementById('id_latitud');
  const inputLng = document.getElementById('id_longitud');
  const tipo = cajaMapa.dataset.tipo;

  // Si el formulario volvió con errores, mostramos el resumen
  document.getElementById('resumen-errores')?.focus();

  // 3.3: zonas válidas (Chile continental, Isla de Pascua y Juan Fernández) — igual que en el servidor
  const ZONAS_CHILE = [[-56.6, -17.4, -76.0, -66.0], [-27.3, -27.0, -109.5, -109.2], [-33.9, -33.5, -80.9, -78.7]];
  const dentroDeChile = (lat, lng) => ZONAS_CHILE.some(([a, b, c, d]) => lat >= a && lat <= b && lng >= c && lng <= d);

  // ---------- 1. Mapa ----------
  if (window.L) {
    const tieneCoords = inputLat.value && inputLng.value;
    const inicio = tieneCoords ? [parseFloat(inputLat.value), parseFloat(inputLng.value)] : PS.CENTRO_SANTIAGO;
    const mapa = PS.crearMapa(cajaMapa, inicio, tieneCoords ? 15 : 12);
    let marcador = null;

    function ponerPin(latlng) {
      if (!dentroDeChile(latlng.lat, latlng.lng)) {
        PS.mostrarAviso('Esa ubicación está fuera de Chile. Marca un punto válido en el mapa.', 'error');
        if (marcador) marcador.setLatLng([parseFloat(inputLat.value), parseFloat(inputLng.value)]);
        return;
      }
      inputLat.value = latlng.lat.toFixed(6);
      inputLng.value = latlng.lng.toFixed(6);
      if (marcador) {
        marcador.setLatLng(latlng);
      } else {
        marcador = L.marker(latlng, { icon: PS.iconoPin(tipo), draggable: true }).addTo(mapa);
        marcador.on('dragend', () => ponerPin(marcador.getLatLng()));
      }
      cajaMapa.closest('.grupo-campo').classList.remove('con-error');
    }

    if (tieneCoords) ponerPin(L.latLng(inicio));
    mapa.on('click', (e) => ponerPin(e.latlng));

    document.getElementById('mi-ubicacion').addEventListener('click', async (e) => {
      const boton = e.currentTarget;
      boton.disabled = true;
      const pos = await PS.obtenerUbicacion();
      boton.disabled = false;
      if (!pos) return PS.mostrarAviso('No pudimos obtener tu ubicación. Marca el punto en el mapa.', 'error');
      mapa.setView(pos, 16);
      ponerPin(L.latLng(pos));
    });
  } else {
    cajaMapa.innerHTML = '<p class="mapa-error">No se pudo cargar el mapa. Revisa tu conexión a internet.</p>';
  }

  // ---------- 2. Vista previa de la foto ----------
  const inputFoto = document.getElementById('id_foto');
  inputFoto.addEventListener('change', () => {
    const archivo = inputFoto.files[0];
    const vista = document.getElementById('vista-foto');
    if (!archivo) return;
    if (archivo.size > 8 * 1024 * 1024) {
      inputFoto.value = '';
      return PS.mostrarAviso('La foto pesa más de 8 MB. Elige una más liviana.', 'error');
    }
    const img = document.createElement('img');
    img.alt = 'Vista previa';
    img.src = URL.createObjectURL(archivo);
    vista.replaceChildren(img);
  });

  // ---------- 3. Validación antes de enviar ----------
  form.addEventListener('submit', (e) => {
    const faltan = [];
    const marcar = (elemento, mensaje) => {
      const grupo = elemento.closest('.grupo-campo');
      grupo.classList.add('con-error');
      if (!grupo.querySelector('.error-campo')) {
        const small = document.createElement('small');
        small.className = 'error-campo';
        small.textContent = mensaje;
        grupo.appendChild(small);
      }
      faltan.push(mensaje);
    };

    const nombre = form.elements.nombre;
    if (tipo === 'perdida' && !nombre.value.trim()) marcar(nombre, 'Ingresa el nombre de tu mascota.');
    if (!form.querySelector('[name=especie]:checked')) marcar(form.querySelector('[name=especie]'), 'Selecciona la especie.');
    const desc = form.elements.descripcion;
    if (desc.value.trim().length < 10) marcar(desc, 'Describe a la mascota (mínimo 10 caracteres).');
    if (!form.elements.fecha_evento.value) marcar(form.elements.fecha_evento, 'Indica la fecha.');
    if (!inputLat.value || !inputLng.value) marcar(cajaMapa, 'Marca en el mapa dónde se vio por última vez.');
    if (!form.elements.zona.value.trim()) marcar(form.elements.zona, 'Escribe una referencia del lugar.');

    if (faltan.length) {
      e.preventDefault();
      let resumen = document.getElementById('resumen-errores');
      if (!resumen) {
        resumen = document.createElement('div');
        resumen.id = 'resumen-errores';
        resumen.className = 'alerta-error';
        resumen.tabIndex = -1;
        form.querySelector('input[name=csrfmiddlewaretoken]').after(resumen);
      }
      resumen.innerHTML = '<b>Faltan datos obligatorios. Complétalos para publicar:</b><ul></ul>';
      faltan.forEach((t) => {
        const li = document.createElement('li');
        li.textContent = t;
        resumen.querySelector('ul').appendChild(li);
      });
      resumen.scrollIntoView({ behavior: 'smooth', block: 'center' });
      resumen.focus({ preventScroll: true });
    } else {
      form.querySelector('[type=submit]').disabled = true;
    }
  });

  // ---------- 2.5 Contador de caracteres de la descripción ----------
  document.querySelectorAll('.contador').forEach((contador) => {
    const campo = document.getElementById(contador.dataset.para);
    const max = Number(campo.getAttribute('maxlength')) || 1000;
    const actualizar = () => {
      contador.textContent = `${campo.value.length} / ${max} caracteres`;
      contador.classList.toggle('excedido', campo.value.length >= max);
    };
    campo.addEventListener('input', actualizar);
    actualizar();
  });

  // Al corregir un campo, se quita su marca roja
  form.addEventListener('input', (e) => {
    const grupo = e.target.closest('.grupo-campo');
    if (grupo) {
      grupo.classList.remove('con-error');
      grupo.querySelectorAll('.error-campo').forEach((s) => s.remove());
    }
  });
})();

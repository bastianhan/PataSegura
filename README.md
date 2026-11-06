# 🐾 PataSegura

Plataforma web para conectar a **dueños de mascotas perdidas**, **personas que encuentran animales** y **refugios**.
Hecha con **Django** (Python), **Leaflet** + **OpenFreeMap** para el mapa (gratis y sin clave de API) y HTML/CSS/JS sin frameworks extra.

## ¿Qué incluye el prototipo?

| # | Funcionalidad | Dónde está |
|---|---|---|
| 1 | **Login y registro** con correo. Entidad USUARIO con `datos_cuenta` y `datos_contacto` | `/login/`, `/registro/` |
| 2 | **Foro de mascotas perdidas** (cronológico) + botón **Crear Alerta** con validación de datos obligatorios | `/perdidas/`, `/perdidas/reportar/` |
| 3 | **Mapa interactivo** con pines, rangos de colores, filtros (perro/gato/ambos) y lista por zona | `/mapa/` |
| 4 | **Foros secundarios**: hallazgos, adopciones (separadas de las emergencias) y veterinarias/refugios | `/hallazgos/`, `/adopciones/`, `/establecimientos/` |
| + | **Chats** entre quien publicó y quien tiene información | `/chats/` |
| + | **Mi cuenta**: mis publicaciones, mis chats y configuración de contacto | `/cuenta/` |

Solo los usuarios con sesión iniciada pueden crear reportes, publicar adopciones y chatear.

🛡️ **Plan de pruebas:** los 15 casos del plan del grupo están resueltos y probados. Revisa [PRUEBAS.md](PRUEBAS.md) para ver qué pasa en cada caso y en qué parte del código está.

---

## Cómo ejecutarlo en tu computador (paso a paso)

Necesitas tener **Python 3.12 o superior** instalado. Para comprobarlo, abre una terminal y escribe `python --version`.

### 1. Abrir una terminal en la carpeta del proyecto
La carpeta es la que contiene el archivo `manage.py`.

### 2. Crear y activar un entorno virtual (solo la primera vez)
Un entorno virtual es una "caja" donde se instalan las librerías del proyecto sin afectar el resto del computador.

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\activate
```
**Mac / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```
Sabrás que funcionó porque aparece `(venv)` al inicio de la línea.

### 3. Instalar las dependencias
```bash
pip install -r requirements.txt
```

### 4. Crear o actualizar la base de datos
```bash
python manage.py migrate
```
> Si ya tenías un `db.sqlite3` de antes, **no se pierde nada**. La migración `0003` traspasa el estado de cada mascota a su nuevo reporte.

### 5. (Opcional) Cargar datos de ejemplo
Crea usuarios, 16 reportes repartidos por Santiago, chats, refugios y adopciones:
```bash
python manage.py cargar_demo
```
Cuenta de prueba: **demo@patasegura.cl** / **patasegura123**
(Para borrarlos y volver a crearlos: `python manage.py cargar_demo --reset`)

### 6. Encender el servidor
```bash
python manage.py runserver
```
Abre **http://127.0.0.1:8000** en el navegador. Para apagarlo, presiona `Ctrl + C` en la terminal.

### Extras
- Panel de administración: `python manage.py createsuperuser` y luego entra a `/admin/`.
- Pruebas automáticas (27, incluidos los 15 casos del plan de pruebas): `python manage.py test`
- Moderación: en `/admin/` → *Mascotas* puedes filtrar por "foto oculta" y usar las acciones "Eliminar la foto" o "Volver a mostrarla". Las denuncias aparecen en *Denuncias*.
- El mapa necesita **conexión a internet**, porque las imágenes del mapa y la librería Leaflet se descargan al abrir la página.
- Recuperación de contraseña: en esta configuración local, el enlace se imprime en la consola donde corre el servidor; no se envía un correo real. Para enviarlo por email hay que configurar un servicio de correo.

---

## Estructura del proyecto

```
core/                     Configuración general de Django (settings, urls)
mascotas/
├── models.py             Entidades: PerfilUsuario, Mascota, ReportePerdida, Conversacion, Mensaje...
├── forms.py              Formularios y sus validaciones
├── views.py              Lógica de cada página
├── moderacion.py         Filtro y censura de palabras ofensivas
├── validators.py         Validación de nombres, correos, fotos y ubicaciones
├── limites.py            Límites anti-spam (alertas, mensajes, duplicados)
├── middleware.py         Rechaza peticiones gigantes
├── urls.py               Rutas (qué vista responde cada dirección)
├── backends.py           Login con correo electrónico
├── context_processors.py Contador de chats sin leer (para el menú)
├── templatetags/         Íconos SVG y filtros propios para las plantillas
├── management/commands/  Comando cargar_demo
├── templates/mascotas/   Plantillas HTML
└── static/mascotas/      estilos.css, main.js, mapa.js, form_alerta.js, chat.js
```

## Modelo de datos

```
USUARIO = User de Django (datos_cuenta) ──1:1── PerfilUsuario (datos_contacto)
   │
   ├──< MASCOTA (nombre, descripcion, especie, raza, color, foto, zona)
   │       └──1:1── REPORTE DE PÉRDIDA (tipo, estado_busqueda, latitud/longitud = coordenadas, fecha_evento)
   │                    ├──< DENUNCIA (foto/texto indebido)
   │                    └──< CONVERSACION ──< MENSAJE
   └──< ADOPCION
ESTABLECIMIENTO (veterinarias, refugios, tiendas)
```

- `ReportePerdida.tipo`: `perdida` (foro principal) o `hallazgo` (foro de hallazgos).
- `ReportePerdida.estado_busqueda`: `activa`, `encontrada` o `cerrada`. En el mapa solo aparecen las activas.
- `ReportePerdida.coordenadas` devuelve `{lat, lng}`, que el mapa usa para poner el pin.

## Próximos pasos sugeridos
- Perfiles de refugio: hoy el botón "Crear perfil de refugio" está maquetado.
- Notificaciones cuando alguien reporta una mascota cerca de ti.
- Enviar fotos por el chat.
- Confirmar el correo con un enlace (para comprobar que el buzón existe de verdad).
- Detección automática de fotos inapropiadas con un servicio externo de IA.

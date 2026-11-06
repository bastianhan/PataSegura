# Plan de pruebas: resultados

Cada caso del plan de pruebas del grupo tiene **una prueba automática** en `mascotas/tests.py`, en la clase `PlanDePruebas` (por ejemplo, `test_1_1_...` corresponde al caso 1.1).

Para ejecutarlas todas:

```bash
python manage.py test
```

Si al final aparece `OK`, todos los casos están protegidos. Hoy son **27 pruebas: 27 OK**.

## Funcionalidad 1: Registrar al usuario

| ID | Qué haremos para que falle | Qué pasa ahora | Dónde está el código |
|---|---|---|---|
| 1.1 ★ | Ingresar nombres ofensivos | Muestra "Ese nombre no está permitido. Por favor usa otro nombre". Detecta trucos como `w3on`, `WEOOON`, `p.u.t.a` y tildes, sin bloquear palabras normales como "perra" (de mascota) o "computadora". | `moderacion.py`, `validators.validar_nombre_persona` |
| 1.2 | Caracteres especiales o inválidos | Pide eliminar los números y caracteres especiales. Acepta nombres reales como "María-José O'Higgins". | `validators.validar_nombre_persona` |
| 1.3 ★ | Dejar casillas en blanco (o con solo espacios) | Muestra un mensaje en cada casilla: "Escribe tu nombre completo", "Escribe tu correo"… | `forms.RegistroForm` |
| 1.4 | Contraseñas distintas | Muestra "Las contraseñas no coinciden. Escríbelas de nuevo." | `forms.RegistroForm` |
| 1.5 ★ | Correo inexistente | Rechaza formatos inválidos. Sugiere la corrección en errores típicos ("¿Quisiste decir …@gmail.com?"). Bloquea correos desechables y de prueba (mailinator, example.com…). Consulta el DNS para comprobar que el dominio exista y reciba correo. | `validators.validar_correo_real` |

> **Límite honesto del caso 1.5:** se puede comprobar que el *dominio* existe (`@gmail.com`), pero no que exista el *buzón* (`nombre@gmail.com`). Para eso habría que enviar un correo de confirmación con un enlace. Lo dejamos como mejora futura.

## Funcionalidad 2: Foro

| ID | Qué haremos para que falle | Qué pasa ahora | Dónde está el código |
|---|---|---|---|
| 2.1 ★ | Spam de alertas o mensajes | **Alertas:** hay que esperar 60 s entre una y otra. **Chat:** máximo 10 mensajes por minuto; si se pasa, aparece "Estás enviando mensajes muy rápido". Se probó con 40 envíos simultáneos y se guardaron exactamente 10. | `limites.py`, `settings.LIMITES` |
| 2.2 ★ | Escribir insultos | El texto se **censura** (`weón` → `w***`) en alertas, adopciones y chat, y se avisa al usuario. | `moderacion.censurar` |
| 2.3 | Mensaje o alerta en blanco | No se envía y aparece "No escribiste nada. El mensaje está en blanco". | `views.chat_detalle`, `chat.js` |
| 2.4 ★ | Mandar fotos indebidas | ① Solo se aceptan imágenes reales (un archivo falso con extensión `.jpg` se rechaza). ② Máximo 5 MB y sin resoluciones gigantes. ③ Cada foto se vuelve a guardar limpia, sin metadatos EXIF, que pueden incluir la ubicación GPS de tu casa. ④ Botón **Denunciar**: con 3 denuncias de personas distintas la foto se oculta sola, y un admin la revisa en `/admin/` con las acciones "Eliminar la foto" o "Volver a mostrarla". | `validators.procesar_foto`, `views.denunciar`, `admin.py` |
| 2.5 | Mensaje muy largo | Informa el límite: "tiene 5000 caracteres y el límite es 1000". Además, mientras escribes aparece un contador. | `views.chat_detalle`, `forms.MascotaForm` |

> **Límite honesto del caso 2.4:** detectar *automáticamente* si una foto es inapropiada requiere un servicio de inteligencia artificial externo (por ejemplo, Google Cloud Vision SafeSearch). Por eso usamos denuncias más revisión de un administrador, que es lo que hacen la mayoría de los foros.

## Funcionalidad 3: Mapa

| ID | Qué haremos para que falle | Qué pasa ahora | Dónde está el código |
|---|---|---|---|
| 3.1 ★ | Muchas alertas por usuario | Máximo **5 alertas por día** y **10 activas** a la vez. El mensaje explica cuánto falta para poder publicar otra. | `limites.bloqueo_alertas` |
| 3.2 | Publicar alertas iguales | Muestra "Ya tienes una alerta activa igual" con enlaces para verla o editarla. Lo detecta aunque cambien las mayúsculas o los espacios. | `limites.alerta_duplicada` |
| 3.3 ★ | Ubicación inexistente o inválida | Rechaza coordenadas vacías, con texto, `NaN`, fuera de rango o **fuera de Chile** (acepta Isla de Pascua y Juan Fernández). El mapa del formulario avisa en cuanto haces clic. | `validators.validar_ubicacion_chile`, `form_alerta.js` |
| 3.4 | Apretar "Publicar" muchas veces | El botón se desactiva al primer clic. Además, el servidor usa un **código de un solo uso** por formulario y un candado por usuario. Se probó con **30 clics simultáneos**: se guardó 1 sola alerta. | `views.reportar_mascota` |
| 3.5 ★ | Manipular la ubicación o el reporte de otro usuario | Muestra la página **"No tienes acceso"** (error 403). Tampoco se puede publicar a nombre de otra persona enviando su id. | `views._reporte_propio` |

## Pruebas extra de "que no se caiga"

Clase `RobustezTests`:

- **Parámetros raros en la URL** (`?pagina=abc`, `?desde=99999999999999999999`, ids que no existen): ninguna página da error 500.
- **Formularios con datos basura** (fechas imposibles, emojis en coordenadas, 5000 caracteres): se rechazan con mensajes claros.
- **HTML o JavaScript malicioso** en los textos (`<script>`): se muestra como texto y no se ejecuta.
- **Peticiones gigantes** (más de 10 MB): se rechazan antes de procesarlas (error 413).
- **Adivinar contraseñas**: después de 5 intentos fallidos, ese correo queda bloqueado 15 minutos.
- **Redirecciones a sitios externos**: están bloqueadas.
- **2000 alertas en el foro**: la página sigue haciendo solo 2 consultas a la base de datos, porque muestra 10 alertas por página.

## Prueba de carga manual

Con el servidor encendido, se simuló otro equipo intentando botar el sistema:

- 320 visitas simultáneas al mapa, al foro y a la API: todas respondieron bien (200), en unos 3 segundos.
- 30 clics simultáneos en Publicar: se guardó 1 sola alerta.
- 40 mensajes de chat simultáneos: se guardaron 10 y los otros 30 recibieron "espera un minuto".
- Errores 500 en total: **0**.

## Cómo cambiar los límites

Todos los números (alertas por día, mensajes por minuto, denuncias necesarias, largo máximo, etc.) están en `core/settings.py`, en el diccionario `LIMITES`.

Para agregar palabras al filtro de groserías, edita `PALABRAS` en `mascotas/moderacion.py`.

> Nota técnica: los candados anti doble-envío usan la caché de Django, que con la configuración actual funciona dentro de un solo proceso. Es suficiente para `runserver` y para la presentación. Si algún día se publica con varios procesos, habría que configurar una caché compartida, como Redis.

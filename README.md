# bbforo — ClashBang Forum

Foro conmemorativo de **BoomBang**, reconstruido a partir de un scrape de Wayback
Machine. Combina un **archivo histórico de solo lectura** (26 categorías, 351 hilos
y 2.362 mensajes de 2008–2009, con sus autores originales como texto plano) con un
**foro activo** donde los usuarios registrados publican de nuevo.

Producción: <https://foro.clashbang.forum>

## Stack

- Django 6.0.7 · Python 3.12 · PostgreSQL 16 (SQLite en local)
- django-allauth 65 (email + Google/Discord/GitHub) · django-axes · django-csp
- Tailwind compilado (CLI) + Alpine.js y HTMX por CDN
- Cloudflare R2 para estáticos e imágenes (django-storages)
- Nginx + Gunicorn + systemd en el VPS

## Puesta en marcha

```bash
git clone git@github.com:standnc/foroWayBack.git bbforo-app
cd bbforo-app
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt        # o requirements.txt en producción
npm ci                                     # solo si vas a tocar los estilos

cp .env.example .env                       # y rellenar (ver más abajo)
python manage.py migrate
python manage.py createsuperuser
python manage.py crear_categorias_clashbang   # las 8 categorías del foro activo
python manage.py runserver
```

En local basta con `DEBUG=True` en el `.env`: la base de datos por defecto es
SQLite y los estáticos se sirven desde disco.

### Variables de entorno

| Variable | Obligatoria | Notas |
|---|---|---|
| `SECRET_KEY` | **sí con `DEBUG=False`** | Sin ella y en producción, el arranque falla a propósito |
| `DEBUG` | no (default `False`) | |
| `ALLOWED_HOSTS` | sí en producción | Separadas por comas |
| `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | solo PostgreSQL | Sin ellas → SQLite local |
| `ACCOUNT_EMAIL_VERIFICATION` | **`mandatory` en producción** | Ver *Verificación de email* |
| `EMAIL_BACKEND`, `EMAIL_HOST_*` | producción | SMTP con Resend |
| `USE_R2` + `R2_*` | producción | Estáticos y media en Cloudflare R2 |
| `LOG_DIR` | no | Por defecto `logs/` en local, `/var/log/django` en el VPS |

## Estilos (Tailwind)

El CSS se compila con la CLI de Tailwind:

```
static/src/input.css   ──build:css──▶   static/css/app.css   ──▶  Django
```

```bash
npm run build:css      # compila y minifica
npm run watch:css      # recompila al guardar, para desarrollo
```

**`static/css/app.css` se commitea a propósito**: el VPS no tiene Node, así que
lo compila el CI y el servidor solo sirve el artefacto. Si editas
`static/src/input.css` o añades clases nuevas en una plantilla, **recompila y
commitea el resultado** — el CI compara y falla si no coincide.

`tailwind.config.js` incluye `forum/forms.py` en `content` porque los widgets
definen ahí sus clases; sin eso el purgado se lleva los estilos de todos los
formularios.

> **No hay colores `boom`, `coral`, `gold` ni `retro` en el theme, a propósito.**
> Estaban en la config inline del CDN, pero nunca llegaron a aplicarse: se
> asignaba `tailwind = {...}` *antes* de cargar el script del CDN, que crea su
> propio `window.tailwind` y la descartaba. Verificado en producción: `.bg-boom`
> era transparente y `.font-display` no daba Fredoka. Definirlos ahora activaría
> de golpe decenas de clases repartidas por las plantillas y cambiaría el
> diseño — es una decisión de diseño pendiente, no parte de la migración.

### Regresión visual

`scripts/capturar_visual.py` compara el render antes y después de tocar estilos:

```bash
python scripts/capturar_visual.py antes       # con el servidor en :8010
# ... cambios ...
python scripts/capturar_visual.py despues
python scripts/capturar_visual.py --comparar antes despues
```

Captura 8 páginas × 2 temas y compara los estilos computados de 20 selectores
sobre 23 propiedades. Requiere `pip install playwright pillow`.

## Tests

```bash
python -m pytest -q      # 183 tests
ruff check .
```

`pytest.ini` usa `config/test_settings.py`: SQLite en memoria, hasher MD5, axes
desactivado y email en `locmem`.

Dos convenciones no obvias:

- **`client.login()` no funciona**: django-axes exige `request` en `authenticate`.
  Usar `force_login` con backend explícito, o las fixtures `auth_client` /
  `staff_client`.
- **Las factories no deben rellenar campos con `default`.** Que `HiloFactory`
  pasara `creado` a mano ocultó durante todo el proyecto que crear un hilo era
  imposible.

## Despliegue

Push a `master` → GitHub Actions ejecuta `ruff`, `pytest` y `check --deploy`, y
**solo si pasan** entra el job de deploy (`needs: test`), que corre `deploy.sh` en
el VPS: `migrate`, `collectstatic`, `recalcular_contadores` y recarga de Gunicorn.

El CSS lo compila el **CI**, no el servidor: el VPS no tiene Node.

Para relanzarlo sin un commit nuevo:

```bash
gh workflow run "CI + Deploy to VPS" --ref master
```

## Management commands

| Comando | Qué hace |
|---|---|
| `migrar_sqlite --sqlite <ruta>` | Importa el scrape (`foro.db`) a la BD. Fechas aware, `es_clashbang=False`, recalcula contadores al terminar |
| `crear_categorias_clashbang` | Crea/actualiza las 8 categorías del foro activo (idempotente) |
| `crear_posts_iniciales` | Hilo sticky de bienvenida en cada categoría activa |
| `recalcular_contadores [--dry-run]` | Repara `num_hilos` / `num_posts` de categorías e hilos |
| `poblar_perfiles` | Recalcula rango, puntos y color de todos los usuarios |
| `marcar_verificados` | `is_verified=True` para quien ya tenga el email confirmado en allauth |
| `upload_r2` | Descarga las imágenes del archivo y las sube a R2 (resumible) |

## Estructura

```
bbforo-app/
├── accounts/          User (email como identificador), manager, admin
├── forum/             modelos, vistas, formularios, señales, middleware, commands
│   ├── middleware.py  BanEnforcementMiddleware
│   ├── mixins.py      VerifiedRequiredMixin
│   ├── signals.py     rangos + contadores denormalizados
│   └── tests/         183 tests
├── config/            settings, test_settings, urls, wsgi
├── static/src/        input.css — FUENTE de los estilos
├── static/css/        app.css — compilado (commiteado, lo genera el CI)
├── templates/         ← ÁRBOL BUENO (registrado en TEMPLATES["DIRS"])
└── forum/templates/   solo parciales HTMX y el visor de logs
```

> ⚠️ **Hay dos árboles de plantillas y `templates/` gana siempre.** Una vez se
> escribió una feature entera en `forum/templates/index.html` y nunca se sirvió a
> nadie. Comprobar cuál resuelve antes de editar.

## Modelo de visibilidad

No es un muro binario. Anónimos y registrados-sin-verificar ven **lo mismo**:
portada, categorías y títulos de hilos. Lo protegido es el **contenido** de los
mensajes y la **escritura**, vía `VerifiedRequiredMixin`.

### Verificación de email

El gate exige `User.is_verified`, que solo pasa a `True` con la señal
`email_confirmed` de allauth. Con `ACCOUNT_EMAIL_VERIFICATION=none` esa señal
**nunca se dispara** y los usuarios quedan bloqueados sin salida — ya ocurrió en
producción. En cualquier entorno con el gate activo, `mandatory`.

## Limitaciones conocidas

- **CSP: queda `unsafe-eval` en `script-src`** porque Alpine evalúa sus
  expresiones (`x-data`, `@click`) con `new Function`. `unsafe-inline` seguirá
  mientras haya `<script>` inline en `base.html` y `style=""` dinámicos en las
  plantillas. El CDN de Tailwind, que era el motivo principal, ya no está.
- **2.249 de 4.776 imágenes del archivo no son recuperables**: dan 404 real en
  Wayback Machine. Las plantillas caen a `url_original` cuando falta `url_r2`.
- Sin 2FA, sin notificaciones y sin favoritos.

## Documentación

El detalle vive en el workspace, un nivel por encima de este repo:

| Fichero | Contenido |
|---|---|
| `config/DOCUMENTACION.md` | Arquitectura, modelos, seguridad, testing |
| `config/ERRORES.md` | 47 incidentes con causa raíz y lección |
| `config/STATUS.md` | Infraestructura y comandos operativos |
| `config/todos.md` | Plan por fases |

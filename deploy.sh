#!/bin/bash
set -e

echo "🚀 Iniciando despliegue..."
cd /var/www/foroWayBack

# 1. Forzar alineación con GitHub
echo " Descargando últimos cambios..."
git fetch origin
git reset --hard origin/master

# 2. Limpiar residuos (proteger .env, .venv y los logs de la app)
# No es fatal: un residuo de otro propietario (p.ej. creado por www-data) no
# debe impedir el despliegue. Se avisa y se sigue.
echo "🧹 Limpiando residuos..."
git clean -fd -e .env -e .venv/ -e logs/ || echo "⚠️  Quedan residuos sin borrar (permisos); continúo."

# 3. Actualizar dependencias (usar pip, no uv)
echo "📦 Actualizando dependencias..."
source .venv/bin/activate
pip install -r requirements.txt

# 4. Verificar integridad
echo "🔍 Verificando configuración..."
python manage.py check

# 5. Aplicar migraciones
echo "🗄️ Aplicando migraciones..."
python manage.py migrate --noinput

# 6. Recolectar estáticos
echo "🎨 Recolectando estáticos..."
python manage.py collectstatic --noinput

# 7. Contadores al día (idempotente; barato si no hay nada que corregir)
echo "🔢 Recalculando contadores..."
python manage.py recalcular_contadores

# 8. Reiniciar Gunicorn (método HUP)
echo "🔄 Reiniciando Gunicorn..."
kill -HUP $(pgrep -f 'gunicorn.*foro' | head -1)

echo "✅ ¡Despliegue completado con éxito!"

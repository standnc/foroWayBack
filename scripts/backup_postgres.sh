#!/bin/bash
# Backup automatico PostgreSQL + config - Foro WayBack
# Ejecuta pg_dump -Fc, empaqueta configs, rota >7 dias, escribe log.
set -euo pipefail

DB_NAME="foroboombang"
PG_BACKUP_DIR="/var/backups/postgresql"
CFG_BACKUP_DIR="/var/backups/config"
LOG_FILE="/var/log/django/backup.log"
TIMESTAMP=$(date +%Y%m%d_%H%M)
PG_BACKUP_FILE="${PG_BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.dump"
CFG_BACKUP_FILE="${CFG_BACKUP_DIR}/config_backup_${TIMESTAMP}.tar.gz"
RETENTION_DAYS=7

log() {
    local level="$1"
    local msg="$2"
    printf "%s  %-8s  backup  %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${level}" "${msg}" >> "${LOG_FILE}"
}

log "INFO" "=== Iniciando backup PostgreSQL ==="

if ! sudo -u postgres pg_dump -Fc "${DB_NAME}" > "${PG_BACKUP_FILE}" 2>/tmp/pg_dump_err; then
    ERR_MSG=$(cat /tmp/pg_dump_err)
    log "ERROR" "pg_dump fallo: ${ERR_MSG}"
    echo "ERROR: pg_dump fallo: ${ERR_MSG}" >&2
    exit 1
fi

if ! sudo -u postgres pg_restore -l "${PG_BACKUP_FILE}" > /dev/null 2>/tmp/pg_restore_err; then
    ERR_MSG=$(cat /tmp/pg_restore_err)
    log "ERROR" "dump corrupto (pg_restore -l fallo): ${ERR_MSG}"
    rm -f "${PG_BACKUP_FILE}"
    exit 1
fi

PG_SIZE=$(du -h "${PG_BACKUP_FILE}" | cut -f1)
log "INFO" "PostgreSQL backup OK: ${PG_BACKUP_FILE} (${PG_SIZE})"

# Rotar backups PostgreSQL antiguos
find "${PG_BACKUP_DIR}" -name "${DB_NAME}_*.dump" -mtime +${RETENTION_DAYS} -print0 2>/dev/null | while IFS= read -r -d "" f; do
    rm -f "$f"
    log "INFO" "PG backup antiguo eliminado: $(basename "$f")"
done

log "INFO" "=== Iniciando backup de configuracion ==="

mkdir -p "${CFG_BACKUP_DIR}"

# El .env NO entra aquí. Este tarball acabó en su día dentro del bucket de R2,
# y al publicar el bucket por Custom Domain habrian quedado descargables el
# SECRET_KEY, la contrasena de PostgreSQL y las claves de R2 y SMTP. En su lugar
# se guarda el inventario de VARIABLES, sin valores: sirve para reconstruir el
# .env sabiendo que falta, sin llevarse los secretos de paseo.
ENV_INVENTARIO="${CFG_BACKUP_DIR}/env_variables_${TIMESTAMP}.txt"
grep -oE '^[A-Z0-9_]+=' /var/www/foroWayBack/.env 2>/dev/null | tr -d '=' > "${ENV_INVENTARIO}" || true
chmod 600 "${ENV_INVENTARIO}"
log "INFO" "Inventario de variables del .env (sin valores): $(wc -l < "${ENV_INVENTARIO}") claves"

if ! tar -czf "${CFG_BACKUP_FILE}" \
    /var/www/foroWayBack/config/settings.py \
    "${ENV_INVENTARIO}" \
    /etc/nginx/sites-available/ \
    /etc/nginx/sites-enabled/ \
    /etc/systemd/system/foro.service \
    /etc/systemd/system/foro-backup.service \
    /etc/systemd/system/foro-backup.timer \
    /var/www/foroWayBack/scripts/ 2>/tmp/tar_err; then
    ERR_MSG=$(cat /tmp/tar_err)
    log "ERROR" "tar.gz fallo: ${ERR_MSG}"
    echo "ERROR: tar.gz fallo: ${ERR_MSG}" >&2
    exit 1
fi

CFG_SIZE=$(du -h "${CFG_BACKUP_FILE}" | cut -f1)
log "INFO" "Config backup OK: ${CFG_BACKUP_FILE} (${CFG_SIZE})"

# Rotar backups config antiguos (el inventario suelto se va con ellos: dentro
# del tarball ya viaja una copia, la de fuera solo es el intermedio del tar)
find "${CFG_BACKUP_DIR}" \( -name "config_backup_*.tar.gz" -o -name "env_variables_*.txt" \) -mtime +${RETENTION_DAYS} -print0 2>/dev/null | while IFS= read -r -d "" f; do
    rm -f "$f"
    log "INFO" "Config backup antiguo eliminado: $(basename "$f")"
done

log "INFO" "=== Backup completado exitosamente ==="
exit 0

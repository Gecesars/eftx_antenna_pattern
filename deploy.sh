#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/eftx_app/eftx_antenna_pattern"
SERVICE_NAME="eftx"
VENV="/opt/py313"

echo "==> Verificando diretório do app..."
test -d "$APP_DIR" || { echo "App dir não encontrado: $APP_DIR"; exit 1; }

echo "==> Garantindo venv..."
test -x "$VENV/bin/python" || { echo "Venv não encontrado em $VENV"; exit 1; }

echo "==> Convertendo .env para LF e ajustando permissões..."
if [ -f "$APP_DIR/.env" ]; then
  sed -i 's/\r$//' "$APP_DIR/.env"  || true
  chown www-data:www-data "$APP_DIR/.env" || true
  chmod 640 "$APP_DIR/.env" || true
fi

echo "==> Descobrindo PORT (fallback 8000 se ausente)..."
PORT_ENV="$(grep -m1 '^PORT=' "$APP_DIR/.env" 2>/dev/null | cut -d= -f2 || true)"
PORT="${PORT_ENV:-8000}"
echo "PORT detectada: $PORT"

echo "==> Atualizando pacotes…"
apt-get update -y

echo "==> (Opcional) Instalando Redis para rate-limit (Flask-Limiter)…"
apt-get install -y redis-server || true
systemctl enable --now redis-server || true

echo "==> Criando diretórios temporários e permissões…"
mkdir -p /opt/tmp /opt/tmp/mpl
chown -R www-data:www-data /opt/tmp
chown -R www-data:www-data "$APP_DIR"

echo "==> Registrando tmpfiles.d para recriar /opt/tmp no boot…"
cat >/etc/tmpfiles.d/${SERVICE_NAME}.conf <<'EOT'
d /opt/tmp 0755 www-data www-data - -
d /opt/tmp/mpl 0755 www-data www-data - -
EOT

echo "==> (Opcional) Liberando porta no UFW…"
if command -v ufw >/dev/null 2>&1; then
  ufw allow "${PORT}/tcp" || true
fi

echo "==> Criando/atualizando service do systemd…"
cat >/etc/systemd/system/${SERVICE_NAME}.service <<EOT
[Unit]
Description=EFTX Antenna Pattern Designer (Gunicorn)
After=network-online.target redis-server.service
Wants=network-online.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=${APP_DIR}

Environment="PATH=${VENV}/bin"
EnvironmentFile=${APP_DIR}/.env
Environment="TMPDIR=/opt/tmp"
Environment="MPLCONFIGDIR=/opt/tmp/mpl"
Environment="FLASK_APP=app:create_app"
# Fallback para PORT caso não exista no .env
Environment="PORT=${PORT}"

# Migrações antes de subir (remova se não usar Flask-Migrate)
ExecStartPre=/bin/mkdir -p /opt/tmp /opt/tmp/mpl
ExecStartPre=/bin/chown -R www-data:www-data /opt/tmp
ExecStartPre=${VENV}/bin/flask db upgrade

# Processo principal (sem --factory, usando run:app)
ExecStart=${VENV}/bin/gunicorn run:app \\
  --workers 3 --bind 0.0.0.0:\${PORT} --timeout 180 \\
  --access-logfile - --error-logfile -

ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=5
TimeoutStartSec=60
KillMode=mixed
LimitNOFILE=65536

# Hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=${APP_DIR} /opt/tmp
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
LockPersonality=true
CapabilityBoundingSet=
AmbientCapabilities=

[Install]
WantedBy=multi-user.target
EOT

echo "==> Aplicando configurações e iniciando serviço…"
systemd-tmpfiles --create || true
systemctl daemon-reload
systemctl enable --now ${SERVICE_NAME}

echo "==> Status do serviço:"
systemctl status ${SERVICE_NAME} --no-pager || true

echo "==> Logs (Ctrl+C para sair):"
journalctl -u ${SERVICE_NAME} -f

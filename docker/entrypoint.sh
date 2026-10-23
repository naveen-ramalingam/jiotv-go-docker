#!/bin/sh
set -eu

if [ "${1:-serve}" != "serve" ]; then
  exec su-exec jiotv:jiotv /usr/local/bin/jiotv_go "$@"
fi
[ "$#" -eq 0 ] || shift
umask 077
mkdir -p /data/logs /tls
chmod 0700 /data /data/logs
chown -Rh jiotv:jiotv /data

# All application logs go to stdout; Docker's logging driver rotates them.
# Preserve an existing regular log file if a user deliberately supplied one.
if [ ! -e /data/logs/jiotv_go.log ] && [ ! -L /data/logs/jiotv_go.log ]; then
  ln -s /dev/null /data/logs/jiotv_go.log
  chown -h jiotv:jiotv /data/logs/jiotv_go.log
fi

if [ -f /tls/server.crt ] && [ -f /tls/server.key ]; then
  :
elif [ -e /tls/server.crt ] || [ -e /tls/server.key ]; then
  printf 'Both /tls/server.crt and /tls/server.key are required.\n' >&2
  exit 1
else
  san='DNS:localhost,IP:127.0.0.1'
  for name in $(printf '%s' "${JIOTV_TLS_NAMES:-}" | tr ',' ' '); do
    case "$name" in
      *[!a-zA-Z0-9.:-]*) printf 'Invalid TLS hostname/IP.\n' >&2; exit 1 ;;
    esac
    if printf '%s' "$name" | grep -Eq '^([0-9]+\.){3}[0-9]+$|:'; then
      san="$san,IP:$name"
    else
      san="$san,DNS:$name"
    fi
  done
  openssl req -x509 -newkey rsa:2048 -sha256 -nodes -days 825 \
    -keyout /tls/server.key -out /tls/server.crt \
    -subj '/CN=JioTV Go local server' -addext "subjectAltName=$san" >/dev/null 2>&1
  printf 'Generated a local TLS certificate in the persistent /tls volume.\n'
fi
chown root:jiotv /tls /tls/server.key /tls/server.crt
chmod 0750 /tls
chmod 0640 /tls/server.key
chmod 0644 /tls/server.crt

exec su-exec jiotv:jiotv /usr/local/bin/jiotv_go \
  --skip-update-check --config /etc/jiotv-go/config.toml \
  serve --host 0.0.0.0 --port 5002 --tls \
  --tls-cert /tls/server.crt --tls-key /tls/server.key "$@"

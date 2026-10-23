#!/bin/sh
set -eu
exec curl --fail --silent --show-error --max-time 5 \
  --cacert /tls/server.crt --output /dev/null https://127.0.0.1:5002/

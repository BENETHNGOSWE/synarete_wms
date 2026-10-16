#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/mnt/d/2026/BENETH/CLIENTS/SYNARATE/synarate-local/frappe-setup}"
SITE="${SITE:-erp.synarete.co.tz}"

cd "$PROJECT_DIR"
unset DOCKER_HOST

docker compose up -d

docker compose exec backend bench --site "$SITE" migrate
docker compose exec backend bench --site "$SITE" execute synarete_wms.utils.workflows.ensure_wms_workflows
docker compose exec backend bench --site "$SITE" clear-cache
docker compose exec backend bench --site "$SITE" list-apps

if docker compose exec -T backend bash -lc 'command -v node >/dev/null 2>&1'; then
  docker compose exec backend bench build --app synarete_wms
else
  echo "WARNING: node is not installed in the local backend image; asset build was skipped."
fi

docker compose exec backend bench --site "$SITE" run-tests --app synarete_wms

echo "Local WMS smoke test completed."

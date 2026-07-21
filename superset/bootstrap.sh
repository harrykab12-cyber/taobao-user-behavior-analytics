#!/bin/sh
set -eu

superset db upgrade

if ! superset fab list-users | grep -Fq "$SUPERSET_ADMIN_USERNAME"; then
  superset fab create-admin \
    --username "$SUPERSET_ADMIN_USERNAME" \
    --firstname Local \
    --lastname Admin \
    --email local-admin@example.invalid \
    --password "$SUPERSET_ADMIN_PASSWORD"
fi

superset init

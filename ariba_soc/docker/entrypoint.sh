#!/bin/sh
set -e

python manage.py migrate --noinput

if [ "$SKIP_COLLECTSTATIC" != "1" ]; then
    python manage.py collectstatic --noinput
fi

exec "$@"

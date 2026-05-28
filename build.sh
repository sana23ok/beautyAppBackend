#!/usr/bin/env bash
# Render build script (also usable locally on Linux/macOS)
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput

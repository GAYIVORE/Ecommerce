#!/bin/bash
# Build script for Vercel deployment.
# 1) Installs Python deps, 2) builds Tailwind CSS, 3) collects static files.
set -e

echo "Installing Python dependencies..."
pip install --break-system-packages -r requirements.txt

echo "Installing Node dependencies and building Tailwind CSS..."
npm install
node ./node_modules/tailwindcss/lib/cli.js -i ./static/css/input.css -o ./static/css/style.css --minify

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear
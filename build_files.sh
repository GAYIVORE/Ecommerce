#!/bin/bash
# Build script for Vercel deployment.
# 1) Installs Python deps, 2) builds Tailwind CSS, 3) collects static files.
set -e

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Installing Node dependencies and building Tailwind CSS..."
npm install
npx tailwindcss -i ./static/css/input.css -o ./static/css/style.css --minify

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

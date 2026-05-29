@echo off
cd /d "%~dp0"
set PGSSLMODE=
set POSTGRES_SSL=
".venv\Scripts\python.exe" manage.py runserver 0.0.0.0:8000

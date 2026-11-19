@echo off
cd /d "%~dp0"
python -c "import requests, pandas" 2>nul
if not %errorlevel%==0 (
  echo Primero abre INICIAR.bat una vez para instalar lo necesario.
  pause
  exit /b
)
echo Iniciando el bot de Telegram de Tutor Tec...
python telegram_bot.py
pause

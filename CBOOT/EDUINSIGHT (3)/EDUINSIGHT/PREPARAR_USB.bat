@echo off
cd /d "%~dp0"
echo Descargando los paquetes de Python a la carpeta "paquetes"...
echo (Hazlo en una compu CON internet y luego copia esa carpeta por USB.)
echo.
python --version
python -m pip download -r requirements.txt -d paquetes --timeout 120 --retries 10 --disable-pip-version-check
echo.
echo Listo. Copia la carpeta "paquetes" dentro de la carpeta EDUINSIGHT
echo de la otra compu y ahi abre INICIAR.bat.
echo IMPORTANTE: las dos compus deben tener la misma version de Python (la de arriba).
pause

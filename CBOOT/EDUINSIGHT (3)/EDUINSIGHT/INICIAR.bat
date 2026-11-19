@echo off
cd /d "%~dp0"

rem Evita la pregunta del correo de Streamlit
if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
  echo [general]> "%USERPROFILE%\.streamlit\credentials.toml"
  echo email = "">> "%USERPROFILE%\.streamlit\credentials.toml"
)

rem Borra entornos virtuales rotos de versiones anteriores
if exist venv rmdir /s /q venv

rem Si ya esta todo instalado, arranca directo (sin internet)
python -c "import streamlit, plotly, networkx, pandas, requests" 2>nul
if %errorlevel%==0 goto correr

rem Si hay carpeta "paquetes" (traida por USB), instala desde ahi sin internet
if exist paquetes (
  echo Instalando desde la carpeta paquetes, sin internet...
  python -m pip install --no-index --find-links paquetes -r requirements.txt --disable-pip-version-check
) else (
  echo Instalando dependencias, necesita internet...
  python -m pip install -r requirements.txt --timeout 120 --retries 10 --disable-pip-version-check
)

python -c "import streamlit, plotly, networkx, pandas, requests" 2>nul
if not %errorlevel%==0 (
  echo.
  echo ============================================================
  echo  No se pudieron instalar las dependencias.
  echo  Opciones: conectate a los datos del celular, o en una compu
  echo  donde la app ya funcione ejecuta PREPARAR_USB.bat y copia la
  echo  carpeta "paquetes" a esta carpeta.
  echo ============================================================
  pause
  exit /b
)

:correr
echo Abriendo EDUINSIGHT en el navegador...
python -m streamlit run Inicio.py
pause

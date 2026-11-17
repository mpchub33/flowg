@echo off
setlocal
cd /d "%~dp0"
set FOLLOW_SUBJECT_HOST=127.0.0.1
set FOLLOW_SUBJECT_OPEN_BROWSER=1
set PORT=8501
set PYTHONUTF8=1

where py >nul 2>&1
if errorlevel 1 goto missing_launcher

if not exist ".venv\Scripts\python.exe" (
  py -3.11 --version >nul 2>&1
  if errorlevel 1 (
    echo Python 3.11 no esta instalado. Descargandolo e instalando el runtime...
    py install 3.11
    if errorlevel 1 goto missing_python
    py -3.11 --version >nul 2>&1
    if errorlevel 1 goto missing_python
  )
  echo Creando entorno virtual con Python 3.11...
  py -3.11 -m venv .venv
  if errorlevel 1 goto missing_python
)

if not exist ".venv\Scripts\python.exe" goto missing_python
echo.
echo Instalando o verificando dependencias. La primera vez puede tardar varios minutos...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto install_error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto install_error

echo.
echo Comprobando aceleracion disponible:
".venv\Scripts\python.exe" comprobar_gpu.py
echo.
echo La interfaz se abrira en http://127.0.0.1:8501. Deja esta ventana abierta mientras la usas.
".venv\Scripts\python.exe" app.py
pause
exit /b 0

:missing_launcher
echo No se encontro el lanzador de Python "py".
echo Instala Python 3.11 de 64 bits desde python.org y vuelve a ejecutar este archivo.
pause
exit /b 1

:missing_python
echo No se pudo instalar o iniciar Python 3.11.
echo Puedes intentarlo manualmente en PowerShell con: py install 3.11
pause
exit /b 1

:install_error
echo Fallo la instalacion de dependencias. Revisa la conexion a internet y el mensaje anterior.
pause
exit /b 1

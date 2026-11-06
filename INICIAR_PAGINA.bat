@echo off
chcp 65001 >nul
title PataSegura - servidor
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
echo ==========================================================
echo    PataSegura - preparando la pagina (no cierres esta ventana)
echo ==========================================================
echo.

rem --- Buscar un Python 3.12 o superior ---
set "PY="
python -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)" <nul >nul 2>nul && set "PY=python"
if not defined PY (
  py -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)" <nul >nul 2>nul && set "PY=py"
)
if not defined PY (
  echo [X] No encontre Python 3.12 o superior en este computador.
  echo     Descargalo desde https://www.python.org/downloads/
  echo     y en el instalador marca "Add python.exe to PATH".
  echo.
  python --version 2>nul
  py --version 2>nul
  goto fin
)
for /f "delims=" %%v in ('%PY% --version') do echo Usando %%v
echo.

if not exist "venv\Scripts\python.exe" (
  echo [1/5] Creando entorno virtual...
  %PY% -m venv venv <nul || goto error
) else (
  echo [1/5] Entorno virtual listo.
)

echo [2/5] Instalando librerias. La primera vez tarda 1 o 2 minutos...
"venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt <nul || goto error

echo [3/5] Preparando la base de datos...
"venv\Scripts\python.exe" manage.py migrate -v 0 <nul || goto error

echo [4/5] Cargando datos de ejemplo...
"venv\Scripts\python.exe" manage.py cargar_demo <nul

echo.
echo ==========================================================
echo  [5/5] LISTO: la pagina esta en  http://127.0.0.1:8000
echo        Cuenta de prueba:  demo@patasegura.cl  /  patasegura123
echo        Deja esta ventana abierta mientras pruebas.
echo        Para apagar la pagina: Ctrl + C  o cierra esta ventana.
echo ==========================================================
echo.
"venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000 --noreload
goto fin

:error
echo.
echo [X] Algo fallo. Saca una captura de esta ventana y mandasela a Claude.

:fin
echo.
pause

@echo off
title Sistema Soma Entrenamientos - Instalador
echo.
echo ========================================
echo   SOMA ENTRENAMIENTOS - INSTALADOR
echo ========================================
echo.

echo Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no encontrado. Instale Python 3.11+ desde python.org
    pause
    exit /b 1
)

echo ✅ Python encontrado

echo.
echo Creando entorno virtual...
if not exist ".venv" (
    python -m venv .venv
    echo ✅ Entorno virtual creado
) else (
    echo ✅ Entorno virtual ya existe
)

echo.
echo Activando entorno virtual...
call .venv\Scripts\activate

echo.
echo Actualizando pip...
python -m pip install --upgrade pip

echo.
echo Instalando dependencias...
pip install -r requirements.txt

echo.
echo ========================================
echo   INSTALACIÓN COMPLETADA
echo ========================================
echo.
echo ✅ Dependencias instaladas correctamente
echo.
echo 🚀 OPCIONES DE EJECUCIÓN:
echo.
echo 1. Ejecutar como módulo (Recomendado):
echo    python -m app.main
echo.
echo 2. Ejecutar archivo principal:
echo    python run.py
echo.
echo 3. Ejecutar desde app/main.py:
echo    python app/main.py
echo.
echo 4. Crear ejecutable:
echo    python crear_exe.py
echo.

:menu
echo.
echo ¿Qué desea hacer?
echo 1. Ejecutar aplicación
echo 2. Crear ejecutable
echo 3. Salir
echo.
set /p choice="Seleccione una opción (1-3): "

if "%choice%"=="1" (
    echo.
    echo 🚀 Iniciando Soma Entrenamientos...
    python -m app.main
    goto menu
) else if "%choice%"=="2" (
    echo.
    echo 🔨 Creando ejecutable...
    python crear_exe.py
    goto menu
) else if "%choice%"=="3" (
    echo.
    echo 👋 ¡Hasta luego!
    pause
    exit /b 0
) else (
    echo.
    echo ❌ Opción inválida. Intente de nuevo.
    goto menu
)

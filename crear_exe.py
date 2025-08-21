import subprocess
import sys
import os
import shutil

def crear_ejecutable():
    """Crea el ejecutable usando PyInstaller"""
    
    print("🔨 Creando ejecutable para Soma Entrenamientos...")
    
    # Comando PyInstaller
    cmd = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        "--name", "SomaEntrenamientos",
        "--icon=app/assets/icon.ico",
        "--add-data", "app/assets;app/assets",  # Windows: src;dest
        "app/main.py"
    ]
    
    try:
        # Ejecutar PyInstaller
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Ejecutable creado exitosamente")
        
        # Crear carpeta de distribución
        dist_folder = "distribucion_SomaEntrenamientos"
        if os.path.exists(dist_folder):
            shutil.rmtree(dist_folder)
        os.makedirs(dist_folder)
        
        # Copiar ejecutable
        exe_source = "dist/SomaEntrenamientos.exe"
        exe_dest = f"{dist_folder}/SomaEntrenamientos.exe"
        shutil.copy2(exe_source, exe_dest)
        
        # Crear archivo LEEME.txt
        leeme_content = """
SOMA ENTRENAMIENTOS - SISTEMA DE GESTIÓN
=======================================

INSTALACIÓN:
1. Copie la carpeta completa a la ubicación deseada
2. Ejecute SomaEntrenamientos.exe

PRIMER USO:
- El sistema creará automáticamente las carpetas necesarias:
  * data/ (base de datos)
  * backups/ (copias de seguridad)
  * logs/ (registros del sistema)

CARACTERÍSTICAS:
- Sistema 100% local (no requiere internet)
- Base de datos SQLite integrada
- Backups automáticos diarios
- Exportación a Excel
- Modo kiosco para consulta de socios

SOPORTE:
- Los datos se guardan en la carpeta 'data/'
- Los backups se crean automáticamente en 'backups/'
- Los logs del sistema están en 'logs/'

IMPORTANTE:
- Realice backups regulares desde la aplicación
- No elimine las carpetas data/, backups/ o logs/
- Para migrar a otra PC, copie toda la carpeta

Versión: 1.0
Desarrollado para Soma Entrenamientos
"""
        
        with open(f"{dist_folder}/LEEME.txt", "w", encoding="utf-8") as f:
            f.write(leeme_content)
        
        print(f"📦 Distribución creada en: {dist_folder}/")
        print("✅ ¡Listo para distribuir!")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creando ejecutable: {e}")
        print(f"Salida: {e.stdout}")
        print(f"Error: {e.stderr}")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    crear_ejecutable()

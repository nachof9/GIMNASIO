import subprocess
import sys
import os
import shutil

try:
    from PIL import Image
except Exception:
    Image = None

def crear_ejecutable():
    """Crea el ejecutable usando PyInstaller"""
    
    print("🔨 Creando ejecutable para Soma Entrenamientos...")
    
    # Preparar ícono: usar app/assets/icon.ico si existe, si no, intentar generar desde logo_soma.png.
    icon_path = os.path.join("app", "assets", "icon.ico")
    if not os.path.exists(icon_path):
        png_path = os.path.join("app", "assets", "logo_soma.png")
        if Image and os.path.exists(png_path):
            try:
                img = Image.open(png_path)
                # Convertir a cuadrado si hace falta (con padding blanco)
                size = max(img.size)
                square = Image.new("RGBA", (size, size), (255, 255, 255, 0))
                square.paste(img, ((size - img.width) // 2, (size - img.height) // 2))
                # Guardar ICO con múltiples tamaños
                square.save(icon_path, format='ICO', sizes=[(256,256), (128,128), (64,64), (48,48), (32,32), (16,16)])
                print(f"🖼️  Generado icono: {icon_path}")
            except Exception as e:
                print(f"⚠️  No se pudo generar icono desde PNG: {e}. Se continuará sin ícono personalizado.")

    # Comando PyInstaller (usamos el intérprete actual para evitar problemas de PATH)
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--noconsole",
        "--name", "SomaEntrenamientos",
    ]
    # Agregar ícono si existe
    if os.path.exists(icon_path):
        cmd += ["--icon", icon_path]
    # Agregar assets (duplicado en dos ubicaciones para compatibilidad)
    # - app/assets -> assets (lo usa resource_path local de main.py)
    # - app/assets -> app/assets (lo usa config.resource_path)
    cmd += [
        "--add-data", "app/assets;assets",
        "--add-data", "app/assets;app/assets",
        "run.py"
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
        
        # Crear Iniciar.bat que setea SOMA_OWNER_PIN si está definido
        owner_pin = os.getenv("SOMA_OWNER_PIN", "soma1234")
        iniciar_bat = f"""@echo off
cd /d "%~dp0"
set SOMA_OWNER_PIN={owner_pin}
start "" SomaEntrenamientos.exe
"""
        with open(f"{dist_folder}/Iniciar.bat", "w", encoding="utf-8") as f:
            f.write(iniciar_bat)
        
        # Crear archivo LEEME.txt
        leeme_content = """
SOMA ENTRENAMIENTOS - SISTEMA DE GESTIÓN
=======================================

INSTALACIÓN:
1. Copie la carpeta completa a la ubicación deseada (ej.: C:\\SomaEntrenamientos)
2. (Opcional) Edite el PIN en Iniciar.bat: set SOMA_OWNER_PIN=mi_pin
3. Ejecute Iniciar.bat (recomendado) o SomaEntrenamientos.exe

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

PIN DEL DUEÑO:
- Puede cambiar el PIN editando Iniciar.bat (variable SOMA_OWNER_PIN)
- Si no usa Iniciar.bat, defina SOMA_OWNER_PIN antes de abrir el exe

Versión: 1.0
Desarrollado para Soma Entrenamientos
"""
        
        with open(f"{dist_folder}/LEEME.txt", "w", encoding="utf-8") as f:
            f.write(leeme_content)

        # Crear script para crear acceso directo en el escritorio
        acceso_bat = r"""@echo off
cd /d "%~dp0"
echo Set oWS = WScript.CreateObject("WScript.Shell") > create_shortcut.vbs
echo sDesktop = CreateObject("WScript.Shell").SpecialFolders("Desktop") >> create_shortcut.vbs
echo sLinkFile = sDesktop ^& "\Soma Entrenamientos.lnk" >> create_shortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> create_shortcut.vbs
echo oLink.TargetPath = CreateObject("Scripting.FileSystemObject").GetAbsolutePathName("Iniciar.bat") >> create_shortcut.vbs
echo oLink.WorkingDirectory = CreateObject("Scripting.FileSystemObject").GetAbsolutePathName(".") >> create_shortcut.vbs
echo oLink.IconLocation = CreateObject("Scripting.FileSystemObject").GetAbsolutePathName("SomaEntrenamientos.exe") ^& ",0" >> create_shortcut.vbs
echo oLink.Save >> create_shortcut.vbs
cscript //nologo create_shortcut.vbs
del create_shortcut.vbs
echo Acceso directo creado en el escritorio.
pause
"""
        with open(f"{dist_folder}/CrearAccesoDirecto.bat", "w", encoding="utf-8") as f:
            f.write(acceso_bat)
        
        print(f"📦 Distribución creada en: {dist_folder}/")
        print("✅ ¡Listo para distribuir!")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creando ejecutable: {e}")
        print(f"Salida: {e.stdout}")
        print(f"Error: {e.stderr}")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        print("Sugerencias:")
        print("- Asegúrate de tener PyInstaller instalado en este intérprete: pip install pyinstaller")
        print("- Ejecuta con este mismo Python: python crear_exe.py")

if __name__ == "__main__":
    crear_ejecutable()

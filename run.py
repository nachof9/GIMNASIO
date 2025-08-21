#!/usr/bin/env python3
"""
Archivo de entrada principal para Soma Entrenamientos
Ejecutar con: python run.py
"""

import sys
import os

# Agregar la carpeta raíz al path de Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar la aplicación principal
from app.main import main

if __name__ == "__main__":
    try:
        print("🚀 Iniciando Soma Entrenamientos...")
        main()
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        print("💡 Asegúrate de tener todas las dependencias instaladas:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        sys.exit(1)

import os
import sys
from datetime import datetime
from pathlib import Path

# Colores oficiales
COLORS = {
    'SOMA_ORANGE': '#E6461A',
    "SUCCESS_GREEN": "#28a745",
    "INFO_BLUE": "#17a2b8",
    'ACTIVE_GREEN': '#4CAF50', 
    'EXPIRED_RED': '#F44336',
    'TEXT_DARK': '#1B1B1B',
    'WHITE': '#FFFFFF',
    'TEXT_SECONDARY': '#6C757D',
    'SOMA_ORANGE_DARK': "#FC3903",
    'WARNING_AMBER': '#FF9800'    
}

# Configuración de fuentes globales
FONTS = {
    'TITLE_LARGE': {'size': 48, 'weight': 'bold'},      # Títulos principales
    'TITLE_MEDIUM': {'size': 36, 'weight': 'bold'},     # Títulos de sección
    'TITLE_SMALL': {'size': 28, 'weight': 'bold'},      # Títulos de subsección
    'HEADER': {'size': 24, 'weight': 'bold'},            # Encabezados
    'SUBTITLE': {'size': 20, 'weight': 'bold'},          # Subtítulos
    'BODY_LARGE': {'size': 18, 'weight': 'normal'},     # Texto del cuerpo grande
    'BODY_MEDIUM': {'size': 16, 'weight': 'normal'},    # Texto del cuerpo mediano
    'BODY_SMALL': {'size': 14, 'weight': 'normal'},     # Texto del cuerpo pequeño
    'CAPTION': {'size': 12, 'weight': 'normal'},         # Texto de captura
    'BUTTON': {'size': 16, 'weight': 'bold'},            # Texto de botones
    'INPUT': {'size': 16, 'weight': 'normal'},           # Texto de entrada
    'LABEL': {'size': 16, 'weight': 'normal'},           # Texto de etiquetas
    'TABLE_HEADER': {'size': 16, 'weight': 'bold'},      # Encabezados de tabla
    'TABLE_DATA': {'size': 14, 'weight': 'normal'},      # Datos de tabla
}

# Configuración
DIAS_CUOTA = 30
DIAS_ALERTA = 7
POPUP_AUTOCLOSE_SECONDS = 4

BACKUP_CONFIG = {
    "auto_backup_hours": 24,  # Backup automático cada 6 horas
    "max_backups": 30,       # Máximo 30 backups
    "compress_after_days": 7, # Comprimir backups después de 7 días
    "verify_integrity": True  # Verificar integridad de backups
}

ALERT_CONFIG = {
    "vencimiento_dias": [1, 3, 7],  # Alertas de vencimiento
    "inactividad_dias": 15,         # Días sin visitas para considerar inactivo
    "max_alertas_dashboard": 5,     # Máximo alertas en dashboard
    "refresh_interval_minutes": 5   # Actualizar dashboard cada 5 minutos
}

# Sonidos (frecuencia Hz, duración ms)
SOUNDS = {
    'ACTIVE': (1000, 220),
    'EXPIRED': [(400, 250), (400, 250)],  # doble beep
    'NOT_REGISTERED': (600, 300)
}

def resource_path(relative_path):
    """Obtiene la ruta absoluta del recurso, compatible con PyInstaller"""
    try:
        # PyInstaller crea una carpeta temporal y almacena la ruta en _MEIPASS
        base_path = sys._MEIPASS
        return os.path.join(base_path, "app", relative_path)
    except AttributeError:
        # En desarrollo
        base_path = os.path.dirname(__file__)
        return os.path.join(base_path, relative_path)

def ensure_directories():
    """Crea las carpetas necesarias si no existen"""
    directories = ['data', 'backups', 'logs']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)

def get_data_path() -> Path:
    """Retorna el path de la carpeta data"""
    return Path("data")

def get_backup_path() -> Path:
    """Retorna el path de la carpeta backups"""
    return Path("backups")

def get_log_filename():
    """Retorna el nombre del archivo de log del día actual"""
    today = datetime.now().strftime("%Y%m%d")
    return f"logs/sistema_{today}.log"

def get_backup_filename():
    """Retorna el nombre del archivo de backup del día actual"""
    today = datetime.now().strftime("%Y%m%d")
    return f"backups/sistema_{today}.db"

def generate_backup_filename() -> str:
    """Genera nombre de archivo de backup con timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"sistema_backup_{timestamp}.db"

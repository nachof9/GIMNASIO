# Soma Entrenamientos - Sistema de Gestión

Sistema de gestión integral para gimnasios desarrollado en Python con CustomTkinter.

## Características

- **100% Local**: No requiere conexión a internet
- **Interfaz Moderna**: CustomTkinter con modo oscuro
- **Base de Datos**: SQLite integrada
- **Modo Kiosco**: Consulta autoservicio para socios
- **Gestión Completa**: Socios, pagos, ingresos y reportes
- **Exportación**: Excel con múltiples formatos
- **Backups Automáticos**: Copias de seguridad diarias

## Instalación

### Opción 1: Ejecutable (Recomendado)
1. Descargue la carpeta `distribucion_SomaEntrenamientos`
2. Ejecute `SomaEntrenamientos.exe`

### Opción 2: Desde código fuente
1. Clone o descargue el repositorio
2. Ejecute `install.bat` (Windows)
3. O manualmente:
   \`\`\`bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   python -m app.main
   \`\`\`

## Uso

### Modo Kiosco
- Pestaña "Consulta" para que los socios verifiquen su estado
- Ingreso de DNI y consulta automática
- Respuesta visual y sonora según estado

### Gestión de Socios
- Alta, edición y eliminación de socios
- Búsqueda y filtros avanzados
- Historial de pagos por socio

### Reportes
- KPIs en tiempo real
- Métricas avanzadas
- Exportación a Excel

## Estructura de Archivos

\`\`\`
soma-entrenamientos/
├── app/
│   ├── main.py              # Aplicación principal
│   ├── db.py                # Gestor de base de datos
│   ├── admin_windows.py     # Ventanas modales
│   ├── import_export.py     # Importación/Exportación
│   ├── config.py            # Configuración
│   └── assets/              # Recursos (logo, icono)
├── data/                    # Base de datos
├── backups/                 # Copias de seguridad
├── logs/                    # Registros del sistema
└── crear_exe.py             # Script para crear ejecutable
\`\`\`

## Desarrollo

### Crear Ejecutable
\`\`\`bash
python crear_exe.py
\`\`\`

### Estructura de Base de Datos
- `socios`: Información de socios
- `pagos`: Registro de pagos
- `ingresos`: Historial de consultas
- `logs`: Registros del sistema

## Soporte

- Los datos se almacenan en `data/sistema_gym.db`
- Backups automáticos en `backups/`
- Logs del sistema en `logs/`

Para migrar a otra PC, copie toda la carpeta del sistema.

## Licencia

Desarrollado para Soma Entrenamientos.

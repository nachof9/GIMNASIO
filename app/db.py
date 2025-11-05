import sqlite3
import os
import shutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from .config import DIAS_CUOTA, get_backup_filename, ensure_directories
from .backup_manager import BackupManager

class DatabaseManager:
    def __init__(self, db_path="data/sistema_gym.db"):
        ensure_directories()
        self.db_path = db_path
        self.init_database()
        self.backup_manager = BackupManager(self.db_path)
        self.backup_manager.start_auto_backup()
        self.backup_automatico()
    
    def init_database(self):
        """Inicializa la base de datos con las tablas necesarias"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabla socios
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS socios (
                    dni INTEGER PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    email TEXT,
                    telefono TEXT,
                    fecha_alta DATE
                )
            ''')
            
            # Tabla pagos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pagos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dni INTEGER NOT NULL,
                    monto REAL NOT NULL,
                    fecha_pago DATE NOT NULL,
                    metodo_pago TEXT CHECK (metodo_pago IN ('efectivo', 'transferencia')) NOT NULL,
                    FOREIGN KEY (dni) REFERENCES socios(dni)
                )
            ''')
            
            # Tabla ingresos (consultas de cuota)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ingresos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dni INTEGER,
                    nombre TEXT,
                    estado TEXT,
                    fecha DATETIME
                )
            ''')
            
            # Tabla logs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    evento TEXT,
                    detalle TEXT,
                    fecha DATETIME
                )
            ''')
            
            # Índices
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pagos_dni_fecha ON pagos(dni, fecha_pago)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ingresos_fecha ON ingresos(fecha)')
            
            conn.commit()
    
    def backup_automatico(self):
        """Realiza backup automático si no existe el del día actual"""
        backup_path = get_backup_filename()
        if not os.path.exists(backup_path):
            try:
                shutil.copy2(self.db_path, backup_path)
                logging.info(f"Backup automático creado: {backup_path}")
            except Exception as e:
                logging.error(f"Error en backup automático: {e}")
    
    def backup_manual(self) -> str:
        """Realiza backup manual con timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"backups/sistema_manual_{timestamp}.db"
        try:
            shutil.copy2(self.db_path, backup_path)
            logging.info(f"Backup manual creado: {backup_path}")
            return backup_path
        except Exception as e:
            logging.error(f"Error en backup manual: {e}")
            raise

    def create_incremental_backup(self, description: str = "") -> Dict:
        """Crea backup incremental usando BackupManager"""
        return self.backup_manager.create_backup(description)
    
    def get_backup_list(self) -> List[Dict]:
        """Obtiene lista de backups disponibles"""
        return self.backup_manager.get_backup_list()
    
    def restore_from_backup(self, backup_filename: str) -> Dict:
        """Restaura desde backup usando BackupManager"""
        return self.backup_manager.restore_backup(backup_filename)
    
    def stop_auto_backup(self):
        """Detiene el sistema de backup automático"""
        if hasattr(self, 'backup_manager'):
            self.backup_manager.stop_auto_backup_system()

    # SOCIOS
    def agregar_socio(self, dni: int, nombre: str, email: Optional[str], telefono: Optional[str], fecha_alta: str) -> None:
        """Agrega un nuevo socio"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO socios (dni, nombre, email, telefono, fecha_alta)
                VALUES (?, ?, ?, ?, ?)
            ''', (dni, nombre, email, telefono, fecha_alta))
            conn.commit()
            logging.info(f"Socio agregado: DNI {dni}, {nombre}")
    
    def editar_socio(self, dni: int, nombre: str, email: Optional[str], telefono: Optional[str]) -> None:
        """Edita un socio existente"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE socios SET nombre=?, email=?, telefono=?
                WHERE dni=?
            ''', (nombre, email, telefono, dni))
            conn.commit()
            logging.info(f"Socio editado: DNI {dni}")
    
    def eliminar_socio_y_pagos(self, dni: int) -> None:
        """Elimina un socio y todos sus pagos"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM pagos WHERE dni=?', (dni,))
            cursor.execute('DELETE FROM socios WHERE dni=?', (dni,))
            conn.commit()
            logging.info(f"Socio eliminado: DNI {dni}")
    
    def cambiar_dni_socio(self, dni_actual: int, nuevo_dni: int) -> None:
        """Cambia el DNI de un socio y actualiza referencias en pagos/ingresos.

        Nota: No se usa ON UPDATE CASCADE. Actualizamos manualmente en una transacción.
        """
        if dni_actual == nuevo_dni:
            return
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Validaciones
            cursor.execute('SELECT 1 FROM socios WHERE dni=?', (dni_actual,))
            if cursor.fetchone() is None:
                raise ValueError(f"No existe socio con DNI {dni_actual}")
            cursor.execute('SELECT 1 FROM socios WHERE dni=?', (nuevo_dni,))
            if cursor.fetchone() is not None:
                raise ValueError(f"Ya existe un socio con DNI {nuevo_dni}")

            try:
                cursor.execute('BEGIN')
                # Actualizar pagos e ingresos primero (no hay FK ON UPDATE)
                cursor.execute('UPDATE pagos SET dni=? WHERE dni=?', (nuevo_dni, dni_actual))
                cursor.execute('UPDATE ingresos SET dni=? WHERE dni=?', (nuevo_dni, dni_actual))
                # Actualizar socio
                cursor.execute('UPDATE socios SET dni=? WHERE dni=?', (nuevo_dni, dni_actual))
                conn.commit()
                logging.info(f"DNI cambiado: {dni_actual} -> {nuevo_dni}")
            except Exception as e:
                conn.rollback()
                logging.error(f"Error cambiando DNI {dni_actual} -> {nuevo_dni}: {e}")
                raise
    
    def obtener_socio(self, dni: int) -> Optional[Dict]:
        """Obtiene un socio por DNI"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM socios WHERE dni=?', (dni,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def buscar_socios(self, texto: str, limite: int = 50) -> List[Dict]:
        """Busca socios por nombre o coincidencia de DNI (texto parcial)."""
        texto = texto.strip()
        if not texto:
            return []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            like = f"%{texto}%"
            cursor.execute(
                '''
                SELECT dni, nombre, email, telefono
                FROM socios
                WHERE nombre LIKE ? OR CAST(dni AS TEXT) LIKE ?
                ORDER BY nombre
                LIMIT ?
                ''', (like, like, limite)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    # PAGOS
    def registrar_pago(self, dni: int, monto: float, fecha_pago: str, metodo: str) -> None:
        """Registra un pago"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO pagos (dni, monto, fecha_pago, metodo_pago)
                VALUES (?, ?, ?, ?)
            ''', (dni, monto, fecha_pago, metodo))
            conn.commit()
            logging.info(f"Pago registrado: DNI {dni}, ${monto}, {metodo}")
    
    def obtener_pago(self, pago_id: int) -> Optional[Dict]:
        """Obtiene un pago por ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM pagos WHERE id=?', (pago_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def editar_pago(self, pago_id: int, dni: int, monto: float, fecha_pago: str, metodo: str) -> None:
        """Edita un pago existente"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Validar existencia de socio destino
            cursor.execute('SELECT 1 FROM socios WHERE dni=?', (dni,))
            if cursor.fetchone() is None:
                raise ValueError(f"No existe socio con DNI {dni}")
            cursor.execute('''
                UPDATE pagos
                SET dni = ?, monto = ?, fecha_pago = ?, metodo_pago = ?
                WHERE id = ?
            ''', (dni, monto, fecha_pago, metodo, pago_id))
            if cursor.rowcount == 0:
                raise ValueError(f"Pago id {pago_id} no encontrado")
            conn.commit()
            logging.info(f"Pago editado: ID {pago_id} (DNI {dni}, ${monto}, {metodo})")

    def eliminar_pago(self, pago_id: int) -> None:
        """Elimina un pago por ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM pagos WHERE id = ?', (pago_id,))
            if cursor.rowcount == 0:
                raise ValueError(f"Pago id {pago_id} no encontrado")
            conn.commit()
            logging.info(f"Pago eliminado: ID {pago_id}")
    
    def obtener_pagos_por_dni(self, dni: int) -> List[Dict]:
        """Obtiene todos los pagos de un socio"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM pagos WHERE dni=? ORDER BY fecha_pago DESC
            ''', (dni,))
            return [dict(row) for row in cursor.fetchall()]
    
    def obtener_todos_los_pagos(self) -> List[Dict]:
        """Obtiene todos los pagos ordenados por fecha"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM pagos ORDER BY fecha_pago DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    # LISTADOS Y ESTADOS
    def socios_con_estado(self) -> List[Dict]:
        """Obtiene todos los socios con su estado calculado"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.dni, s.nombre, s.email, s.telefono, s.fecha_alta,
                       MAX(p.fecha_pago) as ultimo_pago,
                       CASE 
                           WHEN MAX(p.fecha_pago) IS NULL THEN 'Vencido'
                           WHEN date(MAX(p.fecha_pago), '+{} days') >= date('now') THEN 'Activo'
                           ELSE 'Vencido'
                       END as estado,
                       CASE 
                           WHEN MAX(p.fecha_pago) IS NOT NULL 
                           THEN date(MAX(p.fecha_pago), '+{} days')
                           ELSE NULL
                       END as fecha_vencimiento
                FROM socios s
                LEFT JOIN pagos p ON s.dni = p.dni
                GROUP BY s.dni, s.nombre, s.email, s.telefono, s.fecha_alta
                ORDER BY s.nombre
            '''.format(DIAS_CUOTA, DIAS_CUOTA))
            return [dict(row) for row in cursor.fetchall()]
    
    def socios_vencidos(self) -> List[Dict]:
        """Obtiene solo los socios vencidos"""
        socios = self.socios_con_estado()
        return [s for s in socios if s['estado'] == 'Vencido']
    
    def consultar_estado_socio(self, dni: int) -> Dict:
        """Consulta el estado de un socio específico para el kiosco"""
        socio = self.obtener_socio(dni)
        if not socio:
            return {
                'estado': 'No registrado',
                'nombre': None,
                'fecha_vencimiento': None
            }
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT MAX(fecha_pago) as ultimo_pago
                FROM pagos WHERE dni=?
            ''', (dni,))
            result = cursor.fetchone()
            ultimo_pago = result[0] if result and result[0] else None
            
            if ultimo_pago:
                fecha_vencimiento = datetime.strptime(ultimo_pago, '%Y-%m-%d') + timedelta(days=DIAS_CUOTA)
                estado = 'Activo' if fecha_vencimiento >= datetime.now() else 'Vencido'
                return {
                    'estado': estado,
                    'nombre': socio['nombre'],
                    'fecha_vencimiento': fecha_vencimiento.strftime('%Y-%m-%d')
                }
            else:
                return {
                    'estado': 'Vencido',
                    'nombre': socio['nombre'],
                    'fecha_vencimiento': None
                }
    
    # INGRESOS
    def registrar_ingreso(self, dni: Optional[int], nombre: Optional[str], estado: str) -> None:
        """Registra una consulta de ingreso"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO ingresos (dni, nombre, estado, fecha)
                VALUES (?, ?, ?, ?)
            ''', (dni, nombre, estado, datetime.now().isoformat()))
            conn.commit()
    
    def listar_ingresos(self, desde: Optional[str] = None, hasta: Optional[str] = None, filtro: Optional[str] = None) -> List[Dict]:
        """Lista los ingresos con filtros opcionales"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = 'SELECT * FROM ingresos WHERE 1=1'
            params = []
            
            if desde:
                query += ' AND date(fecha) >= ?'
                params.append(desde)
            if hasta:
                query += ' AND date(fecha) <= ?'
                params.append(hasta)
            if filtro:
                query += ' AND (dni LIKE ? OR nombre LIKE ?)'
                params.extend([f'%{filtro}%', f'%{filtro}%'])
            
            query += ' ORDER BY fecha DESC'
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    # KPIS Y MÉTRICAS
    def kpis_basicos(self) -> Dict:
        """Calcula KPIs básicos"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total socios
            cursor.execute('SELECT COUNT(*) FROM socios')
            total_socios = cursor.fetchone()[0]
            
            # Socios activos y vencidos
            socios = self.socios_con_estado()
            activos = len([s for s in socios if s['estado'] == 'Activo'])
            vencidos = len([s for s in socios if s['estado'] == 'Vencido'])
            
            # Pagos del mes
            cursor.execute('''
                SELECT COUNT(*), COALESCE(SUM(monto), 0)
                FROM pagos 
                WHERE strftime('%Y-%m', fecha_pago) = strftime('%Y-%m', 'now')
            ''')
            pagos_mes_count, pagos_mes_monto = cursor.fetchone()
            
            # Consultas del mes
            cursor.execute('''
                SELECT COUNT(*)
                FROM ingresos 
                WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')
            ''')
            consultas_mes = cursor.fetchone()[0]
            
            # Próximos vencimientos
            proximos_vencimientos = len([
                s for s in socios 
                if s['estado'] == 'Activo' and s['fecha_vencimiento'] and
                datetime.strptime(s['fecha_vencimiento'], '%Y-%m-%d') <= datetime.now() + timedelta(days=7)
            ])
            
            return {
                'total_socios': total_socios,
                'activos': activos,
                'vencidos': vencidos,
                'pagos_mes_count': pagos_mes_count,
                'pagos_mes_monto': pagos_mes_monto,
                'consultas_mes': consultas_mes,
                'proximos_vencimientos': proximos_vencimientos
            }
    
    def metricas_avanzadas(self, desde: Optional[str] = None, hasta: Optional[str] = None) -> Dict:
        """Calcula métricas avanzadas"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Permanencia promedio (meses)
            cursor.execute('''
                SELECT AVG(
                    CASE 
                        WHEN MAX(fecha_pago) IS NOT NULL AND MIN(fecha_pago) IS NOT NULL
                        THEN (julianday(MAX(fecha_pago)) - julianday(MIN(fecha_pago))) / 30.0
                        ELSE 0
                    END
                ) as permanencia_promedio
                FROM pagos
                GROUP BY dni
            ''')
            result = cursor.fetchone()
            permanencia_promedio = result[0] if result and result[0] else 0
            
            # Porcentaje de pagos en fecha (simplificado)
            cursor.execute('''
                SELECT COUNT(*) as total_pagos
                FROM pagos
            ''')
            total_pagos = cursor.fetchone()[0]
            
            # Para simplificar, asumimos que todos los pagos son "en fecha"
            porcentaje_pagos_en_fecha = 100.0 if total_pagos > 0 else 0
            
            return {
                'permanencia_promedio_meses': round(permanencia_promedio, 2),
                'churn_mensual': 0,  # Simplificado para MVP
                'porcentaje_pagos_en_fecha': porcentaje_pagos_en_fecha
            }
    
    # EXPORT/IMPORT
    def exportar_socios_excel(self, path_xlsx: str) -> None:
        """Exporta socios a Excel"""
        socios = self.socios_con_estado()
        df = pd.DataFrame(socios)
        df.to_excel(path_xlsx, index=False, sheet_name='Socios')
        logging.info(f"Socios exportados a {path_xlsx}")
    
    def exportar_pagos_excel(self, path_xlsx: str, rango: Optional[Tuple[str, str]] = None) -> None:
        """Exporta pagos a Excel"""
        with sqlite3.connect(self.db_path) as conn:
            query = '''
                SELECT p.*, s.nombre
                FROM pagos p
                LEFT JOIN socios s ON p.dni = s.dni
            '''
            params = []
            
            if rango:
                query += ' WHERE fecha_pago BETWEEN ? AND ?'
                params = list(rango)
            
            query += ' ORDER BY fecha_pago DESC'
            df = pd.read_sql_query(query, conn, params=params)
            df.to_excel(path_xlsx, index=False, sheet_name='Pagos')
            logging.info(f"Pagos exportados a {path_xlsx}")
    
    def exportar_ingresos_excel(self, path_xlsx: str, rango: Optional[Tuple[str, str]] = None) -> None:
        """Exporta ingresos a Excel"""
        ingresos = self.listar_ingresos(
            desde=rango[0] if rango else None,
            hasta=rango[1] if rango else None
        )
        df = pd.DataFrame(ingresos)
        df.to_excel(path_xlsx, index=False, sheet_name='Ingresos')
        logging.info(f"Ingresos exportados a {path_xlsx}")
    
    def importar_pagos_excel(self, path_xlsx: str) -> Dict:
        """Importa pagos desde Excel"""
        try:
            df = pd.read_excel(path_xlsx)
            errores = []
            importados = 0
            
            for index, row in df.iterrows():
                try:
                    dni = int(row['DNI'])
                    monto = float(row['Monto'])
                    fecha = row['Fecha']
                    metodo = row['Metodo'].lower()
                    
                    # Validaciones
                    if not self.obtener_socio(dni):
                        errores.append(f"Fila {index + 2}: DNI {dni} no existe")
                        continue
                    
                    if metodo not in ['efectivo', 'transferencia']:
                        errores.append(f"Fila {index + 2}: Método inválido '{metodo}'")
                        continue
                    
                    if monto <= 0:
                        errores.append(f"Fila {index + 2}: Monto debe ser mayor a 0")
                        continue
                    
                    # Convertir fecha
                    if isinstance(fecha, str):
                        fecha = datetime.strptime(fecha, '%Y-%m-%d').strftime('%Y-%m-%d')
                    else:
                        fecha = fecha.strftime('%Y-%m-%d')
                    
                    self.registrar_pago(dni, monto, fecha, metodo)
                    importados += 1
                    
                except Exception as e:
                    errores.append(f"Fila {index + 2}: {str(e)}")
            
            return {
                'importados': importados,
                'errores': errores,
                'total_filas': len(df)
            }
            
        except Exception as e:
            logging.error(f"Error importando pagos: {e}")
            raise
    def obtener_socio_por_dni(self, dni):
        """Obtiene un socio por DNI (alias para obtener_socio)"""
        return self.obtener_socio(dni)

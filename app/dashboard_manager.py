import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from .config import ALERT_CONFIG, DIAS_CUOTA

class DashboardManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_dashboard_data(self) -> Dict:
        """Obtiene todos los datos para el dashboard inteligente"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            
            dashboard_data = {
                "kpis": self._get_kpis(conn),
                "alerts": self._get_alerts(conn),
                "quick_actions": self._get_quick_actions(conn),
                "recent_activity": self._get_recent_activity(conn),
                "trends": self._get_trends(conn)
            }
            
            conn.close()
            return dashboard_data
            
        except Exception as e:
            print(f"Error obteniendo datos del dashboard: {e}")
            return self._get_empty_dashboard()
    
    def _get_kpis(self, conn: sqlite3.Connection) -> Dict:
        """Obtiene KPIs principales"""
        cursor = conn.cursor()
        
        # Total de socios
        cursor.execute("SELECT COUNT(*) FROM socios")
        total_socios = cursor.fetchone()[0]
        
        # Socios activos (con cuota vigente)
        fecha_limite = (datetime.now() - timedelta(days=DIAS_CUOTA)).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(DISTINCT s.dni) 
            FROM socios s 
            JOIN pagos p ON s.dni = p.dni 
            WHERE p.fecha_pago >= ?
        """, (fecha_limite,))
        socios_activos = cursor.fetchone()[0]
        
        # Ingresos del mes actual
        primer_dia_mes = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COALESCE(SUM(monto), 0) 
            FROM pagos 
            WHERE fecha_pago >= ?
        """, (primer_dia_mes,))
        ingresos_mes = cursor.fetchone()[0]
        
        # Visitas de hoy
        hoy = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(*) 
            FROM ingresos 
            WHERE DATE(fecha) = ?
        """, (hoy,))
        visitas_hoy = cursor.fetchone()[0]
        
        # Promedio de visitas diarias (últimos 30 días)
        hace_30_dias = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(*) / 30.0 
            FROM ingresos 
            WHERE fecha >= ?
        """, (hace_30_dias,))
        promedio_visitas = round(cursor.fetchone()[0], 1)
        
        return {
            "total_socios": total_socios,
            "socios_activos": socios_activos,
            "socios_inactivos": total_socios - socios_activos,
            "tasa_actividad": round((socios_activos / total_socios * 100) if total_socios > 0 else 0, 1),
            "ingresos_mes": ingresos_mes,
            "visitas_hoy": visitas_hoy,
            "promedio_visitas_diarias": promedio_visitas
        }
    
    def _get_alerts(self, conn: sqlite3.Connection) -> List[Dict]:
        """Obtiene alertas inteligentes para el dashboard"""
        alerts = []
        cursor = conn.cursor()
        
        # Alertas de vencimientos próximos
        for dias in ALERT_CONFIG["vencimiento_dias"]:
            fecha_vencimiento = (datetime.now() + timedelta(days=dias)).strftime('%Y-%m-%d')
            fecha_limite = (datetime.now() - timedelta(days=DIAS_CUOTA - dias)).strftime('%Y-%m-%d')
            
            cursor.execute("""
                SELECT s.nombre, s.dni, MAX(p.fecha_pago) as ultima_cuota
                FROM socios s
                JOIN pagos p ON s.dni = p.dni
                WHERE p.fecha_pago = ?
                GROUP BY s.dni
                LIMIT 5
            """, (fecha_limite,))
            
            vencimientos = cursor.fetchall()
            if vencimientos:
                alerts.append({
                    "type": "warning" if dias > 3 else "danger",
                    "title": f"Vencimientos en {dias} día{'s' if dias > 1 else ''}",
                    "message": f"{len(vencimientos)} socio{'s' if len(vencimientos) > 1 else ''} vence{'n' if len(vencimientos) > 1 else ''} en {dias} día{'s' if dias > 1 else ''}",
                    "count": len(vencimientos),
                    "action": "view_expiring",
                    "data": {"dias": dias, "socios": [dict(row) for row in vencimientos]}
                })
        
        # Alertas de socios inactivos (sin visitas)
        hace_x_dias = (datetime.now() - timedelta(days=ALERT_CONFIG["inactividad_dias"])).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT s.nombre, s.dni,
                   MAX(i.fecha) as ultima_visita,
                   MAX(p.fecha_pago) as ultima_cuota
            FROM socios s
            LEFT JOIN ingresos i ON s.dni = i.dni
            LEFT JOIN pagos p ON s.dni = p.dni
            WHERE (i.fecha IS NULL OR i.fecha < ?) 
            AND p.fecha_pago >= ?
            GROUP BY s.dni
            LIMIT 10
        """, (hace_x_dias, (datetime.now() - timedelta(days=DIAS_CUOTA)).strftime('%Y-%m-%d')))
        
        inactivos = cursor.fetchall()
        if inactivos:
            alerts.append({
                "type": "info",
                "title": "Socios inactivos",
                "message": f"{len(inactivos)} socio{'s' if len(inactivos) > 1 else ''} activo{'s' if len(inactivos) > 1 else ''} sin visitas en {ALERT_CONFIG['inactividad_dias']} días",
                "count": len(inactivos),
                "action": "view_inactive",
                "data": {"socios": [dict(row) for row in inactivos]}
            })
        
        # Limitar número de alertas
        return alerts[:ALERT_CONFIG["max_alertas_dashboard"]]
    
    def _get_quick_actions(self, conn: sqlite3.Connection) -> List[Dict]:
        """Obtiene acciones rápidas sugeridas"""
        actions = []
        cursor = conn.cursor()
        
        # Acción: Renovar vencimientos próximos
        fecha_limite = (datetime.now() - timedelta(days=DIAS_CUOTA - 3)).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(DISTINCT s.dni)
            FROM socios s
            JOIN pagos p ON s.dni = p.dni
            WHERE p.fecha_pago = ?
        """, (fecha_limite,))
        
        vencimientos_3_dias = cursor.fetchone()[0]
        if vencimientos_3_dias > 0:
            actions.append({
                "title": "Renovar cuotas",
                "description": f"{vencimientos_3_dias} socio{'s' if vencimientos_3_dias > 1 else ''} vence{'n' if vencimientos_3_dias > 1 else ''} en 3 días",
                "action": "renew_memberships",
                "icon": "💳",
                "priority": "high"
            })
        
        # Acción: Contactar inactivos
        hace_15_dias = (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(DISTINCT s.dni)
            FROM socios s
            LEFT JOIN ingresos i ON s.dni = i.dni
            LEFT JOIN pagos p ON s.dni = p.dni
            WHERE (i.fecha IS NULL OR i.fecha < ?) 
            AND p.fecha_pago >= ?
        """, (hace_15_dias, (datetime.now() - timedelta(days=DIAS_CUOTA)).strftime('%Y-%m-%d')))
        
        inactivos_15_dias = cursor.fetchone()[0]
        if inactivos_15_dias > 0:
            actions.append({
                "title": "Contactar inactivos",
                "description": f"{inactivos_15_dias} socio{'s' if inactivos_15_dias > 1 else ''} sin visitas en 15 días",
                "action": "contact_inactive",
                "icon": "📞",
                "priority": "medium"
            })
        
        # Acción: Crear backup
        actions.append({
            "title": "Crear backup",
            "description": "Respaldar datos del sistema",
            "action": "create_backup",
            "icon": "💾",
            "priority": "low"
        })
        
        return actions
    
    def _get_recent_activity(self, conn: sqlite3.Connection) -> List[Dict]:
        """Obtiene actividad reciente"""
        cursor = conn.cursor()
        
        # Últimas visitas
        cursor.execute("""
            SELECT i.dni, s.nombre, i.fecha, i.estado
            FROM ingresos i
            LEFT JOIN socios s ON i.dni = s.dni
            ORDER BY i.fecha DESC
            LIMIT 10
        """)
        
        visitas = cursor.fetchall()
        activity = []
        
        for visita in visitas:
            activity.append({
                "type": "visit",
                "timestamp": visita[2],
                "description": f"{visita[1] or 'Desconocido'} - {visita[3]}",
                "status": visita[3]
            })
        
        # Últimos pagos
        cursor.execute("""
            SELECT p.fecha_pago, s.nombre, p.monto, p.metodo_pago
            FROM pagos p
            JOIN socios s ON p.dni = s.dni
            ORDER BY p.fecha_pago DESC, p.id DESC
            LIMIT 5
        """)
        
        pagos = cursor.fetchall()
        for pago in pagos:
            activity.append({
                "type": "payment",
                "timestamp": pago[0],
                "description": f"{pago[1]} - ${pago[2]} ({pago[3]})",
                "status": "completed"
            })
        
        # Ordenar por timestamp
        activity.sort(key=lambda x: x["timestamp"], reverse=True)
        return activity[:15]
    
    def _get_trends(self, conn: sqlite3.Connection) -> Dict:
        """Obtiene tendencias y métricas de crecimiento"""
        cursor = conn.cursor()
        
        # Tendencia de visitas (últimos 7 días)
        visitas_por_dia = []
        for i in range(7):
            fecha = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT COUNT(*) 
                FROM ingresos 
                WHERE DATE(fecha) = ?
            """, (fecha,))
            visitas = cursor.fetchone()[0]
            visitas_por_dia.append({
                "fecha": fecha,
                "visitas": visitas
            })
        
        return {
            "visitas_diarias": list(reversed(visitas_por_dia))
        }
    
    def _get_empty_dashboard(self) -> Dict:
        """Retorna estructura vacía del dashboard en caso de error"""
        return {
            "kpis": {
                "total_socios": 0,
                "socios_activos": 0,
                "socios_inactivos": 0,
                "tasa_actividad": 0,
                "ingresos_mes": 0,
                "visitas_hoy": 0,
                "promedio_visitas_diarias": 0
            },
            "alerts": [],
            "quick_actions": [],
            "recent_activity": [],
            "trends": {"visitas_diarias": []}
        }

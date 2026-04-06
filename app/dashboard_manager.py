import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from .config import ALERT_CONFIG, DIAS_CUOTA

class DashboardManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_dashboard_data(self, range_key: Optional[str] = None) -> Dict:
        """Obtiene todos los datos para el dashboard inteligente.
        range_key puede ser: '1d','7d','30d','90d','all'.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            date_from, date_to = self._get_range_bounds(range_key)
            
            dashboard_data = {
                "kpis": self._get_kpis(conn),
                "alerts": self._get_alerts(conn),
                "quick_actions": self._get_quick_actions(conn),
                "recent_activity": self._get_recent_activity(conn),
                "trends": self._get_trends(conn),
                "income_series": self._get_income_series(conn, date_from, date_to),
                "payment_methods": self._get_payment_methods_split(conn)
            }
            
            conn.close()
            return dashboard_data
            
        except Exception as e:
            print(f"Error obteniendo datos del dashboard: {e}")
            return self._get_empty_dashboard()
    
    def _get_range_bounds(self, range_key: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        if not range_key or range_key == 'all':
            return None, None
        now = datetime.now().date()
        if range_key == '1d':
            start = now
        elif range_key == '7d':
            start = now - timedelta(days=6)
        elif range_key == '30d':
            start = now - timedelta(days=29)
        elif range_key == '90d':
            start = now - timedelta(days=89)
        else:
            start = now - timedelta(days=29)
        return start.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d')
    
    def _get_kpis(self, conn: sqlite3.Connection) -> Dict:
        """Obtiene KPIs principales"""
        cursor = conn.cursor()
        
        # Total de socios
        cursor.execute("SELECT COUNT(*) FROM socios")
        total_socios = cursor.fetchone()[0]
        
        # Socios activos (cuota vigente según duración real de cada pago)
        cursor.execute("""
            SELECT COUNT(DISTINCT s.dni)
            FROM socios s
            JOIN pagos p ON p.id = (
                SELECT id FROM pagos p2
                WHERE p2.dni = s.dni
                ORDER BY fecha_pago DESC
                LIMIT 1
            )
            WHERE date(p.fecha_pago, '+' || (COALESCE(p.meses, 1) * 30) || ' days') >= date('now')
        """)
        socios_activos = cursor.fetchone()[0]
        
        # Ingresos del mes actual
        primer_dia_mes = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COALESCE(SUM(monto), 0) 
            FROM pagos 
            WHERE fecha_pago >= ?
        """, (primer_dia_mes,))
        ingresos_mes = cursor.fetchone()[0]

        # Nuevos socios del mes
        cursor.execute("""
            SELECT COUNT(*) FROM socios
            WHERE strftime('%Y-%m', fecha_alta) = strftime('%Y-%m', 'now')
        """)
        nuevos_mes = cursor.fetchone()[0]

        # Renovaciones del mes (socios con pago este mes y al menos un pago previo antes de este mes)
        cursor.execute("""
            SELECT COUNT(DISTINCT p.dni) FROM pagos p
            WHERE strftime('%Y-%m', p.fecha_pago) = strftime('%Y-%m','now')
              AND EXISTS (
                SELECT 1 FROM pagos p2
                WHERE p2.dni = p.dni AND p2.fecha_pago < date('now','start of month')
              )
        """)
        renovaciones_mes = cursor.fetchone()[0]
        
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
            "nuevos_mes": nuevos_mes,
            "renovaciones_mes": renovaciones_mes,
            "visitas_hoy": visitas_hoy,
            "promedio_visitas_diarias": promedio_visitas
        }
    
    def _get_alerts(self, conn: sqlite3.Connection) -> List[Dict]:
        """Obtiene alertas inteligentes para el dashboard"""
        alerts = []
        cursor = conn.cursor()
        
        # Alertas de vencimientos próximos (usa duración real de cada último pago)
        for dias in ALERT_CONFIG["vencimiento_dias"]:
            sql = f"""
                SELECT nombre, dni, fecha_vencimiento, ultima_cuota
                FROM (
                    SELECT s.nombre, s.dni,
                           date(p.fecha_pago, '+' || (COALESCE(p.meses, 1) * 30) || ' days') AS fecha_vencimiento,
                           p.fecha_pago AS ultima_cuota
                    FROM socios s
                    JOIN pagos p ON p.id = (
                        SELECT id FROM pagos p2
                        WHERE p2.dni = s.dni
                        ORDER BY fecha_pago DESC
                        LIMIT 1
                    )
                ) sub
                WHERE fecha_vencimiento = DATE('now', '+{dias} days')
                ORDER BY fecha_vencimiento ASC
                LIMIT 5
            """
            cursor.execute(sql)
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
        
        # Alertas de socios inactivos (sin visitas, pero con cuota vigente)
        hace_x_dias = (datetime.now() - timedelta(days=ALERT_CONFIG["inactividad_dias"])).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT s.nombre, s.dni,
                   MAX(i.fecha) as ultima_visita,
                   p.fecha_pago as ultima_cuota
            FROM socios s
            LEFT JOIN ingresos i ON s.dni = i.dni
            JOIN pagos p ON p.id = (
                SELECT id FROM pagos p2
                WHERE p2.dni = s.dni
                ORDER BY fecha_pago DESC
                LIMIT 1
            )
            WHERE (i.fecha IS NULL OR i.fecha < ?)
            AND date(p.fecha_pago, '+' || (COALESCE(p.meses, 1) * 30) || ' days') >= date('now')
            GROUP BY s.dni
            LIMIT 10
        """, (hace_x_dias,))
        
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
        
        # Acción: Renovar vencimientos próximos (en los próximos 3 días)
        cursor.execute("""
            SELECT COUNT(DISTINCT s.dni)
            FROM socios s
            JOIN pagos p ON p.id = (
                SELECT id FROM pagos p2 WHERE p2.dni = s.dni
                ORDER BY fecha_pago DESC LIMIT 1
            )
            WHERE date(p.fecha_pago, '+' || (COALESCE(p.meses, 1) * 30) || ' days')
                  BETWEEN date('now') AND date('now', '+3 days')
        """)

        vencimientos_3_dias = cursor.fetchone()[0]
        if vencimientos_3_dias > 0:
            actions.append({
                "title": "Renovar cuotas",
                "description": f"{vencimientos_3_dias} socio{'s' if vencimientos_3_dias > 1 else ''} vence{'n' if vencimientos_3_dias > 1 else ''} en 3 días",
                "action": "renew_memberships",
                "icon": "💳",
                "priority": "high"
            })
        
        # Acción: Contactar inactivos (activos sin visitas en 15 días)
        hace_15_dias = (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(DISTINCT s.dni)
            FROM socios s
            LEFT JOIN ingresos i ON s.dni = i.dni
            JOIN pagos p ON p.id = (
                SELECT id FROM pagos p2 WHERE p2.dni = s.dni
                ORDER BY fecha_pago DESC LIMIT 1
            )
            WHERE (i.fecha IS NULL OR i.fecha < ?)
            AND date(p.fecha_pago, '+' || (COALESCE(p.meses, 1) * 30) || ' days') >= date('now')
        """, (hace_15_dias,))
        
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

    def _get_income_series(self, conn: sqlite3.Connection, date_from: Optional[str], date_to: Optional[str]) -> List[Dict]:
        cursor = conn.cursor()
        # Si no hay rango, usar últimos 30 días
        if not date_from or not date_to:
            date_to = datetime.now().strftime('%Y-%m-%d')
            date_from = (datetime.now() - timedelta(days=29)).strftime('%Y-%m-%d')
        cursor.execute(
            """
            SELECT fecha_pago, COALESCE(SUM(monto),0) as total
            FROM pagos
            WHERE fecha_pago BETWEEN ? AND ?
            GROUP BY fecha_pago
            ORDER BY fecha_pago
            """,
            (date_from, date_to)
        )
        rows = cursor.fetchall()
        return [{"fecha": r[0], "total": r[1]} for r in rows]

    def _get_payment_methods_split(self, conn: sqlite3.Connection) -> Dict:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT metodo_pago, COALESCE(SUM(monto),0) as total
            FROM pagos
            WHERE strftime('%Y-%m', fecha_pago) = strftime('%Y-%m','now')
            GROUP BY metodo_pago
            """
        )
        rows = cursor.fetchall()
        totals = {r[0] or 'desconocido': float(r[1] or 0.0) for r in rows}
        return totals
    
    def _get_empty_dashboard(self) -> Dict:
        """Retorna estructura vacía del dashboard en caso de error"""
        return {
            "kpis": {
                "total_socios": 0,
                "socios_activos": 0,
                "socios_inactivos": 0,
                "tasa_actividad": 0,
                "ingresos_mes": 0,
                "nuevos_mes": 0,
                "renovaciones_mes": 0,
                "visitas_hoy": 0,
                "promedio_visitas_diarias": 0
            },
            "alerts": [],
            "quick_actions": [],
            "recent_activity": [],
            "trends": {"visitas_diarias": []},
            "income_series": [],
            "payment_methods": {}
        }

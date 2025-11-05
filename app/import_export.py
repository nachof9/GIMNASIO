import pandas as pd
from tkinter import filedialog, messagebox
from datetime import datetime
import os
import logging
from typing import Optional, Tuple

class ImportExportManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def exportar_socios(self, parent=None) -> Optional[str]:
        """Exporta socios a Excel"""
        try:
            filename = filedialog.asksaveasfilename(
                parent=parent,
                title="Exportar Socios",
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                initialfile=f"socios_{datetime.now().strftime('%Y%m%d')}.xlsx"
            )
            
            if filename:
                self.db_manager.exportar_socios_excel(filename)
                messagebox.showinfo("Éxito", f"Socios exportados a:\n{filename}")
                return filename
                
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar socios: {str(e)}")
            logging.error(f"Error exportando socios: {e}")
        
        return None
    
    def exportar_pagos(self, parent=None, rango: Optional[Tuple[str, str]] = None) -> Optional[str]:
        """Exporta pagos a Excel"""
        try:
            filename = filedialog.asksaveasfilename(
                parent=parent,
                title="Exportar Pagos",
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                initialfile=f"pagos_{datetime.now().strftime('%Y%m%d')}.xlsx"
            )
            
            if filename:
                self.db_manager.exportar_pagos_excel(filename, rango)
                messagebox.showinfo("Éxito", f"Pagos exportados a:\n{filename}")
                return filename
                
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar pagos: {str(e)}")
            logging.error(f"Error exportando pagos: {e}")
        
        return None
    
    def exportar_ingresos(self, parent=None, rango: Optional[Tuple[str, str]] = None) -> Optional[str]:
        """Exporta ingresos a Excel"""
        try:
            filename = filedialog.asksaveasfilename(
                parent=parent,
                title="Exportar Ingresos",
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                # Cambiamos initialname por initialfile que es el parámetro correcto
                initialfile=f"ingresos_{datetime.now().strftime('%Y%m%d')}.xlsx"
            )
            
            if filename:
                self.db_manager.exportar_ingresos_excel(filename, rango)
                messagebox.showinfo("Éxito", f"Ingresos exportados a:\n{filename}")
                return filename
                
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar ingresos: {str(e)}")
            logging.error(f"Error exportando ingresos: {e}")
        
        return None
    
    def exportar_reporte_completo(self, parent=None) -> Optional[str]:
        """Exporta un reporte completo con múltiples hojas"""
        try:
            filename = filedialog.asksaveasfilename(
                parent=parent,
                title="Exportar Reporte Completo",
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                initialfile=f"reporte_completo_{datetime.now().strftime('%Y%m%d')}.xlsx"
            )
            
            if filename:
                # Crear archivo Excel con múltiples hojas
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    # Socios
                    socios = self.db_manager.socios_con_estado()
                    df_socios = pd.DataFrame(socios)
                    df_socios.to_excel(writer, sheet_name='Socios', index=False)
                    
                    # Pagos
                    import sqlite3
                    with sqlite3.connect(self.db_manager.db_path) as conn:
                        df_pagos = pd.read_sql_query('''
                            SELECT p.*, s.nombre
                            FROM pagos p
                            LEFT JOIN socios s ON p.dni = s.dni
                            ORDER BY p.fecha_pago DESC
                        ''', conn)
                        df_pagos.to_excel(writer, sheet_name='Pagos', index=False)
                    
                    # Ingresos
                    ingresos = self.db_manager.listar_ingresos()
                    df_ingresos = pd.DataFrame(ingresos)
                    df_ingresos.to_excel(writer, sheet_name='Ingresos', index=False)
                    
                    # KPIs
                    kpis = self.db_manager.kpis_basicos()
                    metricas = self.db_manager.metricas_avanzadas()
                    
                    # Combinar KPIs y métricas
                    resumen_data = []
                    for key, value in {**kpis, **metricas}.items():
                        resumen_data.append({'Métrica': key, 'Valor': value})
                    
                    df_resumen = pd.DataFrame(resumen_data)
                    df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
                
                messagebox.showinfo("Éxito", f"Reporte completo exportado a:\n{filename}")
                return filename
                
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar reporte: {str(e)}")
            logging.error(f"Error exportando reporte completo: {e}")
        
        return None
    
    def importar_pagos(self, parent=None) -> Optional[dict]:
        """Importa pagos desde Excel"""
        try:
            filename = filedialog.askopenfilename(
                parent=parent,
                title="Importar Pagos",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
            )
            
            if filename:
                resultado = self.db_manager.importar_pagos_excel(filename)
                
                # Mostrar resultado
                mensaje = f"Importación completada:\n"
                mensaje += f"• Filas procesadas: {resultado['total_filas']}\n"
                mensaje += f"• Pagos importados: {resultado['importados']}\n"
                mensaje += f"• Errores: {len(resultado['errores'])}"
                
                if resultado['errores']:
                    mensaje += f"\n\nErrores encontrados:\n"
                    for error in resultado['errores'][:10]:  # Mostrar máximo 10 errores
                        mensaje += f"• {error}\n"
                    
                    if len(resultado['errores']) > 10:
                        mensaje += f"... y {len(resultado['errores']) - 10} errores más"
                
                if resultado['errores']:
                    messagebox.showwarning("Importación con errores", mensaje)
                else:
                    messagebox.showinfo("Éxito", mensaje)
                
                return resultado
                
        except Exception as e:
            messagebox.showerror("Error", f"Error al importar pagos: {str(e)}")
            logging.error(f"Error importando pagos: {e}")
        
        return None
    
    def crear_plantilla_importacion(self, parent=None) -> Optional[str]:
        """Crea una plantilla Excel para importar pagos"""
        try:
            filename = filedialog.asksaveasfilename(
                parent=parent,
                title="Crear Plantilla de Importación",
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                initialfile="plantilla_pagos.xlsx"
            )
            
            if filename:
                # Crear plantilla con ejemplos
                data = {
                    'DNI': [12345678, 87654321],
                    'Monto': [5000.00, 3500.50],
                    'Fecha': ['2024-01-15', '2024-01-16'],
                    'Metodo': ['efectivo', 'transferencia']
                }
                
                df = pd.DataFrame(data)
                df.to_excel(filename, index=False)
                
                messagebox.showinfo("Éxito", f"Plantilla creada en:\n{filename}")
                return filename
                
        except Exception as e:
            messagebox.showerror("Error", f"Error al crear plantilla: {str(e)}")
            logging.error(f"Error creando plantilla: {e}")
        
        return None

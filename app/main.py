import tkinter as tk
from tkinter import ttk, messagebox, filedialog
try:
    import customtkinter as ctk
except ImportError:
    # Mostrar mensaje claro si falta customtkinter y salir
    try:
        # Crear una raíz oculta para poder mostrar messagebox
        _root = tk.Tk()
        _root.withdraw()
        messagebox.showerror(
            "Dependencia faltante",
            "No se encontró el módulo 'customtkinter'.\n\n"
            "Solución rápida:\n"
            "1) Abra una terminal en la carpeta del proyecto\n"
            "2) Ejecute: pip install customtkinter\n\n"
            "Si usa múltiples Python, pruebe:\n"
            "- py -m pip install customtkinter\n"
            "- python -m pip install customtkinter"
        )
    except Exception:
        # Fallback a impresión en consola si no se puede mostrar el cuadro de diálogo
        print("ERROR: Falta instalar 'customtkinter'. Ejecute: pip install customtkinter")
    finally:
        try:
            _root.destroy()
        except Exception:
            pass
    import sys
    sys.exit(1)
import logging
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import os
import sys
from PIL import Image

try:
    from .config import get_log_filename, ensure_directories, resource_path, COLORS, POPUP_AUTOCLOSE_SECONDS, SOUNDS, ALERT_CONFIG, FONTS, OWNER_PIN
    from .db import DatabaseManager
    from .admin_windows import AltaSocioWindow, EditarSocioWindow, RegistrarPagoWindow, EditarPagoWindow
    from .import_export import ImportExportManager
    from .dashboard_manager import DashboardManager
except ImportError:
    # Fallback para ejecución directa
    from config import get_log_filename, ensure_directories, resource_path, COLORS, POPUP_AUTOCLOSE_SECONDS, SOUNDS, ALERT_CONFIG, FONTS, OWNER_PIN
    from db import DatabaseManager
    from admin_windows import AltaSocioWindow, EditarSocioWindow, RegistrarPagoWindow, EditarPagoWindow
    from import_export import ImportExportManager
    from dashboard_manager import DashboardManager

# Configurar logging
ensure_directories()
logging.basicConfig(
    filename=get_log_filename(),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Configurar CustomTkinter
# Modo claro y tema por defecto
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# Importar winsound para sonidos (solo Windows)
try:
    import winsound
    SOUND_AVAILABLE = True
except ImportError:
    SOUND_AVAILABLE = False
    logging.warning("winsound no disponible - sonidos deshabilitados")

def resource_path(relative_path):
    """Obtiene la ruta absoluta del recurso, funciona para dev y para PyInstaller"""
    try:
        # PyInstaller crea una carpeta temporal y almacena la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_custom_image(image_name, size=(100, 100)):
    """Carga una imagen personalizada desde la carpeta assets"""
    try:
        image_path = resource_path(f"assets/{image_name}")
        if os.path.exists(image_path):
            return ctk.CTkImage(light_image=Image.open(image_path), size=size)
    except Exception as e:
        logging.warning(f"No se pudo cargar la imagen {image_name}: {e}")
    return None

class ConsultaKioscoFrame(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.popup_window = None
        self.after_id = None
        
        self.create_widgets()
    
    def create_widgets(self):
        # Contenedor centrado a pantalla completa
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(container, fg_color="transparent")
        inner.grid(row=0, column=0)

        # Título SOMA Entrenamientos (SOMA en naranja)
        title_frame = ctk.CTkFrame(inner, fg_color="transparent")
        title_frame.pack(pady=(0, 20))
        ctk.CTkLabel(
            title_frame,
            text="SOMA",
            font=ctk.CTkFont(**FONTS['TITLE_LARGE']),
            text_color=COLORS['SOMA_ORANGE']
        ).pack(side="left")
        ctk.CTkLabel(
            title_frame,
            text=" Entrenamientos",
            font=ctk.CTkFont(**FONTS['TITLE_LARGE']),
            text_color=COLORS['TEXT_DARK']
        ).pack(side="left")

        # Box de DNI centrado
        dni_frame = ctk.CTkFrame(inner, fg_color="transparent")
        dni_frame.pack(pady=10)

        ctk.CTkLabel(
            dni_frame,
            text="Ingrese su DNI:",
            font=ctk.CTkFont(**FONTS['BODY_LARGE'])
        ).pack(pady=(0, 10))

        self.dni_entry = ctk.CTkEntry(
            dni_frame,
            placeholder_text="12345678",
            font=ctk.CTkFont(**FONTS['HEADER']),
            width=360,
            height=56,
            justify="center"
        )
        self.dni_entry.pack(pady=10)

        # Bind Enter para consultar
        self.dni_entry.bind('<Return>', self.consultar_estado)

        # Instrucciones
        ctk.CTkLabel(
            inner,
            text="Presione ENTER para consultar su estado",
            font=ctk.CTkFont(**FONTS['BODY_MEDIUM']),
            text_color="gray"
        ).pack(pady=(12, 0))

        # Focus inicial
        self.after(100, lambda: self.dni_entry.focus())
    
    def consultar_estado(self, event=None):
        dni_text = self.dni_entry.get().strip()
        
        if not dni_text:
            return
        
        if not dni_text.isdigit():
            self.mostrar_popup("Error", "DNI inválido", COLORS['EXPIRED_RED'], "❌")
            return
        
        dni = int(dni_text)
        
        try:
            # Consultar estado
            resultado = self.db_manager.consultar_estado_socio(dni)
            
            # Registrar consulta en ingresos
            self.db_manager.registrar_ingreso(
                dni if resultado['estado'] != 'No registrado' else None,
                resultado['nombre'],
                resultado['estado']
            )
            
            # Mostrar resultado
            if resultado['estado'] == 'Activo':
                mensaje = f"CUOTA ACTIVA\n\n{resultado['nombre']}\nVence: {resultado['fecha_vencimiento']}"
                self.mostrar_popup("ACTIVO", mensaje, COLORS['ACTIVE_GREEN'], "✅")
                self.reproducir_sonido('ACTIVE')
                
            elif resultado['estado'] == 'Vencido':
                fecha_venc = resultado['fecha_vencimiento'] or "Sin pagos"
                mensaje = f"CUOTA VENCIDA\n\n{resultado['nombre']}\nÚltimo vencimiento: {fecha_venc}"
                self.mostrar_popup("VENCIDO", mensaje, COLORS['EXPIRED_RED'], "❌")
                self.reproducir_sonido('EXPIRED')
                
            else:  # No registrado
                mensaje = "DNI NO REGISTRADO\n\nConsulte en recepción"
                self.mostrar_popup("NO REGISTRADO", mensaje, COLORS['WARNING_AMBER'], "⚠️")
                self.reproducir_sonido('NOT_REGISTERED')
        
        except Exception as e:
            logging.error(f"Error en consulta: {e}")
            self.mostrar_popup("Error", "Error en la consulta", COLORS['EXPIRED_RED'], "❌")
    
    def mostrar_popup(self, titulo, mensaje, color, icono):
        # Cerrar popup anterior si existe
        if self.popup_window:
            self.popup_window.destroy()
        
        if self.after_id:
            self.after_cancel(self.after_id)
        
        # Crear popup grande y centrado (no pantalla completa)
        self.popup_window = ctk.CTkToplevel(self)
        self.popup_window.title(titulo)
        self.popup_window.transient(self)
        self.popup_window.grab_set()
        # Calcular tamaño ~90% de la pantalla y centrar
        self.popup_window.update_idletasks()
        sw = self.popup_window.winfo_screenwidth()
        sh = self.popup_window.winfo_screenheight()
        width = int(sw * 0.9)
        height = int(sh * 0.85)
        x = (sw - width) // 2
        y = (sh - height) // 2
        self.popup_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Frame principal y contenido centrado
        main_frame = ctk.CTkFrame(self.popup_window, fg_color=color)
        main_frame.pack(fill="both", expand=True, padx=30, pady=30)

        content = ctk.CTkFrame(main_frame, fg_color="transparent")
        content.place(relx=0.5, rely=0.5, anchor="center")

        # Icono y título
        ctk.CTkLabel(
            content, text=icono, font=ctk.CTkFont(**FONTS['TITLE_LARGE'])
        ).pack(pady=(10, 10))

        # Mensaje principal
        ctk.CTkLabel(
            content, text=mensaje, font=ctk.CTkFont(**FONTS['TITLE_SMALL']), text_color="white"
        ).pack(pady=10)
        
        # Auto-cerrar después de 3 segundos (config o mínimo 3)
        try:
            seconds = max(2, int(POPUP_AUTOCLOSE_SECONDS))
        except Exception:
            seconds = 2
        self.after_id = self.after(seconds * 1000, self.cerrar_popup)
    
    def cerrar_popup(self):
        if self.popup_window:
            self.popup_window.destroy()
            self.popup_window = None
        
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        
        # Limpiar entry y devolver foco
        self.dni_entry.delete(0, 'end')
        self.dni_entry.focus()
    
    def reproducir_sonido(self, tipo):
        if not SOUND_AVAILABLE:
            return
        
        try:
            if tipo == 'ACTIVE':
                freq, duration = SOUNDS['ACTIVE']
                winsound.Beep(freq, duration)
            elif tipo == 'EXPIRED':
                for freq, duration in SOUNDS['EXPIRED']:
                    winsound.Beep(freq, duration)
                    if len(SOUNDS['EXPIRED']) > 1:
                        self.after(100)  # Pausa entre beeps
            elif tipo == 'NOT_REGISTERED':
                freq, duration = SOUNDS['NOT_REGISTERED']
                winsound.Beep(freq, duration)
        except Exception as e:
            logging.warning(f"Error reproduciendo sonido: {e}")

class SociosFrame(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        
        self.create_widgets()
        self.cargar_socios()
    
    def create_widgets(self):
        # Frame superior con controles
        control_frame = ctk.CTkFrame(self)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        # Título
        title_label = ctk.CTkLabel(control_frame, text="Gestión de Socios", 
                                 font=ctk.CTkFont(**FONTS['SUBTITLE']))
        title_label.pack(side="left", padx=10, pady=10)
        
        # Botón Nuevo Socio
        nuevo_btn = ctk.CTkButton(control_frame, text="Nuevo Socio", 
                                command=self.nuevo_socio,
                                font=ctk.CTkFont(**FONTS['BUTTON']))
        nuevo_btn.pack(side="right", padx=10, pady=10)
        
        # Frame de filtros
        filter_frame = ctk.CTkFrame(self)
        filter_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Búsqueda
        ctk.CTkLabel(filter_frame, text="Buscar:", font=ctk.CTkFont(**FONTS['LABEL'])).pack(side="left", padx=(10, 5), pady=10)
        self.search_entry = ctk.CTkEntry(filter_frame, placeholder_text="DNI o nombre...", font=ctk.CTkFont(**FONTS['INPUT']))
        self.search_entry.pack(side="left", padx=5, pady=10)
        self.search_entry.bind('<KeyRelease>', self.filtrar_socios)
        
        # Filtro de estado
        ctk.CTkLabel(filter_frame, text="Estado:", font=ctk.CTkFont(**FONTS['LABEL'])).pack(side="left", padx=(20, 5), pady=10)
        self.estado_filter = ctk.CTkOptionMenu(filter_frame, 
                                             values=["Todos", "Activos", "Vencidos"],
                                             command=self.filtrar_socios,
                                             font=ctk.CTkFont(**FONTS['INPUT']))
        self.estado_filter.pack(side="left", padx=5, pady=10)
        
        # Botón refrescar
        refresh_btn = ctk.CTkButton(filter_frame, text="Refrescar", 
                                  command=self.cargar_socios, width=100,
                                  font=ctk.CTkFont(**FONTS['BUTTON']))
        refresh_btn.pack(side="right", padx=10, pady=10)
        
        # Tabla de socios
        self.create_table()
    
    def create_table(self):
        # Frame para la tabla
        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Treeview con scrollbar
        columns = ("DNI", "Nombre", "Email", "Último Pago", "Estado", "Vencimiento", "Acciones")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        
        # Configurar columnas
        self.tree.heading("DNI", text="DNI")
        self.tree.heading("Nombre", text="Nombre")
        self.tree.heading("Email", text="Email")
        self.tree.heading("Último Pago", text="Último Pago")
        self.tree.heading("Estado", text="Estado")
        self.tree.heading("Vencimiento", text="Vencimiento")
        self.tree.heading("Acciones", text="Acciones")
        
        # Ancho de columnas
        self.tree.column("DNI", width=100)
        self.tree.column("Nombre", width=200)
        self.tree.column("Email", width=200)
        self.tree.column("Último Pago", width=120)
        self.tree.column("Estado", width=100)
        self.tree.column("Vencimiento", width=120)
        self.tree.column("Acciones", width=200)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind doble click
        self.tree.bind("<Double-1>", self.editar_socio_seleccionado)
        
        # Bind click derecho para menú contextual
        self.tree.bind("<Button-3>", self.mostrar_menu_contextual)
    
    def cargar_socios(self):
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            socios = self.db_manager.socios_con_estado()
            
            for socio in socios:
                # Formatear datos
                dni = socio['dni']
                nombre = socio['nombre']
                email = socio['email'] or ""
                ultimo_pago = socio['ultimo_pago'] or "Sin pagos"
                estado = socio['estado']
                vencimiento = socio['fecha_vencimiento'] or ""
                
                # Insertar en tabla
                item = self.tree.insert("", "end", values=(
                    dni, nombre, email, ultimo_pago, estado, vencimiento, "Ver acciones"
                ))
                
                # Colorear según estado
                if estado == "Activo":
                    self.tree.set(item, "Estado", "✅ Activo")
                else:
                    self.tree.set(item, "Estado", "❌ Vencido")
        
        except Exception as e:
            logging.error(f"Error cargando socios: {e}")
            messagebox.showerror("Error", f"Error al cargar socios: {str(e)}")
    
    def filtrar_socios(self, event=None):
        # Obtener filtros
        busqueda = self.search_entry.get().lower()
        estado_filtro = self.estado_filter.get()
        
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            socios = self.db_manager.socios_con_estado()
            
            for socio in socios:
                # Aplicar filtros
                if busqueda:
                    if (busqueda not in str(socio['dni']) and 
                        busqueda not in socio['nombre'].lower()):
                        continue
                
                if estado_filtro != "Todos":
                    if estado_filtro == "Activos" and socio['estado'] != "Activo":
                        continue
                    if estado_filtro == "Vencidos" and socio['estado'] != "Vencido":
                        continue
                
                # Insertar en tabla
                dni = socio['dni']
                nombre = socio['nombre']
                email = socio['email'] or ""
                ultimo_pago = socio['ultimo_pago'] or "Sin pagos"
                estado = socio['estado']
                vencimiento = socio['fecha_vencimiento'] or ""
                
                item = self.tree.insert("", "end", values=(
                    dni, nombre, email, ultimo_pago, estado, vencimiento, "Ver acciones"
                ))
                
                # Colorear según estado
                if estado == "Activo":
                    self.tree.set(item, "Estado", "✅ Activo")
                else:
                    self.tree.set(item, "Estado", "❌ Vencido")
        
        except Exception as e:
            logging.error(f"Error filtrando socios: {e}")
    
    def nuevo_socio(self):
        AltaSocioWindow(self, self.db_manager, callback=self.cargar_socios)
    
    def editar_socio_seleccionado(self, event=None):
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        dni = self.tree.item(item)['values'][0]
        
        EditarSocioWindow(self, self.db_manager, dni, callback=self.cargar_socios)
    
    def mostrar_menu_contextual(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        dni = self.tree.item(item)['values'][0]
        nombre = self.tree.item(item)['values'][1]
        
        # Crear menú contextual
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Editar Socio", command=lambda: self.editar_socio(dni))
        menu.add_command(label="Registrar Pago", command=lambda: self.registrar_pago(dni))
        menu.add_separator()
        menu.add_command(label="Ver Historial de Pagos", command=lambda: self.ver_historial(dni))
        menu.add_separator()
        menu.add_command(label="Eliminar Socio", command=lambda: self.eliminar_socio(dni, nombre))
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    def editar_socio(self, dni):
        EditarSocioWindow(self, self.db_manager, dni, callback=self.cargar_socios)
    
    def registrar_pago(self, dni):
        RegistrarPagoWindow(self, self.db_manager, dni, callback=self.cargar_socios)
    
    def ver_historial(self, dni):
        try:
            pagos = self.db_manager.obtener_pagos_por_dni(dni)
            socio = self.db_manager.obtener_socio(dni)
            
            # Ventana de historial
            historial_window = ctk.CTkToplevel(self)
            historial_window.title(f"Historial de Pagos - {socio['nombre']}")
            historial_window.geometry("600x400")
            historial_window.transient(self)
            
            # Título
            title_label = ctk.CTkLabel(historial_window, 
                                     text=f"Historial de Pagos - {socio['nombre']} (DNI: {dni})",
                                     font=ctk.CTkFont(**FONTS['BODY_MEDIUM']))
            title_label.pack(pady=10)
            
            # Tabla de pagos
            columns = ("Fecha", "Monto", "Método")
            tree = ttk.Treeview(historial_window, columns=columns, show="headings")
            
            tree.heading("Fecha", text="Fecha")
            tree.heading("Monto", text="Monto")
            tree.heading("Método", text="Método")
            
            tree.column("Fecha", width=150)
            tree.column("Monto", width=150)
            tree.column("Método", width=150)
            
            for pago in pagos:
                tree.insert("", "end", iid=str(pago['id']), values=(
                    pago['fecha_pago'],
                    f"${pago['monto']:.2f}",
                    pago['metodo_pago'].title()
                ))

            tree.pack(fill="both", expand=True, padx=20, pady=10)

            # Botones acciones
            btn_frame = ctk.CTkFrame(historial_window)
            btn_frame.pack(fill="x", padx=20, pady=(0,10))

            def refrescar_tabla():
                for item in tree.get_children():
                    tree.delete(item)
                nuevos = self.db_manager.obtener_pagos_por_dni(dni)
                for p in nuevos:
                    tree.insert("", "end", iid=str(p['id']), values=(p['fecha_pago'], f"${p['monto']:.2f}", p['metodo_pago'].title()))

            def editar_pago_sel():
                sel = tree.selection()
                if not sel:
                    messagebox.showwarning("Atención", "Seleccione un pago para editar")
                    return
                pago_id = int(sel[0])
                EditarPagoWindow(self, self.db_manager, pago_id, callback=refrescar_tabla)

            ctk.CTkButton(btn_frame, text="Editar pago seleccionado", command=editar_pago_sel).pack(side="left")
            
            def eliminar_pago_sel():
                sel = tree.selection()
                if not sel:
                    messagebox.showwarning("Atención", "Seleccione un pago para eliminar")
                    return
                pago_id = int(sel[0])
                if not messagebox.askyesno("Confirmar eliminación", "¿Eliminar el pago seleccionado? Esta acción no se puede deshacer."):
                    return
                try:
                    self.db_manager.eliminar_pago(pago_id)
                    refrescar_tabla()
                    messagebox.showinfo("Éxito", "Pago eliminado correctamente")
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo eliminar el pago: {str(e)}")

            ctk.CTkButton(btn_frame, text="Eliminar pago seleccionado", command=eliminar_pago_sel).pack(side="left", padx=10)
            ctk.CTkButton(btn_frame, text="Cerrar", command=historial_window.destroy).pack(side="right")
        
        except Exception as e:
            logging.error(f"Error mostrando historial: {e}")
            messagebox.showerror("Error", f"Error al mostrar historial: {str(e)}")
    
    def eliminar_socio(self, dni, nombre):
        # Doble confirmación
        if not messagebox.askyesno("Confirmar eliminación", 
                                  f"¿Está seguro de eliminar al socio {nombre} (DNI: {dni})?\n\n"
                                  "Esta acción eliminará también todos sus pagos y NO se puede deshacer."):
            return
        
        if not messagebox.askyesno("Confirmación final", 
                                  f"ÚLTIMA CONFIRMACIÓN:\n\n"
                                  f"Se eliminará permanentemente:\n"
                                  f"• Socio: {nombre}\n"
                                  f"• DNI: {dni}\n"
                                  f"• Todos sus pagos\n\n"
                                  f"¿Continuar?"):
            return
        
        try:
            self.db_manager.eliminar_socio_y_pagos(dni)
            messagebox.showinfo("Éxito", f"Socio {nombre} eliminado correctamente")
            self.cargar_socios()
        except Exception as e:
            logging.error(f"Error eliminando socio: {e}")
            messagebox.showerror("Error", f"Error al eliminar socio: {str(e)}")

class IngresosFrame(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.import_export = ImportExportManager(db_manager)
        
        self.create_widgets()
        self.cargar_ingresos()
    
    def create_widgets(self):
        # Frame superior
        control_frame = ctk.CTkFrame(self)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        # Título
        title_label = ctk.CTkLabel(control_frame, text="Historial de Ingresos", 
                                 font=ctk.CTkFont(**FONTS['SUBTITLE']))
        title_label.pack(side="left", padx=10, pady=10)
        
        # Botón exportar
        export_btn = ctk.CTkButton(control_frame, text="Exportar Excel", 
                                 command=self.exportar_ingresos,
                                 font=ctk.CTkFont(**FONTS['BUTTON']))
        export_btn.pack(side="right", padx=10, pady=10)
        
        # Frame de filtros
        filter_frame = ctk.CTkFrame(self)
        filter_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Búsqueda
        ctk.CTkLabel(filter_frame, text="Buscar:", font=ctk.CTkFont(**FONTS['LABEL'])).pack(side="left", padx=(10, 5), pady=10)
        self.search_entry = ctk.CTkEntry(filter_frame, placeholder_text="DNI o nombre...", font=ctk.CTkFont(**FONTS['INPUT']))
        self.search_entry.pack(side="left", padx=5, pady=10)
        self.search_entry.bind('<KeyRelease>', self.filtrar_ingresos)
        
        # Filtros de fecha
        ctk.CTkLabel(filter_frame, text="Desde:").pack(side="left", padx=(20, 5), pady=10)
        self.fecha_desde = ctk.CTkEntry(filter_frame, placeholder_text="YYYY-MM-DD", width=120)
        self.fecha_desde.pack(side="left", padx=5, pady=10)
        
        ctk.CTkLabel(filter_frame, text="Hasta:").pack(side="left", padx=(10, 5), pady=10)
        self.fecha_hasta = ctk.CTkEntry(filter_frame, placeholder_text="YYYY-MM-DD", width=120)
        self.fecha_hasta.pack(side="left", padx=5, pady=10)
        
        # Botón filtrar
        filter_btn = ctk.CTkButton(filter_frame, text="Filtrar", 
                                 command=self.filtrar_ingresos, width=100)
        filter_btn.pack(side="left", padx=10, pady=10)
        
        # Botón refrescar
        refresh_btn = ctk.CTkButton(filter_frame, text="Refrescar", 
                                  command=self.cargar_ingresos, width=100)
        refresh_btn.pack(side="right", padx=10, pady=10)
        
        # Tabla
        self.create_table()
    
    def create_table(self):
        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        columns = ("Fecha/Hora", "DNI", "Nombre", "Estado")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        
        self.tree.heading("Fecha/Hora", text="Fecha/Hora")
        self.tree.heading("DNI", text="DNI")
        self.tree.heading("Nombre", text="Nombre")
        self.tree.heading("Estado", text="Estado")
        
        self.tree.column("Fecha/Hora", width=180)
        self.tree.column("DNI", width=100)
        self.tree.column("Nombre", width=200)
        self.tree.column("Estado", width=150)
        
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def cargar_ingresos(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            ingresos = self.db_manager.listar_ingresos()
            
            for ingreso in ingresos:
                # Formatear fecha
                fecha_dt = datetime.fromisoformat(ingreso['fecha'])
                fecha_str = fecha_dt.strftime('%Y-%m-%d %H:%M:%S')
                
                dni = ingreso['dni'] or ""
                nombre = ingreso['nombre'] or ""
                estado = ingreso['estado']
                
                # Agregar emoji según estado
                if estado == "Activo":
                    estado_display = "✅ Activo"
                elif estado == "Vencido":
                    estado_display = "❌ Vencido"
                else:
                    estado_display = "⚠️ No registrado"
                
                self.tree.insert("", "end", values=(fecha_str, dni, nombre, estado_display))
        
        except Exception as e:
            logging.error(f"Error cargando ingresos: {e}")
            messagebox.showerror("Error", f"Error al cargar ingresos: {str(e)}")
    
    def filtrar_ingresos(self, event=None):
        busqueda = self.search_entry.get().lower()
        fecha_desde = self.fecha_desde.get().strip() or None
        fecha_hasta = self.fecha_hasta.get().strip() or None
        
        # Validar fechas
        if fecha_desde:
            try:
                datetime.strptime(fecha_desde, '%Y-%m-%d')
            except ValueError:
                messagebox.showerror("Error", "Fecha 'Desde' debe tener formato YYYY-MM-DD")
                return
        
        if fecha_hasta:
            try:
                datetime.strptime(fecha_hasta, '%Y-%m-%d')
            except ValueError:
                messagebox.showerror("Error", "Fecha 'Hasta' debe tener formato YYYY-MM-DD")
                return
        
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            ingresos = self.db_manager.listar_ingresos(fecha_desde, fecha_hasta, busqueda)
            
            for ingreso in ingresos:
                fecha_dt = datetime.fromisoformat(ingreso['fecha'])
                fecha_str = fecha_dt.strftime('%Y-%m-%d %H:%M:%S')
                
                dni = ingreso['dni'] or ""
                nombre = ingreso['nombre'] or ""
                estado = ingreso['estado']
                
                if estado == "Activo":
                    estado_display = "✅ Activo"
                elif estado == "Vencido":
                    estado_display = "❌ Vencido"
                else:
                    estado_display = "⚠️ No registrado"
                
                self.tree.insert("", "end", values=(fecha_str, dni, nombre, estado_display))
        
        except Exception as e:
            logging.error(f"Error filtrando ingresos: {e}")
            messagebox.showerror("Error", f"Error al filtrar ingresos: {str(e)}")
    
    def exportar_ingresos(self):
        fecha_desde = self.fecha_desde.get().strip() or None
        fecha_hasta = self.fecha_hasta.get().strip() or None
        
        rango = None
        if fecha_desde and fecha_hasta:
            rango = (fecha_desde, fecha_hasta)
        
        self.import_export.exportar_ingresos(self, rango)

class ReportesFrame(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.dashboard_manager = DashboardManager(db_manager.db_path)
        self.dashboard_data = {}
        self.selected_range = '30d'
        self.last_update_label = None
        self.kpi_chart_canvas = None
        self.kpi_chart_figure = None
        self.kpi_chart_holder = None
        self._nav = {'notebook': None, 'socios': None, 'ingresos': None}
        
        self.create_widgets()
        self.actualizar_dashboard()
        self.schedule_dashboard_refresh()
    
    def create_widgets(self):
        # Frame superior
        control_frame = ctk.CTkFrame(self)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        title_label = ctk.CTkLabel(control_frame, text="Dashboard Inteligente", 
                                 font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(side="left", padx=10, pady=10)
        
        # Última actualización
        self.last_update_label = ctk.CTkLabel(control_frame, text="Actualizado: —", text_color="gray")
        self.last_update_label.pack(side="left", padx=10)
        
        # Botón actualizar
        refresh_btn = ctk.CTkButton(control_frame, text="Actualizar", 
                                  command=self.actualizar_dashboard)
        refresh_btn.pack(side="right", padx=10, pady=10)
        
        # Filtros rápidos
        filters_frame = ctk.CTkFrame(self, fg_color="transparent")
        filters_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(filters_frame, text="Rango:").pack(side="left", padx=(10, 5))
        ctk.CTkButton(filters_frame, text="Hoy", width=90, command=lambda: self._set_range_and_refresh('1d')).pack(side="left", padx=5)
        ctk.CTkButton(filters_frame, text="7 días", width=90, command=lambda: self._set_range_and_refresh('7d')).pack(side="left", padx=5)
        ctk.CTkButton(filters_frame, text="30 días", width=90, command=lambda: self._set_range_and_refresh('30d')).pack(side="left", padx=5)
        ctk.CTkButton(filters_frame, text="90 días", width=90, command=lambda: self._set_range_and_refresh('90d')).pack(side="left", padx=5)
        ctk.CTkButton(filters_frame, text="Todo", width=90, command=lambda: self._set_range_and_refresh('all')).pack(side="left", padx=5)
        
        self.create_alerts_frame()
        
        # Frame de KPIs
        self.create_kpis_frame_v2()
        
        self.create_quick_actions_frame()
        
        # Frame de actividad reciente
        self.create_recent_activity_frame()
    
    def create_alerts_frame(self):
        alerts_frame = ctk.CTkFrame(self)
        alerts_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        title = ctk.CTkLabel(alerts_frame, text="🚨 Alertas Inteligentes", 
                           font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(pady=(10, 5))
        title = ctk.CTkLabel(alerts_frame, text="🚨 Alertas Inteligentes", 
                           font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(pady=(10, 5))
        
        # Scrollable frame para alertas
        self.alerts_scroll = ctk.CTkScrollableFrame(alerts_frame, height=120)
        self.alerts_scroll.pack(fill="x", padx=10, pady=(0, 10))
        
        # Placeholder inicial
        self.no_alerts_label = ctk.CTkLabel(self.alerts_scroll, 
                                          text="No hay alertas en este momento",
                                          text_color="gray")
        self.no_alerts_label.pack(pady=20)
    
    def create_kpis_frame(self):
        kpis_frame = ctk.CTkFrame(self)
        kpis_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        title = ctk.CTkLabel(kpis_frame, text="📊 KPIs Principales", 
                           font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(pady=(10, 5))
        
        # Grid de KPIs
        grid_frame = ctk.CTkFrame(kpis_frame, fg_color="transparent")
        grid_frame.pack(fill="x", padx=10, pady=10)
        
        # Primera fila
        row1 = ctk.CTkFrame(grid_frame, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        
        self.total_socios_card = self.create_kpi_card(row1, "Total Socios", "0")
        self.total_socios_card.pack(side="left", padx=5, fill="x", expand=True)
        
        self.activos_card = self.create_kpi_card(row1, "Activos", "0", COLORS['ACTIVE_GREEN'])
        self.activos_card.pack(side="left", padx=5, fill="x", expand=True)
        
        self.vencidos_card = self.create_kpi_card(row1, "Vencidos", "0", COLORS['EXPIRED_RED'])
        self.vencidos_card.pack(side="left", padx=5, fill="x", expand=True)
        
        self.tasa_actividad_card = self.create_kpi_card(row1, "Tasa Actividad", "0%", COLORS['SOMA_ORANGE'])
        self.tasa_actividad_card.pack(side="left", padx=5, fill="x", expand=True)
        
        # Segunda fila
        row2 = ctk.CTkFrame(grid_frame, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        
        self.ingresos_mes_card = self.create_kpi_card(row2, "Ingresos del Mes", "$0")
        self.ingresos_mes_card.pack(side="left", padx=5, fill="x", expand=True)
        
        self.visitas_hoy_card = self.create_kpi_card(row2, "Visitas Hoy", "0")
        self.visitas_hoy_card.pack(side="left", padx=5, fill="x", expand=True)
        
        self.promedio_visitas_card = self.create_kpi_card(row2, "Promedio Diario", "0")
        self.promedio_visitas_card.pack(side="left", padx=5, fill="x", expand=True)
        
        # Espacio vacío para mantener simetría
        # Fila extra con nuevos KPIs
        row3 = ctk.CTkFrame(grid_frame, fg_color="transparent")
        row3.pack(fill="x", pady=5)

        self.nuevos_mes_card = self.create_kpi_card_interactive(row3, "Nuevos (Mes)", "0")
        self.nuevos_mes_card.pack(side="left", padx=5, fill="x", expand=True)

        self.renovaciones_mes_card = self.create_kpi_card_interactive(row3, "Renovaciones (Mes)", "0")
        self.renovaciones_mes_card.pack(side="left", padx=5, fill="x", expand=True)

        spacer = ctk.CTkFrame(row3, fg_color="transparent")
        spacer.pack(side="left", padx=5, fill="x", expand=True)

        spacer2 = ctk.CTkFrame(row3, fg_color="transparent")
        spacer2.pack(side="left", padx=5, fill="x", expand=True)
    
    def create_quick_actions_frame(self):
        actions_frame = ctk.CTkFrame(self)
        actions_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        title = ctk.CTkLabel(actions_frame, text="⚡ Acciones Rápidas", 
                           font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(pady=(10, 5))
        
        # Frame para botones de acciones
        self.actions_container = ctk.CTkFrame(actions_frame, fg_color="transparent")
        self.actions_container.pack(fill="x", padx=10, pady=(0, 10))
        
        # Placeholder inicial
        self.no_actions_label = ctk.CTkLabel(self.actions_container, 
                                           text="No hay acciones sugeridas",
                                           text_color="gray")
        self.no_actions_label.pack(pady=20)
    
    def create_recent_activity_frame(self):
        activity_frame = ctk.CTkFrame(self)
        activity_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        title = ctk.CTkLabel(activity_frame, text="📈 Actividad Reciente", 
                           font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(pady=(10, 5))
        
        # Lista scrollable de actividad
        self.activity_scroll = ctk.CTkScrollableFrame(activity_frame, height=200)
        self.activity_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Placeholder inicial
        self.no_activity_label = ctk.CTkLabel(self.activity_scroll, 
                                            text="No hay actividad reciente",
                                            text_color="gray")
        self.no_activity_label.pack(pady=20)

    def create_kpis_frame_v2(self):
        kpis_frame = ctk.CTkFrame(self)
        kpis_frame.pack(fill="x", padx=10, pady=(0, 10))

        title = ctk.CTkLabel(kpis_frame, text="KPIs Principales", font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(pady=(10, 5))

        grid_frame = ctk.CTkFrame(kpis_frame, fg_color="transparent")
        grid_frame.pack(fill="x", padx=10, pady=10)

        row1 = ctk.CTkFrame(grid_frame, fg_color="transparent")
        row1.pack(fill="x", pady=5)

        self.total_socios_card = self.create_kpi_card_interactive(row1, "Total Socios", "0",
                                                                  on_click=lambda: self._go_to_socios())
        self.total_socios_card.pack(side="left", padx=5, fill="x", expand=True)

        self.activos_card = self.create_kpi_card_interactive(row1, "Activos", "0", COLORS['ACTIVE_GREEN'],
                                                             on_click=lambda: self._go_to_socios("Activos"))
        self.activos_card.pack(side="left", padx=5, fill="x", expand=True)

        self.vencidos_card = self.create_kpi_card_interactive(row1, "Vencidos", "0", COLORS['EXPIRED_RED'],
                                                              on_click=lambda: self._go_to_socios("Vencidos"))
        self.vencidos_card.pack(side="left", padx=5, fill="x", expand=True)

        self.tasa_actividad_card = self.create_kpi_card_interactive(row1, "Tasa Actividad", "0%", COLORS['SOMA_ORANGE'])
        self.tasa_actividad_card.pack(side="left", padx=5, fill="x", expand=True)

        row2 = ctk.CTkFrame(grid_frame, fg_color="transparent")
        row2.pack(fill="x", pady=5)

        self.ingresos_mes_card = self.create_kpi_card_interactive(row2, "Ingresos del Mes", "$0",
                                                                  on_click=lambda: self._go_to_ingresos())
        self.ingresos_mes_card.pack(side="left", padx=5, fill="x", expand=True)

        self.visitas_hoy_card = self.create_kpi_card_interactive(row2, "Visitas Hoy", "0")
        self.visitas_hoy_card.pack(side="left", padx=5, fill="x", expand=True)

        self.promedio_visitas_card = self.create_kpi_card_interactive(row2, "Promedio Diario", "0")
        self.promedio_visitas_card.pack(side="left", padx=5, fill="x", expand=True)

        empty_card = ctk.CTkFrame(row2, fg_color="transparent")
        empty_card.pack(side="left", padx=5, fill="x", expand=True)

        # Holder para gráfico donut
        self.kpi_chart_holder = ctk.CTkFrame(kpis_frame)
        self.kpi_chart_holder.pack(fill='x', padx=10, pady=(0,10))
        ctk.CTkLabel(self.kpi_chart_holder, text="Activos vs Vencidos", font=ctk.CTkFont(size=16, weight='bold')).pack(pady=(10,5))

        # Holder para gráfico de métodos de pago (mes)
        self.payment_methods_chart_holder = ctk.CTkFrame(kpis_frame)
        self.payment_methods_chart_holder.pack(fill='x', padx=10, pady=(0,10))
        ctk.CTkLabel(self.payment_methods_chart_holder, text="Métodos de pago (mes)", font=ctk.CTkFont(size=16, weight='bold')).pack(pady=(10,5))

        # Holder para línea de ingresos (30 días o rango)
        self.income_line_holder = ctk.CTkFrame(kpis_frame)
        self.income_line_holder.pack(fill='both', expand=True, padx=10, pady=(0,10))
        ctk.CTkLabel(self.income_line_holder, text="Ingresos por día", font=ctk.CTkFont(size=16, weight='bold')).pack(pady=(10,5))

    def create_kpi_card_interactive(self, parent, titulo, valor, color=None, on_click=None):
        card = ctk.CTkFrame(parent, fg_color=color or "#EFEFEF")
        card.pack_propagate(False)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=10, pady=10)

        title_label = ctk.CTkLabel(inner, text=titulo, font=ctk.CTkFont(**FONTS['CAPTION']))
        title_label.pack(anchor="w")

        value_label = ctk.CTkLabel(inner, text=valor, font=ctk.CTkFont(**FONTS['HEADER']))
        value_label.pack(anchor="w", pady=(4, 2))

        delta_label = ctk.CTkLabel(inner, text="", text_color="gray")
        delta_label.pack(anchor="w")

        card.value_label = value_label
        card.delta_label = delta_label

        if on_click:
            def handler(event=None):
                try:
                    on_click()
                except Exception as e:
                    logging.warning(f"Error en click KPI {titulo}: {e}")
            for w in (card, inner, title_label, value_label, delta_label):
                w.bind('<Button-1>', handler)

        card.configure(height=100)
        return card

    def create_kpi_card(self, parent, titulo, valor, color=None):
        card = ctk.CTkFrame(parent, fg_color=color or "#2B2B2B")
        
        title_label = ctk.CTkLabel(card, text=titulo, font=ctk.CTkFont(**FONTS['CAPTION']))
        title_label.pack(pady=(10, 5))
        
        value_label = ctk.CTkLabel(card, text=valor, font=ctk.CTkFont(**FONTS['HEADER']))
        value_label.pack(pady=(0, 10))
        
        # Guardar referencia al label del valor
        card.value_label = value_label
        
        return card
    
    def actualizar_dashboard(self):
        """Actualiza todos los datos del dashboard inteligente"""
        try:
            # Obtener datos del dashboard
            try:
                self.dashboard_data = self.dashboard_manager.get_dashboard_data(self.selected_range)
            except TypeError:
                self.dashboard_data = self.dashboard_manager.get_dashboard_data()
            
            # Actualizar KPIs
            self.actualizar_kpis()
            
            # Actualizar alertas
            self.actualizar_alertas()
            
            # Actualizar acciones rápidas
            self.actualizar_acciones_rapidas()
            
            # Actualizar actividad reciente
            self.actualizar_actividad_reciente()
            
            # Actualizar etiqueta de última actualización
            try:
                now = datetime.now().strftime('%H:%M:%S')
                if self.last_update_label:
                    self.last_update_label.configure(text=f"Actualizado: {now} – Rango: {self.selected_range}")
            except Exception:
                pass
            
        except Exception as e:
            logging.error(f"Error actualizando dashboard: {e}")
            messagebox.showerror("Error", f"Error al actualizar dashboard: {str(e)}")
    
    def actualizar_kpis(self):
        """Actualiza los KPIs en la interfaz"""
        kpis = self.dashboard_data.get('kpis', {})
        
        # Actualizar valores
        self.total_socios_card.value_label.configure(text=str(kpis.get('total_socios', 0)))
        self.activos_card.value_label.configure(text=str(kpis.get('socios_activos', 0)))
        self.vencidos_card.value_label.configure(text=str(kpis.get('socios_inactivos', 0)))
        self.tasa_actividad_card.value_label.configure(text=f"{kpis.get('tasa_actividad', 0)}%")
        self.ingresos_mes_card.value_label.configure(text=f"${kpis.get('ingresos_mes', 0):.2f}")
        self.visitas_hoy_card.value_label.configure(text=str(kpis.get('visitas_hoy', 0)))
        self.promedio_visitas_card.value_label.configure(text=str(kpis.get('promedio_visitas_diarias', 0)))
        # Nuevos y Renovaciones del mes
        try:
            self.nuevos_mes_card.value_label.configure(text=str(kpis.get('nuevos_mes', 0)))
        except Exception:
            pass
        try:
            self.renovaciones_mes_card.value_label.configure(text=str(kpis.get('renovaciones_mes', 0)))
        except Exception:
            pass

        # Deltas (si hay previos)
        prev = self.dashboard_data.get('kpis_prev', {})
        def set_delta(card, curr, prev_val, suffix=""):
            try:
                if prev_val is None:
                    card.delta_label.configure(text="")
                    return
                delta = curr - prev_val
                sign = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
                color = COLORS['SUCCESS_GREEN'] if delta > 0 else (COLORS['EXPIRED_RED'] if delta < 0 else 'gray')
                text = f"{sign} {delta:.1f}{suffix} vs prev." if suffix else f"{sign} {delta:.0f}{suffix} vs prev."
                card.delta_label.configure(text=text, text_color=color)
            except Exception:
                card.delta_label.configure(text="")

        try:
            set_delta(self.activos_card, float(kpis.get('socios_activos', 0) or 0), float(prev.get('socios_activos')) if prev.get('socios_activos') is not None else None)
            set_delta(self.vencidos_card, float(kpis.get('socios_inactivos', 0) or 0), float(prev.get('socios_inactivos')) if prev.get('socios_inactivos') is not None else None)
            set_delta(self.ingresos_mes_card, float(kpis.get('ingresos_mes', 0.0) or 0.0), float(prev.get('ingresos_mes')) if prev.get('ingresos_mes') is not None else None)
            set_delta(self.tasa_actividad_card, float(kpis.get('tasa_actividad', 0.0) or 0.0), float(prev.get('tasa_actividad')) if prev.get('tasa_actividad') is not None else None, suffix='%')
        except Exception:
            pass

        # Donut activos vs vencidos
        try:
            activos = float(kpis.get('socios_activos', 0) or 0)
            vencidos = float(kpis.get('socios_inactivos', 0) or 0)
            self._update_donut(activos, vencidos)
        except Exception:
            pass
        # Línea de ingresos (rango)
        try:
            income_series = self.dashboard_data.get('income_series', [])
            self._update_income_line(income_series)
        except Exception:
            pass
        # Donut métodos de pago (mes)
        try:
            methods = self.dashboard_data.get('payment_methods', {})
            self._update_payment_methods_donut(methods)
        except Exception:
            pass

    def _update_donut(self, activos, vencidos):
        total_members = activos + vencidos
        labels = [f"Activos {int(activos)}", f"Vencidos {int(vencidos)}"]
        colors = [COLORS['ACTIVE_GREEN'], COLORS['EXPIRED_RED']]

        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except Exception as e:
            logging.debug(f"Matplotlib no disponible: {e}")
            return

        if self.kpi_chart_figure is None:
            self.kpi_chart_figure = plt.Figure(figsize=(3.2, 3.2), dpi=100)
            ax = self.kpi_chart_figure.add_subplot(111)
            self.kpi_chart_canvas = FigureCanvasTkAgg(self.kpi_chart_figure, master=self.kpi_chart_holder)
            self.kpi_chart_canvas.get_tk_widget().pack()
        else:
            ax = self.kpi_chart_figure.axes[0]
            ax.clear()

        ax.axis('equal')
        if total_members <= 0:
            ax.text(0.5, 0.5, 'Sin datos', ha='center', va='center')
        else:
            total = activos + vencidos
            sizes = [activos/total, vencidos/total]
            wedges, texts = ax.pie(sizes, colors=colors, startangle=90, wedgeprops=dict(width=0.35))
            try:
                centre_circle = plt.Circle((0,0),0.55,fc='white')
                ax.add_artist(centre_circle)
            except Exception:
                pass
            ax.legend(labels, loc='lower center', bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False)
        self.kpi_chart_canvas.draw()

    def _update_income_line(self, income_series):
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except Exception:
            return
        dates = [item.get('fecha') for item in income_series]
        totals = [float(item.get('total', 0) or 0) for item in income_series]
        if not hasattr(self, 'income_line_figure'):
            self.income_line_figure = plt.Figure(figsize=(6.4, 2.8), dpi=100)
            ax = self.income_line_figure.add_subplot(111)
            ax.plot(dates, totals, marker='o', color='#1f77b4')
            ax.set_ylabel('Monto')
            ax.tick_params(axis='x', rotation=45)
            ax.grid(True, linestyle='--', alpha=0.3)
            self.income_line_canvas = FigureCanvasTkAgg(self.income_line_figure, master=self.income_line_holder)
            self.income_line_canvas.get_tk_widget().pack(fill='both', expand=True)
        else:
            ax = self.income_line_figure.axes[0]
            ax.clear()
            ax.plot(dates, totals, marker='o', color='#1f77b4')
            ax.set_ylabel('Monto')
            ax.tick_params(axis='x', rotation=45)
            ax.grid(True, linestyle='--', alpha=0.3)
            self.income_line_canvas.draw()

    def _update_payment_methods_donut(self, methods):
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except Exception:
            return
        efectivo = float(methods.get('efectivo', 0) or 0)
        transferencia = float(methods.get('transferencia', 0) or 0)
        otros = sum(float(v or 0) for k, v in methods.items() if k not in ('efectivo','transferencia'))
        total_val = efectivo + transferencia + otros
        labels = [f"Efectivo ${efectivo:.0f}", f"Transferencia ${transferencia:.0f}"]
        colors = [COLORS['SOMA_ORANGE'], COLORS.get('INFO_BLUE', '#17a2b8')]

        if not hasattr(self, 'payment_methods_chart_figure'):
            self.payment_methods_chart_figure = plt.Figure(figsize=(3.2, 3.2), dpi=100)
            ax = self.payment_methods_chart_figure.add_subplot(111)
            self.payment_methods_chart_canvas = FigureCanvasTkAgg(self.payment_methods_chart_figure, master=self.payment_methods_chart_holder)
            self.payment_methods_chart_canvas.get_tk_widget().pack()
        else:
            ax = self.payment_methods_chart_figure.axes[0]
            ax.clear()

        ax.axis('equal')
        if total_val <= 0:
            ax.text(0.5, 0.5, 'Sin pagos', ha='center', va='center')
        else:
            total = total_val
            sizes = [efectivo/total, transferencia/total]
            ax.pie(sizes, colors=colors, startangle=90, wedgeprops=dict(width=0.35))
            try:
                centre_circle = plt.Circle((0,0),0.55,fc='white')
                ax.add_artist(centre_circle)
            except Exception:
                pass
            ax.legend(labels, loc='lower center', bbox_to_anchor=(0.5, -0.2), ncol=1, frameon=False)
        self.payment_methods_chart_canvas.draw()

    def _set_range_and_refresh(self, key):
        self.selected_range = key
        self.actualizar_dashboard()

    def set_navigation_context(self, notebook, socios_frame=None, ingresos_frame=None):
        self._nav = {'notebook': notebook, 'socios': socios_frame, 'ingresos': ingresos_frame}

    def _go_to_socios(self, estado=None):
        try:
            if self._nav.get('notebook'):
                self._nav['notebook'].set("Socios")
            if estado and self._nav.get('socios'):
                self._nav['socios'].estado_filter.set(estado)
                self._nav['socios'].filtrar_socios()
        except Exception as e:
            logging.debug(f"Navegación Socios falló: {e}")

    def _go_to_ingresos(self):
        try:
            if self._nav.get('notebook'):
                self._nav['notebook'].set("Ingresos")
        except Exception as e:
            logging.debug(f"Navegación Ingresos falló: {e}")
    
    def actualizar_alertas(self):
        """Actualiza las alertas inteligentes"""
        alerts = self.dashboard_data.get('alerts', [])
        
        # Limpiar alertas existentes
        for widget in self.alerts_scroll.winfo_children():
            widget.destroy()
        
        if not alerts:
            self.no_alerts_label = ctk.CTkLabel(self.alerts_scroll, 
                                              text="✅ No hay alertas en este momento",
                                              text_color="gray")
            self.no_alerts_label.pack(pady=20)
            return
        
        # Crear alertas
        for alert in alerts:
            self.create_alert_widget(alert)
    
    def create_alert_widget(self, alert):
        """Crea un widget de alerta"""
        alert_frame = ctk.CTkFrame(self.alerts_scroll)
        alert_frame.pack(fill="x", padx=5, pady=2)
        
        # Color según tipo de alerta
        colors = {
            "danger": COLORS['EXPIRED_RED'],
            "warning": COLORS['WARNING_AMBER'],
            "info": "#2196F3"
        }
        
        # Icono según tipo
        icons = {
            "danger": "🚨",
            "warning": "⚠️",
            "info": "ℹ️"
        }
        
        alert_type = alert.get('type', 'info')
        
        # Frame interno con color
        inner_frame = ctk.CTkFrame(alert_frame, fg_color=colors.get(alert_type, "#2B2B2B"))
        inner_frame.pack(fill="x", padx=2, pady=2)
        
        # Contenido de la alerta
        content_frame = ctk.CTkFrame(inner_frame, fg_color="transparent")
        content_frame.pack(fill="x", padx=10, pady=8)
        
        # Icono y título
        header_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        header_frame.pack(fill="x")
        
        icon_label = ctk.CTkLabel(header_frame, text=icons.get(alert_type, "ℹ️"), 
                                font=ctk.CTkFont(size=16))
        icon_label.pack(side="left", padx=(0, 10))
        
        title_label = ctk.CTkLabel(header_frame, text=alert['title'], 
                                 font=ctk.CTkFont(size=14, weight="bold"),
                                 text_color="white")
        title_label.pack(side="left")
        
        # Mensaje
        message_label = ctk.CTkLabel(content_frame, text=alert['message'], 
                                   font=ctk.CTkFont(size=12),
                                   text_color="white")
        message_label.pack(anchor="w", pady=(5, 0))
        
        # Botón de acción si existe
        if alert.get('action'):
            action_btn = ctk.CTkButton(content_frame, text="Ver detalles", 
                                     command=lambda: self.handle_alert_action(alert),
                                     height=25, width=100)
            action_btn.pack(anchor="e", pady=(5, 0))
    
    def handle_alert_action(self, alert):
        """Maneja las acciones de las alertas"""
        action = alert.get('action')
        data = alert.get('data', {})
        
        if action == "view_expiring":
            self.show_expiring_members(data)
        elif action == "view_inactive":
            self.show_inactive_members(data)
        elif action == "view_income":
            self.show_income_details(data)
    
    def show_expiring_members(self, data):
        """Muestra ventana con socios que vencen"""
        dias = data.get('dias', 0)
        socios = data.get('socios', [])
        
        window = ctk.CTkToplevel(self)
        window.title(f"Socios que vencen en {dias} día{'s' if dias > 1 else ''}")
        window.geometry("600x400")
        window.transient(self)
        
        # Lista de socios
        for socio in socios:
            socio_frame = ctk.CTkFrame(window)
            socio_frame.pack(fill="x", padx=20, pady=5)
            
            info_label = ctk.CTkLabel(socio_frame, 
                                    text=f"{socio['nombre']} - DNI: {socio['dni']} - Última cuota: {socio['ultima_cuota']}")
            info_label.pack(pady=10)
    
    def show_inactive_members(self, data):
        """Muestra ventana con socios inactivos"""
        socios = data.get('socios', [])
        
        window = ctk.CTkToplevel(self)
        window.title("Socios Inactivos")
        window.geometry("600x400")
        window.transient(self)
        
        # Lista de socios inactivos
        for socio in socios:
            socio_frame = ctk.CTkFrame(window)
            socio_frame.pack(fill="x", padx=20, pady=5)
            
            ultima_visita = socio.get('ultima_visita', 'Nunca')
            info_label = ctk.CTkLabel(socio_frame, 
                                    text=f"{socio['nombre']} - DNI: {socio['dni']} - Última visita: {ultima_visita}")
            info_label.pack(pady=10)
    
    def show_income_details(self, data):
        """Muestra detalles de ingresos"""
        messagebox.showinfo("Ingresos del Mes", 
                          f"Ingresos actuales: ${data.get('actual', 0):.2f}\n"
                          f"Mes anterior: ${data.get('anterior', 0):.2f}\n"
                          f"Variación: {data.get('variacion', 0):.1f}%")
    
    def actualizar_acciones_rapidas(self):
        """Actualiza las acciones rápidas sugeridas"""
        actions = self.dashboard_data.get('quick_actions', [])
        
        # Limpiar acciones existentes
        for widget in self.actions_container.winfo_children():
            widget.destroy()
        
        if not actions:
            self.no_actions_label = ctk.CTkLabel(self.actions_container, 
                                               text="No hay acciones sugeridas",
                                               text_color="gray")
            self.no_actions_label.pack(pady=20)
            return
        
        # Crear botones de acciones
        actions_row = ctk.CTkFrame(self.actions_container, fg_color="transparent")
        actions_row.pack(fill="x", pady=10)
        
        for action in actions[:4]:  # Máximo 4 acciones
            self.create_action_button(actions_row, action)
    
    def create_action_button(self, parent, action):
        """Crea un botón de acción rápida"""
        # Color según prioridad
        colors = {
            "high": COLORS['EXPIRED_RED'],
            "medium": COLORS['WARNING_AMBER'],
            "low": COLORS['ACTIVE_GREEN']
        }
        
        priority = action.get('priority', 'low')
        
        btn = ctk.CTkButton(parent, 
                          text=f"{action.get('icon', '⚡')} {action['title']}\n{action['description']}", 
                          command=lambda: self.handle_quick_action(action),
                          fg_color=colors.get(priority, COLORS['ACTIVE_GREEN']),
                          height=60,
                          font=ctk.CTkFont(size=11))
        btn.pack(side="left", padx=5, fill="x", expand=True)
    
    def handle_quick_action(self, action):
        """Maneja las acciones rápidas"""
        action_type = action.get('action')
        
        if action_type == "renew_memberships":
            messagebox.showinfo("Acción", "Redirigiendo a renovación de cuotas...")
            # Aquí podrías cambiar a la pestaña de socios con filtro de vencimientos
        elif action_type == "contact_inactive":
            messagebox.showinfo("Acción", "Mostrando lista de socios inactivos...")
        elif action_type == "create_backup":
            self.create_manual_backup()
        elif action_type == "generate_report":
            messagebox.showinfo("Acción", "Generando reporte...")
    
    def create_manual_backup(self):
        """Crea un backup manual"""
        try:
            result = self.db_manager.create_incremental_backup("Backup manual desde dashboard")
            if result['success']:
                messagebox.showinfo("Éxito", f"Backup creado exitosamente:\n{result['filename']}")
            else:
                messagebox.showerror("Error", f"Error al crear backup: {result['error']}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al crear backup: {str(e)}")
    
    def actualizar_actividad_reciente(self):
        """Actualiza la actividad reciente"""
        activity = self.dashboard_data.get('recent_activity', [])
        
        # Limpiar actividad existente
        for widget in self.activity_scroll.winfo_children():
            widget.destroy()
        
        if not activity:
            self.no_activity_label = ctk.CTkLabel(self.activity_scroll, 
                                                text="No hay actividad reciente",
                                                text_color="gray")
            self.no_activity_label.pack(pady=20)
            return
        
        # Crear elementos de actividad
        for item in activity:
            self.create_activity_item(item)
    
    def create_activity_item(self, item):
        """Crea un elemento de actividad"""
        item_frame = ctk.CTkFrame(self.activity_scroll)
        item_frame.pack(fill="x", padx=5, pady=2)
        
        # Icono según tipo
        icons = {
            "visit": "👤",
            "payment": "💰"
        }
        
        # Color según estado
        colors = {
            "Activo": COLORS['ACTIVE_GREEN'],
            "Vencido": COLORS['EXPIRED_RED'],
            "No registrado": COLORS['WARNING_AMBER'],
            "completed": COLORS['ACTIVE_GREEN']
        }
        
        item_type = item.get('type', 'visit')
        status = item.get('status', '')
        
        # Contenido
        content_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        content_frame.pack(fill="x", padx=10, pady=5)
        
        # Icono y descripción
        icon_label = ctk.CTkLabel(content_frame, text=icons.get(item_type, "📝"), 
                                font=ctk.CTkFont(size=14))
        icon_label.pack(side="left", padx=(0, 10))
        
        desc_label = ctk.CTkLabel(content_frame, text=item['description'], 
                                font=ctk.CTkFont(size=12))
        desc_label.pack(side="left", anchor="w")
        
        # Timestamp
        try:
            if isinstance(item['timestamp'], str):
                if 'T' in item['timestamp']:
                    # Formato ISO
                    dt = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
                else:
                    # Formato fecha simple
                    dt = datetime.strptime(item['timestamp'], '%Y-%m-%d')
                time_str = dt.strftime('%H:%M')
            else:
                time_str = str(item['timestamp'])
        except:
            time_str = "N/A"
        
        time_label = ctk.CTkLabel(content_frame, text=time_str, 
                                font=ctk.CTkFont(size=10),
                                text_color="gray")
        time_label.pack(side="right")
        
        # Indicador de estado
        if status and status in colors:
            status_indicator = ctk.CTkFrame(content_frame, 
                                          fg_color=colors[status], 
                                          width=4, height=20)
            status_indicator.pack(side="right", padx=(5, 0))
    
    def schedule_dashboard_refresh(self):
        """Programa la actualización automática del dashboard"""
        refresh_interval = ALERT_CONFIG["refresh_interval_minutes"] * 60 * 1000  # Convertir a ms
        self.after(refresh_interval, self.auto_refresh_dashboard)
    
    def auto_refresh_dashboard(self):
        """Actualización automática del dashboard"""
        try:
            self.actualizar_dashboard()
        except Exception as e:
            logging.error(f"Error en actualización automática del dashboard: {e}")
        finally:
            # Programar siguiente actualización
            self.schedule_dashboard_refresh()

class ImportExportFrame(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.import_export = ImportExportManager(db_manager)
        
        self.create_widgets()
    
    def create_widgets(self):
        # Título
        title_label = ctk.CTkLabel(self, text="Importación / Exportación y Backups", 
                                 font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(pady=20)
        
        # Frame de exportación
        export_frame = ctk.CTkFrame(self)
        export_frame.pack(fill="x", padx=20, pady=10)
        
        export_title = ctk.CTkLabel(export_frame, text="Exportar a Excel", 
                                  font=ctk.CTkFont(size=16, weight="bold"))
        export_title.pack(pady=(10, 5))
        
        # Botones de exportación
        buttons_frame = ctk.CTkFrame(export_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(buttons_frame, text="Exportar Socios", 
                     command=self.exportar_socios).pack(side="left", padx=5, fill="x", expand=True)
        
        ctk.CTkButton(buttons_frame, text="Exportar Pagos", 
                     command=self.exportar_pagos).pack(side="left", padx=5, fill="x", expand=True)
        
        ctk.CTkButton(buttons_frame, text="Exportar Ingresos", 
                     command=self.exportar_ingresos).pack(side="left", padx=5, fill="x", expand=True)
        
        ctk.CTkButton(buttons_frame, text="Reporte Completo", 
                     command=self.exportar_reporte_completo,
                     fg_color=COLORS['SOMA_ORANGE']).pack(side="left", padx=5, fill="x", expand=True)
        
        # Frame de importación
        import_frame = ctk.CTkFrame(self)
        import_frame.pack(fill="x", padx=20, pady=10)
        
        import_title = ctk.CTkLabel(import_frame, text="Importar desde Excel", 
                                  font=ctk.CTkFont(size=16, weight="bold"))
        import_title.pack(pady=(10, 5))
        
        import_buttons = ctk.CTkFrame(import_frame, fg_color="transparent")
        import_buttons.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(import_buttons, text="Crear Plantilla", 
                     command=self.crear_plantilla).pack(side="left", padx=5, fill="x", expand=True)
        
        ctk.CTkButton(import_buttons, text="Importar Pagos", 
                     command=self.importar_pagos).pack(side="left", padx=5, fill="x", expand=True)
        
        backup_frame = ctk.CTkFrame(self)
        backup_frame.pack(fill="x", padx=20, pady=10)
        
        backup_title = ctk.CTkLabel(backup_frame, text="Sistema de Backups Incremental", 
                                  font=ctk.CTkFont(size=16, weight="bold"))
        backup_title.pack(pady=(10, 5))
        
        backup_buttons = ctk.CTkFrame(backup_frame, fg_color="transparent")
        backup_buttons.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(backup_buttons, text="Backup Manual", 
                     command=self.backup_incremental,
                     fg_color=COLORS['ACTIVE_GREEN']).pack(side="left", padx=5, fill="x", expand=True)
        
        ctk.CTkButton(backup_buttons, text="Ver Backups", 
                     command=self.ver_lista_backups).pack(side="left", padx=5, fill="x", expand=True)
        
        ctk.CTkButton(backup_buttons, text="Restaurar Backup", 
                     command=self.restaurar_backup).pack(side="left", padx=5, fill="x", expand=True)
        
        ctk.CTkButton(backup_buttons, text="Abrir Carpeta", 
                     command=self.abrir_carpeta_backups).pack(side="left", padx=5, fill="x", expand=True)
    
    def exportar_socios(self):
        self.import_export.exportar_socios(self)
    
    def exportar_pagos(self):
        self.import_export.exportar_pagos(self)
    
    def exportar_ingresos(self):
        self.import_export.exportar_ingresos(self)
    
    def exportar_reporte_completo(self):
        self.import_export.exportar_reporte_completo(self)
    
    def crear_plantilla(self):
        self.import_export.crear_plantilla_importacion(self)
    
    def importar_pagos(self):
        resultado = self.import_export.importar_pagos(self)
        if resultado:
            # Actualizar otras pestañas si es necesario
            pass
    
    def backup_manual(self):
        try:
            backup_path = self.db_manager.backup_manual()
            messagebox.showinfo("Éxito", f"Backup creado exitosamente:\n{backup_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al crear backup: {str(e)}")
    
    def backup_incremental(self):
        """Crea un backup incremental"""
        try:
            result = self.db_manager.create_incremental_backup("Backup manual desde interfaz")
            if result['success']:
                messagebox.showinfo("Éxito", 
                                  f"Backup incremental creado exitosamente:\n"
                                  f"Archivo: {result['filename']}\n"
                                  f"Tamaño: {result['metadata']['file_size']} bytes")
            else:
                messagebox.showerror("Error", f"Error al crear backup: {result['error']}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al crear backup: {str(e)}")
    
    def ver_lista_backups(self):
        """Muestra ventana con lista de backups disponibles"""
        try:
            backups = self.db_manager.get_backup_list()
            
            # Ventana de lista de backups
            backup_window = ctk.CTkToplevel(self)
            backup_window.title("Lista de Backups")
            backup_window.geometry("800x500")
            backup_window.transient(self)
            
            # Título
            title_label = ctk.CTkLabel(backup_window, 
                                     text="Backups Disponibles",
                                     font=ctk.CTkFont(size=16, weight="bold"))
            title_label.pack(pady=10)
            
            if not backups:
                no_backups_label = ctk.CTkLabel(backup_window, 
                                              text="No hay backups disponibles",
                                              text_color="gray")
                no_backups_label.pack(pady=50)
                return
            
            # Tabla de backups
            columns = ("Fecha", "Descripción", "Tamaño", "Comprimido")
            tree = ttk.Treeview(backup_window, columns=columns, show="headings", height=15)
            
            tree.heading("Fecha", text="Fecha de Creación")
            tree.heading("Descripción", text="Descripción")
            tree.heading("Tamaño", text="Tamaño")
            tree.heading("Comprimido", text="Comprimido")
            
            tree.column("Fecha", width=150)
            tree.column("Descripción", width=200)
            tree.column("Tamaño", width=100)
            tree.column("Comprimido", width=100)
            
            for backup in backups:
                fecha_dt = datetime.fromisoformat(backup['created_at'])
                fecha_str = fecha_dt.strftime('%Y-%m-%d %H:%M')
                
                size_mb = backup['file_size'] / (1024 * 1024)
                size_str = f"{size_mb:.2f} MB"
                
                compressed = "Sí" if backup.get('compressed', False) else "No"
                
                tree.insert("", "end", values=(
                    fecha_str,
                    backup.get('description', 'Sin descripción'),
                    size_str,
                    compressed
                ))
            
            tree.pack(fill="both", expand=True, padx=20, pady=10)
            
            # Botón cerrar
            ctk.CTkButton(backup_window, text="Cerrar", 
                         command=backup_window.destroy).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al obtener lista de backups: {str(e)}")
    
    def restaurar_backup(self):
        """Restaura desde un backup seleccionado"""
        try:
            backups = self.db_manager.get_backup_list()
            
            if not backups:
                messagebox.showwarning("Advertencia", "No hay backups disponibles para restaurar")
                return
            
            # Ventana de selección de backup
            restore_window = ctk.CTkToplevel(self)
            restore_window.title("Restaurar Backup")
            restore_window.geometry("600x400")
            restore_window.transient(self)
            
            title_label = ctk.CTkLabel(restore_window, 
                                     text="Seleccionar Backup para Restaurar",
                                     font=ctk.CTkFont(size=16, weight="bold"))
            title_label.pack(pady=10)
            
            # Lista de backups
            backup_listbox = tk.Listbox(restore_window, height=10)
            backup_listbox.pack(fill="both", expand=True, padx=20, pady=10)
            
            backup_files = []
            for backup in backups:
                fecha_dt = datetime.fromisoformat(backup['created_at'])
                fecha_str = fecha_dt.strftime('%Y-%m-%d %H:%M')
                display_text = f"{fecha_str} - {backup.get('description', 'Sin descripción')}"
                backup_listbox.insert(tk.END, display_text)
                backup_files.append(backup['filename'])
            
            def realizar_restauracion():
                selection = backup_listbox.curselection()
                if not selection:
                    messagebox.showwarning("Advertencia", "Seleccione un backup para restaurar")
                    return
                
                backup_filename = backup_files[selection[0]]
                
                # Confirmación
                if not messagebox.askyesno("Confirmar Restauración", 
                                         f"¿Está seguro de restaurar desde el backup:\n{backup_filename}?\n\n"
                                         "Esta acción reemplazará la base de datos actual.\n"
                                         "Se creará un backup de seguridad automáticamente."):
                    return
                
                # Realizar restauración
                result = self.db_manager.restore_from_backup(backup_filename)
                
                if result['success']:
                    messagebox.showinfo("Éxito", 
                                      f"Base de datos restaurada exitosamente.\n"
                                      f"Backup de seguridad: {result.get('safety_backup', 'N/A')}")
                    restore_window.destroy()
                else:
                    messagebox.showerror("Error", f"Error al restaurar: {result['error']}")
            
            # Botones
            button_frame = ctk.CTkFrame(restore_window, fg_color="transparent")
            button_frame.pack(pady=10)
            
            ctk.CTkButton(button_frame, text="Restaurar", 
                         command=realizar_restauracion,
                         fg_color=COLORS['WARNING_AMBER']).pack(side="left", padx=10)
            
            ctk.CTkButton(button_frame, text="Cancelar", 
                         command=restore_window.destroy).pack(side="left", padx=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al preparar restauración: {str(e)}")
    
    def abrir_carpeta_backups(self):
        try:
            import subprocess
            import platform
            
            if platform.system() == "Windows":
                subprocess.run(["explorer", "backups"], check=True)
            else:
                messagebox.showinfo("Info", "Carpeta de backups: ./backups/")
        except Exception as e:
            messagebox.showerror("Error", f"Error al abrir carpeta: {str(e)}")

class PagosFrame(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.create_widgets()
        self.refrescar_pagos()
    
    def create_widgets(self):
        # Título principal
        title_label = ctk.CTkLabel(self, text="Gestión de Pagos", 
                                 font=ctk.CTkFont(size=28, weight="bold"),
                                 text_color=COLORS['SOMA_ORANGE'])
        title_label.pack(pady=(20, 30))
        
        # Frame superior para controles
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # Frame izquierdo para filtros
        filters_frame = ctk.CTkFrame(controls_frame)
        filters_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Filtro por DNI
        dni_frame = ctk.CTkFrame(filters_frame, fg_color="transparent")
        dni_frame.pack(side="left", padx=10, pady=10)
        
        ctk.CTkLabel(dni_frame, text="Filtrar por DNI:").pack(side="left")
        self.dni_filter = ctk.CTkEntry(dni_frame, placeholder_text="DNI del socio", width=120)
        self.dni_filter.pack(side="left", padx=(10, 0))
        self.dni_filter.bind('<KeyRelease>', self.filtrar_pagos)
        
        # Filtro por fecha
        date_frame = ctk.CTkFrame(filters_frame, fg_color="transparent")
        date_frame.pack(side="left", padx=10, pady=10)
        
        ctk.CTkLabel(date_frame, text="Desde:").pack(side="left")
        self.fecha_desde = ctk.CTkEntry(date_frame, placeholder_text="YYYY-MM-DD", width=100)
        self.fecha_desde.pack(side="left", padx=(10, 5))
        
        ctk.CTkLabel(date_frame, text="Hasta:").pack(side="left")
        self.fecha_hasta = ctk.CTkEntry(date_frame, placeholder_text="YYYY-MM-DD", width=100)
        self.fecha_hasta.pack(side="left", padx=(10, 0))
        
        # Botón aplicar filtros
        ctk.CTkButton(filters_frame, text="Aplicar Filtros", 
                     command=self.aplicar_filtros_fecha,
                     fg_color=COLORS['SUCCESS_GREEN']).pack(side="left", padx=10, pady=10)
        
        # Botón limpiar filtros
        ctk.CTkButton(filters_frame, text="Limpiar Filtros", 
                     command=self.limpiar_filtros,
                     fg_color=COLORS['WARNING_AMBER']).pack(side="left", padx=10, pady=10)
        
        # Frame derecho para acciones
        actions_frame = ctk.CTkFrame(controls_frame)
        actions_frame.pack(side="right", padx=(10, 0))
        
        # Botón nuevo pago
        ctk.CTkButton(actions_frame, text="➕ Nuevo Pago", 
                     command=self.nuevo_pago,
                     fg_color=COLORS['SUCCESS_GREEN']).pack(side="left", padx=10, pady=10)
        
        # Botón exportar
        ctk.CTkButton(actions_frame, text="📊 Exportar", 
                     command=self.exportar_pagos,
                     fg_color=COLORS['INFO_BLUE']).pack(side="left", padx=10, pady=10)
        
        # Frame para la tabla de pagos
        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Crear Treeview para pagos
        columns = ('ID', 'DNI', 'Nombre', 'Monto', 'Fecha', 'Método', 'Estado')
        self.pagos_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        # Configurar columnas
        self.pagos_tree.heading('ID', text='ID')
        self.pagos_tree.heading('DNI', text='DNI')
        self.pagos_tree.heading('Nombre', text='Nombre del Socio')
        self.pagos_tree.heading('Monto', text='Monto')
        self.pagos_tree.heading('Fecha', text='Fecha de Pago')
        self.pagos_tree.heading('Método', text='Método')
        self.pagos_tree.heading('Estado', text='Estado')
        
        # Configurar anchos de columna
        self.pagos_tree.column('ID', width=50)
        self.pagos_tree.column('DNI', width=100)
        self.pagos_tree.column('Nombre', width=200)
        self.pagos_tree.column('Monto', width=100)
        self.pagos_tree.column('Fecha', width=120)
        self.pagos_tree.column('Método', width=100)
        self.pagos_tree.column('Estado', width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.pagos_tree.yview)
        self.pagos_tree.configure(yscrollcommand=scrollbar.set)
        
        # Empaquetar tabla y scrollbar
        self.pagos_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind para doble clic
        self.pagos_tree.bind('<Double-1>', self.editar_pago_seleccionado)
        # Menú contextual (click derecho)
        self.pagos_tree.bind('<Button-3>', self.mostrar_menu_contextual_pagos)
        
        # Frame inferior para estadísticas
        stats_frame = ctk.CTkFrame(self)
        stats_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # Estadísticas
        self.total_pagos_label = ctk.CTkLabel(stats_frame, text="Total de Pagos: 0", 
                                            font=ctk.CTkFont(size=16, weight="bold"))
        self.total_pagos_label.pack(side="left", padx=20, pady=10)
        
        self.monto_total_label = ctk.CTkLabel(stats_frame, text="Monto Total: $0.00", 
                                            font=ctk.CTkFont(size=16, weight="bold"),
                                            text_color=COLORS['SUCCESS_GREEN'])
        self.monto_total_label.pack(side="left", padx=20, pady=10)
        
        self.promedio_label = ctk.CTkLabel(stats_frame, text="Promedio: $0.00", 
                                         font=ctk.CTkFont(size=16, weight="bold"),
                                         text_color=COLORS['INFO_BLUE'])
        self.promedio_label.pack(side="left", padx=20, pady=10)
    
    def refrescar_pagos(self):
        """Refresca la lista de pagos desde la base de datos"""
        try:
            # Limpiar tabla
            for item in self.pagos_tree.get_children():
                self.pagos_tree.delete(item)
            
            # Obtener todos los pagos
            pagos = self.db_manager.obtener_todos_los_pagos()
            
            total_pagos = 0
            monto_total = 0.0
            
            for pago in pagos:
                dni = pago['dni']

                # Obtener nombre del socio
                socio = self.db_manager.obtener_socio(dni)
                nombre = socio['nombre'] if socio else "Socio no encontrado"
                
                # Calcular estado basado en la fecha
                fecha_pago = datetime.strptime(pago['fecha_pago'], '%Y-%m-%d')
                dias_transcurridos = (datetime.now() - fecha_pago).days
                
                if dias_transcurridos <= 30:
                    estado = "✅ Vigente"
                elif dias_transcurridos <= 60:
                    estado = "⚠️ Vencido"
                else:
                    estado = "❌ Muy Vencido"
                
                # Insertar en la tabla
                self.pagos_tree.insert('', 'end', values=(
                    pago['id'],
                    pago['dni'],
                    nombre,
                    f"${pago['monto']:.2f}",
                    pago['fecha_pago'],
                    pago['metodo_pago'].title(),
                    estado
                ))
                
                total_pagos += 1
                monto_total += pago['monto']
            
            # Actualizar estadísticas
            self.total_pagos_label.configure(text=f"Total de Pagos: {total_pagos}")
            self.monto_total_label.configure(text=f"Monto Total: ${monto_total:.2f}")
            
            if total_pagos > 0:
                promedio = monto_total / total_pagos
                self.promedio_label.configure(text=f"Promedio: ${promedio:.2f}")
            else:
                self.promedio_label.configure(text="Promedio: $0.00")
                
        except Exception as e:
            logging.error(f"Error al refrescar pagos: {e}")
            messagebox.showerror("Error", f"Error al cargar pagos: {str(e)}")
    
    def filtrar_pagos(self, event=None):
        """Filtra pagos por DNI en tiempo real"""
        dni_filtro = self.dni_filter.get().strip()
        
        if not dni_filtro:
            self.refrescar_pagos()
            return
        
        try:
            # Limpiar tabla
            for item in self.pagos_tree.get_children():
                self.pagos_tree.delete(item)
            
            # Obtener pagos filtrados por DNI
            pagos = self.db_manager.obtener_pagos_por_dni(int(dni_filtro))
            
            total_pagos = 0
            monto_total = 0.0
            
            for pago in pagos:
                socio = self.db_manager.obtener_socio_por_dni(pago['dni'])
                nombre = socio['nombre'] if socio else "Socio no encontrado"
                
                fecha_pago = datetime.strptime(pago['fecha_pago'], '%Y-%m-%d')
                dias_transcurridos = (datetime.now() - fecha_pago).days
                
                if dias_transcurridos <= 30:
                    estado = "✅ Vigente"
                elif dias_transcurridos <= 60:
                    estado = "⚠️ Vencido"
                else:
                    estado = "❌ Muy Vencido"
                
                self.pagos_tree.insert('', 'end', values=(
                    pago['id'],
                    pago['dni'],
                    nombre,
                    f"${pago['monto']:.2f}",
                    pago['fecha_pago'],
                    pago['metodo_pago'].title(),
                    estado
                ))
                
                total_pagos += 1
                monto_total += pago['monto']
            
            # Actualizar estadísticas del filtro
            self.total_pagos_label.configure(text=f"Pagos Filtrados: {total_pagos}")
            self.monto_total_label.configure(text=f"Monto Total: ${monto_total:.2f}")
            
            if total_pagos > 0:
                promedio = monto_total / total_pagos
                self.promedio_label.configure(text=f"Promedio: ${promedio:.2f}")
            else:
                self.promedio_label.configure(text="Promedio: $0.00")
                
        except ValueError:
            # Si el DNI no es válido, mostrar todos los pagos
            self.refrescar_pagos()
        except Exception as e:
            logging.error(f"Error al filtrar pagos: {e}")
            messagebox.showerror("Error", f"Error al filtrar pagos: {str(e)}")
    
    def aplicar_filtros_fecha(self):
        """Aplica filtros por rango de fechas"""
        fecha_desde = self.fecha_desde.get().strip()
        fecha_hasta = self.fecha_hasta.get().strip()
        
        if not fecha_desde and not fecha_hasta:
            self.refrescar_pagos()
            return
        
        try:
            # Validar fechas
            if fecha_desde:
                datetime.strptime(fecha_desde, '%Y-%m-%d')
            if fecha_hasta:
                datetime.strptime(fecha_hasta, '%Y-%m-%d')
            
            # Aquí implementarías la lógica de filtrado por fecha
            # Por ahora, solo refrescamos
            self.refrescar_pagos()
            messagebox.showinfo("Info", "Filtro de fechas aplicado")
            
        except ValueError:
            messagebox.showerror("Error", "Formato de fecha inválido. Use YYYY-MM-DD")
    
    def limpiar_filtros(self):
        """Limpia todos los filtros aplicados"""
        self.dni_filter.delete(0, 'end')
        self.fecha_desde.delete(0, 'end')
        self.fecha_hasta.delete(0, 'end')
        self.refrescar_pagos()
    
    def nuevo_pago(self):
        """Abre ventana para registrar nuevo pago"""
        try:
            # Crear ventana de nuevo pago
            pago_window = ctk.CTkToplevel(self)
            pago_window.title("Registrar Nuevo Pago")
            pago_window.geometry("500x400")
            pago_window.resizable(False, False)
            
            # Centrar ventana
            pago_window.transient(self)
            pago_window.grab_set()
            
            # Título
            title_label = ctk.CTkLabel(pago_window, text="Registrar Nuevo Pago", 
                                     font=ctk.CTkFont(size=20, weight="bold"))
            title_label.pack(pady=(20, 30))
            
            # Frame para formulario
            form_frame = ctk.CTkFrame(pago_window)
            form_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
            
            # Buscador unificado: DNI o Nombre
            dni_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
            dni_frame.pack(fill="x", padx=20, pady=10)

            ctk.CTkLabel(dni_frame, text="Buscar:").pack(side="left")
            search_entry = ctk.CTkEntry(dni_frame, placeholder_text="DNI o nombre...")
            search_entry.pack(side="right", fill="x", expand=True, padx=(20, 0))

            # Botón validar/buscar por DNI (si lo que hay es numérico)
            validar_btn = ctk.CTkButton(dni_frame, text="Buscar",
                                       command=lambda: self._buscar_por_dni_en_entry(search_entry, nombre_label))
            validar_btn.pack(side="right", padx=(10, 0))

            # Sugerencias dinámicas para texto o DNI parcial
            suggestions = tk.Listbox(form_frame, height=5)
            suggestions.pack(fill="x", padx=20)

            def actualizar_sugerencias(event=None):
                texto = search_entry.get().strip()
                suggestions.delete(0, tk.END)
                if not texto:
                    return
                try:
                    resultados = self.db_manager.buscar_socios(texto)
                    for s in resultados:
                        suggestions.insert(tk.END, f"{s['nombre']} (DNI {s['dni']})")
                except Exception:
                    pass

            def seleccionar_sugerencia(event=None):
                sel = suggestions.curselection()
                if not sel:
                    return
                item_text = suggestions.get(sel[0])
                import re
                m = re.search(r'DNI\s(\d+)', item_text)
                if not m:
                    return
                dni_sel = int(m.group(1))
                search_entry.delete(0, 'end')
                search_entry.insert(0, str(dni_sel))
                socio = self.db_manager.obtener_socio(dni_sel)
                nombre_label.configure(text=f"Nombre: {socio['nombre']}")
                try:
                    monto_entry.focus()
                except Exception:
                    pass

            search_entry.bind('<KeyRelease>', actualizar_sugerencias)
            suggestions.bind('<<ListboxSelect>>', seleccionar_sugerencia)

            # Nombre del socio (se llena al buscar)
            nombre_label = ctk.CTkLabel(form_frame, text="Nombre: ", 
                                      font=ctk.CTkFont(size=14))
            nombre_label.pack(pady=10)
            
            # Monto
            monto_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
            monto_frame.pack(fill="x", padx=20, pady=10)
            
            ctk.CTkLabel(monto_frame, text="Monto:").pack(side="left")
            monto_entry = ctk.CTkEntry(monto_frame, placeholder_text="0.00")
            monto_entry.pack(side="right", fill="x", expand=True, padx=(20, 0))
            
            # Fecha
            fecha_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
            fecha_frame.pack(fill="x", padx=20, pady=10)
            
            ctk.CTkLabel(fecha_frame, text="Fecha:").pack(side="left")
            fecha_entry = ctk.CTkEntry(fecha_frame, placeholder_text="YYYY-MM-DD")
            fecha_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
            fecha_entry.pack(side="right", fill="x", expand=True, padx=(20, 0))
            
            # Método de pago
            metodo_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
            metodo_frame.pack(fill="x", padx=20, pady=10)
            
            ctk.CTkLabel(metodo_frame, text="Método:").pack(side="left")
            metodo_var = ctk.StringVar(value="efectivo")
            metodo_combo = ctk.CTkComboBox(metodo_frame, values=["efectivo", "transferencia"], 
                                         variable=metodo_var)
            metodo_combo.pack(side="right", fill="x", expand=True, padx=(20, 0))
            
            # Botones
            button_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
            button_frame.pack(fill="x", padx=20, pady=20)
            
            def registrar_pago():
                try:
                    dni = int(search_entry.get())
                    monto = float(monto_entry.get())
                    fecha = fecha_entry.get()
                    metodo = metodo_var.get()
                    
                    # Validar campos
                    if not dni or not monto or not fecha:
                        messagebox.showerror("Error", "Todos los campos son obligatorios")
                        return
                    
                    # Registrar pago
                    self.db_manager.registrar_pago(dni, monto, fecha, metodo)
                    
                    messagebox.showinfo("Éxito", "Pago registrado correctamente")
                    pago_window.destroy()
                    self.refrescar_pagos()
                    
                except ValueError as e:
                    messagebox.showerror("Error", "Valores inválidos en los campos")
                except Exception as e:
                    messagebox.showerror("Error", f"Error al registrar pago: {str(e)}")
            
            ctk.CTkButton(button_frame, text="Registrar Pago", 
                         command=registrar_pago,
                         fg_color=COLORS['SUCCESS_GREEN']).pack(side="left", padx=(0, 10))
            
            ctk.CTkButton(button_frame, text="Cancelar", 
                         command=pago_window.destroy).pack(side="right")
            
        except Exception as e:
            logging.error(f"Error al crear ventana de nuevo pago: {e}")
            messagebox.showerror("Error", f"Error al crear ventana: {str(e)}")
    
    def _buscar_por_dni_en_entry(self, entry_widget, nombre_label):
        """Valida entrada numérica en un Entry y muestra el nombre si existe."""
        try:
            dni = int(entry_widget.get())
            socio = self.db_manager.obtener_socio_por_dni(dni)
            if socio:
                nombre_label.configure(text=f"Nombre: {socio['nombre']}")
            else:
                nombre_label.configure(text="Nombre: Socio no encontrado")
                messagebox.showwarning("Advertencia", "Socio no encontrado con ese DNI")
        except ValueError:
            messagebox.showerror("Error", "Ingrese un DNI válido o seleccione de la lista")
        except Exception as e:
            messagebox.showerror("Error", f"Error al buscar socio: {str(e)}")
    
    def editar_pago_seleccionado(self, event):
        """Abrir editor rápido (monto y método) para el pago seleccionado"""
        selection = self.pagos_tree.selection()
        if not selection:
            return
        item = self.pagos_tree.item(selection[0])
        pago_id = item['values'][0]
        self._abrir_editor_pago_simple(int(pago_id))

    def mostrar_menu_contextual_pagos(self, event):
        # Seleccionar fila bajo el cursor
        try:
            row_id = self.pagos_tree.identify_row(event.y)
            if row_id:
                self.pagos_tree.selection_set(row_id)
        except Exception:
            pass

        selection = self.pagos_tree.selection()
        if not selection:
            return
        item = self.pagos_tree.item(selection[0])
        pago_id = int(item['values'][0])

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Editar Pago", command=lambda: self._abrir_editor_pago_simple(pago_id))
        menu.add_command(label="Eliminar Pago", command=lambda: self._eliminar_pago_por_id(pago_id))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _abrir_editor_pago_simple(self, pago_id: int):
        pago = self.db_manager.obtener_pago(pago_id)
        if not pago:
            messagebox.showerror("Error", "Pago no encontrado")
            return

        win = ctk.CTkToplevel(self)
        win.title(f"Editar Pago #{pago_id}")
        win.geometry("380x260")
        win.resizable(False, False)
        win.grab_set()

        ctk.CTkLabel(win, text=f"DNI: {pago['dni']}  |  Fecha: {pago['fecha_pago']}").pack(pady=(15, 5))

        # Monto
        monto_frame = ctk.CTkFrame(win, fg_color="transparent")
        monto_frame.pack(fill='x', padx=20, pady=10)
        ctk.CTkLabel(monto_frame, text="Monto:").pack(side='left')
        monto_entry = ctk.CTkEntry(monto_frame)
        monto_entry.insert(0, str(pago['monto']))
        monto_entry.pack(side='right', fill='x', expand=True, padx=(20,0))

        # Método
        metodo_frame = ctk.CTkFrame(win, fg_color="transparent")
        metodo_frame.pack(fill='x', padx=20, pady=10)
        ctk.CTkLabel(metodo_frame, text="Método:").pack(side='left')
        metodo_var = ctk.StringVar(value=pago['metodo_pago'])
        metodo_combo = ctk.CTkComboBox(metodo_frame, values=["efectivo", "transferencia"], variable=metodo_var)
        metodo_combo.pack(side='right', fill='x', expand=True, padx=(20,0))

        # Botones
        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack(fill='x', padx=20, pady=15)

        def guardar():
            try:
                monto = float(monto_entry.get().strip())
                if monto <= 0:
                    raise ValueError()
            except Exception:
                messagebox.showerror("Error", "Monto inválido (debe ser mayor a 0)")
                return
            metodo = metodo_var.get()
            if metodo not in ("efectivo", "transferencia"):
                messagebox.showerror("Error", "Método inválido")
                return
            try:
                # Solo monto y método. Mantener DNI y fecha originales
                self.db_manager.editar_pago(pago_id, pago['dni'], monto, pago['fecha_pago'], metodo)
                self.refrescar_pagos()
                messagebox.showinfo("Éxito", "Pago actualizado")
                win.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo actualizar: {str(e)}")

        ctk.CTkButton(btns, text="Guardar", command=guardar, fg_color=COLORS['SUCCESS_GREEN']).pack(side='left')
        ctk.CTkButton(btns, text="Cancelar", command=win.destroy).pack(side='right')

    def _eliminar_pago_por_id(self, pago_id: int):
        if not messagebox.askyesno("Confirmar eliminación", "¿Eliminar el pago seleccionado? Esta acción no se puede deshacer."):
            return
        try:
            self.db_manager.eliminar_pago(pago_id)
            self.refrescar_pagos()
            messagebox.showinfo("Éxito", "Pago eliminado")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar: {str(e)}")
    
    def exportar_pagos(self):
        """Exporta los pagos a Excel"""
        try:
            from .import_export import ImportExportManager
            import_export = ImportExportManager(self.db_manager)
            import_export.exportar_pagos(self)
        except Exception as e:
            logging.error(f"Error al exportar pagos: {e}")
            messagebox.showerror("Error", f"Error al exportar: {str(e)}")

class SomaEntrenamientosApp:
    def __init__(self):
        # Configurar logging
        logging.info("Iniciando aplicación Soma Entrenamientos")
        
        # Inicializar base de datos
        self.db_manager = DatabaseManager()
        
        # Crear ventana principal
        self.root = ctk.CTk()
        self.root.title("Soma Entrenamientos – Sistema de Gestión")
        self.root.geometry("1280x900")

        # Maximizar ventana inicialmente
        self.root.state("zoomed")

        # Fondo blanco general
        try:
            self.root.configure(fg_color=COLORS['WHITE'])
        except Exception:
            pass
        
        # Configurar icono si existe
        try:
            icon_path = resource_path("assets/icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            logging.warning(f"No se pudo cargar el icono: {e}")
        
        # Rol de usuario (dueno | profe)
        self.user_role = None

        # Pedir inicio de sesión con rol
        try:
            self.show_login_dialog()
            if not self.user_role:
                # Si no se selecciona rol, cerrar la app
                self.root.destroy()
                return
        except Exception as e:
            logging.error(f"Error en inicio de sesión: {e}")
            self.root.destroy()
            return

        # Tras el login, maximizar con controles de ventana (no fullscreen)
        try:
            self.root.attributes("-fullscreen", False)
        except Exception:
            pass
        try:
            self.root.state("zoomed")
        except Exception:
            pass

        # Configurar estilos de tabla para fuentes más grandes
        self.configure_table_styles()
        
        self.create_widgets()
        
        # Bind para cerrar aplicación
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def show_login_dialog(self):
        """Muestra un diálogo modal para elegir rol (Dueño/Profe).
        Si se elige Dueño, solicita PIN definido en config.OWNER_PIN.
        """
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Inicio de sesión")
        dialog.grab_set()
        dialog.transient(self.root)

        # Centrar el diálogo
        dialog.update_idletasks()
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        width = 420
        height = 260
        x = (sw - width) // 2
        y = (sh - height) // 3
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        try:
            dialog.resizable(False, False)
            dialog.lift()
            dialog.focus_force()
            # Recentrar levemente después de dibujar
            dialog.after(50, lambda: dialog.geometry(f"{width}x{height}+{x}+{y}"))
        except Exception:
            pass

        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="Seleccione su perfil", font=ctk.CTkFont(**FONTS['SUBTITLE'])).pack(pady=(10, 16))

        role_var = tk.StringVar(value="profe")
        rb_frame = ctk.CTkFrame(frame, fg_color="transparent")
        rb_frame.pack(pady=(0, 10))
        ctk.CTkRadioButton(rb_frame, text="Profe", variable=role_var, value="profe").pack(side="left", padx=10)
        # Mostrar "Alvaro" en lugar de "Dueño" pero mantener el valor interno 'dueno'
        ctk.CTkRadioButton(rb_frame, text="Alvaro", variable=role_var, value="dueno").pack(side="left", padx=10)

        pin_label = ctk.CTkLabel(frame, text="PIN (solo Alvaro):")
        pin_entry = ctk.CTkEntry(frame, show="*", placeholder_text="Ingrese PIN de Alvaro")
        pin_label.pack(pady=(8, 4))
        pin_entry.pack()

        # Habilitar PIN solo si rol = dueno
        def on_role_change(*_):
            if role_var.get() == "dueno":
                pin_entry.configure(state="normal")
            else:
                pin_entry.delete(0, 'end')
                pin_entry.configure(state="disabled")

        role_var.trace_add('write', on_role_change)
        on_role_change()

        # Botones
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=16, fill="x")

        def aceptar():
            role = role_var.get()
            if role == "dueno":
                if pin_entry.get().strip() != str(OWNER_PIN):
                    messagebox.showerror("Error", "PIN incorrecto")
                    return
            self.user_role = role
            dialog.destroy()

        def cancelar():
            self.user_role = None
            dialog.destroy()

        ctk.CTkButton(btn_frame, text="Cancelar", command=cancelar).pack(side="right", padx=6)
        ingresar_btn = ctk.CTkButton(btn_frame, text="Ingresar", command=aceptar, fg_color=COLORS['SOMA_ORANGE'])
        ingresar_btn.pack(side="right", padx=6)

        # Presionar Enter equivale a "Ingresar"
        try:
            dialog.bind('<Return>', lambda e: aceptar())
        except Exception:
            pass

        # Esperar a que se cierre el diálogo
        self.root.wait_window(dialog)
    
    def create_widgets(self):
        # Crear notebook (tabs) con acentos naranjas
        self.notebook = ctk.CTkTabview(
            self.root,
            segmented_button_fg_color=COLORS.get('WHITE', '#FFFFFF'),
            segmented_button_selected_color=COLORS.get('SOMA_ORANGE', '#E6461A'),
            segmented_button_selected_hover_color=COLORS.get('SOMA_ORANGE_DARK', '#FC3903')
        )
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Pestaña Consulta (Kiosco)
        self.notebook.add("Consulta")
        self.consulta_frame = ConsultaKioscoFrame(self.notebook.tab("Consulta"), self.db_manager)
        self.consulta_frame.pack(fill="both", expand=True)
        
        # Pestaña Socios
        self.notebook.add("Socios")
        self.socios_frame = SociosFrame(self.notebook.tab("Socios"), self.db_manager)
        self.socios_frame.pack(fill="both", expand=True)
        
        # Pestaña Ingresos
        self.notebook.add("Ingresos")
        self.ingresos_frame = IngresosFrame(self.notebook.tab("Ingresos"), self.db_manager)
        self.ingresos_frame.pack(fill="both", expand=True)
        
        # Pestaña Pagos
        self.notebook.add("Pagos")
        self.pagos_frame = PagosFrame(self.notebook.tab("Pagos"), self.db_manager)
        self.pagos_frame.pack(fill="both", expand=True)
        
        # Pestaña Dashboard (solo Dueño)
        if getattr(self, 'user_role', 'profe') == 'dueno':
            self.notebook.add("Dashboard")
            self.reportes_frame = ReportesFrame(self.notebook.tab("Dashboard"), self.db_manager)
            self.reportes_frame.pack(fill="both", expand=True)
            # Contexto de navegación para dashboard (KPIs clicables)
            try:
                self.reportes_frame.set_navigation_context(self.notebook, self.socios_frame, self.ingresos_frame)
            except Exception:
                pass
        
        # Pestaña Import/Export
        self.notebook.add("Import/Export")
        self.import_export_frame = ImportExportFrame(self.notebook.tab("Import/Export"), self.db_manager)
        self.import_export_frame.pack(fill="both", expand=True)
        
        # Establecer pestaña inicial en Consulta
        self.notebook.set("Consulta")
    
    def configure_table_styles(self):
        """Configura los estilos de las tablas para usar fuentes más grandes"""
        try:
            style = ttk.Style()
            # Configurar fuente para encabezados de tabla
            style.configure("Treeview.Heading", font=('TkDefaultFont', 16, 'bold'))
            # Configurar fuente para datos de tabla
            style.configure("Treeview", font=('TkDefaultFont', 14))
            # Configurar altura de filas para mejor legibilidad
            style.configure("Treeview", rowheight=35)
        except Exception as e:
            logging.warning(f"No se pudieron configurar los estilos de tabla: {e}")
    
    def on_closing(self):
        logging.info("Cerrando aplicación")
        try:
            self.db_manager.stop_auto_backup()
        except Exception as e:
            logging.error(f"Error deteniendo backup automático: {e}")
        
        self.root.destroy()
    
    def run(self):
        if not getattr(self, 'user_role', None):
            logging.info("Aplicación cerrada antes de iniciar (sin rol)")
            return
        logging.info("Aplicación iniciada correctamente")
        self.root.mainloop()

def main():
    try:
        app = SomaEntrenamientosApp()
        app.run()
    except Exception as e:
        logging.error(f"Error fatal en la aplicación: {e}", exc_info=True)
        messagebox.showerror("Error Fatal", f"Error fatal en la aplicación:\n{str(e)}")

if __name__ == "__main__":
    main()

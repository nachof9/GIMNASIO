import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import logging
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import os
import sys
from PIL import Image
from functools import lru_cache
import threading
from typing import Optional, Dict, Any, List

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

try:
    from .config import get_log_filename, ensure_directories, resource_path, COLORS, POPUP_AUTOCLOSE_SECONDS, SOUNDS, ALERT_CONFIG, FONTS
    from .db import DatabaseManager
    from .admin_windows import AltaSocioWindow, EditarSocioWindow, RegistrarPagoWindow
    from .import_export import ImportExportManager
    from .dashboard_manager import DashboardManager
except ImportError:
    # Fallback para ejecución directa
    from config import get_log_filename, ensure_directories, resource_path, COLORS, POPUP_AUTOCLOSE_SECONDS, SOUNDS, ALERT_CONFIG, FONTS
    from db import DatabaseManager
    from admin_windows import AltaSocioWindow, EditarSocioWindow, RegistrarPagoWindow
    from import_export import ImportExportManager
    from dashboard_manager import DashboardManager

ensure_directories()
logging.basicConfig(
    filename=get_log_filename(),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

try:
    import winsound
    SOUND_AVAILABLE = True
except ImportError:
    SOUND_AVAILABLE = False
    logging.warning("winsound no disponible - sonidos deshabilitados")

_image_cache: Dict[str, Any] = {}

@lru_cache(maxsize=32)
def get_resource_path(relative_path: str) -> str:
    """Obtiene la ruta absoluta del recurso, funciona para dev y para PyInstaller"""
    try:
        # PyInstaller crea una carpeta temporal y almacena la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_custom_image(filename: str, size: tuple = (100, 100)) -> Optional[ctk.CTkImage]:
    """Carga una imagen personalizada desde la carpeta assets con cache"""
    cache_key = f"{filename}_{size[0]}x{size[1]}"
    
    if cache_key in _image_cache:
        return _image_cache[cache_key]
    
    try:
        image_path = get_resource_path(f"assets/{filename}")
        if os.path.exists(image_path):
            pil_image = Image.open(image_path)
            ctk_image = ctk.CTkImage(light_image=pil_image, size=size)
            _image_cache[cache_key] = ctk_image
            return ctk_image
    except Exception as e:
        logging.warning(f"No se pudo cargar la imagen {filename}: {e}")
    
    _image_cache[cache_key] = None
    return None

class ConsultaKioscoFrame(ctk.CTkFrame):
    def __init__(self, parent, db_manager: DatabaseManager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.popup_window: Optional[tk.Toplevel] = None
        self.after_id: Optional[str] = None
        self._last_query_time = 0
        self._query_cache: Dict[str, Any] = {}
        
        self.create_widgets()
    
    def create_widgets(self):
        self._create_logo()
        
        # Título
        title_label = ctk.CTkLabel(
            self, 
            text="Consulta de Estado de Cuota", 
            font=ctk.CTkFont(**FONTS['HEADER'])
        )
        title_label.pack(pady=(0, 30))
        
        # Frame para entrada DNI
        self._create_dni_input()
        
        # Botón de consulta
        self._create_consultation_button()
        
        # Instrucciones
        self._create_instructions()
    
    def _create_logo(self):
        """Crea el logo de manera optimizada"""
        try:
            logo_path = get_resource_path("assets/logo_soma.png")
            if os.path.exists(logo_path):
                logo_image = load_custom_image("logo_soma.png", (200, 100))
                if logo_image:
                    logo_label = ctk.CTkLabel(self, image=logo_image, text="")
                    logo_label.pack(pady=(50, 30))
                    return
        except Exception as e:
            logging.warning(f"No se pudo cargar el logo: {e}")
        
        # Logo de texto como fallback
        logo_label = ctk.CTkLabel(
            self, 
            text="SOMA ENTRENAMIENTOS", 
            font=ctk.CTkFont(**FONTS['TITLE_MEDIUM']),
            text_color=COLORS['SOMA_ORANGE']
        )
        logo_label.pack(pady=(50, 30))
    
    def _create_dni_input(self):
        """Crea el campo de entrada DNI"""
        dni_frame = ctk.CTkFrame(self, fg_color="transparent")
        dni_frame.pack(pady=20)
        
        dni_label = ctk.CTkLabel(
            dni_frame, 
            text="Ingrese su DNI:", 
            font=ctk.CTkFont(**FONTS['BODY_LARGE'])
        )
        dni_label.pack(pady=(0, 10))
        
        self.dni_entry = ctk.CTkEntry(
            dni_frame,
            placeholder_text="Ej: 12345678",
            font=ctk.CTkFont(size=18),
            width=200,
            height=40,
            justify="center"
        )
        self.dni_entry.pack(pady=10)
        
        self.dni_entry.bind('<Return>', lambda e: self.consultar_estado())
        self.dni_entry.bind('<KeyRelease>', self._validate_dni_input)
    
    def _create_consultation_button(self):
        """Crea el botón de consulta"""
        self.consultar_btn = ctk.CTkButton(
            self,
            text="CONSULTAR ESTADO",
            command=self.consultar_estado,
            font=ctk.CTkFont(**FONTS['BUTTON']),
            width=250,
            height=50,
            fg_color=COLORS['SOMA_ORANGE'],
            hover_color=COLORS['SOMA_ORANGE_DARK']
        )
        self.consultar_btn.pack(pady=30)
    
    def _create_instructions(self):
        """Crea las instrucciones"""
        instrucciones_frame = ctk.CTkFrame(self, fg_color="transparent")
        instrucciones_frame.pack(pady=20, padx=40, fill="x")
        
        instrucciones_text = (
            "• Ingrese su número de DNI sin puntos ni espacios\n"
            "• Presione ENTER o haga clic en CONSULTAR ESTADO\n"
            "• El sistema mostrará el estado actual de su cuota"
        )
        
        instrucciones_label = ctk.CTkLabel(
            instrucciones_frame,
            text=instrucciones_text,
            font=ctk.CTkFont(**FONTS['BODY_SMALL']),
            text_color=COLORS['TEXT_SECONDARY'],
            justify="left"
        )
        instrucciones_label.pack()
    
    def _validate_dni_input(self, event=None):
        """Valida la entrada del DNI en tiempo real"""
        current_text = self.dni_entry.get()
        filtered_text = ''.join(filter(str.isdigit, current_text))
        
        if filtered_text != current_text:
            self.dni_entry.delete(0, tk.END)
            self.dni_entry.insert(0, filtered_text)
        
        if len(filtered_text) > 8:
            self.dni_entry.delete(8, tk.END)
    
    def consultar_estado(self):
        """Consulta el estado de la cuota con optimizaciones"""
        dni_text = self.dni_entry.get().strip()
        
        if not self._validate_dni(dni_text):
            return
        
        current_time = datetime.now().timestamp()
        cache_key = f"consulta_{dni_text}"
        
        if (cache_key in self._query_cache and 
            current_time - self._query_cache[cache_key]['timestamp'] < 30):  # Cache por 30 segundos
            resultado = self._query_cache[cache_key]['data']
        else:
            try:
                dni = int(dni_text)
                resultado = self.db_manager.obtener_estado_socio(dni)
                
                self._query_cache[cache_key] = {
                    'data': resultado,
                    'timestamp': current_time
                }
                
            except ValueError:
                self._show_error("DNI inválido", "Por favor ingrese un DNI válido (solo números)")
                return
            except Exception as e:
                logging.error(f"Error en consulta de estado: {e}")
                self._show_error("Error de consulta", "Error al consultar el estado. Intente nuevamente.")
                return
        
        self._mostrar_resultado(resultado, dni_text)
    
    def _validate_dni(self, dni_text: str) -> bool:
        """Valida el formato del DNI"""
        if not dni_text:
            self._show_error("DNI requerido", "Por favor ingrese su número de DNI")
            return False
        
        if not dni_text.isdigit():
            self._show_error("DNI inválido", "El DNI debe contener solo números")
            return False
        
        if len(dni_text) < 7 or len(dni_text) > 8:
            self._show_error("DNI inválido", "El DNI debe tener entre 7 y 8 dígitos")
            return False
        
        return True
    
    def _show_error(self, title: str, message: str):
        """Muestra un mensaje de error de manera consistente"""
        messagebox.showerror(title, message)
        self.dni_entry.focus_set()
    
    def _mostrar_resultado(self, resultado: Dict[str, Any], dni: str):
        """Muestra el resultado de la consulta de manera optimizada"""
        if self.popup_window and self.popup_window.winfo_exists():
            self.popup_window.destroy()
        
        self.popup_window = tk.Toplevel(self)
        self.popup_window.title("Estado de Cuota")
        self.popup_window.geometry("500x400")
        self.popup_window.resizable(False, False)
        self.popup_window.transient(self.master)
        self.popup_window.grab_set()
        
        # Centrar ventana
        self._center_popup()
        
        self._create_popup_content(resultado, dni)
        
        if POPUP_AUTOCLOSE_SECONDS > 0:
            self.after_id = self.after(
                POPUP_AUTOCLOSE_SECONDS * 1000, 
                self._auto_close_popup
            )
    
    def _center_popup(self):
        """Centra la ventana popup"""
        self.popup_window.update_idletasks()
        x = (self.popup_window.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.popup_window.winfo_screenheight() // 2) - (400 // 2)
        self.popup_window.geometry(f"500x400+{x}+{y}")
    
    def _create_popup_content(self, resultado: Dict[str, Any], dni: str):
        """Crea el contenido del popup de manera optimizada"""
        main_frame = ctk.CTkFrame(self.popup_window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        if not resultado:
            self._create_not_found_content(main_frame, dni)
        else:
            self._create_found_content(main_frame, resultado)
        
        # Botón cerrar
        close_btn = ctk.CTkButton(
            main_frame,
            text="CERRAR",
            command=self._close_popup,
            font=ctk.CTkFont(size=14, weight="bold"),
            width=120,
            height=35
        )
        close_btn.pack(pady=(20, 0))
    
    def _create_not_found_content(self, parent, dni: str):
        """Crea contenido para socio no encontrado"""
        # Icono de error
        error_label = ctk.CTkLabel(
            parent,
            text="❌",
            font=ctk.CTkFont(size=48)
        )
        error_label.pack(pady=(20, 10))
        
        # Título
        title_label = ctk.CTkLabel(
            parent,
            text="Socio No Encontrado",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLORS['ERROR_RED']
        )
        title_label.pack(pady=(0, 20))
        
        # Mensaje
        message_label = ctk.CTkLabel(
            parent,
            text=f"No se encontró ningún socio con DNI: {dni}",
            font=ctk.CTkFont(size=16),
            wraplength=400
        )
        message_label.pack(pady=(0, 10))
        
        # Instrucciones
        instructions_label = ctk.CTkLabel(
            parent,
            text="Por favor verifique el número ingresado o\nconsulte en recepción para más información.",
            font=ctk.CTkFont(size=14),
            text_color=COLORS['TEXT_SECONDARY'],
            wraplength=400
        )
        instructions_label.pack(pady=(10, 0))
    
    def _create_found_content(self, parent, resultado: Dict[str, Any]):
        """Crea contenido para socio encontrado"""
        estado_info = self._calculate_status(resultado)
        
        # Icono de estado
        status_label = ctk.CTkLabel(
            parent,
            text=estado_info['icon'],
            font=ctk.CTkFont(size=48)
        )
        status_label.pack(pady=(20, 10))
        
        # Nombre del socio
        name_label = ctk.CTkLabel(
            parent,
            text=f"¡Hola, {resultado['nombre']}!",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        name_label.pack(pady=(0, 20))
        
        # Estado de la cuota
        status_frame = ctk.CTkFrame(parent, fg_color=estado_info['bg_color'])
        status_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        status_text_label = ctk.CTkLabel(
            status_frame,
            text=estado_info['message'],
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=estado_info['text_color']
        )
        status_text_label.pack(pady=15)
        
        # Información adicional
        self._create_additional_info(parent, resultado, estado_info)
        
        self._play_status_sound(estado_info['status'])
    
    def _calculate_status(self, resultado: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula el estado del socio de manera optimizada"""
        if not resultado.get('ultimo_pago'):
            return {
                'status': 'sin_pagos',
                'icon': '❌',
                'message': 'Sin pagos registrados',
                'bg_color': COLORS['ERROR_RED'],
                'text_color': 'white',
                'days': None
            }
        
        try:
            fecha_pago = datetime.strptime(resultado['ultimo_pago'], '%Y-%m-%d')
            dias_transcurridos = (datetime.now() - fecha_pago).days
            
            if dias_transcurridos <= 30:
                return {
                    'status': 'vigente',
                    'icon': '✅',
                    'message': 'Cuota al día',
                    'bg_color': COLORS['SUCCESS_GREEN'],
                    'text_color': 'white',
                    'days': dias_transcurridos
                }
            elif dias_transcurridos <= 60:
                return {
                    'status': 'vencido',
                    'icon': '⚠️',
                    'message': 'Cuota vencida',
                    'bg_color': COLORS['WARNING_YELLOW'],
                    'text_color': 'black',
                    'days': dias_transcurridos
                }
            else:
                return {
                    'status': 'muy_vencido',
                    'icon': '❌',
                    'message': 'Cuota muy vencida',
                    'bg_color': COLORS['ERROR_RED'],
                    'text_color': 'white',
                    'days': dias_transcurridos
                }
        except (ValueError, TypeError) as e:
            logging.error(f"Error al calcular estado: {e}")
            return {
                'status': 'error',
                'icon': '❓',
                'message': 'Error al calcular estado',
                'bg_color': COLORS['ERROR_RED'],
                'text_color': 'white',
                'days': None
            }
    
    def _create_additional_info(self, parent, resultado: Dict[str, Any], estado_info: Dict[str, Any]):
        """Crea información adicional del socio"""
        info_frame = ctk.CTkFrame(parent, fg_color="transparent")
        info_frame.pack(fill="x", padx=20)
        
        # Último pago
        if resultado.get('ultimo_pago'):
            ultimo_pago_label = ctk.CTkLabel(
                info_frame,
                text=f"Último pago: {resultado['ultimo_pago']}",
                font=ctk.CTkFont(size=14)
            )
            ultimo_pago_label.pack(pady=2)
            
            # Días transcurridos
            if estado_info['days'] is not None:
                dias_label = ctk.CTkLabel(
                    info_frame,
                    text=f"Días transcurridos: {estado_info['days']}",
                    font=ctk.CTkFont(size=14)
                )
                dias_label.pack(pady=2)
        
        # Monto del último pago
        if resultado.get('monto_ultimo_pago'):
            monto_label = ctk.CTkLabel(
                info_frame,
                text=f"Monto: ${resultado['monto_ultimo_pago']:.2f}",
                font=ctk.CTkFont(size=14)
            )
            monto_label.pack(pady=2)
    
    def _play_status_sound(self, status: str):
        """Reproduce sonido según el estado"""
        if not SOUND_AVAILABLE:
            return
        
        try:
            sound_map = {
                'vigente': SOUNDS.get('SUCCESS'),
                'vencido': SOUNDS.get('WARNING'),
                'muy_vencido': SOUNDS.get('ERROR'),
                'sin_pagos': SOUNDS.get('ERROR')
            }
            
            sound_file = sound_map.get(status)
            if sound_file and os.path.exists(sound_file):
                threading.Thread(
                    target=lambda: winsound.PlaySound(sound_file, winsound.SND_FILENAME),
                    daemon=True
                ).start()
        except Exception as e:
            logging.warning(f"Error al reproducir sonido: {e}")
    
    def _auto_close_popup(self):
        """Cierra automáticamente el popup"""
        if self.popup_window and self.popup_window.winfo_exists():
            self.popup_window.destroy()
        self.after_id = None
    
    def _close_popup(self):
        """Cierra el popup manualmente"""
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        
        if self.popup_window and self.popup_window.winfo_exists():
            self.popup_window.destroy()
        
        self.dni_entry.delete(0, tk.END)
        self.dni_entry.focus_set()

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
                tree.insert("", "end", values=(
                    pago['fecha_pago'],
                    f"${pago['monto']:.2f}",
                    pago['metodo_pago'].title()
                ))
            
            tree.pack(fill="both", expand=True, padx=20, pady=10)
            
            # Botón cerrar
            ctk.CTkButton(historial_window, text="Cerrar", 
                         command=historial_window.destroy).pack(pady=10)
        
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
        
        refresh_btn = ctk.CTkButton(control_frame, text="Actualizar", 
                                  command=self.actualizar_dashboard)
        refresh_btn.pack(side="right", padx=10, pady=10)
        
        self.create_alerts_frame()
        
        # Frame de KPIs
        self.create_kpis_frame()
        
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
        empty_card = ctk.CTkFrame(row2, fg_color="transparent")
        empty_card.pack(side="left", padx=5, fill="x", expand=True)
    
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
            self.dashboard_data = self.dashboard_manager.get_dashboard_data()
            
            # Actualizar KPIs
            self.actualizar_kpis()
            
            # Actualizar alertas
            self.actualizar_alertas()
            
            # Actualizar acciones rápidas
            self.actualizar_acciones_rapidas()
            
            # Actualizar actividad reciente
            self.actualizar_actividad_reciente()
            
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
    def __init__(self, parent, db_manager: DatabaseManager):
        super().__init__(parent)
        self.db_manager = db_manager
        self._last_refresh = 0
        self._refresh_cache: Optional[List[Dict[str, Any]]] = None
        
        self.create_widgets()
        self.refrescar_pagos()
    
    def create_widgets(self):
        # Título
        title_label = ctk.CTkLabel(
            self, 
            text="Gestión de Pagos", 
            font=ctk.CTkFont(**FONTS['HEADER'])
        )
        title_label.pack(pady=(20, 30))
        
        self._create_filter_frame()
        
        self._create_table_frame()
        
        self._create_stats_frame()
    
    def _create_filter_frame(self):
        """Crea el frame de filtros de manera optimizada"""
        filter_frame = ctk.CTkFrame(self)
        filter_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # Filtro por DNI
        dni_filter_frame = ctk.CTkFrame(filter_frame, fg_color="transparent")
        dni_filter_frame.pack(side="left", padx=10, pady=10)
        
        ctk.CTkLabel(
            dni_filter_frame, 
            text="Filtrar por DNI:",
            font=ctk.CTkFont(size=14)
        ).pack(side="left", padx=(0, 10))
        
        self.dni_filter = ctk.CTkEntry(
            dni_filter_frame,
            placeholder_text="Ingrese DNI",
            width=150
        )
        self.dni_filter.pack(side="left")
        
        self.dni_filter.bind('<KeyRelease>', self._debounced_filter)
        
        # Botón refrescar
        refresh_btn = ctk.CTkButton(
            filter_frame,
            text="🔄 Refrescar",
            command=self.refrescar_pagos,
            width=100,
            height=32
        )
        refresh_btn.pack(side="right", padx=10, pady=10)
    
    def _create_table_frame(self):
        """Crea el frame de la tabla de manera optimizada"""
        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        columns = ('ID', 'DNI', 'Nombre', 'Monto', 'Fecha', 'Método', 'Estado')
        self.pagos_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        # Configurar columnas de manera optimizada
        column_configs = {
            'ID': {'width': 60, 'anchor': 'center'},
            'DNI': {'width': 100, 'anchor': 'center'},
            'Nombre': {'width': 200, 'anchor': 'w'},
            'Monto': {'width': 100, 'anchor': 'e'},
            'Fecha': {'width': 120, 'anchor': 'center'},
            'Método': {'width': 100, 'anchor': 'center'},
            'Estado': {'width': 120, 'anchor': 'center'}
        }
        
        for col, config in column_configs.items():
            self.pagos_tree.heading(col, text=col)
            self.pagos_tree.column(col, **config)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.pagos_tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.pagos_tree.xview)
        
        self.pagos_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack elementos
        self.pagos_tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
    
    def _create_stats_frame(self):
        """Crea el frame de estadísticas"""
        stats_frame = ctk.CTkFrame(self)
        stats_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.total_pagos_label = ctk.CTkLabel(
            stats_frame, 
            text="Total de Pagos: 0", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.total_pagos_label.pack(side="left", padx=20, pady=10)
        
        self.monto_total_label = ctk.CTkLabel(
            stats_frame, 
            text="Monto Total: $0.00", 
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS['SUCCESS_GREEN']
        )
        self.monto_total_label.pack(side="left", padx=20, pady=10)
        
        self.promedio_label = ctk.CTkLabel(
            stats_frame, 
            text="Promedio: $0.00", 
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS['INFO_BLUE']
        )
        self.promedio_label.pack(side="left", padx=20, pady=10)
    
    def refrescar_pagos(self):
        """Refresca la lista de pagos desde la base de datos con cache"""
        current_time = datetime.now().timestamp()
        
        if (self._refresh_cache is not None and 
            current_time - self._last_refresh < 30):
            pagos = self._refresh_cache
        else:
            try:
                pagos = self.db_manager.obtener_todos_los_pagos()
                self._refresh_cache = pagos
                self._last_refresh = current_time
            except Exception as e:
                logging.error(f"Error al obtener pagos: {e}")
                messagebox.showerror("Error", f"Error al cargar pagos: {str(e)}")
                return
        
        self._populate_table(pagos)
    
    def _populate_table(self, pagos: List[Dict[str, Any]]):
        """Puebla la tabla con los datos de pagos de manera optimizada"""
        self.pagos_tree.delete(*self.pagos_tree.get_children())
        
        total_pagos = 0
        monto_total = 0.0
        
        batch_size = 100
        for i in range(0, len(pagos), batch_size):
            batch = pagos[i:i + batch_size]
            
            for pago in batch:
                try:
                    dni = pago['dni']
                    
                    socio = self._get_socio_cached(dni)
                    nombre = socio['nombre'] if socio else "Socio no encontrado"
                    
                    estado = self._calculate_payment_status(pago['fecha_pago'])
                    
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
                    
                except Exception as e:
                    logging.error(f"Error al procesar pago {pago.get('id', 'unknown')}: {e}")
                    continue
            
            self.update_idletasks()
        
        # Actualizar estadísticas
        self._update_statistics(total_pagos, monto_total)
    
    @lru_cache(maxsize=128)
    def _get_socio_cached(self, dni: int) -> Optional[Dict[str, Any]]:
        """Obtiene información del socio con cache"""
        try:
            return self.db_manager.obtener_socio(dni)
        except Exception as e:
            logging.error(f"Error al obtener socio {dni}: {e}")
            return None
    
    def _calculate_payment_status(self, fecha_pago_str: str) -> str:
        """Calcula el estado del pago de manera optimizada"""
        try:
            fecha_pago = datetime.strptime(fecha_pago_str, '%Y-%m-%d')
            dias_transcurridos = (datetime.now() - fecha_pago).days
            
            if dias_transcurridos <= 30:
                return "✅ Vigente"
            elif dias_transcurridos <= 60:
                return "⚠️ Vencido"
            else:
                return "❌ Muy Vencido"
        except (ValueError, TypeError):
            return "❓ Error"
    
    def _update_statistics(self, total_pagos: int, monto_total: float):
        """Actualiza las estadísticas de manera optimizada"""
        self.total_pagos_label.configure(text=f"Total de Pagos: {total_pagos}")
        self.monto_total_label.configure(text=f"Monto Total: ${monto_total:.2f}")
        
        if total_pagos > 0:
            promedio = monto_total / total_pagos
            self.promedio_label.configure(text=f"Promedio: ${promedio:.2f}")
        else:
            self.promedio_label.configure(text="Promedio: $0.00")
    
    def _debounced_filter(self, event=None):
        """Filtro con debounce para mejor performance"""
        if hasattr(self, '_filter_after_id'):
            self.after_cancel(self._filter_after_id)
        
        self._filter_after_id = self.after(300, self.filtrar_pagos)  # 300ms debounce
    
    def filtrar_pagos(self, event=None):
        """Filtra pagos por DNI en tiempo real con optimizaciones"""
        dni_filtro = self.dni_filter.get().strip()
        
        if not dni_filtro:
            self.refrescar_pagos()
            return
        
        try:
            if not dni_filtro.isdigit():
                return
            
            dni = int(dni_filtro)
            
            pagos = self.db_manager.obtener_pagos_por_dni(dni)
            self._populate_filtered_table(pagos)
            
        except ValueError:
            # DNI inválido, no hacer nada
            pass
        except Exception as e:
            logging.error(f"Error al filtrar pagos: {e}")
    
    def _populate_filtered_table(self, pagos: List[Dict[str, Any]]):
        """Puebla la tabla con pagos filtrados"""
        # Limpiar tabla
        self.pagos_tree.delete(*self.pagos_tree.get_children())
        
        total_pagos = 0
        monto_total = 0.0
        
        for pago in pagos:
            try:
                socio = self._get_socio_cached(pago['dni'])
                nombre = socio['nombre'] if socio else "Socio no encontrado"
                
                estado = self._calculate_payment_status(pago['fecha_pago'])
                
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
                
            except Exception as e:
                logging.error(f"Error al procesar pago filtrado {pago.get('id', 'unknown')}: {e}")
                continue
        
        # Actualizar estadísticas
        self._update_statistics(total_pagos, monto_total)

class SomaEntrenamientosApp:
    def __init__(self):
        # Configurar logging
        logging.info("Iniciando aplicación Soma Entrenamientos")
        
        # Inicializar base de datos
        self.db_manager = DatabaseManager()
        
        # Crear ventana principal usando tk en lugar de ctk
        self.root = tk.Tk()
        self.root.title("Soma Entrenamientos — Sistema de Gestión")
        self.root.geometry("1280x900")
        
        
        
        # Maximizar ventana
        self.root.state("zoomed")
        
        # Configurar icono si existe
        try:
            icon_path = resource_path("assets/icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            logging.warning(f"No se pudo cargar el icono: {e}")
        
        # Configurar estilos de tabla para fuentes más grandes
        self.configure_table_styles()
        
        self.create_widgets()
        
        # Bind para cerrar aplicación
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_widgets(self):
        # Crear notebook (tabs)
        self.notebook = ctk.CTkTabview(self.root)
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
        
        # Pestaña Dashboard
        self.notebook.add("Dashboard")
        self.reportes_frame = ReportesFrame(self.notebook.tab("Dashboard"), self.db_manager)
        self.reportes_frame.pack(fill="both", expand=True)
        
        # Pestaña Import/Export
        self.notebook.add("Import/Export")
        self.import_export_frame = ImportExportFrame(self.notebook.tab("Import/Export"), self.db_manager)
        self.import_export_frame.pack(fill="both", expand=True)
        
        # Establecer pestaña inicial
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

import tkinter as tk
from tkinter import ttk

def configurar_tema_claro(root):
    # Colores personalizados
    root.configure(bg='white')
    
    style = ttk.Style()
    style.theme_use('default')
    
    # Configuración base
    style.configure('.',
        background='white',
        foreground='black',
        fieldbackground='white'
    )
    
    # Botones
    style.configure('TButton',
        background='#F66002',  # Naranja SOMA
        foreground='black',
        padding=5
    )
    
    # Frames
    style.configure('TFrame', background='white')
    
    # Labels
    style.configure('TLabel', 
        background='white',
        foreground='black'
    )
    
    # Tablas
    style.configure('Treeview',
        background='white',
        fieldbackground='white',
        foreground='black'
    )
    style.configure('Treeview.Heading',
        background='#F66002',
        foreground='black'
    )
    
    # Configuración de pestañas
    style.configure('TNotebook',
        background='white'
    )
    style.configure('TNotebook.Tab',
        background='white',
        foreground='black',
        padding=[10, 2]
    )
    
    # Entradas de texto
    style.configure('TEntry',
        fieldbackground='white',
        selectbackground='#FF8C00'
    )



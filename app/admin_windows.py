import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from datetime import datetime
from typing import Optional, Callable
import re
try:
    import customtkinter as ctk
except ImportError:
    ctk = None  # fallback: ventanas de grupo usarán ttk si no está disponible

# Colores de marca (se usan en ventanas CTk)
_ORANGE      = "#E6461A"
_ORANGE_DARK = "#C93D16"
_GRAY_BTN    = "#E5E7EB"
_GRAY_HOVER  = "#D1D5DB"
_TEXT_DARK   = "#1A1A1A"
_BORDER      = "#E5E7EB"

class AltaSocioWindow:
    def __init__(self, parent, db_manager, callback: Optional[Callable] = None):
        self.db_manager = db_manager
        self.callback = callback
        
        # Ventana modal
        self.window = tk.Toplevel(parent)
        self.window.title("Alta de Socio")
        self.window.geometry("500x600")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Centrar ventana
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.window.winfo_screenheight() // 2) - (600 // 2)
        self.window.geometry(f"500x600+{x}+{y}")
        
        self.create_widgets()
        self.dni_entry.focus()
    
    def create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        title_label = ttk.Label(main_frame, text="Nuevo Socio", font=('TkDefaultFont', 28, 'bold'))
        title_label.pack(pady=(0, 30))
        
        # DNI
        ttk.Label(main_frame, text="DNI *", font=('TkDefaultFont', 18)).pack(anchor="w")
        self.dni_entry = ttk.Entry(main_frame, font=('TkDefaultFont', 18))
        self.dni_entry.pack(fill="x", pady=(0, 15))
        
        # Nombre
        ttk.Label(main_frame, text="Nombre *", font=('TkDefaultFont', 18)).pack(anchor="w")
        self.nombre_entry = ttk.Entry(main_frame, font=('TkDefaultFont', 18))
        self.nombre_entry.pack(fill="x", pady=(0, 15))
        
        # Email
        ttk.Label(main_frame, text="Email", font=('TkDefaultFont', 18)).pack(anchor="w")
        self.email_entry = ttk.Entry(main_frame, font=('TkDefaultFont', 18))
        self.email_entry.pack(fill="x", pady=(0, 15))
        
        # Teléfono
        ttk.Label(main_frame, text="Teléfono", font=('TkDefaultFont', 18)).pack(anchor="w")
        self.telefono_entry = ttk.Entry(main_frame, font=('TkDefaultFont', 18))
        self.telefono_entry.pack(fill="x", pady=(0, 30))
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x")
        
        ttk.Button(button_frame, text="Cancelar", command=self.cancelar).pack(side="right", padx=(10, 0))
        ttk.Button(button_frame, text="Guardar", command=self.guardar).pack(side="right")
        
        # Bind Enter para guardar
        self.window.bind('<Return>', lambda e: self.guardar())
    
    def validar_datos(self) -> bool:
        # DNI
        dni_text = self.dni_entry.get().strip()
        if not dni_text:
            messagebox.showerror("Error", "El DNI es obligatorio")
            return False
        
        if not dni_text.isdigit() or len(dni_text) < 7 or len(dni_text) > 8:
            messagebox.showerror("Error", "El DNI debe ser numérico de 7-8 dígitos")
            return False
        
        # Verificar si ya existe
        dni = int(dni_text)
        if self.db_manager.obtener_socio(dni):
            messagebox.showerror("Error", f"Ya existe un socio con DNI {dni}")
            return False
        
        # Nombre
        if not self.nombre_entry.get().strip():
            messagebox.showerror("Error", "El nombre es obligatorio")
            return False
        
        # Email (opcional pero si se ingresa debe ser válido)
        email = self.email_entry.get().strip()
        if email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            messagebox.showerror("Error", "El email no tiene un formato válido")
            return False
        
        return True
    
    def guardar(self):
        if not self.validar_datos():
            return
        
        try:
            dni = int(self.dni_entry.get().strip())
            nombre = self.nombre_entry.get().strip()
            email = self.email_entry.get().strip() or None
            telefono = self.telefono_entry.get().strip() or None
            fecha_alta = datetime.now().strftime('%Y-%m-%d')
            
            self.db_manager.agregar_socio(dni, nombre, email, telefono, fecha_alta)
            
            messagebox.showinfo("Éxito", f"Socio {nombre} agregado correctamente")
            
            if self.callback:
                self.callback()
            
            self.window.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar socio: {str(e)}")
    
    def cancelar(self):
        self.window.destroy()

class EditarSocioWindow:
    def __init__(self, parent, db_manager, dni: int, callback: Optional[Callable] = None):
        self.db_manager = db_manager
        self.dni = dni
        self.callback = callback
        
        # Obtener datos actuales
        self.socio_actual = db_manager.obtener_socio(dni)
        if not self.socio_actual:
            messagebox.showerror("Error", "Socio no encontrado")
            return
        
        # Ventana modal
        self.window = tk.Toplevel(parent)
        self.window.title("Editar Socio")
        self.window.geometry("500x600")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Centrar ventana
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.window.winfo_screenheight() // 2) - (600 // 2)
        self.window.geometry(f"500x600+{x}+{y}")
        
        self.create_widgets()
        self.nombre_entry.focus()
    
    def create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        title_label = ttk.Label(main_frame, text=f"Editar Socio - DNI {self.dni}", 
                                 font=('TkDefaultFont', 28, 'bold'))
        title_label.pack(pady=(0, 30))
        
        # DNI (editable)
        ttk.Label(main_frame, text="DNI *", font=('TkDefaultFont', 18)).pack(anchor="w")
        self.dni_entry = ttk.Entry(main_frame, font=('TkDefaultFont', 18))
        self.dni_entry.insert(0, str(self.dni))
        self.dni_entry.pack(fill="x", pady=(0, 15))
        
        # Nombre
        ttk.Label(main_frame, text="Nombre *", font=('TkDefaultFont', 18)).pack(anchor="w")
        self.nombre_entry = ttk.Entry(main_frame, font=('TkDefaultFont', 18))
        self.nombre_entry.insert(0, self.socio_actual['nombre'])
        self.nombre_entry.pack(fill="x", pady=(0, 15))
        
        # Email
        ttk.Label(main_frame, text="Email", font=('TkDefaultFont', 18)).pack(anchor="w")
        self.email_entry = ttk.Entry(main_frame, font=('TkDefaultFont', 18))
        if self.socio_actual['email']:
            self.email_entry.insert(0, self.socio_actual['email'])
        self.email_entry.pack(fill="x", pady=(0, 15))
        
        # Teléfono
        ttk.Label(main_frame, text="Teléfono", font=('TkDefaultFont', 18)).pack(anchor="w")
        self.telefono_entry = ttk.Entry(main_frame, font=('TkDefaultFont', 18))
        if self.socio_actual['telefono']:
            self.telefono_entry.insert(0, self.socio_actual['telefono'])
        self.telefono_entry.pack(fill="x", pady=(0, 30))
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x")
        
        ttk.Button(button_frame, text="Cancelar", command=self.cancelar).pack(side="right", padx=(10, 0))
        ttk.Button(button_frame, text="Guardar", command=self.guardar).pack(side="right")
        
        # Bind Enter para guardar
        self.window.bind('<Return>', lambda e: self.guardar())
    
    def validar_datos(self) -> bool:
        # DNI
        dni_text = self.dni_entry.get().strip()
        if not dni_text or not dni_text.isdigit() or len(dni_text) < 7 or len(dni_text) > 8:
            messagebox.showerror("Error", "El DNI debe ser numérico de 7-8 dígitos")
            return False

        # Nombre
        if not self.nombre_entry.get().strip():
            messagebox.showerror("Error", "El nombre es obligatorio")
            return False
        
        # Email (opcional pero si se ingresa debe ser válido)
        email = self.email_entry.get().strip()
        if email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            messagebox.showerror("Error", "El email no tiene un formato válido")
            return False
        
        return True
    
    def guardar(self):
        if not self.validar_datos():
            return
        
        try:
            nuevo_dni = int(self.dni_entry.get().strip())
            nombre = self.nombre_entry.get().strip()
            email = self.email_entry.get().strip() or None
            telefono = self.telefono_entry.get().strip() or None

            # Si cambió el DNI, actualizar en base
            if nuevo_dni != self.dni:
                self.db_manager.cambiar_dni_socio(self.dni, nuevo_dni)
                self.dni = nuevo_dni

            self.db_manager.editar_socio(self.dni, nombre, email, telefono)
            
            messagebox.showinfo("Éxito", f"Socio {nombre} actualizado correctamente")
            
            if self.callback:
                self.callback()
            
            self.window.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al actualizar socio: {str(e)}")
    
    def cancelar(self):
        self.window.destroy()

class RegistrarPagoWindow:
    def __init__(self, parent, db_manager, dni: Optional[int] = None, callback: Optional[Callable] = None):
        self.db_manager = db_manager
        self.callback = callback
        
        # Ventana modal
        self.window = tk.Toplevel(parent)
        self.window.title("Registrar Pago")
        self.window.geometry("500x680")
        self.window.transient(parent)
        self.window.grab_set()

        # Centrar ventana
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.window.winfo_screenheight() // 2) - (680 // 2)
        self.window.geometry(f"500x680+{x}+{y}")
        
        self.create_widgets()
        
        # Pre-cargar DNI si se proporciona
        if dni:
            self.dni_entry.insert(0, str(dni))
            self.monto_entry.focus()
        else:
            self.dni_entry.focus()
    
    def create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        title_label = ttk.Label(main_frame, text="Registrar Pago", font=('TkDefaultFont', 28, 'bold'))
        title_label.pack(pady=(0, 30))
        
        # DNI
        ttk.Label(main_frame, text="DNI *", font=('TkDefaultFont', 18)).pack(anchor="w")
        self.dni_entry = ttk.Entry(main_frame, font=('TkDefaultFont', 18))
        self.dni_entry.pack(fill="x", pady=(0, 10))

        # Búsqueda por nombre/apellido
        ttk.Label(main_frame, text="Buscar socio (Nombre o apellido)", font=('TkDefaultFont', 14)).pack(anchor="w")
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill="both", expand=False, pady=(0, 10))
        self.search_entry = ttk.Entry(search_frame, font=('TkDefaultFont', 14))
        self.search_entry.pack(fill="x")
        self.search_entry.bind('<KeyRelease>', self._actualizar_sugerencias)
        # Navegación por teclado en sugerencias
        self.search_entry.bind('<Down>', self._focus_suggestions_down)
        self.search_entry.bind('<Up>', self._focus_suggestions_up)
        self.search_entry.bind('<Return>', self._enter_desde_entry)
        
        self.suggestions = tk.Listbox(main_frame, height=5)
        self.suggestions.pack(fill="x", pady=(5, 15))
        self.suggestions.bind('<<ListboxSelect>>', self._seleccionar_sugerencia)
        self.suggestions.bind('<Return>', self._enter_desde_listbox)
        # Las teclas de flecha funcionan por defecto dentro del Listbox.
        
        # Monto
        ttk.Label(main_frame, text="Monto *", font=('TkDefaultFont', 18)).pack(anchor="w")
        self.monto_entry = ttk.Entry(main_frame, font=('TkDefaultFont', 18))
        self.monto_entry.pack(fill="x", pady=(0, 15))

        # Duración
        ttk.Label(main_frame, text="Duración *", font=('TkDefaultFont', 18)).pack(anchor="w")
        self.meses_var = tk.IntVar(self.window, value=1)
        meses_frame = ttk.Frame(main_frame)
        meses_frame.pack(fill="x", pady=(0, 15))
        for meses, label in [(1, "1 mes"), (3, "3 meses"), (6, "6 meses"), (12, "12 meses")]:
            ttk.Radiobutton(
                meses_frame, text=label, variable=self.meses_var,
                value=meses, font=('TkDefaultFont', 16)
            ).pack(side="left", padx=(0, 15))

        # Fecha
        ttk.Label(main_frame, text="Fecha de Pago *", font=('TkDefaultFont', 18)).pack(anchor="w")
        self.fecha_entry = ttk.Entry(main_frame, font=('TkDefaultFont', 18))
        self.fecha_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.fecha_entry.pack(fill="x", pady=(0, 15))

        # Método de pago
        ttk.Label(main_frame, text="Método de Pago *", font=('TkDefaultFont', 18)).pack(anchor="w")
        self.metodo_var = tk.StringVar(self.window,value="efectivo")
        metodo_frame = ttk.Frame(main_frame)
        metodo_frame.pack(fill="x", pady=(0, 30))
        
        ttk.Radiobutton(metodo_frame, text="Efectivo", variable=self.metodo_var, 
                          value="efectivo", font=('TkDefaultFont', 18)).pack(side="left", padx=(0, 20))
        ttk.Radiobutton(metodo_frame, text="Transferencia", variable=self.metodo_var, 
                          value="transferencia", font=('TkDefaultFont', 18)).pack(side="left")
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x")
        
        ttk.Button(button_frame, text="Cancelar", command=self.cancelar).pack(side="right", padx=(10, 0))
        ttk.Button(button_frame, text="Registrar", command=self.registrar).pack(side="right")
        
        # Bind Enter para registrar
        self.window.bind('<Return>', lambda e: self.registrar())

    def _actualizar_sugerencias(self, event=None):
        texto = self.search_entry.get().strip()
        self.suggestions.delete(0, tk.END)
        if not texto:
            return
        try:
            resultados = self.db_manager.buscar_socios(texto)
            for s in resultados:
                display = f"{s['nombre']} (DNI {s['dni']})"
                self.suggestions.insert(tk.END, display)
            # Preseleccionar el primer elemento para facilitar Enter directo
            if self.suggestions.size() > 0:
                self.suggestions.selection_clear(0, tk.END)
                self.suggestions.selection_set(0)
                self.suggestions.activate(0)
        except Exception:
            pass

    def _focus_suggestions_down(self, event=None):
        # Desde el Entry: mover foco a la lista y bajar una posición
        if self.suggestions.size() == 0:
            return 'break'
        self.suggestions.focus_set()
        sel = self.suggestions.curselection()
        idx = sel[0] if sel else -1
        new_idx = min(idx + 1, self.suggestions.size() - 1)
        self.suggestions.selection_clear(0, tk.END)
        self.suggestions.selection_set(new_idx)
        self.suggestions.activate(new_idx)
        self.suggestions.see(new_idx)
        return 'break'

    def _focus_suggestions_up(self, event=None):
        # Desde el Entry: mover foco a la lista y subir una posición
        if self.suggestions.size() == 0:
            return 'break'
        self.suggestions.focus_set()
        sel = self.suggestions.curselection()
        # Si no hay selección previa, ir al último
        idx = sel[0] if sel else self.suggestions.size()
        new_idx = max(idx - 1, 0)
        self.suggestions.selection_clear(0, tk.END)
        self.suggestions.selection_set(new_idx)
        self.suggestions.activate(new_idx)
        self.suggestions.see(new_idx)
        return 'break'

    def _enter_desde_entry(self, event=None):
        # Si hay sugerencias, seleccionar la actual (o primera) y aplicar
        if self.suggestions.size() == 0:
            return None  # No bloquear Enter si no hay sugerencias
        sel = self.suggestions.curselection()
        if not sel:
            idx = 0
            self.suggestions.selection_clear(0, tk.END)
            self.suggestions.selection_set(idx)
            self.suggestions.activate(idx)
        # Ejecutar selección y evitar que el Enter dispare Registrar
        self._seleccionar_sugerencia()
        return 'break'

    def _enter_desde_listbox(self, event=None):
        # Confirmar la sugerencia seleccionada
        self._seleccionar_sugerencia()
        return 'break'

    def _seleccionar_sugerencia(self, event=None):
        sel = self.suggestions.curselection()
        if not sel:
            return
        texto = self.suggestions.get(sel[0])
        # Extraer DNI al final del texto
        m = re.search(r'DNI\s(\d+)', texto)
        if m:
            self.dni_entry.delete(0, tk.END)
            self.dni_entry.insert(0, m.group(1))
            self.monto_entry.focus()
    
    def validar_datos(self) -> bool:
        # DNI
        dni_text = self.dni_entry.get().strip()
        if not dni_text:
            messagebox.showerror("Error", "El DNI es obligatorio")
            return False
        
        if not dni_text.isdigit():
            messagebox.showerror("Error", "El DNI debe ser numérico")
            return False
        
        dni = int(dni_text)
        if not self.db_manager.obtener_socio(dni):
            messagebox.showerror("Error", f"No existe un socio con DNI {dni}")
            return False
        
        # Monto
        try:
            monto = float(self.monto_entry.get().strip())
            if monto <= 0:
                messagebox.showerror("Error", "El monto debe ser mayor a 0")
                return False
        except ValueError:
            messagebox.showerror("Error", "El monto debe ser un número válido")
            return False
        
        # Fecha
        try:
            datetime.strptime(self.fecha_entry.get().strip(), '%Y-%m-%d')
        except ValueError:
            messagebox.showerror("Error", "La fecha debe tener formato YYYY-MM-DD")
            return False
        metodo = self.metodo_var.get()
        if metodo not in ("efectivo", "transferencia"):
            messagebox.showerror("Error", "Seleccione un método de pago")
            return False
        
        return True
    
    def registrar(self):
        if not self.validar_datos():
            return

        try:
            dni = int(self.dni_entry.get().strip())
            monto = float(self.monto_entry.get().strip())
            fecha = self.fecha_entry.get().strip()
            metodo = self.metodo_var.get()
            meses = self.meses_var.get()

            self.db_manager.registrar_pago(dni, monto, fecha, metodo, meses)

            socio = self.db_manager.obtener_socio(dni)
            duracion_txt = f"{meses} mes" if meses == 1 else f"{meses} meses"
            messagebox.showinfo("Éxito", f"Pago registrado para {socio['nombre']}\n${monto} — {duracion_txt} — {metodo}")
            
            if self.callback:
                self.callback()
            
            self.window.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al registrar pago: {str(e)}")
    
    def cancelar(self):
        self.window.destroy()

class EditarPagoWindow:
    def __init__(self, parent, db_manager, pago_id: int, callback: Optional[Callable] = None):
        self.db_manager = db_manager
        self.pago_id = pago_id
        self.callback = callback

        self.pago = db_manager.obtener_pago(pago_id)
        if not self.pago:
            messagebox.showerror("Error", "Pago no encontrado")
            return

        self.window = tk.Toplevel(parent)
        self.window.title("Editar Pago")
        self.window.geometry("500x580")
        self.window.transient(parent)
        self.window.grab_set()

        # Centrar
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.window.winfo_screenheight() // 2) - (580 // 2)
        self.window.geometry(f"500x580+{x}+{y}")

        self._create_widgets()

    def _create_widgets(self):
        main = ttk.Frame(self.window)
        main.pack(fill="both", expand=True, padx=20, pady=20)

        ttk.Label(main, text=f"ID Pago: {self.pago_id}", font=('TkDefaultFont', 12)).pack(anchor='w', pady=(0, 10))

        # DNI
        ttk.Label(main, text="DNI *", font=('TkDefaultFont', 18)).pack(anchor='w')
        self.dni_entry = ttk.Entry(main, font=('TkDefaultFont', 18))
        self.dni_entry.insert(0, str(self.pago['dni']))
        self.dni_entry.pack(fill='x', pady=(0, 10))

        # Buscar socio por nombre (opcional)
        ttk.Label(main, text="Buscar socio (Nombre o apellido)", font=('TkDefaultFont', 12)).pack(anchor='w')
        self.search_entry = ttk.Entry(main, font=('TkDefaultFont', 12))
        self.search_entry.pack(fill='x')
        self.search_entry.bind('<KeyRelease>', self._actualizar_sugerencias)
        # Navegación por teclado en sugerencias
        self.search_entry.bind('<Down>', self._focus_suggestions_down)
        self.search_entry.bind('<Up>', self._focus_suggestions_up)
        self.search_entry.bind('<Return>', self._enter_desde_entry)
        self.suggestions = tk.Listbox(main, height=4)
        self.suggestions.pack(fill='x', pady=(5, 10))
        self.suggestions.bind('<<ListboxSelect>>', self._seleccionar_sugerencia)
        self.suggestions.bind('<Return>', self._enter_desde_listbox)

        # Monto
        ttk.Label(main, text="Monto *", font=('TkDefaultFont', 18)).pack(anchor='w')
        self.monto_entry = ttk.Entry(main, font=('TkDefaultFont', 18))
        self.monto_entry.insert(0, str(self.pago['monto']))
        self.monto_entry.pack(fill='x', pady=(0, 10))

        # Duración
        ttk.Label(main, text="Duración *", font=('TkDefaultFont', 18)).pack(anchor='w')
        meses_actual = int(self.pago.get('meses', 1) or 1)
        # Si el valor guardado no es una opción estándar, usar 1 como fallback
        if meses_actual not in (1, 3, 6, 12):
            meses_actual = 1
        self.meses_var = tk.IntVar(self.window, value=meses_actual)
        meses_frame = ttk.Frame(main)
        meses_frame.pack(fill='x', pady=(0, 10))
        for meses, label in [(1, "1 mes"), (3, "3 meses"), (6, "6 meses"), (12, "12 meses")]:
            ttk.Radiobutton(
                meses_frame, text=label, variable=self.meses_var,
                value=meses, font=('TkDefaultFont', 16)
            ).pack(side='left', padx=(0, 15))

        # Fecha
        ttk.Label(main, text="Fecha de Pago *", font=('TkDefaultFont', 18)).pack(anchor='w')
        self.fecha_entry = ttk.Entry(main, font=('TkDefaultFont', 18))
        self.fecha_entry.insert(0, self.pago['fecha_pago'])
        self.fecha_entry.pack(fill='x', pady=(0, 10))

        # Método
        ttk.Label(main, text="Método de Pago *", font=('TkDefaultFont', 18)).pack(anchor='w')
        self.metodo_var = tk.StringVar(self.window, value=self.pago['metodo_pago'])
        metodo_frame = ttk.Frame(main)
        metodo_frame.pack(fill='x', pady=(0, 20))
        ttk.Radiobutton(metodo_frame, text="Efectivo", variable=self.metodo_var, value="efectivo", font=('TkDefaultFont', 16)).pack(side='left', padx=(0, 20))
        ttk.Radiobutton(metodo_frame, text="Transferencia", variable=self.metodo_var, value="transferencia", font=('TkDefaultFont', 16)).pack(side='left')

        # Botones
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill='x')
        ttk.Button(btn_frame, text="Cancelar", command=self.window.destroy).pack(side='right', padx=(10,0))
        ttk.Button(btn_frame, text="Guardar", command=self._guardar).pack(side='right')

        self.window.bind('<Return>', lambda e: self._guardar())

    def _actualizar_sugerencias(self, event=None):
        texto = self.search_entry.get().strip()
        self.suggestions.delete(0, tk.END)
        if not texto:
            return
        try:
            resultados = self.db_manager.buscar_socios(texto)
            for s in resultados:
                self.suggestions.insert(tk.END, f"{s['nombre']} (DNI {s['dni']})")
            if self.suggestions.size() > 0:
                self.suggestions.selection_clear(0, tk.END)
                self.suggestions.selection_set(0)
                self.suggestions.activate(0)
        except Exception:
            pass

    def _focus_suggestions_down(self, event=None):
        if self.suggestions.size() == 0:
            return 'break'
        self.suggestions.focus_set()
        sel = self.suggestions.curselection()
        idx = sel[0] if sel else -1
        new_idx = min(idx + 1, self.suggestions.size() - 1)
        self.suggestions.selection_clear(0, tk.END)
        self.suggestions.selection_set(new_idx)
        self.suggestions.activate(new_idx)
        self.suggestions.see(new_idx)
        return 'break'

    def _focus_suggestions_up(self, event=None):
        if self.suggestions.size() == 0:
            return 'break'
        self.suggestions.focus_set()
        sel = self.suggestions.curselection()
        idx = sel[0] if sel else self.suggestions.size()
        new_idx = max(idx - 1, 0)
        self.suggestions.selection_clear(0, tk.END)
        self.suggestions.selection_set(new_idx)
        self.suggestions.activate(new_idx)
        self.suggestions.see(new_idx)
        return 'break'

    def _enter_desde_entry(self, event=None):
        if self.suggestions.size() == 0:
            return None
        sel = self.suggestions.curselection()
        if not sel:
            idx = 0
            self.suggestions.selection_clear(0, tk.END)
            self.suggestions.selection_set(idx)
            self.suggestions.activate(idx)
        self._seleccionar_sugerencia()
        return 'break'

    def _enter_desde_listbox(self, event=None):
        self._seleccionar_sugerencia()
        return 'break'

    def _seleccionar_sugerencia(self, event=None):
        sel = self.suggestions.curselection()
        if not sel:
            return
        texto = self.suggestions.get(sel[0])
        m = re.search(r'DNI\s(\d+)', texto)
        if m:
            self.dni_entry.delete(0, tk.END)
            self.dni_entry.insert(0, m.group(1))

    def _guardar(self):
        # Validaciones
        dni_text = self.dni_entry.get().strip()
        if not dni_text.isdigit():
            messagebox.showerror("Error", "El DNI debe ser numérico")
            return
        try:
            monto = float(self.monto_entry.get().strip())
            if monto <= 0:
                raise ValueError()
        except Exception:
            messagebox.showerror("Error", "El monto debe ser mayor a 0")
            return
        fecha = self.fecha_entry.get().strip()
        try:
            datetime.strptime(fecha, '%Y-%m-%d')
        except ValueError:
            messagebox.showerror("Error", "La fecha debe tener formato YYYY-MM-DD")
            return
        metodo = self.metodo_var.get()
        if metodo not in ("efectivo", "transferencia"):
            messagebox.showerror("Error", "Seleccione un método de pago")
            return

        meses = self.meses_var.get()

        try:
            self.db_manager.editar_pago(self.pago_id, int(dni_text), monto, fecha, metodo, meses)
            messagebox.showinfo("Éxito", "Pago actualizado correctamente")
            if self.callback:
                self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Error al actualizar pago: {str(e)}")


class GrupoFamiliarWindow:
    """Ventana para crear o editar un grupo familiar y gestionar sus miembros."""

    def __init__(self, parent, db_manager, grupo_id: Optional[int] = None,
                 callback: Optional[Callable] = None):
        self.db_manager = db_manager
        self.grupo_id = grupo_id
        self.callback = callback
        self._miembros: list = []

        self.window = ctk.CTkToplevel(parent)
        self.window.title("Grupo Familiar" if not grupo_id else "Editar Grupo Familiar")
        self.window.geometry("520x640")
        self.window.transient(parent)
        self.window.grab_set()
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - 260
        y = (self.window.winfo_screenheight() // 2) - 320
        self.window.geometry(f"520x640+{x}+{y}")

        self._create_widgets()
        if grupo_id:
            self._precargar_datos()

    def _create_widgets(self):
        main = ctk.CTkFrame(self.window, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=24, pady=20)

        title_txt = "Nuevo Grupo Familiar" if not self.grupo_id else "Editar Grupo Familiar"
        ctk.CTkLabel(main, text=title_txt,
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=_TEXT_DARK).pack(pady=(0, 16))

        # Nombre
        ctk.CTkLabel(main, text="Nombre del grupo *",
                     font=ctk.CTkFont(size=14), text_color=_TEXT_DARK).pack(anchor='w')
        self.nombre_entry = ctk.CTkEntry(main, font=ctk.CTkFont(size=14), height=36,
                                          placeholder_text="Ej: Familia García")
        self.nombre_entry.pack(fill='x', pady=(4, 12))

        # Precio especial
        ctk.CTkLabel(main, text="Precio especial del grupo (opcional)",
                     font=ctk.CTkFont(size=14), text_color=_TEXT_DARK).pack(anchor='w')
        self.precio_entry = ctk.CTkEntry(main, font=ctk.CTkFont(size=14), height=36,
                                          placeholder_text="0.00")
        self.precio_entry.pack(fill='x', pady=(4, 16))

        # Miembros actuales
        ctk.CTkLabel(main, text="Miembros del grupo",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=_TEXT_DARK).pack(anchor='w')
        members_bg = ctk.CTkFrame(main, fg_color="#FFFFFF", border_width=1,
                                   border_color=_BORDER, corner_radius=8)
        members_bg.pack(fill='x', pady=(4, 2))
        self.miembros_listbox = tk.Listbox(members_bg, height=4, font=('TkDefaultFont', 12),
                                            bg="#FFFFFF", relief="flat", bd=0,
                                            selectbackground=_ORANGE, selectforeground="white",
                                            activestyle="none")
        self.miembros_listbox.pack(fill='x', padx=8, pady=6)

        ctk.CTkButton(main, text="✕  Quitar seleccionado", command=self._quitar_miembro,
                      fg_color=_GRAY_BTN, text_color=_TEXT_DARK, hover_color=_GRAY_HOVER,
                      height=28, font=ctk.CTkFont(size=12)).pack(anchor='e', pady=(2, 12))

        # Buscador para agregar
        ctk.CTkLabel(main, text="Buscar y agregar socio",
                     font=ctk.CTkFont(size=13), text_color=_TEXT_DARK).pack(anchor='w')
        self.add_search_entry = ctk.CTkEntry(main, font=ctk.CTkFont(size=13), height=34,
                                              placeholder_text="Nombre o apellido...")
        self.add_search_entry.pack(fill='x', pady=(4, 2))
        self.add_search_entry.bind('<KeyRelease>', self._actualizar_sugerencias_agregar)

        sug_bg = ctk.CTkFrame(main, fg_color="#FFFFFF", border_width=1,
                               border_color=_BORDER, corner_radius=6)
        sug_bg.pack(fill='x', pady=(0, 4))
        self.add_suggestions = tk.Listbox(sug_bg, height=3, font=('TkDefaultFont', 12),
                                           bg="#FFFFFF", relief="flat", bd=0,
                                           selectbackground=_ORANGE, selectforeground="white",
                                           activestyle="none")
        self.add_suggestions.pack(fill='x', padx=8, pady=4)
        self.add_suggestions.bind('<<ListboxSelect>>', self._agregar_sugerido)

        ctk.CTkButton(main, text="➕  Agregar", command=self._agregar_desde_busqueda,
                      fg_color=_ORANGE, hover_color=_ORANGE_DARK,
                      height=30, font=ctk.CTkFont(size=12)).pack(anchor='w', pady=(2, 16))

        # Botones finales
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill='x')
        ctk.CTkButton(btn_frame, text="Cancelar", command=self.window.destroy,
                      fg_color=_GRAY_BTN, text_color=_TEXT_DARK, hover_color=_GRAY_HOVER,
                      height=36).pack(side='right', padx=(8, 0))
        ctk.CTkButton(btn_frame, text="Guardar", command=self._guardar,
                      fg_color=_ORANGE, hover_color=_ORANGE_DARK,
                      height=36).pack(side='right')

    def _precargar_datos(self):
        grupo = self.db_manager.obtener_grupo(self.grupo_id)
        if not grupo:
            return
        self.nombre_entry.insert(0, grupo['nombre'])
        if grupo['precio_especial'] is not None:
            self.precio_entry.insert(0, str(grupo['precio_especial']))
        # Cargar miembros actuales
        for s in self.db_manager.obtener_miembros_grupo(self.grupo_id):
            self._miembros.append({'dni': s['dni'], 'nombre': s['nombre']})
            self.miembros_listbox.insert(tk.END, f"{s['nombre']}  (DNI {s['dni']})")

    def _actualizar_sugerencias_agregar(self, event=None):
        texto = self.add_search_entry.get().strip()
        self.add_suggestions.delete(0, tk.END)
        if not texto:
            return
        try:
            resultados = self.db_manager.buscar_socios(texto)
            miembros_dni = {m['dni'] for m in self._miembros}
            for s in resultados:
                if s['dni'] not in miembros_dni:
                    self.add_suggestions.insert(tk.END, f"{s['nombre']}  (DNI {s['dni']})")
        except Exception:
            pass

    def _agregar_sugerido(self, event=None):
        sel = self.add_suggestions.curselection()
        if not sel:
            return
        texto = self.add_suggestions.get(sel[0])
        m = re.search(r'DNI\s(\d+)', texto)
        if m:
            dni = int(m.group(1))
            nombre = texto.split('  (DNI')[0].strip()
            if not any(mem['dni'] == dni for mem in self._miembros):
                self._miembros.append({'dni': dni, 'nombre': nombre})
                self.miembros_listbox.insert(tk.END, f"{nombre}  (DNI {dni})")
            self.add_search_entry.delete(0, tk.END)
            self.add_suggestions.delete(0, tk.END)

    def _agregar_desde_busqueda(self):
        # Seleccionar el primero de las sugerencias si hay alguno
        if self.add_suggestions.size() > 0:
            self.add_suggestions.selection_clear(0, tk.END)
            self.add_suggestions.selection_set(0)
            self._agregar_sugerido()

    def _quitar_miembro(self):
        sel = self.miembros_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self._miembros.pop(idx)
        self.miembros_listbox.delete(idx)

    def _guardar(self):
        nombre = self.nombre_entry.get().strip()
        if not nombre:
            messagebox.showerror("Error", "El nombre del grupo es obligatorio")
            return

        precio_txt = self.precio_entry.get().strip()
        precio_especial = None
        if precio_txt:
            try:
                precio_especial = float(precio_txt)
                if precio_especial <= 0:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("Error", "El precio especial debe ser un número mayor a 0")
                return

        try:
            if self.grupo_id is None:
                # Crear nuevo grupo
                grupo_id = self.db_manager.crear_grupo(nombre, precio_especial)
            else:
                grupo_id = self.grupo_id
                self.db_manager.editar_grupo(grupo_id, nombre, precio_especial)
                # Limpiar asignaciones previas del grupo
                for s in self.db_manager.obtener_miembros_grupo(grupo_id):
                    self.db_manager.remover_socio_de_grupo(s['dni'])

            # Asignar miembros actuales
            for mem in self._miembros:
                self.db_manager.asignar_socio_a_grupo(mem['dni'], grupo_id)

            accion = "creado" if self.grupo_id is None else "actualizado"
            messagebox.showinfo("Éxito", f"Grupo '{nombre}' {accion} con {len(self._miembros)} miembro(s)")
            if self.callback:
                self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el grupo: {str(e)}")


class RegistrarPagoGrupalWindow:
    """Ventana para registrar un pago para todos los miembros de un grupo familiar."""

    def __init__(self, parent, db_manager, grupo_id: int, callback: Optional[Callable] = None):
        self.db_manager = db_manager
        self.grupo_id = grupo_id
        self.callback = callback

        self.grupo = db_manager.obtener_grupo(grupo_id)
        if not self.grupo:
            messagebox.showerror("Error", "Grupo no encontrado")
            return
        self.miembros = db_manager.obtener_miembros_grupo(grupo_id)
        if not self.miembros:
            messagebox.showerror("Error", "El grupo no tiene miembros. Agregue socios al grupo primero.")
            return

        self.window = ctk.CTkToplevel(parent)
        self.window.title(f"Pago Grupal — {self.grupo['nombre']}")
        self.window.geometry("500x520")
        self.window.transient(parent)
        self.window.grab_set()
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - 250
        y = (self.window.winfo_screenheight() // 2) - 260
        self.window.geometry(f"500x520+{x}+{y}")

        self._create_widgets()

    def _create_widgets(self):
        main = ctk.CTkFrame(self.window, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=24, pady=20)

        ctk.CTkLabel(main, text="Pago Grupal",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=_TEXT_DARK).pack(pady=(0, 4))

        # Info del grupo
        nombres = ", ".join(m['nombre'].split()[0] for m in self.miembros)
        info_txt = f"Grupo: {self.grupo['nombre']}   |   {len(self.miembros)} miembro(s)"
        ctk.CTkLabel(main, text=info_txt,
                     font=ctk.CTkFont(size=13), text_color=_TEXT_DARK).pack(pady=(0, 2))
        ctk.CTkLabel(main, text=f"({nombres})",
                     font=ctk.CTkFont(size=11),
                     text_color="#6B7280").pack(pady=(0, 16))

        # Monto
        ctk.CTkLabel(main, text="Monto *",
                     font=ctk.CTkFont(size=14), text_color=_TEXT_DARK).pack(anchor='w')
        self.monto_entry = ctk.CTkEntry(main, font=ctk.CTkFont(size=14), height=36,
                                         placeholder_text="0.00")
        if self.grupo.get('precio_especial'):
            self.monto_entry.insert(0, str(self.grupo['precio_especial']))
        self.monto_entry.pack(fill='x', pady=(4, 12))

        # Duración
        ctk.CTkLabel(main, text="Duración *",
                     font=ctk.CTkFont(size=14), text_color=_TEXT_DARK).pack(anchor='w')
        self.meses_var = tk.IntVar(self.window, value=1)
        meses_frame = ctk.CTkFrame(main, fg_color="transparent")
        meses_frame.pack(fill='x', pady=(4, 12))
        for meses, label in [(1, "1 mes"), (3, "3 meses"), (6, "6 meses"), (12, "12 meses")]:
            ctk.CTkRadioButton(meses_frame, text=label, variable=self.meses_var,
                               value=meses, font=ctk.CTkFont(size=13),
                               fg_color=_ORANGE, hover_color=_ORANGE_DARK).pack(side='left', padx=(0, 12))

        # Fecha
        ctk.CTkLabel(main, text="Fecha de Pago *",
                     font=ctk.CTkFont(size=14), text_color=_TEXT_DARK).pack(anchor='w')
        self.fecha_entry = ctk.CTkEntry(main, font=ctk.CTkFont(size=14), height=36)
        self.fecha_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.fecha_entry.pack(fill='x', pady=(4, 12))

        # Método
        ctk.CTkLabel(main, text="Método de Pago *",
                     font=ctk.CTkFont(size=14), text_color=_TEXT_DARK).pack(anchor='w')
        self.metodo_var = tk.StringVar(self.window, value='efectivo')
        metodo_frame = ctk.CTkFrame(main, fg_color="transparent")
        metodo_frame.pack(fill='x', pady=(4, 16))
        for val, lbl in [("efectivo", "Efectivo"), ("transferencia", "Transferencia")]:
            ctk.CTkRadioButton(metodo_frame, text=lbl, variable=self.metodo_var,
                               value=val, font=ctk.CTkFont(size=13),
                               fg_color=_ORANGE, hover_color=_ORANGE_DARK).pack(side='left', padx=(0, 20))

        # Aviso informativo
        n = len(self.miembros)
        aviso = f"ℹ  Se crearán {n} pago{'s' if n > 1 else ''} individual{'es' if n > 1 else ''}"
        ctk.CTkLabel(main, text=aviso,
                     font=ctk.CTkFont(size=12),
                     text_color="#2563EB").pack(pady=(0, 16))

        # Botones
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill='x')
        ctk.CTkButton(btn_frame, text="Cancelar", command=self.window.destroy,
                      fg_color=_GRAY_BTN, text_color=_TEXT_DARK, hover_color=_GRAY_HOVER,
                      height=36).pack(side='right', padx=(8, 0))
        ctk.CTkButton(btn_frame, text="Registrar", command=self._registrar,
                      fg_color=_ORANGE, hover_color=_ORANGE_DARK,
                      height=36).pack(side='right')
        self.window.bind('<Return>', lambda e: self._registrar())

    def _registrar(self):
        try:
            monto = float(self.monto_entry.get().strip())
            if monto <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "El monto debe ser un número mayor a 0")
            return
        fecha = self.fecha_entry.get().strip()
        try:
            datetime.strptime(fecha, '%Y-%m-%d')
        except ValueError:
            messagebox.showerror("Error", "La fecha debe tener formato YYYY-MM-DD")
            return
        metodo = self.metodo_var.get()
        if metodo not in ("efectivo", "transferencia"):
            messagebox.showerror("Error", "Seleccione un método de pago")
            return
        meses = self.meses_var.get()
        try:
            cantidad = self.db_manager.registrar_pago_grupal(self.grupo_id, monto, fecha, metodo, meses)
            duracion_txt = f"{meses} mes" if meses == 1 else f"{meses} meses"
            messagebox.showinfo(
                "Éxito",
                f"Pago grupal registrado para '{self.grupo['nombre']}'\n"
                f"{cantidad} pago(s) de ${monto} — {duracion_txt} — {metodo}"
            )
            if self.callback:
                self.callback()
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo registrar el pago grupal: {str(e)}")

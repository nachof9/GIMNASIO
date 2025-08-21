import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from datetime import datetime
from typing import Optional, Callable
import re

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
        
        # DNI (solo lectura)
        ttk.Label(main_frame, text="DNI", font=('TkDefaultFont', 18)).pack(anchor="w")
        dni_entry = ttk.Entry(main_frame, font=('TkDefaultFont', 18))
        dni_entry.insert(0, str(self.dni))
        dni_entry.configure(state="disabled")
        dni_entry.pack(fill="x", pady=(0, 15))
        
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
            nombre = self.nombre_entry.get().strip()
            email = self.email_entry.get().strip() or None
            telefono = self.telefono_entry.get().strip() or None
            
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
        self.window.geometry("500x600")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Centrar ventana
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.window.winfo_screenheight() // 2) - (600 // 2)
        self.window.geometry(f"500x600+{x}+{y}")
        
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
        self.dni_entry.pack(fill="x", pady=(0, 15))
        
        # Monto
        ttk.Label(main_frame, text="Monto *", font=('TkDefaultFont', 18)).pack(anchor="w")
        self.monto_entry = ttk.Entry(main_frame, font=('TkDefaultFont', 18))
        self.monto_entry.pack(fill="x", pady=(0, 15))
        
        # Fecha
        ttk.Label(main_frame, text="Fecha de Pago *", font=('TkDefaultFont', 18)).pack(anchor="w")
        self.fecha_entry = ttk.Entry(main_frame, font=('TkDefaultFont', 18))
        self.fecha_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.fecha_entry.pack(fill="x", pady=(0, 15))
        
        # Método de pago
        ttk.Label(main_frame, text="Método de Pago *", font=('TkDefaultFont', 18)).pack(anchor="w")
        self.metodo_var = tk.StringVar(value="efectivo")
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
        
        return True
    
    def registrar(self):
        if not self.validar_datos():
            return
        
        try:
            dni = int(self.dni_entry.get().strip())
            monto = float(self.monto_entry.get().strip())
            fecha = self.fecha_entry.get().strip()
            metodo = self.metodo_var.get()
            
            self.db_manager.registrar_pago(dni, monto, fecha, metodo)
            
            socio = self.db_manager.obtener_socio(dni)
            messagebox.showinfo("Éxito", f"Pago registrado para {socio['nombre']}\n${monto} - {metodo}")
            
            if self.callback:
                self.callback()
            
            self.window.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al registrar pago: {str(e)}")
    
    def cancelar(self):
        self.window.destroy()

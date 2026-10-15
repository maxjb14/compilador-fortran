import tkinter as tk

import customtkinter as ctk

# en windows los menus de tk y los messagebox los dibuja el sistema y no se les puede
# cambiar la letra; con la ventana escalada salen diminutos, por eso se hacen con customtkinter

FUENTE_BARRA = ("Segoe UI", 14)
FUENTE_MENU = ("Segoe UI", 14)
FUENTE_DIALOGO = ("Segoe UI", 15)
COLOR_BARRA = "#0b2a2c"
COLOR_MENU = "#123a3d"
COLOR_BORDE = "#3a7a7e"
COLOR_HOVER = "#1f6266"
COLOR_TEXTO = "#e6f4f2"
COLOR_ATAJO = "#8fc7c2"


class BarraMenu(ctk.CTkFrame):
    # entradas de un menu: (texto, atajo, funcion), (texto, None, [submenu]) o None para separador
    def __init__(self, master):
        super().__init__(master, fg_color=COLOR_BARRA, corner_radius=0)
        self.ventana = master
        self.abiertos = []
        master.bind_all("<Button-1>", self._clic_global, add="+")
        master.bind_all("<Escape>", lambda e: self.cerrar(), add="+")
        master.bind("<Configure>", self._ventana_movida, add="+")
        master.bind("<Unmap>", lambda e: self.cerrar(), add="+")

    def agregar(self, titulo, entradas):
        boton = ctk.CTkButton(self, text=titulo, font=FUENTE_BARRA, fg_color="transparent",
                              hover_color=COLOR_HOVER, text_color=COLOR_TEXTO, corner_radius=4,
                              width=20, height=30)
        boton.configure(command=lambda: self.abrir_desde(boton, entradas))
        boton.pack(side="left", padx=(4, 0), pady=2)
        return boton

    def abrir_desde(self, boton, entradas):
        ya_abierto = bool(self.abiertos) and self.abiertos[0].boton is boton
        self.cerrar()
        if ya_abierto:
            return
        x = boton.winfo_rootx()
        y = boton.winfo_rooty() + boton.winfo_height()
        self.abiertos.append(Desplegable(self, entradas, x, y, nivel=0, boton=boton))

    def abrir_submenu(self, nivel, entradas, x, y):
        for menu in self.abiertos[nivel + 1:]:
            menu.destroy()
        del self.abiertos[nivel + 1:]
        self.abiertos.append(Desplegable(self, entradas, x, y, nivel=nivel + 1))

    def cerrar(self):
        for menu in self.abiertos:
            menu.destroy()
        self.abiertos = []

    def _ventana_movida(self, evento):
        if evento.widget is self.ventana:
            self.cerrar()

    def _clic_global(self, evento):
        if not self.abiertos:
            return
        try:
            ventana = evento.widget.winfo_toplevel()
            dentro_barra = str(evento.widget).startswith(str(self))
        except (tk.TclError, AttributeError):
            return
        if ventana not in self.abiertos and not dentro_barra:
            self.cerrar()


class Desplegable(tk.Toplevel):
    def __init__(self, barra, entradas, x, y, nivel, boton=None):
        super().__init__(barra)
        self.barra = barra
        self.nivel = nivel
        self.boton = boton
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=COLOR_BORDE)

        marco = ctk.CTkFrame(self, fg_color=COLOR_MENU, corner_radius=0)
        marco.pack(fill="both", expand=True, padx=1, pady=1)
        marco.grid_columnconfigure(0, weight=1)
        for entrada in entradas:
            if entrada is None:
                ctk.CTkFrame(marco, height=2, fg_color="#2c5f62").pack(fill="x", padx=10, pady=4)
                continue
            texto, atajo, accion = entrada
            fila = ctk.CTkFrame(marco, fg_color="transparent", corner_radius=4)
            fila.pack(fill="x", padx=4, pady=1)
            etiqueta = ctk.CTkLabel(fila, text=texto, font=FUENTE_MENU, text_color=COLOR_TEXTO, anchor="w")
            etiqueta.pack(side="left", padx=(12, 36), pady=3)
            extra = "▸" if isinstance(accion, list) else (atajo or "")
            lado = ctk.CTkLabel(fila, text=extra, font=FUENTE_MENU, text_color=COLOR_ATAJO, anchor="e")
            lado.pack(side="right", padx=(8, 12), pady=3)
            for w in (fila, etiqueta, lado):
                w.bind("<Enter>", lambda e, f=fila: f.configure(fg_color=COLOR_HOVER))
                w.bind("<Leave>", lambda e, f=fila: f.configure(fg_color="transparent"))
                w.bind("<Button-1>", lambda e, a=accion, f=fila: self.elegir(a, f))
        self.geometry(f"+{x}+{y}")

    def elegir(self, accion, fila):
        if isinstance(accion, list):
            self.barra.abrir_submenu(self.nivel, accion, self.winfo_rootx() + self.winfo_width(),
                                     fila.winfo_rooty())
            return
        self.barra.cerrar()
        self.barra.after(10, accion)


class Dialogo(ctk.CTkToplevel):
    def __init__(self, master, titulo, mensaje, botones, entrada=False):
        super().__init__(master)
        self.title(titulo)
        self.resultado = None
        self.transient(master)
        self.resizable(False, False)

        ctk.CTkLabel(self, text=mensaje, font=FUENTE_DIALOGO, justify="left",
                     wraplength=480).pack(padx=26, pady=(22, 12), anchor="w")
        self.campo = None
        if entrada:
            self.campo = ctk.CTkEntry(self, font=FUENTE_DIALOGO, width=380, height=36)
            self.campo.pack(padx=26, pady=(0, 12))
            self.campo.bind("<Return>", lambda e: self.responder(botones[0][1]))
        fila = ctk.CTkFrame(self, fg_color="transparent")
        fila.pack(padx=26, pady=(4, 20), anchor="e")
        for texto, valor in botones:
            ctk.CTkButton(fila, text=texto, font=FUENTE_DIALOGO, height=36, width=110,
                          command=lambda v=valor: self.responder(v)).pack(side="left", padx=5)
        self.bind("<Escape>", lambda e: self.responder(None))
        self.protocol("WM_DELETE_WINDOW", lambda: self.responder(None))

        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.after(150, self._enfocar)

    def _enfocar(self):
        if not self.winfo_exists():
            return
        self.lift()
        self.grab_set()
        (self.campo or self).focus_force()

    def responder(self, valor):
        if self.campo is not None and valor is True:
            valor = self.campo.get()
        self.resultado = valor
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()

    def esperar(self):
        self.wait_window()
        return self.resultado


def mostrar_info(master, titulo, mensaje):
    Dialogo(master, titulo, mensaje, [("Aceptar", True)]).esperar()


def preguntar_si_no_cancelar(master, titulo, mensaje):
    return Dialogo(master, titulo, mensaje, [("Si", True), ("No", False), ("Cancelar", None)]).esperar()


def pedir_texto(master, titulo, mensaje):
    return Dialogo(master, titulo, mensaje, [("Aceptar", True), ("Cancelar", None)], entrada=True).esperar()

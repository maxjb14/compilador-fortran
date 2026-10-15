import os
import re
import sys
import shutil
import tempfile
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from arbol import arbol_texto  # noqa: E402
from compilador import Compilador  # noqa: E402
from maquina import ErrorEjecucion  # noqa: E402

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

TEAL_BG = "#0d3b3e"
TEAL_BG_LIGHT = "#0f4448"
FONT_EDITOR = ("Consolas", 13)

PROGRAMA_INICIAL = """PROGRAM nuevo
  IMPLICIT NONE

END PROGRAM nuevo
"""

PLANTILLAS = {
    "Programa": PROGRAMA_INICIAL,
    "IF ... THEN ... ELSE": "IF (x > 0) THEN\n\nELSE\n\nEND IF\n",
    "DO con contador": "DO i = 1, 10\n\nEND DO\n",
    "DO WHILE": "DO WHILE (x > 0)\n\nEND DO\n",
    "READ": "READ *, x\n",
    "PRINT": "PRINT *, 'texto', x\n",
}

DECLARACIONES = {
    "INTEGER": "INTEGER :: n\n",
    "REAL": "REAL :: x\n",
    "DOUBLE PRECISION": "DOUBLE PRECISION :: d\n",
    "CHARACTER": "CHARACTER(len=20) :: nombre\n",
    "LOGICAL": "LOGICAL :: listo\n",
    "PARAMETER": "REAL, PARAMETER :: pi = 3.1416\n",
}

OPERADORES = "+-*/="

COLOR_RESERVADA = "#5cb8ff"

# palabras reservadas de fortran 90
PALABRAS_RESERVADAS = [
    "PROGRAM", "END", "IMPLICIT", "NONE", "INTEGER", "REAL", "DOUBLE", "PRECISION",
    "COMPLEX", "LOGICAL", "CHARACTER", "PARAMETER", "DIMENSION", "ALLOCATABLE",
    "ALLOCATE", "DEALLOCATE", "IF", "THEN", "ELSE", "ELSEIF", "ENDIF", "DO", "ENDDO",
    "WHILE", "CONTINUE", "EXIT", "CYCLE", "STOP", "GOTO", "SELECT", "CASE", "DEFAULT",
    "CALL", "SUBROUTINE", "FUNCTION", "RETURN", "RESULT", "MODULE", "USE", "CONTAINS",
    "INTENT", "IN", "OUT", "INOUT", "TYPE", "PRINT", "READ", "WRITE", "OPEN", "CLOSE",
    "FORMAT", "INCLUDE",
]
OPERADORES_PUNTO = [".TRUE.", ".FALSE.", ".AND.", ".OR.", ".NOT.", ".EQ.", ".NE.",
                    ".LT.", ".LE.", ".GT.", ".GE.", ".EQV.", ".NEQV."]
CONJUNTO_RESERVADAS = set(PALABRAS_RESERVADAS) | set(OPERADORES_PUNTO)

PATRON_RESERVADA = re.compile(
    r"(?<![A-Za-z0-9_])(?:" + "|".join(PALABRAS_RESERVADAS) + r")(?![A-Za-z0-9_])"
    r"|\.(?:" + "|".join(p.strip(".") for p in OPERADORES_PUNTO) + r")\.",
    re.IGNORECASE)

PATRON_PALABRA = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# cadenas y comentarios (! hasta fin de linea) no cuentan como palabras reservadas ni variables
PATRON_EXCLUIDO = re.compile(r'"[^"\n]*"|' + r"'[^'\n]*'|![^\n]*")


def validar_palabra(palabra, campo):
    if palabra == "":
        return f"Escribe la palabra a {campo}"
    if any(c in OPERADORES for c in palabra):
        return "Los operadores + - * / = no entran en la busqueda"
    if not PATRON_PALABRA.fullmatch(palabra):
        return "Solo se pueden buscar palabras reservadas o variables"
    return None


def tipo_palabra(palabra):
    return "palabra reservada" if palabra.upper() in CONJUNTO_RESERVADAS else "variable"


def buscar_reservadas(texto):
    excluidos = [m.span() for m in PATRON_EXCLUIDO.finditer(texto)]
    return [m for m in PATRON_RESERVADA.finditer(texto)
            if not any(ini <= m.start() < fin for ini, fin in excluidos)]


def buscar_coincidencias(texto, palabra, distinguir_mayusculas=True):
    excluidos = [m.span() for m in PATRON_EXCLUIDO.finditer(texto)]
    flags = 0 if distinguir_mayusculas else re.IGNORECASE
    patron = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(palabra)}(?![A-Za-z0-9_])", flags)
    coincidencias = []
    for m in patron.finditer(texto):
        if not any(ini <= m.start() < fin for ini, fin in excluidos):
            coincidencias.append((m.start(), m.end()))
    return coincidencias


class HistorialTemporal:
    # cada estado del editor se guarda en un archivo temporal propio
    def __init__(self, limite=200):
        self.carpeta = tempfile.mkdtemp(prefix="compilador_historial_")
        self.estados = []
        self.actual = -1
        self.limite = limite
        self.contador = 0
        self.ultimo_texto = None

    def guardar(self, texto):
        if texto == self.ultimo_texto:
            return False

        # si se escribe despues de deshacer, los estados de rehacer se descartan
        for ruta in self.estados[self.actual + 1:]:
            self._borrar(ruta)
        del self.estados[self.actual + 1:]

        self.contador += 1
        ruta = os.path.join(self.carpeta, f"estado_{self.contador:04d}.tmp")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(texto)
        self.estados.append(ruta)

        if len(self.estados) > self.limite:
            self._borrar(self.estados.pop(0))

        self.actual = len(self.estados) - 1
        self.ultimo_texto = texto
        return True

    def deshacer(self):
        if not self.puede_deshacer():
            return None
        self.actual -= 1
        return self._cargar_actual()

    def rehacer(self):
        if not self.puede_rehacer():
            return None
        self.actual += 1
        return self._cargar_actual()

    def puede_deshacer(self):
        return self.actual > 0

    def puede_rehacer(self):
        return self.actual < len(self.estados) - 1

    def reiniciar(self, texto):
        for ruta in self.estados:
            self._borrar(ruta)
        self.estados = []
        self.actual = -1
        self.ultimo_texto = None
        self.guardar(texto)

    def eliminar(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def _cargar_actual(self):
        with open(self.estados[self.actual], "r", encoding="utf-8") as f:
            self.ultimo_texto = f.read()
        return self.ultimo_texto

    def _borrar(self, ruta):
        if os.path.exists(ruta):
            os.remove(ruta)


class CompiladorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Compilador Fortran")
        self.geometry("1000x700")
        self.minsize(700, 500)

        self.archivo_actual = None
        self.texto_modificado = False

        self.historial = HistorialTemporal()
        self._id_estado = None
        self._restaurando = False

        self.ventana_buscar = None
        self._coincidencia_actual = None
        self._id_resaltado = None
        self.compilador = Compilador()

        self._crear_menu()
        self._crear_widgets()
        self._crear_atajos()

        self.editor.insert("1.0", PROGRAMA_INICIAL)
        self.editor.edit_modified(False)
        self.historial.reiniciar(PROGRAMA_INICIAL)
        self.resaltar_reservadas()
        self.protocol("WM_DELETE_WINDOW", self.cerrar_aplicacion)
        self._actualizar_titulo()

    def _crear_menu(self):
        menubar = tk.Menu(self)

        menu_archivo = tk.Menu(menubar, tearoff=0)
        menu_archivo.add_command(label="Abrir", accelerator="Ctrl+A", command=self.abrir_archivo)
        menu_archivo.add_command(label="Guardar", accelerator="Ctrl+G", command=self.guardar_archivo)
        menu_archivo.add_command(label="Guardar como...", command=self.guardar_como)
        menu_archivo.add_separator()
        menu_archivo.add_command(label="Limpiar pantalla", accelerator="Ctrl+P", command=self.limpiar_pantalla)
        menu_archivo.add_separator()
        menu_archivo.add_command(label="Cerrar", accelerator="Ctrl+Q", command=self.cerrar_aplicacion)
        menubar.add_cascade(label="Archivo", menu=menu_archivo)

        menu_editar = tk.Menu(menubar, tearoff=0)
        menu_editar.add_command(label="Deshacer", accelerator="Ctrl+Z", command=self.deshacer)
        menu_editar.add_command(label="Hacer", accelerator="Ctrl+Y", command=self.rehacer)
        menu_editar.add_command(label="Ver historial temporal", command=self.mostrar_historial)
        menu_editar.add_separator()
        menu_editar.add_command(label="Buscar y reemplazar", accelerator="Ctrl+F", command=self.abrir_buscar)
        menu_editar.add_separator()
        menu_editar.add_command(label="Cortar", accelerator="Ctrl+X",
                                 command=lambda: self._editar_evento("<<Cut>>"))
        menu_editar.add_command(label="Copiar", accelerator="Ctrl+C",
                                 command=lambda: self._editar_evento("<<Copy>>"))
        menu_editar.add_command(label="Pegar", accelerator="Ctrl+V",
                                 command=lambda: self._editar_evento("<<Paste>>"))
        menu_editar.add_separator()
        menu_editar.add_command(label="Seleccionar todo", accelerator="Ctrl+E", command=self.seleccionar_todo)
        menubar.add_cascade(label="Editar", menu=menu_editar)

        menu_ejecutar = tk.Menu(menubar, tearoff=0)
        menu_ejecutar.add_command(label="Compilar", accelerator="F9", command=self.compilar_todo)
        menu_ejecutar.add_command(label="Ejecutar", accelerator="F5", command=self.ejecutar)
        menubar.add_cascade(label="Ejecutar", menu=menu_ejecutar)

        menu_compiladores = tk.Menu(menubar, tearoff=0)
        menu_compiladores.add_command(label="Analisis Lexico", accelerator="Alt+L", command=self.fase_lexica)
        menu_compiladores.add_command(label="Analisis Sintactico", accelerator="Alt+S",
                                       command=self.fase_sintactica)
        menu_compiladores.add_command(label="Analisis Semantico", accelerator="Alt+M",
                                       command=self.fase_semantica)
        menu_compiladores.add_command(label="Generacion Codigo Intermedio", accelerator="Alt+G",
                                       command=self.fase_codigo)
        menu_compiladores.add_command(label="Codigo Objeto", accelerator="Alt+O", command=self.codigo_objeto)
        menu_compiladores.add_separator()
        menu_compiladores.add_command(label="Checklist palabras reservadas", accelerator="Ctrl+R",
                                       command=self.checklist_reservadas)
        menubar.add_cascade(label="Compiladores", menu=menu_compiladores)

        menu_ayuda = tk.Menu(menubar, tearoff=0)
        menu_plantillas = tk.Menu(menu_ayuda, tearoff=0)
        for nombre in PLANTILLAS:
            menu_plantillas.add_command(label=nombre, command=lambda n=nombre: self.insertar_plantilla(n))
        menu_ayuda.add_cascade(label="Plantillas", menu=menu_plantillas)
        menu_ejemplos = tk.Menu(menu_ayuda, tearoff=0)
        for nombre in self.ejemplos():
            menu_ejemplos.add_command(label=nombre, command=lambda n=nombre: self.abrir_ejemplo(n))
        menu_ayuda.add_cascade(label="Ejemplos", menu=menu_ejemplos)
        menu_ayuda.add_separator()
        menu_ayuda.add_command(label="Acerca de", command=self.acerca_de)
        menubar.add_cascade(label="Ayuda", menu=menu_ayuda)

        menu_variables = tk.Menu(menubar, tearoff=0)
        menu_tipos = tk.Menu(menu_variables, tearoff=0)
        for tipo in DECLARACIONES:
            menu_tipos.add_command(label=tipo, command=lambda t=tipo: self.insertar_declaracion(t))
        menu_variables.add_cascade(label="Tipos", menu=menu_tipos)
        menubar.add_cascade(label="Variables", menu=menu_variables)

        self.config(menu=menubar)

    def _crear_widgets(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=10, pady=10)
        contenedor.grid_rowconfigure(0, weight=3)
        contenedor.grid_rowconfigure(1, weight=1)
        contenedor.grid_columnconfigure(0, weight=1)

        # el deshacer interno de tk se apaga, el historial va en archivos temporales
        self.editor = ctk.CTkTextbox(
            contenedor,
            fg_color=TEAL_BG,
            text_color="#d9f2f0",
            font=FONT_EDITOR,
            corner_radius=6,
            undo=False,
            wrap="none",
        )
        self.editor.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        self.editor.bind("<<Modified>>", self._on_texto_modificado)
        self.editor.tag_config("coincidencia", background="#3f6f2a")
        self.editor.tag_config("coincidencia_actual", background="#d9a520", foreground="#1b1b1b")

        self.fuente_reservada = tkfont.Font(font=self.editor._textbox.cget("font"))
        self.fuente_reservada.configure(weight="bold")
        for palabra in CONJUNTO_RESERVADAS:
            self.editor._textbox.tag_config(palabra, foreground=COLOR_RESERVADA, font=self.fuente_reservada)
        self.editor._textbox.tag_config("linea_error", background="#7a2230")
        self.editor._textbox.tag_raise("coincidencia")
        self.editor._textbox.tag_raise("coincidencia_actual")

        consola_frame = ctk.CTkFrame(contenedor, fg_color="transparent")
        consola_frame.grid(row=1, column=0, sticky="nsew")
        consola_frame.grid_rowconfigure(1, weight=1)
        consola_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(consola_frame, text="Consola", anchor="w",
                     text_color="#9fd8d4").grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.consola = ctk.CTkTextbox(
            consola_frame,
            fg_color=TEAL_BG_LIGHT,
            text_color="#9fd8d4",
            font=FONT_EDITOR,
            corner_radius=6,
            state="disabled",
        )
        self.consola.grid(row=1, column=0, sticky="nsew")

        self.status_var = tk.StringVar(value="Listo")
        status_bar = ctk.CTkLabel(self, textvariable=self.status_var, anchor="w",
                                   height=24, fg_color="#062223", text_color="#7fb8b4")
        status_bar.pack(fill="x", side="bottom")

    def _crear_atajos(self):
        self.bind_all("<Control-a>", lambda e: self.abrir_archivo())
        self.bind_all("<Control-A>", lambda e: self.abrir_archivo())
        self.bind_all("<Control-g>", lambda e: self.guardar_archivo())
        self.bind_all("<Control-G>", lambda e: self.guardar_archivo())
        self.bind_all("<Control-p>", lambda e: self.limpiar_pantalla())
        self.bind_all("<Control-P>", lambda e: self.limpiar_pantalla())
        self.bind_all("<Control-q>", lambda e: self.cerrar_aplicacion())
        self.bind_all("<Control-Q>", lambda e: self.cerrar_aplicacion())
        self.bind_all("<Control-e>", lambda e: self.seleccionar_todo())
        self.bind_all("<Control-E>", lambda e: self.seleccionar_todo())
        self.bind_all("<F5>", lambda e: self.ejecutar())
        self.bind_all("<F9>", lambda e: self.compilar_todo())
        self.bind_all("<Alt-l>", lambda e: self.fase_lexica())
        self.bind_all("<Alt-s>", lambda e: self.fase_sintactica())
        self.bind_all("<Alt-m>", lambda e: self.fase_semantica())
        self.bind_all("<Alt-g>", lambda e: self.fase_codigo())
        self.bind_all("<Alt-o>", lambda e: self.codigo_objeto())

        # "break" evita que el editor aplique sus atajos por defecto
        for tecla in ("<Control-z>", "<Control-Z>"):
            self.editor.bind(tecla, lambda e: (self.deshacer(), "break")[1])
        for tecla in ("<Control-y>", "<Control-Y>"):
            self.editor.bind(tecla, lambda e: (self.rehacer(), "break")[1])
        for tecla in ("<Control-r>", "<Control-R>"):
            self.bind_all(tecla, lambda e: self.checklist_reservadas())
        for tecla in ("<Control-f>", "<Control-F>", "<Control-h>", "<Control-H>"):
            self.bind_all(tecla, lambda e: self.abrir_buscar())
            self.editor.bind(tecla, lambda e: (self.abrir_buscar(), "break")[1])

    def abrir_archivo(self):
        if not self._confirmar_descartar_cambios():
            return

        ruta = filedialog.askopenfilename(
            title="Abrir archivo",
            filetypes=[("Archivos Fortran", "*.f90 *.f *.for"), ("Archivos de texto", "*.txt"),
                       ("Todos los archivos", "*.*")],
        )
        if not ruta:
            return

        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
        except Exception as e:
            messagebox.showerror("Error al abrir", f"No se pudo abrir el archivo:\n{e}")
            return

        self._restaurando = True
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", contenido)
        self.editor.edit_modified(False)
        self._restaurando = False
        self.historial.reiniciar(contenido)
        self.archivo_actual = ruta
        self.texto_modificado = False
        self._actualizar_titulo()
        self._log(f"Archivo abierto: {ruta}")

    def guardar_archivo(self):
        if self.archivo_actual is None:
            return self.guardar_como()

        try:
            with open(self.archivo_actual, "w", encoding="utf-8") as f:
                f.write(self.editor.get("1.0", "end-1c"))
        except Exception as e:
            messagebox.showerror("Error al guardar", f"No se pudo guardar el archivo:\n{e}")
            return False

        self.texto_modificado = False
        self.editor.edit_modified(False)
        self._actualizar_titulo()
        self._log(f"Archivo guardado: {self.archivo_actual}")
        return True

    def guardar_como(self):
        ruta = filedialog.asksaveasfilename(
            title="Guardar como",
            defaultextension=".f90",
            filetypes=[("Archivos Fortran", "*.f90"), ("Archivos de texto", "*.txt"),
                       ("Todos los archivos", "*.*")],
        )
        if not ruta:
            return False

        self.archivo_actual = ruta
        return self.guardar_archivo()

    def limpiar_pantalla(self):
        if not self._confirmar_descartar_cambios(accion="limpiar la pantalla"):
            return

        self._restaurando = True
        self.editor.delete("1.0", "end")
        self.editor.edit_modified(False)
        self._restaurando = False
        self.historial.reiniciar("")
        self.consola.configure(state="normal")
        self.consola.delete("1.0", "end")
        self.consola.configure(state="disabled")
        self.archivo_actual = None
        self.texto_modificado = False
        self._actualizar_titulo()
        self.status_var.set("Pantalla limpiada")

    def cerrar_aplicacion(self):
        if not self._confirmar_descartar_cambios(accion="cerrar la aplicación"):
            return
        self.historial.eliminar()
        self.destroy()

    def _confirmar_descartar_cambios(self, accion="continuar"):
        if not self.texto_modificado:
            return True

        respuesta = messagebox.askyesnocancel(
            "Cambios sin guardar",
            f"Hay cambios sin guardar. ¿Desea guardarlos antes de {accion}?",
        )
        if respuesta is None:
            return False
        if respuesta:
            return self.guardar_archivo()
        return True

    def _on_texto_modificado(self, event=None):
        if self.editor.edit_modified():
            self.texto_modificado = True
            self._actualizar_titulo()
            self.editor.edit_modified(False)
            self.editor.tag_remove("linea_error", "1.0", "end")
            self._programar_resaltado()
            if not self._restaurando:
                self._programar_estado()

    def _actualizar_titulo(self):
        nombre = os.path.basename(self.archivo_actual) if self.archivo_actual else "Sin título"
        marca = " *" if self.texto_modificado else ""
        self.title(f"Compilador Fortran - {nombre}{marca}")

    def _programar_estado(self):
        # se espera a que el usuario deje de escribir para guardar un solo estado
        if self._id_estado is not None:
            self.after_cancel(self._id_estado)
        self._id_estado = self.after(400, self._guardar_estado)

    def _guardar_estado(self):
        self._id_estado = None
        if self.historial.guardar(self.editor.get("1.0", "end-1c")):
            total = len(self.historial.estados)
            self.status_var.set(f"Estado {total} guardado en archivo temporal")

    def _pendiente_a_historial(self):
        if self._id_estado is not None:
            self.after_cancel(self._id_estado)
            self._guardar_estado()

    def deshacer(self):
        self._pendiente_a_historial()
        texto = self.historial.deshacer()
        if texto is None:
            self.status_var.set("No hay nada que deshacer")
            return
        self._restaurar(texto)
        self._log(f"Deshacer: estado {self.historial.actual + 1} de {len(self.historial.estados)}")

    def rehacer(self):
        self._pendiente_a_historial()
        texto = self.historial.rehacer()
        if texto is None:
            self.status_var.set("No hay nada que hacer de nuevo")
            return
        self._restaurar(texto)
        self._log(f"Hacer: estado {self.historial.actual + 1} de {len(self.historial.estados)}")

    def _restaurar(self, texto):
        cursor = self.editor.index("insert")
        self._restaurando = True
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", texto)
        self.editor.edit_modified(False)
        self._restaurando = False
        self.editor.mark_set("insert", cursor)
        self.editor.see("insert")
        self.texto_modificado = True
        self._actualizar_titulo()
        self.resaltar_reservadas()

    def _programar_resaltado(self):
        if self._id_resaltado is not None:
            self.after_cancel(self._id_resaltado)
        self._id_resaltado = self.after(150, self.resaltar_reservadas)

    def resaltar_reservadas(self):
        self._id_resaltado = None
        texto = self.editor.get("1.0", "end-1c")
        for palabra in CONJUNTO_RESERVADAS:
            self.editor.tag_remove(palabra, "1.0", "end")
        for match in buscar_reservadas(texto):
            palabra = match.group(0).upper()
            inicio_index = f"1.0 + {match.start()} chars"
            fin_index = f"1.0 + {match.end()} chars"
            self.editor.tag_add(palabra, inicio_index, fin_index)

    def checklist_reservadas(self):
        texto = self.editor.get("1.0", "end-1c")
        conteo = {}
        for match in buscar_reservadas(texto):
            palabra = match.group(0).upper()
            conteo[palabra] = conteo.get(palabra, 0) + 1
        lista = PALABRAS_RESERVADAS + OPERADORES_PUNTO
        encontradas = [p for p in lista if p in conteo]
        self._log(f"Checklist de palabras reservadas: {len(encontradas)} de {len(lista)} encontradas")
        for palabra in encontradas:
            self._log(f"  [x] {palabra}  ({conteo[palabra]})")
        faltantes = [p for p in lista if p not in conteo]
        self._log("  [ ] " + ", ".join(faltantes))

    def mostrar_historial(self):
        self._pendiente_a_historial()
        self._log(f"Historial temporal: {self.historial.carpeta}")
        for i, ruta in enumerate(self.historial.estados):
            marca = "  <- actual" if i == self.historial.actual else ""
            tam = os.path.getsize(ruta)
            self._log(f"  {os.path.basename(ruta)}  ({tam} bytes){marca}")

    def abrir_buscar(self):
        if self.ventana_buscar is not None and self.ventana_buscar.winfo_exists():
            self.ventana_buscar.focus()
            return
        self.ventana_buscar = VentanaBuscar(self)

    def _indice(self, posicion):
        return f"1.0+{posicion}c"

    def _linea(self, posicion):
        return self.editor.index(self._indice(posicion)).split(".")[0]

    def _coincidencias(self, palabra):
        texto = self.editor.get("1.0", "end-1c")
        return buscar_coincidencias(texto, palabra, self.ventana_buscar.var_mayus.get())

    def _leer_palabras(self, con_reemplazo):
        v = self.ventana_buscar
        palabra = v.var_buscar.get().strip()
        error = validar_palabra(palabra, "buscar")
        reemplazo = None
        if error is None and con_reemplazo:
            reemplazo = v.var_reemplazar.get().strip()
            error = validar_palabra(reemplazo, "reemplazar")
            if error is None and tipo_palabra(palabra) == "variable" and reemplazo.upper() in CONJUNTO_RESERVADAS:
                error = "Una variable no se puede reemplazar por una palabra reservada"
        if error:
            v.mensaje(error)
            self.status_var.set(error)
            return None, None
        return palabra, reemplazo

    def resaltar(self, coincidencias, actual=None):
        self.limpiar_resaltado()
        for ini, fin in coincidencias:
            self.editor.tag_add("coincidencia", self._indice(ini), self._indice(fin))
        if actual is not None:
            self.editor.tag_add("coincidencia_actual", self._indice(actual[0]), self._indice(actual[1]))

    def limpiar_resaltado(self):
        self.editor.tag_remove("coincidencia", "1.0", "end")
        self.editor.tag_remove("coincidencia_actual", "1.0", "end")

    def buscar_siguiente(self):
        palabra, _ = self._leer_palabras(con_reemplazo=False)
        if palabra is None:
            return None

        tipo = tipo_palabra(palabra)
        coincidencias = self._coincidencias(palabra)
        if not coincidencias:
            self.limpiar_resaltado()
            self._coincidencia_actual = None
            self.ventana_buscar.mensaje(f"'{palabra}' ({tipo}) no se encontro")
            self._log(f"Buscar '{palabra}' ({tipo}): sin coincidencias")
            return None

        cursor = len(self.editor.get("1.0", "insert"))
        if self._coincidencia_actual in coincidencias:
            cursor = self._coincidencia_actual[1]
        siguiente = next((c for c in coincidencias if c[0] >= cursor), coincidencias[0])

        self.resaltar(coincidencias, siguiente)
        self._coincidencia_actual = siguiente
        self.editor.mark_set("insert", self._indice(siguiente[1]))
        self.editor.see(self._indice(siguiente[0]))

        n = coincidencias.index(siguiente) + 1
        self.ventana_buscar.mensaje(f"{tipo}: coincidencia {n} de {len(coincidencias)}")
        self._log(f"Buscar '{palabra}' ({tipo}): {len(coincidencias)} coincidencias, "
                  f"actual en linea {self._linea(siguiente[0])}")
        return siguiente

    def reemplazar(self):
        palabra, reemplazo = self._leer_palabras(con_reemplazo=True)
        if palabra is None:
            return

        coincidencias = self._coincidencias(palabra)
        # el primer clic solo ubica la coincidencia, el segundo la reemplaza
        if self._coincidencia_actual not in coincidencias:
            self.buscar_siguiente()
            return

        ini, fin = self._coincidencia_actual
        linea = self._linea(ini)
        self._pendiente_a_historial()
        self.editor.delete(self._indice(ini), self._indice(fin))
        self.editor.insert(self._indice(ini), reemplazo)
        self._guardar_estado()

        self._coincidencia_actual = None
        self.editor.mark_set("insert", self._indice(ini + len(reemplazo)))
        self._log(f"Reemplazo en linea {linea}: '{palabra}' -> '{reemplazo}'")
        if self.buscar_siguiente() is None:
            self.ventana_buscar.mensaje(f"Ya no quedan coincidencias de '{palabra}'")

    def reemplazar_todo(self):
        palabra, reemplazo = self._leer_palabras(con_reemplazo=True)
        if palabra is None:
            return

        coincidencias = self._coincidencias(palabra)
        if not coincidencias:
            self.ventana_buscar.mensaje(f"'{palabra}' no se encontro")
            return

        self._pendiente_a_historial()
        # de atras hacia adelante para no mover las posiciones pendientes
        for ini, fin in reversed(coincidencias):
            self.editor.delete(self._indice(ini), self._indice(fin))
            self.editor.insert(self._indice(ini), reemplazo)
        self._guardar_estado()

        self.limpiar_resaltado()
        self._coincidencia_actual = None
        mensaje = f"{len(coincidencias)} reemplazos: '{palabra}' -> '{reemplazo}'"
        self.ventana_buscar.mensaje(mensaje)
        self._log(f"Reemplazar todo ({tipo_palabra(palabra)}): {mensaje}")

    def _editar_evento(self, evento):
        try:
            self.editor.event_generate(evento)
        except tk.TclError:
            pass

    def seleccionar_todo(self):
        self.editor.tag_add("sel", "1.0", "end")
        return "break"

    def insertar_plantilla(self, nombre):
        self.editor.insert("insert", PLANTILLAS[nombre])
        self._log(f"Plantilla insertada: {nombre}")

    def insertar_declaracion(self, tipo):
        self.editor.insert("insert", "  " + DECLARACIONES[tipo])
        self._log(f"Declaracion {tipo} insertada")

    def ejemplos(self):
        carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ejemplos")
        if not os.path.isdir(carpeta):
            return []
        return sorted(f for f in os.listdir(carpeta) if f.endswith(".f90"))

    def abrir_ejemplo(self, nombre):
        if not self._confirmar_descartar_cambios():
            return
        ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ejemplos", nombre)
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read()
        self._restaurando = True
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", contenido)
        self.editor.edit_modified(False)
        self._restaurando = False
        self.historial.reiniciar(contenido)
        self.resaltar_reservadas()
        self.archivo_actual = ruta
        self.texto_modificado = False
        self._actualizar_titulo()
        self._log(f"Ejemplo abierto: {nombre}")

    def acerca_de(self):
        messagebox.showinfo(
            "Acerca de",
            "Compilador Fortran\nSubconjunto de Fortran 90\n"
            "Lexico, sintactico, semantico, codigo intermedio y ejecucion.\n"
            "Interfaz construida con CustomTkinter.",
        )

    # fases del compilador

    def compilar(self):
        resultado = self.compilador.compilar(self.editor.get("1.0", "end-1c"))
        self.editor.tag_remove("linea_error", "1.0", "end")
        for error in resultado.errores:
            partes = error.split()
            if len(partes) > 1 and partes[0] == "LINEA" and partes[1].isdigit():
                linea = int(partes[1])
                self.editor.tag_add("linea_error", f"{linea}.0", f"{linea}.end+1c")
        return resultado

    def limpia_consola(self, titulo):
        self.consola.configure(state="normal")
        self.consola.delete("1.0", "end")
        self.consola.configure(state="disabled")
        self._log(f"== {titulo} ==")

    def muestra_errores(self, resultado, desde):
        orden = ["lexico", "sintactico", "semantico"]
        if resultado.advertencias and orden.index(desde) >= 2:
            self._log("")
            for a in resultado.advertencias:
                self._log(a)
        if resultado.exito or orden.index(resultado.etapa) > orden.index(desde):
            return False
        self._log("")
        for e in resultado.errores:
            self._log(e)
        self.status_var.set(f"{len(resultado.errores)} error(es) en el analisis {resultado.etapa}")
        return True

    def fase_lexica(self):
        r = self.compilar()
        self.limpia_consola("ANALISIS LEXICO")
        self._log(f"{'linea':>5}  {'lexema':<22}token")
        for fila in r.lexico.tabla():
            self._log(fila)
        if not self.muestra_errores(r, "lexico"):
            self.status_var.set(f"Analisis lexico correcto: {len(r.lexico.tabla())} tokens")

    def fase_sintactica(self):
        r = self.compilar()
        self.limpia_consola("ANALISIS SINTACTICO")
        if r.etapa == "lexico":
            self.muestra_errores(r, "lexico")
            return
        for linea in r.traza:
            self._log(linea)
        if self.muestra_errores(r, "sintactico"):
            return
        self._log("")
        self._log("== ARBOL SINTACTICO ==")
        for linea in arbol_texto(r.programa):
            self._log(linea)
        self.status_var.set("Analisis sintactico correcto")

    def fase_semantica(self):
        r = self.compilar()
        self.limpia_consola("ANALISIS SEMANTICO")
        if r.etapa in ("lexico", "sintactico"):
            self.muestra_errores(r, r.etapa)
            return
        self._log("Tabla de simbolos:")
        for fila in r.semantico.tabla.tabla():
            self._log("  " + fila)
        if not self.muestra_errores(r, "semantico"):
            self.status_var.set("Analisis semantico correcto")

    def fase_codigo(self):
        r = self.compilar()
        self.limpia_consola("GENERACION DE CODIGO INTERMEDIO")
        if not r.exito:
            self.muestra_errores(r, r.etapa)
            return
        for linea in r.codigo().splitlines():
            self._log(linea)
        self.status_var.set(f"Codigo generado: {len(r.generador.codigo)} instrucciones")

    def codigo_objeto(self):
        r = self.compilar()
        self.limpia_consola("CODIGO OBJETO")
        if not r.exito:
            self.muestra_errores(r, r.etapa)
            return
        if self.archivo_actual:
            ruta = os.path.splitext(self.archivo_actual)[0] + ".obj"
        else:
            ruta = filedialog.asksaveasfilename(title="Guardar codigo objeto", defaultextension=".obj",
                                                filetypes=[("Codigo objeto", "*.obj")])
            if not ruta:
                return
        r.generador.guardar(ruta)
        self._log(f"Codigo objeto guardado en {ruta}")
        self._log(f"{len(r.generador.datos)} variables, {len(r.generador.codigo)} instrucciones")

    def compilar_todo(self):
        r = self.compilar()
        self.limpia_consola("COMPILACION")
        if r.exito:
            for a in r.advertencias:
                self._log(a)
            self._log("COMPILACION EXITOSA")
        else:
            self._log(f"COMPILACION FALLIDA en el analisis {r.etapa}")
            for e in r.errores:
                self._log(e)
        return r

    def ejecutar(self):
        r = self.compilar_todo()
        if not r.exito:
            return
        self._log("")
        self._log("== EJECUCION ==")

        def entrada(texto):
            valor = simpledialog.askstring("READ", f"Valor para {texto.split('=')[0].strip()}:", parent=self)
            if valor is None:
                raise ErrorEjecucion("EJECUCION CANCELADA")
            self._log(f"> {valor}")
            return valor

        try:
            self.compilador.ejecutar(r, entrada=entrada, salida=self._log)
            self._log("== FIN DE LA EJECUCION ==")
        except ErrorEjecucion as e:
            self._log(str(e))

    def _log(self, mensaje):
        self.consola.configure(state="normal")
        self.consola.insert("end", mensaje + "\n")
        self.consola.see("end")
        self.consola.configure(state="disabled")
        self.status_var.set(mensaje)


class VentanaBuscar(ctk.CTkToplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Buscar y reemplazar")
        self.geometry("460x220")
        self.resizable(False, False)
        self.transient(app)

        self.var_buscar = tk.StringVar()
        self.var_reemplazar = tk.StringVar()
        self.var_mayus = tk.BooleanVar(value=True)

        self.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self, text="Buscar:").grid(row=0, column=0, sticky="w", padx=12, pady=(14, 4))
        self.entry_buscar = ctk.CTkEntry(self, textvariable=self.var_buscar)
        self.entry_buscar.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(0, 12), pady=(14, 4))

        ctk.CTkLabel(self, text="Reemplazar con:").grid(row=1, column=0, sticky="w", padx=12, pady=4)
        self.entry_reemplazar = ctk.CTkEntry(self, textvariable=self.var_reemplazar)
        self.entry_reemplazar.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(0, 12), pady=4)

        ctk.CTkCheckBox(self, text="Distinguir mayusculas y minusculas",
                        variable=self.var_mayus).grid(row=2, column=0, columnspan=3,
                                                      sticky="w", padx=12, pady=6)

        botones = ctk.CTkFrame(self, fg_color="transparent")
        botones.grid(row=3, column=0, columnspan=3, sticky="ew", padx=12, pady=4)
        ctk.CTkButton(botones, text="Buscar siguiente", width=130,
                      command=app.buscar_siguiente).pack(side="left", padx=(0, 6))
        ctk.CTkButton(botones, text="Reemplazar", width=130,
                      command=app.reemplazar).pack(side="left", padx=6)
        ctk.CTkButton(botones, text="Reemplazar todo", width=130,
                      command=app.reemplazar_todo).pack(side="left", padx=(6, 0))

        self.label_resultado = ctk.CTkLabel(self, text="", anchor="w", text_color="#9fd8d4")
        self.label_resultado.grid(row=4, column=0, columnspan=3, sticky="ew", padx=12, pady=(4, 10))

        self.bind("<Return>", lambda e: app.buscar_siguiente())
        self.bind("<Escape>", lambda e: self.cerrar())
        self.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.after(150, self.entry_buscar.focus_set)

    def mensaje(self, texto):
        self.label_resultado.configure(text=texto)

    def cerrar(self):
        self.app.limpiar_resaltado()
        self.app.ventana_buscar = None
        self.destroy()


if __name__ == "__main__":
    app = CompiladorApp()
    app.mainloop()

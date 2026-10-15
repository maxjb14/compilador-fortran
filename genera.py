from arbol import (Asignacion, Binaria, Ciclar, Constructor, Elemento, Escribir, Funcion, Hacer,
                   Leer, Literal, Mientras, Parar, Salir, Si, Unaria, Variable)

OPERADORES = {
    "+": "ADD", "*": "MUL", "**": "POW", "//": "CONCAT",
    "==": "EQ", "/=": "NE", "<": "LT", "<=": "LE", ">": "GT", ">=": "GE",
    ".AND.": "AND", ".OR.": "OR", ".EQV.": "EQV", ".NEQV.": "NEQV",
}


class GeneraCodigo:
    def __init__(self, objeto=None, traza=0):
        self.objeto = objeto
        self.traza = traza
        self.datos = []
        self.codigo = []
        self.etiquetas = 0
        self.temporales = 0
        self.ciclos = []

    # instrucciones (mismos nombres que la clase GeneraCodigo vista en clase)

    def emite(self, instruccion):
        self.codigo.append(instruccion)
        if self.traza:
            print(instruccion)

    def code(self):
        self.emite(".CODE")

    def pushc(self, constante):
        self.emite(f"PUSHC {constante}")

    def pusha(self, direccion):
        self.emite(f"PUSHA {direccion}")

    def load(self):
        self.emite("LOAD")

    def store(self):
        self.emite("STORE")

    def neg(self):
        self.emite("NEG")

    def add(self):
        self.emite("ADD")

    def mul(self):
        self.emite("MUL")

    def div(self):
        self.emite("DIV")

    def mod(self):
        self.emite("CALL mod 2")

    def input(self, direccion):
        self.emite(f"INPUT {direccion}")

    def output(self):
        self.emite("OUTPUT")

    def end(self):
        self.emite("END")

    def label(self, etiqueta):
        self.emite(f"LABEL {etiqueta}")

    def jmp(self, etiqueta):
        self.emite(f"JMP {etiqueta}")

    def jmpf(self, etiqueta):
        self.emite(f"JMPF {etiqueta}")

    # utilidades

    def nueva_etiqueta(self):
        self.etiquetas += 1
        return f"L{self.etiquetas}"

    def temporal(self, tipo):
        self.temporales += 1
        nombre = f"_t{self.temporales}"
        self.datos.append(f"VAR {nombre} {tipo.upper().replace(' ', '_')}")
        return nombre

    def texto(self):
        return "\n".join([".DATA"] + self.datos + self.codigo) + "\n"

    def guardar(self, ruta=None):
        ruta = ruta or self.objeto
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(self.texto())
        return ruta

    # recorrido del arbol

    def generar(self, programa, tabla):
        for s in tabla.variables():
            tipo = s.tipo.upper().replace(" ", "_")
            extra = f" {s.longitud}" if s.tipo == "character" else ""
            if s.dimension is not None:
                inferior, superior = s.dimension
                self.datos.append(f"ARRAY {s.nombre.lower()} {tipo} {inferior} {superior}{extra}")
            else:
                self.datos.append(f"VAR {s.nombre.lower()} {tipo}{extra}")
        self.tabla = tabla
        self.code()
        for d in programa.declaraciones:
            for nombre, valor, _ in d.variables:
                if valor is not None:
                    self.asigna(nombre, valor)
        self.bloque(programa.sentencias)
        self.end()
        return self.codigo

    def tipo_de(self, nombre):
        return self.tabla.buscar(nombre).tipo

    def asigna(self, nombre, expresion, indice=None):
        self.direccion(nombre, indice)
        self.expresion(expresion)
        # en un arreglo completo la conversion la hace store elemento por elemento
        if getattr(expresion, "tamano", None) is None:
            self.convierte(expresion.tipo, self.tipo_de(nombre))
        self.store()

    def direccion(self, nombre, indice=None):
        # direccion de una variable o de un elemento de arreglo
        self.pusha(nombre.lower())
        if indice is not None:
            self.expresion(indice)
            self.emite("INDEX")

    def convierte(self, origen, destino):
        if destino == "integer" and origen in ("real", "double precision"):
            self.emite("CVTI")
        elif destino in ("real", "double precision") and origen == "integer":
            self.emite("CVTR")

    def bloque(self, sentencias):
        for s in sentencias:
            self.sentencia(s)

    def sentencia(self, s):
        if isinstance(s, Asignacion):
            self.asigna(s.variable, s.expresion, s.indice)
        elif isinstance(s, Leer):
            for nombre, indice in zip(s.variables, s.indices):
                if indice is None:
                    self.input(nombre.lower())
                else:
                    self.direccion(nombre, indice)
                    self.emite("INPUT")
        elif isinstance(s, Escribir):
            for e in s.elementos:
                self.expresion(e)
                self.output()
            self.emite("NEWLINE")
        elif isinstance(s, Si):
            self.condicional(s)
        elif isinstance(s, Hacer):
            self.ciclo_do(s)
        elif isinstance(s, Mientras):
            self.ciclo_while(s)
        elif isinstance(s, Salir):
            self.jmp(self.ciclos[-1][1])
        elif isinstance(s, Ciclar):
            self.jmp(self.ciclos[-1][0])
        elif isinstance(s, Parar):
            self.emite("HALT")

    def condicional(self, s):
        fin = self.nueva_etiqueta()
        for condicion, cuerpo in s.ramas:
            siguiente = self.nueva_etiqueta()
            self.expresion(condicion)
            self.jmpf(siguiente)
            self.bloque(cuerpo)
            self.jmp(fin)
            self.label(siguiente)
        if s.sino is not None:
            self.bloque(s.sino)
        self.label(fin)

    def ciclo_do(self, s):
        # como en fortran, las vueltas se calculan una sola vez:
        # vueltas = max(0, (fin - inicio + paso) / paso)
        var = s.variable.lower()
        paso = self.temporal("integer")
        vueltas = self.temporal("integer")
        inicio, continua, salida = self.nueva_etiqueta(), self.nueva_etiqueta(), self.nueva_etiqueta()

        self.asigna(var, s.inicio)
        self.pusha(paso)
        if s.paso is None:
            self.pushc(1)
        else:
            self.expresion(s.paso)
            self.convierte(s.paso.tipo, "integer")
        self.store()

        self.pusha(vueltas)
        self.expresion(s.fin)
        self.convierte(s.fin.tipo, "integer")
        self.pusha(var)
        self.load()
        self.neg()
        self.add()
        self.pusha(paso)
        self.load()
        self.add()
        self.pusha(paso)
        self.load()
        self.emite("IDIV")
        self.store()

        self.label(inicio)
        self.pusha(vueltas)
        self.load()
        self.pushc(0)
        self.emite("GT")
        self.jmpf(salida)
        self.ciclos.append((continua, salida))
        self.bloque(s.cuerpo)
        self.ciclos.pop()
        self.label(continua)
        self.pusha(var)
        self.pusha(var)
        self.load()
        self.pusha(paso)
        self.load()
        self.add()
        self.store()
        self.pusha(vueltas)
        self.pusha(vueltas)
        self.load()
        self.pushc(1)
        self.neg()
        self.add()
        self.store()
        self.jmp(inicio)
        self.label(salida)

    def ciclo_while(self, s):
        inicio, salida = self.nueva_etiqueta(), self.nueva_etiqueta()
        self.label(inicio)
        self.expresion(s.condicion)
        self.jmpf(salida)
        self.ciclos.append((inicio, salida))
        self.bloque(s.cuerpo)
        self.ciclos.pop()
        self.jmp(inicio)
        self.label(salida)

    def expresion(self, nodo):
        if isinstance(nodo, Literal):
            if nodo.tipo == "character":
                self.pushc("'" + nodo.valor.replace("'", "''") + "'")
            elif nodo.tipo == "logical":
                self.pushc(".TRUE." if nodo.valor else ".FALSE.")
            else:
                self.pushc(nodo.valor)
        elif isinstance(nodo, Variable):
            self.pusha(nodo.nombre.lower())
            self.load()
        elif isinstance(nodo, Elemento):
            self.direccion(nodo.nombre, nodo.indice)
            self.load()
        elif isinstance(nodo, Constructor):
            for e in nodo.elementos:
                self.expresion(e)
            self.emite(f"PACK {len(nodo.elementos)}")
        elif isinstance(nodo, Unaria):
            self.expresion(nodo.expresion)
            self.emite("NOT" if nodo.operador == ".NOT." else "NEG")
        elif isinstance(nodo, Binaria):
            self.expresion(nodo.izquierda)
            self.expresion(nodo.derecha)
            if nodo.operador == "-":
                self.neg()
                self.add()
            elif nodo.operador == "/":
                enteros = nodo.izquierda.tipo == "integer" and nodo.derecha.tipo == "integer"
                self.emite("IDIV" if enteros else "DIV")
            else:
                self.emite(OPERADORES[nodo.operador])
        elif isinstance(nodo, Funcion):
            for a in nodo.argumentos:
                self.expresion(a)
            self.emite(f"CALL {nodo.nombre} {len(nodo.argumentos)}")

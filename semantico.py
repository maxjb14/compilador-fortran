from arbol import (Asignacion, Binaria, Ciclar, Escribir, Funcion, Hacer, Leer, Literal,
                   Mientras, Parar, Salir, Si, Unaria, Variable)
from simbolos import TablaSimbolos

ERRORES_SEMANTICOS = {
    1: "AMBIGUEDAD, LA VARIABLE YA TIENE OTRO TIPO",
    2: "VARIABLE YA DECLARADA",
    3: "VARIABLE NO DECLARADA",
    4: "TIPOS INCOMPATIBLES EN LA ASIGNACION",
    5: "TIPOS INCOMPATIBLES EN LA OPERACION",
    6: "LA CONDICION DEBE SER LOGICAL",
    7: "LA VARIABLE DEL DO DEBE SER INTEGER",
    8: "NO SE PUEDE MODIFICAR LA VARIABLE DEL DO DENTRO DEL CICLO",
    9: "EXIT O CYCLE FUERA DE UN CICLO",
    10: "NO SE PUEDE ASIGNAR UN VALOR A UN PARAMETER",
    11: "EL PARAMETER NECESITA UN VALOR",
    12: "DIVISION ENTRE CERO",
    13: "FUNCION DESCONOCIDA O CON ARGUMENTOS INCORRECTOS",
    14: "EL VALOR INICIAL DEBE SER CONSTANTE",
    15: "EL PASO DEL DO NO PUEDE SER CERO",
}

NUMERICOS = ("integer", "real", "double precision")
RANGO = {"integer": 0, "real": 1, "double precision": 2}

# nombre: (numero de argumentos, tipo de resultado o None si es el de los argumentos)
FUNCIONES = {
    "mod": (2, None), "abs": (1, None), "max": (-2, None), "min": (-2, None),
    "sqrt": (1, "real"), "exp": (1, "real"), "log": (1, "real"), "sin": (1, "real"),
    "cos": (1, "real"), "int": (1, "integer"), "nint": (1, "integer"), "real": (1, "real"),
}


def mayor_numerico(a, b):
    return a if RANGO[a] >= RANGO[b] else b


class Semantico:
    def __init__(self, programa):
        self.programa = programa
        self.tabla = TablaSimbolos()
        self.errores = []
        self.advertencias = []
        self.variables_do = []
        self.ciclos = 0
        self.avisadas = set()

    def error(self, linea, codigo, detalle=""):
        texto = f"LINEA {linea} ERROR SEMANTICO {codigo} :{ERRORES_SEMANTICOS[codigo]}"
        self.errores.append(texto + (f" ({detalle})" if detalle else ""))

    def advertencia(self, linea, texto):
        self.advertencias.append(f"LINEA {linea} ADVERTENCIA :{texto}")

    def analizar(self):
        p = self.programa
        self.tabla.declarar(p.nombre, None, "programa", p.linea)
        for declaracion in p.declaraciones:
            self.declaracion(declaracion)
        self.bloque(p.sentencias)
        for s in self.tabla.variables():
            if not s.usada and s.clase == "variable":
                self.advertencia(s.linea, f"la variable '{s.nombre}' se declaro pero no se usa")
        return not self.errores

    # declaraciones

    def declaracion(self, d):
        clase = "parametro" if d.parametro else "variable"
        for nombre, valor, linea in d.variables:
            if valor is not None:
                tipo_valor = self.expresion(valor)
                if not self.es_constante(valor):
                    self.error(linea, 14, nombre)
                elif tipo_valor is not None:
                    self.revisa_asignacion(d.tipo, tipo_valor, linea, nombre, d.longitud, valor)
            elif d.parametro:
                self.error(linea, 11, nombre)
            simbolo, problema = self.tabla.declarar(nombre, d.tipo, clase, linea, d.longitud)
            if problema:
                ambigua = problema.startswith("ambiguedad")
                self.error(linea, 1 if ambigua else 2, problema.replace("ambiguedad: ", ""))
                continue
            if valor is not None:
                simbolo.inicializada = True
                simbolo.valor = self.valor_constante(valor)

    def es_constante(self, nodo):
        if isinstance(nodo, Literal):
            return True
        if isinstance(nodo, Variable):
            s = self.tabla.buscar(nodo.nombre)
            return s is not None and s.clase == "parametro"
        if isinstance(nodo, (Binaria, Unaria, Funcion)):
            return all(self.es_constante(h) for h in nodo.hijos())
        return False

    def valor_constante(self, nodo):
        if isinstance(nodo, Literal):
            return nodo.texto
        if isinstance(nodo, Unaria) and isinstance(nodo.expresion, Literal) and nodo.operador == "-":
            return "-" + nodo.expresion.texto
        return "(expresion)"

    # sentencias

    def bloque(self, sentencias):
        for s in sentencias:
            self.sentencia(s)

    def sentencia(self, s):
        if isinstance(s, Asignacion):
            simbolo = self.simbolo(s.variable, s.linea)
            tipo = self.expresion(s.expresion)
            if simbolo is None:
                return
            if simbolo.clase == "parametro":
                self.error(s.linea, 10, s.variable)
            elif s.variable.lower() in self.variables_do:
                self.error(s.linea, 8, s.variable)
            if tipo is not None:
                self.revisa_asignacion(simbolo.tipo, tipo, s.linea, s.variable, simbolo.longitud, s.expresion)
            simbolo.inicializada = True
        elif isinstance(s, Leer):
            for nombre in s.variables:
                simbolo = self.simbolo(nombre, s.linea)
                if simbolo is None:
                    continue
                if simbolo.clase == "parametro":
                    self.error(s.linea, 10, nombre)
                elif nombre.lower() in self.variables_do:
                    self.error(s.linea, 8, nombre)
                simbolo.inicializada = True
        elif isinstance(s, Escribir):
            for e in s.elementos:
                self.expresion(e)
        elif isinstance(s, Si):
            for condicion, cuerpo in s.ramas:
                self.condicion(condicion)
                self.bloque(cuerpo)
            if s.sino is not None:
                self.bloque(s.sino)
        elif isinstance(s, Hacer):
            self.ciclo_do(s)
        elif isinstance(s, Mientras):
            self.condicion(s.condicion)
            self.ciclos += 1
            self.bloque(s.cuerpo)
            self.ciclos -= 1
        elif isinstance(s, (Salir, Ciclar)):
            if self.ciclos == 0:
                self.error(s.linea, 9, "exit" if isinstance(s, Salir) else "cycle")
        elif isinstance(s, Parar):
            pass

    def ciclo_do(self, s):
        simbolo = self.simbolo(s.variable, s.linea)
        if simbolo is not None:
            if simbolo.tipo != "integer":
                self.error(s.linea, 7, f"{s.variable} es {simbolo.tipo}")
            if simbolo.clase == "parametro":
                self.error(s.linea, 10, s.variable)
            simbolo.inicializada = True
            simbolo.usada = True
        for parte in (s.inicio, s.fin, s.paso):
            if parte is None:
                continue
            tipo = self.expresion(parte)
            if tipo is not None and tipo not in NUMERICOS:
                self.error(parte.linea, 5, f"el limite del do es {tipo}")
        if isinstance(s.paso, Literal) and s.paso.valor == 0:
            self.error(s.linea, 15)
        self.variables_do.append(s.variable.lower())
        self.ciclos += 1
        self.bloque(s.cuerpo)
        self.ciclos -= 1
        self.variables_do.pop()

    def condicion(self, nodo):
        tipo = self.expresion(nodo)
        if tipo is not None and tipo != "logical":
            self.error(nodo.linea, 6, f"la condicion es {tipo}")

    def revisa_asignacion(self, destino, origen, linea, nombre, longitud, expresion):
        if destino in NUMERICOS and origen in NUMERICOS:
            if destino == "integer" and origen != "integer":
                self.advertencia(linea, f"el valor {origen} se trunca a integer al guardarlo en '{nombre}'")
            return
        if destino == origen:
            if destino == "character" and isinstance(expresion, Literal) and len(expresion.valor) > longitud:
                self.advertencia(linea, f"la cadena se recorta a {longitud} caracteres en '{nombre}'")
            return
        self.error(linea, 4, f"{nombre} es {destino} y el valor es {origen}")

    # expresiones: regresan el tipo o None si hubo error

    def simbolo(self, nombre, linea):
        simbolo = self.tabla.buscar(nombre)
        if simbolo is not None and simbolo.clase != "programa":
            return simbolo
        if self.programa.implicit_none:
            if nombre.lower() not in self.avisadas:
                self.avisadas.add(nombre.lower())
                self.error(linea, 3, nombre)
            return None
        # sin implicit none fortran usa tipos implicitos: i a n integer, lo demas real
        tipo = "integer" if nombre[0].lower() in "ijklmn" else "real"
        simbolo, _ = self.tabla.declarar(nombre, tipo, "variable", linea)
        self.advertencia(linea, f"'{nombre}' no esta declarada, se toma como {tipo} (tipo implicito)")
        return simbolo

    def expresion(self, nodo):
        tipo = self._expresion(nodo)
        nodo.tipo = tipo
        return tipo

    def _expresion(self, nodo):
        if isinstance(nodo, Literal):
            return nodo.tipo
        if isinstance(nodo, Variable):
            simbolo = self.simbolo(nodo.nombre, nodo.linea)
            if simbolo is None:
                return None
            simbolo.usada = True
            if not simbolo.inicializada and simbolo.nombre.lower() not in self.avisadas:
                self.avisadas.add(simbolo.nombre.lower())
                self.advertencia(nodo.linea, f"la variable '{nodo.nombre}' se usa antes de tener valor")
            return simbolo.tipo
        if isinstance(nodo, Unaria):
            tipo = self.expresion(nodo.expresion)
            if tipo is None:
                return None
            if nodo.operador == ".NOT.":
                if tipo != "logical":
                    self.error(nodo.linea, 5, f".NOT. con {tipo}")
                    return None
                return "logical"
            if tipo not in NUMERICOS:
                self.error(nodo.linea, 5, f"signo - con {tipo}")
                return None
            return tipo
        if isinstance(nodo, Binaria):
            return self.binaria(nodo)
        if isinstance(nodo, Funcion):
            return self.funcion(nodo)
        return None

    def binaria(self, nodo):
        izq = self.expresion(nodo.izquierda)
        der = self.expresion(nodo.derecha)
        if izq is None or der is None:
            return None
        op = nodo.operador
        detalle = f"{izq} {op} {der}"
        if op in ("+", "-", "*", "/", "**"):
            if izq in NUMERICOS and der in NUMERICOS:
                if op == "/" and isinstance(nodo.derecha, Literal) and nodo.derecha.valor == 0:
                    self.error(nodo.linea, 12)
                return mayor_numerico(izq, der)
        elif op == "//":
            if izq == der == "character":
                return "character"
        elif op in ("==", "/=", "<", "<=", ">", ">="):
            if (izq in NUMERICOS and der in NUMERICOS) or izq == der == "character":
                return "logical"
        elif op in (".AND.", ".OR.", ".EQV.", ".NEQV."):
            if izq == der == "logical":
                return "logical"
        self.error(nodo.linea, 5, detalle)
        return None

    def funcion(self, nodo):
        tipos = [self.expresion(a) for a in nodo.argumentos]
        if nodo.nombre not in FUNCIONES:
            self.error(nodo.linea, 13, nodo.nombre)
            return None
        cantidad, resultado = FUNCIONES[nodo.nombre]
        if (cantidad > 0 and len(tipos) != cantidad) or (cantidad < 0 and len(tipos) < -cantidad):
            self.error(nodo.linea, 13, f"{nodo.nombre} con {len(tipos)} argumentos")
            return None
        if None in tipos:
            return None
        if any(t not in NUMERICOS for t in tipos):
            self.error(nodo.linea, 13, f"{nodo.nombre} necesita argumentos numericos")
            return None
        if resultado is not None:
            return resultado
        tipo = tipos[0]
        for t in tipos[1:]:
            tipo = mayor_numerico(tipo, t)
        return tipo

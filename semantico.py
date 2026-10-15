from arbol import (Asignacion, Binaria, Ciclar, Constructor, Elemento, Escribir, Funcion, Hacer,
                   Leer, Literal, Mientras, Parar, Salir, Si, Unaria, Variable)
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
    16: "EL INDICE DEL ARREGLO DEBE SER INTEGER",
    17: "INDICE FUERA DEL RANGO DEL ARREGLO",
    18: "LA DIMENSION DEBE SER UNA CONSTANTE INTEGER",
    19: "EL ARREGLO COMPLETO NO SE PUEDE USAR AQUI, FALTA EL INDICE",
    20: "LA VARIABLE NO ES UN ARREGLO",
    21: "EL TAMANO DE LOS ARREGLOS NO COINCIDE",
    22: "LOS ELEMENTOS DEL ARREGLO DEBEN SER DEL MISMO TIPO",
}

NUMERICOS = ("integer", "real", "double precision")
RANGO = {"integer": 0, "real": 1, "double precision": 2}

# nombre: (numero de argumentos, tipo de resultado o None si es el de los argumentos)
FUNCIONES = {
    "mod": (2, None), "abs": (1, None), "max": (-2, None), "min": (-2, None),
    "sqrt": (1, "real"), "exp": (1, "real"), "log": (1, "real"), "sin": (1, "real"),
    "cos": (1, "real"), "int": (1, "integer"), "nint": (1, "integer"), "real": (1, "real"),
}

# reciben un arreglo completo; tipo de resultado o None si es el del arreglo
FUNCIONES_ARREGLO = {"size": "integer", "sum": None, "maxval": None, "minval": None}


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
            errores_antes = len(self.errores)
            dimension = None
            if nombre in d.dimensiones:
                dimension = self.dimension(d.dimensiones[nombre], linea, nombre)
            if valor is not None:
                tipo_valor = self.expresion(valor, arreglo=dimension is not None)
                if not self.es_constante(valor):
                    self.error(linea, 14, nombre)
                elif tipo_valor is not None:
                    self.revisa_asignacion(d.tipo, tipo_valor, linea, nombre, d.longitud, valor)
                    if dimension is not None:
                        self.revisa_tamano(dimension[1] - dimension[0] + 1, valor, linea, nombre)
            elif d.parametro:
                self.error(linea, 11, nombre)
            simbolo, problema = self.tabla.declarar(nombre, d.tipo, clase, linea, d.longitud, dimension)
            if problema:
                ambigua = problema.startswith("ambiguedad")
                self.error(linea, 1 if ambigua else 2, problema.replace("ambiguedad: ", ""))
                continue
            if valor is not None and len(self.errores) == errores_antes:
                simbolo.inicializada = True
                simbolo.valor = self.valor_constante(valor)
                if dimension is None:
                    simbolo.constante = self.evalua(valor)

    def dimension(self, limites, linea, nombre):
        valores = []
        for limite in limites:
            if limite is None:
                valores.append(1)
                continue
            tipo = self.expresion(limite)
            valor = self.evalua(limite) if self.es_constante(limite) else None
            if tipo is not None and (tipo != "integer" or not isinstance(valor, int)):
                self.error(linea, 18, nombre)
            valores.append(valor if isinstance(valor, int) else 1)
        return valores[0], max(valores[1], valores[0] - 1)

    def evalua(self, nodo):
        # valor de una expresion constante o None si no se sabe al compilar
        if isinstance(nodo, Literal):
            return nodo.valor
        if isinstance(nodo, Variable):
            s = self.tabla.buscar(nodo.nombre)
            return s.constante if s is not None and s.clase == "parametro" else None
        if isinstance(nodo, Unaria) and nodo.operador == "-":
            valor = self.evalua(nodo.expresion)
            return None if valor is None else -valor
        if isinstance(nodo, Binaria) and nodo.operador in ("+", "-", "*", "/", "**"):
            a, b = self.evalua(nodo.izquierda), self.evalua(nodo.derecha)
            if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (a, b)):
                return None
            if nodo.operador == "+":
                return a + b
            if nodo.operador == "-":
                return a - b
            if nodo.operador == "*":
                return a * b
            if nodo.operador == "**":
                return a ** b if b >= 0 else None
            if b == 0:
                return None
            if isinstance(a, int) and isinstance(b, int):
                return int(a / b)
            return a / b
        return None

    def es_constante(self, nodo):
        if isinstance(nodo, Literal):
            return True
        if isinstance(nodo, Variable):
            s = self.tabla.buscar(nodo.nombre)
            return s is not None and s.clase == "parametro"
        if isinstance(nodo, (Binaria, Unaria, Funcion, Constructor)):
            return all(self.es_constante(h) for h in nodo.hijos())
        return False

    def valor_constante(self, nodo):
        if isinstance(nodo, Literal):
            return nodo.texto
        if isinstance(nodo, Unaria) and isinstance(nodo.expresion, Literal) and nodo.operador == "-":
            return "-" + nodo.expresion.texto
        if isinstance(nodo, Constructor):
            return "[" + ", ".join(self.valor_constante(e) for e in nodo.elementos) + "]"
        return "(expresion)"

    # sentencias

    def bloque(self, sentencias):
        for s in sentencias:
            self.sentencia(s)

    def sentencia(self, s):
        if isinstance(s, Asignacion):
            simbolo = self.simbolo(s.variable, s.linea)
            completo = simbolo is not None and simbolo.dimension is not None and s.indice is None
            tipo = self.expresion(s.expresion, arreglo=completo)
            if s.indice is not None:
                self.revisa_indice(simbolo, s.indice, s.linea, s.variable)
            if simbolo is None:
                return
            if completo and tipo is not None:
                self.revisa_tamano(simbolo.elementos, s.expresion, s.linea, s.variable)
            if simbolo.clase == "parametro":
                self.error(s.linea, 10, s.variable)
            elif s.variable.lower() in self.variables_do:
                self.error(s.linea, 8, s.variable)
            if tipo is not None:
                self.revisa_asignacion(simbolo.tipo, tipo, s.linea, s.variable, simbolo.longitud, s.expresion)
            simbolo.inicializada = True
        elif isinstance(s, Leer):
            for nombre, indice in zip(s.variables, s.indices):
                simbolo = self.simbolo(nombre, s.linea)
                if indice is not None:
                    self.revisa_indice(simbolo, indice, s.linea, nombre)
                if simbolo is None:
                    continue
                if simbolo.clase == "parametro":
                    self.error(s.linea, 10, nombre)
                elif nombre.lower() in self.variables_do:
                    self.error(s.linea, 8, nombre)
                simbolo.inicializada = True
        elif isinstance(s, Escribir):
            for e in s.elementos:
                self.expresion(e, arreglo=True)
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
        if s.variable.lower() in self.variables_do:
            self.error(s.linea, 8, f"{s.variable} ya controla un do exterior")
        if simbolo is not None:
            if simbolo.dimension is not None:
                self.error(s.linea, 7, f"{s.variable} es un arreglo")
            elif simbolo.tipo != "integer":
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

    def revisa_tamano(self, elementos, expresion, linea, nombre):
        # un escalar llena todo el arreglo; otro arreglo debe tener los mismos elementos
        tamano = getattr(expresion, "tamano", None)
        if tamano is not None and tamano != elementos:
            self.error(linea, 21, f"{nombre} tiene {elementos} elementos y el valor tiene {tamano}")

    def revisa_indice(self, simbolo, indice, linea, nombre):
        tipo = self.expresion(indice)
        if simbolo is None:
            return
        if simbolo.dimension is None:
            self.error(linea, 20, nombre)
            return
        if tipo is not None and tipo != "integer":
            self.error(linea, 16, f"{nombre}({tipo})")
            return
        valor = self.evalua(indice)
        inferior, superior = simbolo.dimension
        if isinstance(valor, int) and not inferior <= valor <= superior:
            self.error(linea, 17, f"{nombre}({valor}), el rango es {inferior}:{superior}")

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

    def expresion(self, nodo, arreglo=False):
        # arreglo indica si ahi se acepta un arreglo completo (print, asignacion, size, sum...)
        nodo.tamano = None
        tipo = self._expresion(nodo)
        nodo.tipo = tipo
        if tipo is not None and nodo.tamano is not None and not arreglo:
            nombre = nodo.nombre if isinstance(nodo, Variable) else "[...]"
            self.error(nodo.linea, 19, nombre)
            return None
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
            if simbolo.dimension is not None:
                nodo.tamano = simbolo.elementos
            return simbolo.tipo
        if isinstance(nodo, Elemento):
            simbolo = self.simbolo(nodo.nombre, nodo.linea)
            self.revisa_indice(simbolo, nodo.indice, nodo.linea, nodo.nombre)
            if simbolo is None or simbolo.dimension is None:
                return None
            simbolo.usada = True
            if not simbolo.inicializada and simbolo.nombre.lower() not in self.avisadas:
                self.avisadas.add(simbolo.nombre.lower())
                self.advertencia(nodo.linea, f"el arreglo '{nodo.nombre}' se usa antes de tener valor")
            return simbolo.tipo
        if isinstance(nodo, Constructor):
            return self.constructor(nodo)
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

    def constructor(self, nodo):
        tipos = [self.expresion(e) for e in nodo.elementos]
        if None in tipos:
            return None
        if any(t != tipos[0] for t in tipos):
            self.error(nodo.linea, 22, ", ".join(dict.fromkeys(tipos)))
            return None
        nodo.tamano = len(tipos)
        return tipos[0]

    def funcion_arreglo(self, nodo):
        if len(nodo.argumentos) != 1:
            self.error(nodo.linea, 13, f"{nodo.nombre} con {len(nodo.argumentos)} argumentos")
            return None
        argumento = nodo.argumentos[0]
        tipo = self.expresion(argumento, arreglo=True)
        if tipo is None:
            return None
        if argumento.tamano is None:
            self.error(nodo.linea, 13, f"{nodo.nombre} necesita un arreglo")
            return None
        resultado = FUNCIONES_ARREGLO[nodo.nombre]
        if resultado is None and tipo not in NUMERICOS:
            self.error(nodo.linea, 13, f"{nodo.nombre} necesita un arreglo numerico")
            return None
        return resultado or tipo

    def funcion(self, nodo):
        if nodo.nombre in FUNCIONES_ARREGLO:
            return self.funcion_arreglo(nodo)
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

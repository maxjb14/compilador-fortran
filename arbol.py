class Nodo:
    linea = 0

    def etiqueta(self):
        return type(self).__name__

    def hijos(self):
        return []


class Programa(Nodo):
    def __init__(self, nombre, usos, implicit_none, declaraciones, sentencias, linea):
        self.nombre = nombre
        self.usos = usos
        self.implicit_none = implicit_none
        self.declaraciones = declaraciones
        self.sentencias = sentencias
        self.linea = linea

    def etiqueta(self):
        return f"Programa {self.nombre}"

    def hijos(self):
        return self.declaraciones + self.sentencias


class Declaracion(Nodo):
    def __init__(self, tipo, longitud, parametro, variables, linea, dimensiones=None):
        self.tipo = tipo
        self.longitud = longitud
        self.parametro = parametro
        # lista de (nombre, expresion o None, linea)
        self.variables = variables
        self.linea = linea
        # nombre del arreglo: (limite inferior o None, limite superior)
        self.dimensiones = dimensiones or {}

    def etiqueta(self):
        tipo = self.tipo + (f"({self.longitud})" if self.tipo == "character" else "")
        extra = ", parameter" if self.parametro else ""
        nombres = ", ".join(n + ("(...)" if n in self.dimensiones else "") for n, _, _ in self.variables)
        return f"Declaracion {tipo}{extra} :: {nombres}"

    def hijos(self):
        nodos = []
        for nombre, valor, _ in self.variables:
            if nombre in self.dimensiones:
                inferior, superior = self.dimensiones[nombre]
                limites = [superior] if inferior is None else [inferior, superior]
                nodos.append(Grupo(f"Dimension {nombre}", limites))
            if valor is not None:
                nodos.append(valor)
        return nodos


class Asignacion(Nodo):
    def __init__(self, variable, expresion, linea, indice=None):
        self.variable = variable
        self.expresion = expresion
        self.linea = linea
        self.indice = indice

    def etiqueta(self):
        destino = self.variable + ("(...)" if self.indice is not None else "")
        return f"Asignacion {destino} ="

    def hijos(self):
        if self.indice is not None:
            return [Grupo("Indice", [self.indice]), self.expresion]
        return [self.expresion]


class Leer(Nodo):
    def __init__(self, variables, linea, indices=None):
        self.variables = variables
        self.linea = linea
        # indice de cada variable leida, None si no es un elemento de arreglo
        self.indices = indices or [None] * len(variables)

    def etiqueta(self):
        nombres = [v + ("(...)" if i is not None else "") for v, i in zip(self.variables, self.indices)]
        return "Read " + ", ".join(nombres)

    def hijos(self):
        return [Grupo(f"Indice {v}", [i]) for v, i in zip(self.variables, self.indices) if i is not None]


class Escribir(Nodo):
    def __init__(self, elementos, linea):
        self.elementos = elementos
        self.linea = linea

    def etiqueta(self):
        return "Print"

    def hijos(self):
        return self.elementos


class Si(Nodo):
    def __init__(self, ramas, sino, linea, logico=False):
        # ramas: lista de (condicion, sentencias); sino: sentencias o None
        self.ramas = ramas
        self.sino = sino
        self.linea = linea
        self.logico = logico

    def etiqueta(self):
        return "If logico" if self.logico else "If"

    def hijos(self):
        nodos = []
        for i, (cond, cuerpo) in enumerate(self.ramas):
            nodos.append(Grupo("Condicion" if i == 0 else "Else if", [cond]))
            nodos.append(Grupo("Then", cuerpo))
        if self.sino is not None:
            nodos.append(Grupo("Else", self.sino))
        return nodos


class Hacer(Nodo):
    def __init__(self, variable, inicio, fin, paso, cuerpo, linea):
        self.variable = variable
        self.inicio = inicio
        self.fin = fin
        self.paso = paso
        self.cuerpo = cuerpo
        self.linea = linea

    def etiqueta(self):
        return f"Do {self.variable}"

    def hijos(self):
        nodos = [Grupo("Inicio", [self.inicio]), Grupo("Fin", [self.fin])]
        if self.paso is not None:
            nodos.append(Grupo("Paso", [self.paso]))
        nodos.append(Grupo("Cuerpo", self.cuerpo))
        return nodos


class Mientras(Nodo):
    def __init__(self, condicion, cuerpo, linea):
        self.condicion = condicion
        self.cuerpo = cuerpo
        self.linea = linea

    def etiqueta(self):
        return "Do while"

    def hijos(self):
        return [Grupo("Condicion", [self.condicion]), Grupo("Cuerpo", self.cuerpo)]


class Salir(Nodo):
    def __init__(self, linea):
        self.linea = linea

    def etiqueta(self):
        return "Exit"


class Ciclar(Nodo):
    def __init__(self, linea):
        self.linea = linea

    def etiqueta(self):
        return "Cycle"


class Parar(Nodo):
    def __init__(self, linea):
        self.linea = linea

    def etiqueta(self):
        return "Stop"


class Binaria(Nodo):
    def __init__(self, operador, izquierda, derecha, linea):
        self.operador = operador
        self.izquierda = izquierda
        self.derecha = derecha
        self.linea = linea
        self.tipo = None

    def etiqueta(self):
        return f"Operador {self.operador}"

    def hijos(self):
        return [self.izquierda, self.derecha]


class Unaria(Nodo):
    def __init__(self, operador, expresion, linea):
        self.operador = operador
        self.expresion = expresion
        self.linea = linea
        self.tipo = None

    def etiqueta(self):
        return f"Operador unario {self.operador}"

    def hijos(self):
        return [self.expresion]


class Literal(Nodo):
    def __init__(self, tipo, valor, texto, linea):
        self.tipo = tipo
        self.valor = valor
        self.texto = texto
        self.linea = linea

    def etiqueta(self):
        return f"Constante {self.texto} ({self.tipo})"


class Variable(Nodo):
    def __init__(self, nombre, linea):
        self.nombre = nombre
        self.linea = linea
        self.tipo = None

    def etiqueta(self):
        return f"Variable {self.nombre}"


class Elemento(Nodo):
    def __init__(self, nombre, indice, linea):
        self.nombre = nombre
        self.indice = indice
        self.linea = linea
        self.tipo = None

    def etiqueta(self):
        return f"Elemento {self.nombre}"

    def hijos(self):
        return [self.indice]


class Constructor(Nodo):
    def __init__(self, elementos, linea):
        self.elementos = elementos
        self.linea = linea
        self.tipo = None

    def etiqueta(self):
        return f"Arreglo [{len(self.elementos)}]"

    def hijos(self):
        return self.elementos


class Funcion(Nodo):
    def __init__(self, nombre, argumentos, linea):
        self.nombre = nombre
        self.argumentos = argumentos
        self.linea = linea
        self.tipo = None

    def etiqueta(self):
        return f"Funcion {self.nombre}"

    def hijos(self):
        return self.argumentos


class Grupo(Nodo):
    # nodo solo para mostrar el arbol con secciones (then, else, cuerpo)
    def __init__(self, nombre, nodos):
        self.nombre = nombre
        self.nodos = nodos

    def etiqueta(self):
        return self.nombre

    def hijos(self):
        return self.nodos


def arbol_texto(nodo, nivel=0):
    lineas = ["    " * nivel + nodo.etiqueta()]
    for hijo in nodo.hijos():
        lineas += arbol_texto(hijo, nivel + 1)
    return lineas

TAMANOS = {"integer": 4, "real": 4, "double precision": 8, "logical": 4, "character": 1}

DIRECCION_INICIAL = 1000


class Simbolo:
    def __init__(self, nombre, tipo, clase, linea, direccion, longitud=1, dimension=None):
        self.nombre = nombre
        self.tipo = tipo
        self.clase = clase
        self.linea = linea
        self.direccion = direccion
        self.longitud = longitud
        # (inferior, superior) si es arreglo
        self.dimension = dimension
        self.valor = None
        self.inicializada = False
        self.usada = False

    @property
    def elementos(self):
        if self.dimension is None:
            return 1
        return max(0, self.dimension[1] - self.dimension[0] + 1)


class TablaSimbolos:
    def __init__(self):
        self.simbolos = {}
        self.siguiente = DIRECCION_INICIAL

    def declarar(self, nombre, tipo, clase, linea, longitud=1, dimension=None):
        # regresa el simbolo y, si la declaracion choca con otra, el mensaje del problema
        clave = nombre.lower()
        if clave in self.simbolos:
            anterior = self.simbolos[clave]
            if anterior.clase == "programa":
                return anterior, f"'{nombre}' es el nombre del programa"
            if anterior.tipo != tipo:
                return anterior, f"ambiguedad: '{nombre}' ya fue declarada como {anterior.tipo} en la linea {anterior.linea}"
            return anterior, f"'{nombre}' ya fue declarada en la linea {anterior.linea}"
        simbolo = Simbolo(nombre, tipo, clase, linea, self.siguiente, longitud, dimension)
        tam = TAMANOS.get(tipo, 0) * (longitud if tipo == "character" else 1) * simbolo.elementos
        self.simbolos[clave] = simbolo
        self.siguiente += tam
        return simbolo, None

    def buscar(self, nombre):
        return self.simbolos.get(nombre.lower())

    def variables(self):
        return [s for s in self.simbolos.values() if s.clase in ("variable", "parametro")]

    def tabla(self):
        filas = [f"{'nombre':<14}{'tipo':<22}{'clase':<11}{'dir':<7}{'linea':<7}valor"]
        for s in self.simbolos.values():
            tipo = (s.tipo or "-") + (f"({s.longitud})" if s.tipo == "character" else "")
            if s.dimension is not None:
                tipo += f"[{s.dimension[0]}:{s.dimension[1]}]"
            valor = "" if s.valor is None else str(s.valor)
            direccion = "" if s.clase == "programa" else str(s.direccion)
            filas.append(f"{s.nombre:<14}{tipo:<22}{s.clase:<11}{direccion:<7}{s.linea:<7}{valor}")
        return filas

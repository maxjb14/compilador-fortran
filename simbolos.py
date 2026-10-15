TAMANOS = {"integer": 4, "real": 4, "double precision": 8, "logical": 4, "character": 1}

DIRECCION_INICIAL = 1000


class Simbolo:
    def __init__(self, nombre, tipo, clase, linea, direccion, longitud=1):
        self.nombre = nombre
        self.tipo = tipo
        self.clase = clase
        self.linea = linea
        self.direccion = direccion
        self.longitud = longitud
        self.valor = None
        self.inicializada = False
        self.usada = False


class TablaSimbolos:
    def __init__(self):
        self.simbolos = {}
        self.siguiente = DIRECCION_INICIAL

    def declarar(self, nombre, tipo, clase, linea, longitud=1):
        # regresa el simbolo y, si la declaracion choca con otra, el mensaje del problema
        clave = nombre.lower()
        if clave in self.simbolos:
            anterior = self.simbolos[clave]
            if anterior.tipo != tipo:
                return anterior, f"ambiguedad: '{nombre}' ya fue declarada como {anterior.tipo} en la linea {anterior.linea}"
            return anterior, f"'{nombre}' ya fue declarada en la linea {anterior.linea}"
        tam = TAMANOS.get(tipo, 0) * (longitud if tipo == "character" else 1)
        simbolo = Simbolo(nombre, tipo, clase, linea, self.siguiente, longitud)
        self.simbolos[clave] = simbolo
        self.siguiente += tam
        return simbolo, None

    def buscar(self, nombre):
        return self.simbolos.get(nombre.lower())

    def variables(self):
        return [s for s in self.simbolos.values() if s.clase in ("variable", "parametro")]

    def tabla(self):
        filas = [f"{'nombre':<14}{'tipo':<18}{'clase':<11}{'dir':<7}{'linea':<7}valor"]
        for s in self.simbolos.values():
            tipo = (s.tipo or "-") + (f"({s.longitud})" if s.tipo == "character" else "")
            valor = "" if s.valor is None else str(s.valor)
            direccion = "" if s.clase == "programa" else str(s.direccion)
            filas.append(f"{s.nombre:<14}{tipo:<18}{s.clase:<11}{direccion:<7}{s.linea:<7}{valor}")
        return filas

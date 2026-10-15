import math


class ErrorEjecucion(Exception):
    pass


class Direccion:
    def __init__(self, nombre):
        self.nombre = nombre


def division_entera(a, b):
    # fortran trunca hacia cero, python redondea hacia abajo
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def modulo(a, b):
    if isinstance(a, int) and isinstance(b, int):
        return a - division_entera(a, b) * b
    return math.fmod(a, b)


def redondeo(x):
    return int(math.floor(abs(x) + 0.5)) * (1 if x >= 0 else -1)


FUNCIONES = {
    "mod": modulo,
    "abs": abs,
    "max": max,
    "min": min,
    "sqrt": math.sqrt,
    "exp": math.exp,
    "log": math.log,
    "sin": math.sin,
    "cos": math.cos,
    "int": lambda x: int(x),
    "nint": redondeo,
    "real": lambda x: float(x),
}


def formato(valor):
    if isinstance(valor, bool):
        return "T" if valor else "F"
    if isinstance(valor, float):
        return f"{valor:.6f}"
    return str(valor)


class MaquinaPila:
    def __init__(self, texto, entrada=input, salida=print, limite=2_000_000):
        self.entrada = entrada
        self.salida = salida
        self.limite = limite
        self.tipos = {}
        self.longitudes = {}
        self.instrucciones = []
        self.etiquetas = {}
        self.cargar(texto)

    def cargar(self, texto):
        seccion = None
        for linea in texto.splitlines():
            linea = linea.strip()
            if not linea:
                continue
            if linea in (".DATA", ".CODE"):
                seccion = linea
                continue
            if seccion == ".DATA":
                partes = linea.split()
                self.tipos[partes[1]] = partes[2].lower().replace("_", " ")
                if len(partes) > 3:
                    self.longitudes[partes[1]] = int(partes[3])
            else:
                op, _, arg = linea.partition(" ")
                if op == "LABEL":
                    self.etiquetas[arg] = len(self.instrucciones)
                self.instrucciones.append((op, arg))

    def constante(self, texto):
        if texto.startswith("'"):
            return texto[1:-1].replace("''", "'")
        if texto in (".TRUE.", ".FALSE."):
            return texto == ".TRUE."
        try:
            return int(texto)
        except ValueError:
            return float(texto)

    def ajusta(self, nombre, valor):
        tipo = self.tipos[nombre]
        if tipo == "integer":
            return int(valor)
        if tipo in ("real", "double precision"):
            return float(valor)
        if tipo == "character":
            return str(valor)[:self.longitudes.get(nombre, 1)]
        return valor

    def lee(self, nombre):
        texto = self.entrada(f"{nombre} = ").strip()
        tipo = self.tipos[nombre]
        try:
            if tipo == "integer":
                return int(texto)
            if tipo in ("real", "double precision"):
                return float(texto.lower().replace("d", "e"))
            if tipo == "logical":
                if texto.upper() in (".TRUE.", "T", "TRUE", "1"):
                    return True
                if texto.upper() in (".FALSE.", "F", "FALSE", "0"):
                    return False
                raise ValueError
            return self.ajusta(nombre, texto.strip("'\""))
        except ValueError:
            raise ErrorEjecucion(f"ERROR DE EJECUCION: '{texto}' no es un valor {tipo} valido para {nombre}")

    def ejecutar(self):
        memoria = {}
        pila = []
        renglon = []
        pc = 0
        pasos = 0

        def saca():
            if not pila:
                raise ErrorEjecucion("ERROR DE EJECUCION: pila vacia")
            return pila.pop()

        while pc < len(self.instrucciones):
            pasos += 1
            if pasos > self.limite:
                raise ErrorEjecucion("ERROR DE EJECUCION: demasiadas instrucciones, posible ciclo infinito")
            op, arg = self.instrucciones[pc]
            pc += 1
            if op == "PUSHC":
                pila.append(self.constante(arg))
            elif op == "PUSHA":
                pila.append(Direccion(arg))
            elif op == "LOAD":
                d = saca()
                if d.nombre not in memoria:
                    raise ErrorEjecucion(f"ERROR DE EJECUCION: la variable '{d.nombre}' no tiene valor")
                pila.append(memoria[d.nombre])
            elif op == "STORE":
                valor = saca()
                d = saca()
                memoria[d.nombre] = self.ajusta(d.nombre, valor)
            elif op == "INPUT":
                memoria[arg] = self.lee(arg)
            elif op == "OUTPUT":
                renglon.append(formato(saca()))
            elif op == "NEWLINE":
                self.salida(" ".join(renglon))
                renglon = []
            elif op == "NEG":
                pila.append(-saca())
            elif op == "NOT":
                pila.append(not saca())
            elif op == "CVTI":
                pila.append(int(saca()))
            elif op == "CVTR":
                pila.append(float(saca()))
            elif op == "LABEL":
                pass
            elif op == "JMP":
                pc = self.etiquetas[arg]
            elif op == "JMPF":
                if not saca():
                    pc = self.etiquetas[arg]
            elif op == "CALL":
                nombre, n = arg.split()
                argumentos = [saca() for _ in range(int(n))][::-1]
                try:
                    pila.append(FUNCIONES[nombre](*argumentos))
                except (ValueError, ZeroDivisionError):
                    raise ErrorEjecucion(f"ERROR DE EJECUCION: argumento invalido en {nombre}")
            elif op in ("HALT", "END"):
                break
            else:
                b = saca()
                a = saca()
                pila.append(self.binaria(op, a, b))
        if renglon:
            self.salida(" ".join(renglon))
        return memoria

    def binaria(self, op, a, b):
        if op in ("DIV", "IDIV") and b == 0:
            raise ErrorEjecucion("ERROR DE EJECUCION: division entre cero")
        if op == "ADD":
            return a + b
        if op == "MUL":
            return a * b
        if op == "DIV":
            return a / b
        if op == "IDIV":
            return division_entera(a, b)
        if op == "POW":
            if isinstance(a, int) and isinstance(b, int) and b < 0:
                return 0 if abs(a) != 1 else a ** b
            return a ** b
        if op == "CONCAT":
            return a + b
        if op == "EQ":
            return a == b
        if op == "NE":
            return a != b
        if op == "LT":
            return a < b
        if op == "LE":
            return a <= b
        if op == "GT":
            return a > b
        if op == "GE":
            return a >= b
        if op == "AND":
            return a and b
        if op == "OR":
            return a or b
        if op == "EQV":
            return a == b
        if op == "NEQV":
            return a != b
        raise ErrorEjecucion(f"ERROR DE EJECUCION: instruccion desconocida {op}")

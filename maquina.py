import math


class ErrorEjecucion(Exception):
    pass


class Direccion:
    def __init__(self, nombre, indice=None):
        self.nombre = nombre
        self.indice = indice

    def texto(self):
        return self.nombre if self.indice is None else f"{self.nombre}({self.indice})"


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
    "size": len,
    "sum": sum,
    "maxval": max,
    "minval": min,
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
        self.dimensiones = {}
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
                # VAR nombre TIPO [longitud] o ARRAY nombre TIPO inferior superior [longitud]
                partes = linea.split()
                self.tipos[partes[1]] = partes[2].lower().replace("_", " ")
                if partes[0] == "ARRAY":
                    self.dimensiones[partes[1]] = (int(partes[3]), int(partes[4]))
                    partes = partes[:3] + partes[5:]
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

    def lee(self, nombre, etiqueta=None):
        etiqueta = etiqueta or nombre
        texto = self.entrada(f"{etiqueta} = ").strip()
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
            raise ErrorEjecucion(f"ERROR DE EJECUCION: '{texto}' no es un valor {tipo} valido para {etiqueta}")

    def posicion(self, d):
        inferior, superior = self.dimensiones[d.nombre]
        if not inferior <= d.indice <= superior:
            raise ErrorEjecucion(f"ERROR DE EJECUCION: indice fuera de rango en {d.texto()}, "
                                 f"el rango es {inferior}:{superior}")
        return d.indice - inferior

    def carga(self, memoria, d):
        if d.indice is not None:
            valor = memoria[d.nombre][self.posicion(d)]
        elif d.nombre in self.dimensiones:
            valor = memoria[d.nombre]
            valor = None if None in valor else list(valor)
        else:
            valor = memoria.get(d.nombre)
        if valor is None:
            raise ErrorEjecucion(f"ERROR DE EJECUCION: la variable '{d.texto()}' no tiene valor")
        return valor

    def guarda(self, memoria, d, valor):
        if d.indice is not None:
            memoria[d.nombre][self.posicion(d)] = self.ajusta(d.nombre, valor)
        elif d.nombre in self.dimensiones:
            elementos = len(memoria[d.nombre])
            if not isinstance(valor, list):
                valor = [valor] * elementos
            elif len(valor) != elementos:
                raise ErrorEjecucion(f"ERROR DE EJECUCION: {d.nombre} tiene {elementos} elementos "
                                     f"y el valor tiene {len(valor)}")
            memoria[d.nombre] = [self.ajusta(d.nombre, v) for v in valor]
        else:
            memoria[d.nombre] = self.ajusta(d.nombre, valor)

    def lee_en(self, memoria, d):
        if d.indice is None and d.nombre in self.dimensiones:
            inferior, _ = self.dimensiones[d.nombre]
            for i in range(len(memoria[d.nombre])):
                memoria[d.nombre][i] = self.lee(d.nombre, f"{d.nombre}({inferior + i})")
            return
        valor = self.lee(d.nombre, d.texto())
        self.guarda(memoria, d, valor)

    def ejecutar(self):
        # los arreglos empiezan con todos sus elementos sin valor
        memoria = {nombre: [None] * max(0, sup - inf + 1) for nombre, (inf, sup) in self.dimensiones.items()}
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
            elif op == "INDEX":
                indice = saca()
                d = saca()
                pila.append(Direccion(d.nombre, indice))
            elif op == "LOAD":
                pila.append(self.carga(memoria, saca()))
            elif op == "STORE":
                valor = saca()
                self.guarda(memoria, saca(), valor)
            elif op == "INPUT":
                self.lee_en(memoria, Direccion(arg) if arg else saca())
            elif op == "PACK":
                elementos = [saca() for _ in range(int(arg))]
                pila.append(elementos[::-1])
            elif op == "OUTPUT":
                valor = saca()
                if isinstance(valor, list):
                    renglon.extend(formato(v) for v in valor)
                else:
                    renglon.append(formato(valor))
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

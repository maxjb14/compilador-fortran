import re

TAM_BUFFER = 100

TIPOS_DATO = {"INTEGER", "REAL", "DOUBLE", "LOGICAL", "CHARACTER"}

PALABRAS_RESERVADAS = {
    "PROGRAM", "END", "IMPLICIT", "NONE", "PRECISION", "PARAMETER", "IF", "THEN", "ELSE",
    "ELSEIF", "ENDIF", "DO", "ENDDO", "WHILE", "EXIT", "CYCLE", "STOP", "PRINT", "READ",
    "USE", "LEN", "DIMENSION",
}

OPERADORES_PUNTO = {
    ".EQ.": ("OP_RELACIONAL", "=="), ".NE.": ("OP_RELACIONAL", "/="),
    ".LT.": ("OP_RELACIONAL", "<"), ".LE.": ("OP_RELACIONAL", "<="),
    ".GT.": ("OP_RELACIONAL", ">"), ".GE.": ("OP_RELACIONAL", ">="),
    ".AND.": ("OP_LOGICO", ".AND."), ".OR.": ("OP_LOGICO", ".OR."),
    ".NOT.": ("OP_LOGICO", ".NOT."), ".EQV.": ("OP_LOGICO", ".EQV."),
    ".NEQV.": ("OP_LOGICO", ".NEQV."),
    ".TRUE.": ("LOGICO", ".TRUE."), ".FALSE.": ("LOGICO", ".FALSE."),
}

CATEGORIAS = {
    "RESERVADA": "palabra reservada",
    "TIPO_DATO": "tipo de dato",
    "IDENTIFICADOR": "identificador",
    "ENTERO": "constante entera",
    "REAL": "constante real",
    "CADENA": "constante cadena",
    "LOGICO": "constante logica",
    "OP_ARITMETICO": "operador aritmetico",
    "OP_RELACIONAL": "operador relacional",
    "OP_LOGICO": "operador logico",
    "CONCATENACION": "concatenacion",
    "ASIGNACION": "asignacion",
    "DELIMITADOR": "delimitador",
    "FIN_LINEA": "fin de instruccion",
    "FIN": "fin de archivo",
    "INVALIDO": "token invalido",
}

ERRORES_LEXICOS = {
    1: "CARACTER DESCONOCIDO",
    2: "IDENTIFICADOR INVALIDO, NO PUEDE EMPEZAR CON NUMERO",
    3: "CADENA SIN CERRAR",
    4: "OPERADOR CON PUNTO DESCONOCIDO",
}

PATRON_TOKEN = re.compile(r"""
    (?P<CONTINUACION>&[ \t]*(?:![^\n]*)?\r?\n)
  | (?P<COMENTARIO>![^\n]*)
  | (?P<FIN_LINEA>\n|;)
  | (?P<ESPACIO>[ \t\r]+)
  | (?P<CADENA>'[^'\n]*'|"[^"\n]*")
  | (?P<CADENA_ABIERTA>['"][^\n]*)
  | (?P<PUNTO>\.[A-Za-z]+\.)
  | (?P<REAL>\d+\.\d*(?:[eEdD][+-]?\d+)?|\.\d+(?:[eEdD][+-]?\d+)?|\d+[eEdD][+-]?\d+)
  | (?P<INVALIDO>\d+[A-Za-z_]\w*)
  | (?P<ENTERO>\d+)
  | (?P<IDENTIFICADOR>[A-Za-z_]\w*)
  | (?P<CONSTRUCTOR>\(/|/\))
  | (?P<CONCATENACION>//)
  | (?P<OP_RELACIONAL>==|/=|<=|>=|<|>)
  | (?P<DELIMITADOR>::|[(),:\[\]])
  | (?P<OP_ARITMETICO>\*\*|[+\-*/])
  | (?P<ASIGNACION>=)
  | (?P<DESCONOCIDO>.)
""", re.VERBOSE)


class Token:
    def __init__(self, tipo, valor, linea, norma=None):
        self.tipo = tipo
        self.valor = valor
        self.linea = linea
        # forma normalizada: fortran no distingue mayusculas
        self.norma = norma if norma is not None else valor

    def es(self, tipo, norma=None):
        return self.tipo == tipo and (norma is None or self.norma == norma)

    def __repr__(self):
        return f"<{self.tipo} {self.valor!r} linea {self.linea}>"


class Lexico:
    def __init__(self, fuente, traza=0):
        self.fuente = fuente
        self.traza = traza
        self.errores = []
        self.tokens = self.tokenizar(fuente)
        self.pos = 0
        self.linea = 1
        self.buffer = []

    def error(self, linea, codigo, detalle):
        self.errores.append(f"LINEA {linea} ERROR LEXICO {codigo} :{ERRORES_LEXICOS[codigo]} '{detalle}'")

    def tokenizar(self, fuente):
        tokens = []
        linea = 1
        for m in PATRON_TOKEN.finditer(fuente):
            tipo, valor = m.lastgroup, m.group()
            if tipo == "CONTINUACION":
                linea += 1
                continue
            if tipo in ("ESPACIO", "COMENTARIO"):
                continue
            token = self.clasificar(tipo, valor, linea)
            if token is not None:
                # no se repiten fines de instruccion seguidos
                if not (token.tipo == "FIN_LINEA" and tokens and tokens[-1].tipo == "FIN_LINEA"):
                    tokens.append(token)
            if valor == "\n":
                linea += 1
        if tokens and tokens[0].tipo == "FIN_LINEA":
            tokens.pop(0)
        tokens.append(Token("FIN", "", linea))
        return tokens

    def clasificar(self, tipo, valor, linea):
        if tipo == "IDENTIFICADOR":
            mayus = valor.upper()
            if mayus in TIPOS_DATO:
                return Token("TIPO_DATO", valor, linea, mayus)
            if mayus in PALABRAS_RESERVADAS:
                return Token("RESERVADA", valor, linea, mayus)
            return Token("IDENTIFICADOR", valor, linea, valor.lower())
        if tipo == "PUNTO":
            if valor.upper() in OPERADORES_PUNTO:
                nuevo, norma = OPERADORES_PUNTO[valor.upper()]
                return Token(nuevo, valor, linea, norma)
            self.error(linea, 4, valor)
            return Token("INVALIDO", valor, linea)
        if tipo == "CADENA":
            return Token("CADENA", valor, linea, valor[1:-1])
        if tipo == "CADENA_ABIERTA":
            self.error(linea, 3, valor)
            return Token("INVALIDO", valor, linea)
        if tipo == "INVALIDO":
            self.error(linea, 2, valor)
            return Token("INVALIDO", valor, linea, valor.lower())
        if tipo == "DESCONOCIDO":
            self.error(linea, 1, valor)
            return Token("INVALIDO", valor, linea)
        if tipo == "FIN_LINEA":
            return Token("FIN_LINEA", valor, linea, "\\n")
        if tipo == "CONSTRUCTOR":
            # (/ y /) son la forma vieja de [ y ]
            return Token("DELIMITADOR", valor, linea, "[" if valor == "(/" else "]")
        if tipo == "REAL":
            return Token("REAL", valor, linea, valor.lower().replace("d", "e"))
        return Token(tipo, valor, linea)

    def siguienteToken(self):
        if self.buffer:
            token = self.buffer.pop()
        else:
            token = self.tokens[min(self.pos, len(self.tokens) - 1)]
            self.pos += 1
        self.linea = token.linea
        if self.traza:
            print(f"ANALIZADOR LEXICO: Lee el token {token.valor!r} ({token.tipo})")
        return token

    def devuelveToken(self, token):
        if len(self.buffer) >= TAM_BUFFER:
            raise RuntimeError("DESBORDAMIENTO DEL BUFFER DEL ANALIZADOR LEXICO")
        self.buffer.append(token)

    def verToken(self):
        # mira el siguiente token sin consumirlo y sin imprimir traza
        if self.buffer:
            return self.buffer[-1]
        return self.tokens[min(self.pos, len(self.tokens) - 1)]

    def lineaActual(self):
        return self.linea

    def existeTraza(self):
        return bool(self.traza)

    def tabla(self):
        filas = []
        for t in self.tokens:
            if t.tipo in ("FIN_LINEA", "FIN"):
                continue
            filas.append(f"{t.linea:>5}  {t.valor:<22}{CATEGORIAS[t.tipo]}")
        return filas

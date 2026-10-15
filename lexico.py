import re

TAM_BUFFER = 100

PATRON_TOKEN = re.compile(r"""
    (?P<FIN_LINEA>\n)
  | (?P<ESPACIO>[ \t\r]+)
  | (?P<REAL>\d+\.\d*(?:[eEdD][+-]?\d+)?|\d+[eEdD][+-]?\d+)
  | (?P<ENTERO>\d+)
  | (?P<IDENTIFICADOR>[A-Za-z_]\w*)
  | (?P<OP_RELACIONAL>==|/=|<=|>=|<|>)
  | (?P<DELIMITADOR>::|[(),:])
  | (?P<OP_ARITMETICO>\*\*|[+\-*/])
  | (?P<ASIGNACION>=)
  | (?P<DESCONOCIDO>.)
""", re.VERBOSE)


class Token:
    def __init__(self, tipo, valor, linea):
        self.tipo = tipo
        self.valor = valor
        self.linea = linea

    def __repr__(self):
        return f"<{self.tipo} {self.valor!r} linea {self.linea}>"


class Lexico:
    def __init__(self, fuente, traza=0):
        self.fuente = fuente
        self.traza = traza
        self.tokens = self.tokenizar(fuente)
        self.pos = 0
        self.linea = 1
        self.buffer = []

    def tokenizar(self, fuente):
        tokens = []
        linea = 1
        for m in PATRON_TOKEN.finditer(fuente):
            tipo, valor = m.lastgroup, m.group()
            if tipo == "ESPACIO":
                continue
            tokens.append(Token(tipo, valor, linea))
            if tipo == "FIN_LINEA":
                linea += 1
        tokens.append(Token("FIN", "", linea))
        return tokens

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

    def lineaActual(self):
        return self.linea

    def existeTraza(self):
        return bool(self.traza)

from arbol import (Asignacion, Binaria, Declaracion, Escribir, Funcion, Leer, Literal,
                   Programa, Unaria, Variable)

ERRORES_SINTACTICOS = {
    1: "ESPERABA FIN DE INSTRUCCION",
    2: "ESPERABA END PROGRAM",
    3: "ESPERABA UN =",
    4: "ESPERABA UN )",
    5: "ESPERABA UN IDENTIFICADOR",
    6: "INSTRUCCION DESCONOCIDA",
    7: "ESPERABA UNA CONSTANTE, VARIABLE O EXPRESION",
    8: "ESPERABA PROGRAM",
    9: "ESPERABA EL NOMBRE DEL PROGRAMA",
    10: "ESPERABA * , DESPUES DE READ O PRINT",
    11: "ESPERABA UN (",
    15: "ESPERABA UNA ,",
    16: "ESPERABA PRECISION DESPUES DE DOUBLE",
    17: "ESPERABA NONE DESPUES DE IMPLICIT",
    20: "INSTRUCCION DESPUES DE END PROGRAM",
}


class ErrorSintactico(Exception):
    def __init__(self, linea, codigo):
        self.linea = linea
        self.codigo = codigo
        super().__init__(f"LINEA {linea} ERROR SINTACTICO {codigo} :{ERRORES_SINTACTICOS[codigo]}")


class Sintactico:
    def __init__(self, lexico, traza=0):
        self.lexico = lexico
        self.traza = traza
        self.mensajes = []

    def analizar(self):
        self.reporta("INICIO DE ANALISIS SINTACTICO")
        programa = self.programa()
        self.reporta("FIN DE ANALISIS SINTACTICO")
        return programa

    # utilidades

    def reporta(self, texto):
        self.mensajes.append(texto)
        if self.traza:
            print(texto)

    def regla(self, nombre):
        self.reporta(f"ANALISIS SINTACTICO: <{nombre}>")

    def errores(self, codigo, token=None):
        linea = token.linea if token is not None else self.lexico.lineaActual()
        raise ErrorSintactico(linea, codigo)

    def token(self):
        return self.lexico.siguienteToken()

    def ver(self):
        return self.lexico.verToken()

    def es_palabra(self, token, palabra):
        return token.tipo == "RESERVADA" and token.norma == palabra

    def espera_valor(self, valor, codigo):
        token = self.token()
        if token.norma != valor or token.tipo in ("CADENA",):
            self.errores(codigo, token)
        return token

    def espera_identificador(self):
        token = self.token()
        if token.tipo != "IDENTIFICADOR":
            self.errores(5, token)
        return token

    def fin_instruccion(self):
        token = self.token()
        if token.tipo == "FIN":
            self.lexico.devuelveToken(token)
            return
        if token.tipo != "FIN_LINEA":
            self.errores(1, token)

    # programa

    def programa(self):
        self.regla("PROGRAMA")
        token = self.token()
        if not self.es_palabra(token, "PROGRAM"):
            self.errores(8, token)
        nombre = self.token()
        if nombre.tipo != "IDENTIFICADOR":
            self.errores(9, nombre)
        self.fin_instruccion()

        usos = []
        while self.es_palabra(self.ver(), "USE"):
            self.token()
            usos.append(self.espera_identificador().valor)
            self.fin_instruccion()

        implicit_none = False
        if self.es_palabra(self.ver(), "IMPLICIT"):
            self.token()
            if not self.es_palabra(self.token(), "NONE"):
                self.errores(17)
            implicit_none = True
            self.fin_instruccion()

        declaraciones = []
        while self.ver().tipo == "TIPO_DATO":
            declaraciones.append(self.declaracion())
            self.fin_instruccion()

        sentencias = self.bloque(("END",))
        self.fin_programa(nombre.valor)
        return Programa(nombre.valor, usos, implicit_none, declaraciones, sentencias, nombre.linea)

    def fin_programa(self, nombre):
        token = self.token()
        if not self.es_palabra(token, "END"):
            self.errores(2, token)
        token = self.token()
        if self.es_palabra(token, "PROGRAM"):
            token = self.token()
            if token.tipo == "IDENTIFICADOR":
                token = self.token()
        if token.tipo == "FIN_LINEA":
            token = self.token()
        if token.tipo != "FIN":
            self.errores(20, token)

    # declaraciones

    def declaracion(self):
        self.regla("DECLARACION")
        token = self.token()
        linea = token.linea
        tipo = token.norma.lower()
        longitud = 1
        if token.norma == "DOUBLE":
            if not self.es_palabra(self.token(), "PRECISION"):
                self.errores(16)
            tipo = "double precision"
        if tipo == "character":
            longitud = self.longitud_cadena()

        parametro = False
        if self.ver().norma == ",":
            self.token()
            if not self.es_palabra(self.token(), "PARAMETER"):
                self.errores(5)
            parametro = True
        if self.ver().norma == "::":
            self.token()

        variables = []
        while True:
            nombre = self.espera_identificador()
            valor = None
            if self.ver().norma == "=":
                self.token()
                valor = self.expresion()
            variables.append((nombre.valor, valor, nombre.linea))
            if self.ver().norma != ",":
                break
            self.token()
        return Declaracion(tipo, longitud, parametro, variables, linea)

    def longitud_cadena(self):
        # character(len=n), character(n) o character*n
        if self.ver().norma == "(":
            self.token()
            if self.es_palabra(self.ver(), "LEN"):
                self.token()
                self.espera_valor("=", 3)
            token = self.token()
            if token.tipo != "ENTERO":
                self.errores(7, token)
            self.espera_valor(")", 4)
            return int(token.valor)
        if self.ver().norma == "*":
            self.token()
            token = self.token()
            if token.tipo != "ENTERO":
                self.errores(7, token)
            return int(token.valor)
        return 1

    # sentencias

    def bloque(self, terminadores):
        self.regla("BLOQUE")
        sentencias = []
        while True:
            token = self.ver()
            if token.tipo == "FIN" or (token.tipo == "RESERVADA" and token.norma in terminadores):
                return sentencias
            sentencias.append(self.sentencia())
            self.fin_instruccion()

    def sentencia(self):
        self.regla("SENTENCIA")
        token = self.ver()
        if token.tipo == "IDENTIFICADOR":
            return self.asignacion()
        if self.es_palabra(token, "READ"):
            return self.lectura()
        if self.es_palabra(token, "PRINT"):
            return self.escritura()
        self.errores(6, token)

    def asignacion(self):
        self.regla("ASIGNACION")
        nombre = self.token()
        self.espera_valor("=", 3)
        return Asignacion(nombre.valor, self.expresion(), nombre.linea)

    def formato_lista(self):
        if self.token().norma != "*":
            self.errores(10)

    def lectura(self):
        self.regla("LECTURA")
        linea = self.token().linea
        self.formato_lista()
        if self.token().norma != ",":
            self.errores(10)
        variables = [self.espera_identificador().valor]
        while self.ver().norma == ",":
            self.token()
            variables.append(self.espera_identificador().valor)
        return Leer(variables, linea)

    def escritura(self):
        self.regla("ESCRITURA")
        linea = self.token().linea
        self.formato_lista()
        elementos = []
        if self.ver().norma == ",":
            self.token()
            elementos.append(self.expresion())
            while self.ver().norma == ",":
                self.token()
                elementos.append(self.expresion())
        return Escribir(elementos, linea)

    # expresiones, de menor a mayor precedencia

    def expresion(self):
        self.regla("EXPRESION")
        nodo = self.disyuncion()
        while self.ver().norma in (".EQV.", ".NEQV."):
            op = self.token()
            nodo = Binaria(op.norma, nodo, self.disyuncion(), op.linea)
        return nodo

    def disyuncion(self):
        nodo = self.conjuncion()
        while self.ver().norma == ".OR.":
            op = self.token()
            nodo = Binaria(".OR.", nodo, self.conjuncion(), op.linea)
        return nodo

    def conjuncion(self):
        nodo = self.negacion()
        while self.ver().norma == ".AND.":
            op = self.token()
            nodo = Binaria(".AND.", nodo, self.negacion(), op.linea)
        return nodo

    def negacion(self):
        if self.ver().norma == ".NOT.":
            op = self.token()
            return Unaria(".NOT.", self.negacion(), op.linea)
        return self.relacion()

    def relacion(self):
        nodo = self.concatenacion()
        if self.ver().tipo == "OP_RELACIONAL":
            op = self.token()
            nodo = Binaria(op.norma, nodo, self.concatenacion(), op.linea)
        return nodo

    def concatenacion(self):
        nodo = self.aditiva()
        while self.ver().tipo == "CONCATENACION":
            op = self.token()
            nodo = Binaria("//", nodo, self.aditiva(), op.linea)
        return nodo

    def aditiva(self):
        if self.ver().norma in ("+", "-"):
            op = self.token()
            nodo = self.termino()
            if op.norma == "-":
                nodo = Unaria("-", nodo, op.linea)
        else:
            nodo = self.termino()
        while self.ver().norma in ("+", "-"):
            op = self.token()
            nodo = Binaria(op.norma, nodo, self.termino(), op.linea)
        return nodo

    def termino(self):
        self.regla("TERMINO")
        nodo = self.potencia()
        while self.ver().norma in ("*", "/"):
            op = self.token()
            nodo = Binaria(op.norma, nodo, self.potencia(), op.linea)
        return nodo

    def potencia(self):
        base = self.factor()
        if self.ver().norma == "**":
            op = self.token()
            # la potencia asocia por la derecha: 2**3**2 = 2**(3**2)
            return Binaria("**", base, self.potencia(), op.linea)
        return base

    def factor(self):
        self.regla("FACTOR")
        token = self.token()
        if token.tipo == "ENTERO":
            return Literal("integer", int(token.valor), token.valor, token.linea)
        if token.tipo == "REAL":
            return Literal("real", float(token.norma), token.valor, token.linea)
        if token.tipo == "CADENA":
            return Literal("character", token.norma, token.valor, token.linea)
        if token.tipo == "LOGICO":
            return Literal("logical", token.norma == ".TRUE.", token.valor, token.linea)
        if token.norma == "(":
            nodo = self.expresion()
            self.espera_valor(")", 4)
            return nodo
        if token.tipo == "IDENTIFICADOR" or (token.tipo == "TIPO_DATO" and token.norma == "REAL"):
            if self.ver().norma == "(":
                return self.funcion(token)
            if token.tipo == "IDENTIFICADOR":
                return Variable(token.valor, token.linea)
        self.errores(7, token)

    def funcion(self, nombre):
        self.token()
        argumentos = [self.expresion()]
        while self.ver().norma == ",":
            self.token()
            argumentos.append(self.expresion())
        self.espera_valor(")", 4)
        return Funcion(nombre.norma.lower() if nombre.tipo == "TIPO_DATO" else nombre.valor.lower(),
                       argumentos, nombre.linea)

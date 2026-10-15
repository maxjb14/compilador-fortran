import argparse
import os
import sys

from arbol import arbol_texto
from genera import GeneraCodigo
from lexico import Lexico
from maquina import ErrorEjecucion, MaquinaPila
from semantico import Semantico
from sintactico import ErrorSintactico, Sintactico


class Resultado:
    def __init__(self, fuente):
        self.fuente = fuente
        self.lexico = None
        self.traza = []
        self.programa = None
        self.semantico = None
        self.generador = None
        self.etapa = None
        self.errores = []

    @property
    def exito(self):
        return self.etapa is None

    @property
    def advertencias(self):
        return self.semantico.advertencias if self.semantico else []

    def codigo(self):
        return self.generador.texto() if self.generador else ""


class Compilador:
    def compilar(self, fuente):
        r = Resultado(fuente)

        r.lexico = Lexico(fuente)
        if r.lexico.errores:
            r.etapa, r.errores = "lexico", r.lexico.errores
            return r

        sintactico = Sintactico(Lexico(fuente))
        try:
            r.programa = sintactico.analizar()
        except ErrorSintactico as e:
            r.etapa, r.errores = "sintactico", [str(e)]
            return r
        finally:
            r.traza = sintactico.mensajes

        r.semantico = Semantico(r.programa)
        if not r.semantico.analizar():
            r.etapa, r.errores = "semantico", r.semantico.errores
            return r

        r.generador = GeneraCodigo()
        r.generador.generar(r.programa, r.semantico.tabla)
        return r

    def ejecutar(self, resultado, entrada=input, salida=print):
        maquina = MaquinaPila(resultado.codigo(), entrada=entrada, salida=salida)
        return maquina.ejecutar()


def titulo(texto):
    print(f"\n== {texto} ==")


def main():
    parser = argparse.ArgumentParser(description="Compilador de un subconjunto de Fortran 90")
    parser.add_argument("archivo", help="programa fuente .f90")
    parser.add_argument("-l", "--lexico", action="store_true", help="muestra la tabla de tokens")
    parser.add_argument("-s", "--sintactico", action="store_true", help="muestra la traza y el arbol sintactico")
    parser.add_argument("-t", "--tabla", action="store_true", help="muestra la tabla de simbolos")
    parser.add_argument("-c", "--codigo", action="store_true", help="muestra el codigo objeto")
    parser.add_argument("-e", "--ejecutar", action="store_true", help="ejecuta el programa compilado")
    parser.add_argument("-a", "--todo", action="store_true", help="muestra todas las fases y ejecuta")
    args = parser.parse_args()
    if args.todo:
        args.lexico = args.sintactico = args.tabla = args.codigo = args.ejecutar = True

    with open(args.archivo, encoding="utf-8") as f:
        fuente = f.read()
    compilador = Compilador()
    r = compilador.compilar(fuente)

    if args.lexico:
        titulo("ANALISIS LEXICO")
        print(f"{'linea':>5}  {'lexema':<22}token")
        print("\n".join(r.lexico.tabla()))
    if args.sintactico and r.traza:
        titulo("ANALISIS SINTACTICO")
        print("\n".join(r.traza))
        if r.programa:
            titulo("ARBOL SINTACTICO")
            print("\n".join(arbol_texto(r.programa)))
    if args.tabla and r.semantico:
        titulo("TABLA DE SIMBOLOS")
        print("\n".join(r.semantico.tabla.tabla()))

    if r.advertencias:
        titulo("ADVERTENCIAS")
        print("\n".join(r.advertencias))
    if not r.exito:
        titulo(f"ERRORES ({r.etapa.upper()})")
        print("\n".join(r.errores))
        print("\nCOMPILACION FALLIDA")
        sys.exit(1)

    objeto = os.path.splitext(args.archivo)[0] + ".obj"
    r.generador.guardar(objeto)
    if args.codigo:
        titulo("CODIGO OBJETO")
        print(r.codigo(), end="")
    print(f"\nCOMPILACION EXITOSA: {os.path.basename(objeto)}")

    if args.ejecutar:
        titulo("EJECUCION")
        try:
            compilador.ejecutar(r)
        except ErrorEjecucion as e:
            print(e)
            sys.exit(2)


if __name__ == "__main__":
    main()

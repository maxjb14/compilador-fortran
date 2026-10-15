import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from compilador import Compilador  # noqa: E402
from lexico import Lexico  # noqa: E402


def compila(fuente):
    return Compilador().compilar(fuente)


def ejecuta(fuente, entradas=()):
    r = compila(fuente)
    if not r.exito:
        raise AssertionError("\n".join(r.errores))
    valores = iter(entradas)
    salida = []
    Compilador().ejecutar(r, entrada=lambda _: next(valores), salida=salida.append)
    return salida


def programa(cuerpo, declaraciones="INTEGER :: i, n, x"):
    return f"PROGRAM prueba\n  IMPLICIT NONE\n  {declaraciones}\n{cuerpo}\nEND PROGRAM prueba\n"


class PruebasLexico(unittest.TestCase):
    def test_palabras_reservadas_sin_distinguir_mayusculas(self):
        tokens = Lexico("program x\nEnD Program x").tokens
        self.assertEqual([t.tipo for t in tokens if t.tipo == "RESERVADA"], ["RESERVADA"] * 3)
        self.assertEqual(tokens[0].norma, "PROGRAM")

    def test_operadores_con_punto(self):
        normas = [t.norma for t in Lexico("a .GE. 1 .and. .not. b .eq. .TRUE.").tokens]
        self.assertEqual(normas[:-1], ["a", ">=", "1", ".AND.", ".NOT.", "b", "==", ".TRUE."])

    def test_comentarios_y_continuacion(self):
        tokens = Lexico("x = 1 + & ! sigue\n  2 ! fin\ny = 3").tokens
        self.assertEqual([t.valor for t in tokens if t.tipo != "FIN"], ["x", "=", "1", "+", "2", "\n", "y", "=", "3"])
        self.assertEqual(tokens[-2].linea, 3)

    def test_errores_lexicos(self):
        errores = Lexico("a = 2q + 1 # 'abc\nb = .si.").errores
        self.assertEqual(len(errores), 4)
        self.assertIn("ERROR LEXICO 2", errores[0])


class PruebasSintactico(unittest.TestCase):
    def error(self, fuente):
        r = compila(fuente)
        self.assertEqual(r.etapa, "sintactico")
        return r.errores[0]

    def test_falta_program(self):
        self.assertIn("ERROR SINTACTICO 8", self.error("x = 1\nEND PROGRAM p"))

    def test_if_sin_then(self):
        self.assertIn("LINEA 4 ERROR SINTACTICO 12", self.error(programa("  IF (x == 1)\n  END IF")))

    def test_if_con_asignacion(self):
        self.assertIn("ERROR SINTACTICO 18", self.error(programa("  IF (x = 1) THEN\n  END IF")))

    def test_falta_end_if(self):
        self.assertIn("ERROR SINTACTICO 13", self.error(programa("  IF (x == 1) THEN\n  x = 2")))

    def test_falta_end_do(self):
        self.assertIn("ERROR SINTACTICO 14", self.error(programa("  DO i = 1, 3\n  x = 2")))

    def test_parentesis_sin_cerrar(self):
        self.assertIn("ERROR SINTACTICO 4", self.error(programa("  x = (1 + 2")))

    def test_print_sin_formato(self):
        self.assertIn("ERROR SINTACTICO 10", self.error(programa("  PRINT x")))


class PruebasSemantico(unittest.TestCase):
    def errores(self, fuente):
        r = compila(fuente)
        self.assertEqual(r.etapa, "semantico", r.errores)
        return " ".join(r.errores)

    def test_ambiguedad(self):
        self.assertIn("ERROR SEMANTICO 1", self.errores(programa("", "INTEGER :: x\n  REAL :: x")))

    def test_variable_no_declarada(self):
        self.assertIn("ERROR SEMANTICO 3", self.errores(programa("  y = 1")))

    def test_condicion_no_logica(self):
        self.assertIn("ERROR SEMANTICO 6", self.errores(programa("  IF (x) THEN\n  END IF")))

    def test_variable_del_do_modificada(self):
        self.assertIn("ERROR SEMANTICO 8", self.errores(programa("  DO i = 1, 3\n    i = 2\n  END DO")))

    def test_exit_fuera_de_ciclo(self):
        self.assertIn("ERROR SEMANTICO 9", self.errores(programa("  EXIT")))

    def test_parameter(self):
        texto = self.errores(programa("  k = 2", "INTEGER, PARAMETER :: k = 1"))
        self.assertIn("ERROR SEMANTICO 10", texto)

    def test_tipos_incompatibles(self):
        self.assertIn("ERROR SEMANTICO 5", self.errores(programa("  x = 'a' + 1")))

    def test_tipo_implicito_sin_implicit_none(self):
        r = compila("PROGRAM p\n  k = 2\n  r = 1.5\n  PRINT *, k, r\nEND PROGRAM p")
        self.assertTrue(r.exito)
        self.assertEqual(r.semantico.tabla.buscar("k").tipo, "integer")
        self.assertEqual(r.semantico.tabla.buscar("r").tipo, "real")


class PruebasEjecucion(unittest.TestCase):
    def test_aritmetica_como_fortran(self):
        salida = ejecuta(programa("  PRINT *, 7 / 2, -7 / 2, MOD(-7, 2), 2 ** 3 ** 2, 7 / 2.0"))
        self.assertEqual(salida, ["3 -3 -1 512 3.500000"])

    def test_asignacion_trunca_a_entero(self):
        self.assertEqual(ejecuta(programa("  x = 3.9\n  PRINT *, x")), ["3"])

    def test_do_con_paso_negativo(self):
        salida = ejecuta(programa("  DO i = 10, 1, -3\n    PRINT *, i\n  END DO"))
        self.assertEqual(salida, ["10", "7", "4", "1"])

    def test_do_sin_vueltas(self):
        self.assertEqual(ejecuta(programa("  DO i = 5, 1\n    PRINT *, i\n  END DO")), [])

    def test_exit_y_cycle(self):
        cuerpo = "  DO i = 1, 10\n    IF (i == 6) EXIT\n    IF (MOD(i, 2) == 0) CYCLE\n    PRINT *, i\n  END DO"
        self.assertEqual(ejecuta(programa(cuerpo)), ["1", "3", "5"])

    def test_do_while_y_lectura(self):
        cuerpo = "  READ *, n\n  x = 0\n  DO WHILE (n > 0)\n    x = x + n\n    n = n - 1\n  END DO\n  PRINT *, x"
        self.assertEqual(ejecuta(programa(cuerpo), ["4"]), ["10"])

    def test_if_else_if(self):
        cuerpo = "  READ *, n\n  IF (n > 10) THEN\n    PRINT *, 'a'\n  ELSE IF (n > 5) THEN\n    PRINT *, 'b'\n  ELSE\n    PRINT *, 'c'\n  END IF"
        self.assertEqual([ejecuta(programa(cuerpo), [v])[0] for v in ("20", "7", "1")], ["a", "b", "c"])

    def test_cadenas_y_logicos(self):
        salida = ejecuta(programa("  PRINT *, 'ab' // 'cd', 3 > 2 .AND. .NOT. .FALSE."))
        self.assertEqual(salida, ["abcd T"])

    def test_ejemplos_compilan(self):
        carpeta = os.path.join(RAIZ, "ejemplos")
        for nombre in os.listdir(carpeta):
            if nombre.endswith(".f90"):
                with open(os.path.join(carpeta, nombre), encoding="utf-8") as f:
                    r = compila(f.read())
                self.assertEqual(r.exito, not nombre.startswith("errores"), nombre)


if __name__ == "__main__":
    unittest.main()

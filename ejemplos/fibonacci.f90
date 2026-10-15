! primeros terminos de la serie de fibonacci con do while
PROGRAM fibonacci
  IMPLICIT NONE
  INTEGER :: a = 0, b = 1, siguiente, contador = 0
  INTEGER, PARAMETER :: limite = 15
  DO WHILE (contador < limite)
    PRINT *, contador + 1, a
    siguiente = a + b
    a = b
    b = siguiente
    contador = contador + 1
  END DO
END PROGRAM fibonacci

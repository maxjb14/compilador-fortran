! factorial de un numero leido del teclado
PROGRAM factorial
  IMPLICIT NONE
  INTEGER :: n, i, f = 1
  PRINT *, 'Numero:'
  READ *, n
  IF (n < 0) THEN
    PRINT *, 'No existe el factorial de un numero negativo'
    STOP
  END IF
  DO i = 2, n
    f = f * i
  END DO
  PRINT *, n, '! =', f
END PROGRAM factorial

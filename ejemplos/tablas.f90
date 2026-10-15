! tablas de multiplicar del 1 al 3 con paso y ciclos anidados
PROGRAM tablas
  IMPLICIT NONE
  INTEGER :: i, j
  DO i = 1, 3
    PRINT *, 'Tabla del', i
    DO j = 2, 10, 2
      PRINT *, i, 'x', j, '=', i * j
    END DO
  END DO
END PROGRAM tablas

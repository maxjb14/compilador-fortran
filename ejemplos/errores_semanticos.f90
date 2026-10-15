PROGRAM semantico
  IMPLICIT NONE
  INTEGER :: x = 5, i
  CHARACTER :: x = 'a'
  REAL, PARAMETER :: pi = 3.1416
  LOGICAL :: listo = 1
  y = 0
  pi = 3.0
  IF (x) THEN
    PRINT *, 'hola' + 1
  END IF
  DO i = 1, 10
    i = i + 1
  END DO
  EXIT
END PROGRAM semantico

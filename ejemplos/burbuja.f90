! ordenamiento por el metodo burbuja con arreglos
PROGRAM burbuja
  IMPLICIT NONE
  INTEGER, PARAMETER :: n = 8
  INTEGER :: datos(n) = [64, 34, 25, 12, 22, 11, 90, 5]
  INTEGER :: i, j, temp
  LOGICAL :: cambio

  PRINT *, 'Arreglo original:'
  PRINT *, datos

  DO i = 1, n - 1
    cambio = .FALSE.
    ! cada pasada deja el mayor al final
    DO j = 1, n - i
      IF (datos(j) > datos(j + 1)) THEN
        temp = datos(j)
        datos(j) = datos(j + 1)
        datos(j + 1) = temp
        cambio = .TRUE.
      END IF
    END DO
    ! si no hubo intercambios ya esta ordenado
    IF (.NOT. cambio) EXIT
  END DO

  PRINT *, 'Arreglo ordenado:'
  PRINT *, datos
  PRINT *, 'Menor:', MINVAL(datos), ' Mayor:', MAXVAL(datos), ' Suma:', SUM(datos)
END PROGRAM burbuja

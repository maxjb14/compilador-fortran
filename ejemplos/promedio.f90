! promedio, maximo y minimo de n calificaciones
PROGRAM promedio
  IMPLICIT NONE
  INTEGER :: n, i
  REAL :: cal, suma = 0.0, mayor, menor
  PRINT *, 'Cuantas calificaciones?'
  READ *, n
  DO i = 1, n
    READ *, cal
    IF (i == 1) THEN
      mayor = cal
      menor = cal
    END IF
    mayor = MAX(mayor, cal)
    menor = MIN(menor, cal)
    suma = suma + cal
  END DO
  IF (n > 0) THEN
    PRINT *, 'Promedio:', suma / n
    PRINT *, 'Mayor:', mayor, 'Menor:', menor
    IF (suma / n >= 90.0) THEN
      PRINT *, 'Excelente'
    ELSE IF (suma / n >= 60.0) THEN
      PRINT *, 'Aprobado'
    ELSE
      PRINT *, 'Reprobado'
    END IF
  END IF
END PROGRAM promedio

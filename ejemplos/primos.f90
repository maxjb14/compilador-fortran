! numeros primos hasta un limite, con ciclos anidados, exit y cycle
PROGRAM primos
  IMPLICIT NONE
  INTEGER :: n, d, limite
  LOGICAL :: es_primo
  PRINT *, 'Primos hasta:'
  READ *, limite
  DO n = 2, limite
    es_primo = .TRUE.
    DO d = 2, n - 1
      IF (d * d > n) EXIT
      IF (MOD(n, d) /= 0) CYCLE
      es_primo = .FALSE.
      EXIT
    END DO
    IF (es_primo) PRINT *, n
  END DO
END PROGRAM primos

PROGRAM hola
  IMPLICIT NONE
  CHARACTER(len=20) :: nombre
  PRINT *, 'Como te llamas?'
  READ *, nombre
  PRINT *, 'Hola, ' // nombre
END PROGRAM hola

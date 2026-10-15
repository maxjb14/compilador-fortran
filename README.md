# Compilador de Fortran

Proyecto final de Compiladores (D04, 2026-B), CUCEI, Universidad de Guadalajara.
Bradley Maximillian Johnson Beltran (223378957).

Compilador para un subconjunto de Fortran 90 escrito en Python, con un IDE propio. El programa
fuente pasa por análisis léxico, sintáctico y semántico, se traduce a código intermedio para una
máquina de pila y ese código se puede ejecutar.

## Uso

Desde la terminal:

```
python compilador.py ejemplos/factorial.f90 -e      compila y ejecuta
python compilador.py ejemplos/factorial.f90 -a      muestra todas las fases y ejecuta
```

| Opción | Muestra |
|---|---|
| `-l` | tabla de tokens (análisis léxico) |
| `-s` | traza del análisis sintáctico y árbol sintáctico |
| `-t` | tabla de símbolos |
| `-c` | código objeto |
| `-e` | ejecuta el programa |
| `-a` | todo lo anterior |

Al compilar sin errores se guarda el código objeto en un archivo `.obj` junto al fuente.

IDE (necesita `customtkinter`):

```
python ide.py
```

El menú **Compiladores** corre cada fase sobre el código del editor (Análisis Léxico Alt+L,
Sintáctico Alt+S, Semántico Alt+M, Código Intermedio Alt+G, Código Objeto Alt+O) y **Ejecutar**
compila y ejecuta (F5); los `READ` se piden en una ventana. Las líneas con error se marcan en rojo.
El editor pinta las palabras reservadas de Fortran, tiene hacer y deshacer con archivos temporales
(Ctrl+Z, Ctrl+Y), buscar y reemplazar (Ctrl+F), plantillas y ejemplos en el menú Ayuda.

Pruebas:

```
python -m unittest discover -s pruebas
```

## Lenguaje aceptado

```fortran
PROGRAM nombre
  USE modulo                      ! opcional
  IMPLICIT NONE                   ! opcional
  INTEGER :: n, i, total = 0
  REAL, PARAMETER :: pi = 3.1416
  DOUBLE PRECISION :: d
  CHARACTER(len=20) :: nombre
  LOGICAL :: listo = .FALSE.

  READ *, n
  total = total + n * 2
  PRINT *, 'total:', total

  IF (n > 0 .AND. .NOT. listo) THEN
    ...
  ELSE IF (n == 0) THEN
    ...
  ELSE
    ...
  END IF
  IF (n < 0) STOP                 ! if de una linea

  DO i = 1, n, 2
    IF (MOD(i, 3) == 0) CYCLE
    IF (i > 10) EXIT
  END DO

  DO WHILE (n > 0)
    n = n - 1
  END DO
END PROGRAM nombre
```

- Tipos: `INTEGER`, `REAL`, `DOUBLE PRECISION`, `CHARACTER(len=n)`, `LOGICAL` y `PARAMETER`.
- Operadores: `+ - * / **`, `//` (concatenación), `== /= < <= > >=` y sus formas `.EQ. .NE. .LT. .LE. .GT. .GE.`,
  `.AND. .OR. .NOT. .EQV. .NEQV.`.
- Funciones intrínsecas: `MOD ABS MAX MIN SQRT EXP LOG SIN COS INT NINT REAL`.
- No distingue mayúsculas; comentarios con `!`, continuación de línea con `&` y `;` para separar instrucciones.
- Sin `IMPLICIT NONE` las variables no declaradas toman el tipo implícito de Fortran (i a n `INTEGER`, las demás `REAL`).

## Fases

| Archivo | Fase |
|---|---|
| `lexico.py` | Análisis léxico: tokens con línea, tipos de dato, palabras reservadas y errores léxicos |
| `simbolos.py` | Tabla de símbolos: nombre, tipo, clase, dirección (desde 1000), línea y valor |
| `arbol.py` | Nodos del árbol sintáctico |
| `sintactico.py` | Análisis sintáctico por descenso recursivo, con traza y errores numerados |
| `semantico.py` | Análisis semántico: tipos, declaraciones y reglas de `IF` y `DO` |
| `genera.py` | Generación de código intermedio para la máquina de pila |
| `maquina.py` | Máquina de pila que ejecuta el código objeto |
| `compilador.py` | Une las fases; línea de comandos |
| `ide.py` | Entorno de desarrollo |

## Errores

Los errores se reportan con el formato `LINEA n ERROR <FASE> k :MENSAJE`.

Léxicos: 1 carácter desconocido, 2 identificador que empieza con número, 3 cadena sin cerrar,
4 operador con punto desconocido.

Sintácticos:

| | | | |
|---|---|---|---|
| 1 | esperaba fin de instrucción | 11 | esperaba ( |
| 2 | esperaba END PROGRAM | 12 | esperaba THEN |
| 3 | esperaba = | 13 | esperaba END IF |
| 4 | esperaba ) | 14 | esperaba END DO |
| 5 | esperaba identificador | 15 | esperaba , |
| 6 | instrucción desconocida | 16 | esperaba PRECISION después de DOUBLE |
| 7 | esperaba constante, variable o expresión | 17 | esperaba NONE después de IMPLICIT |
| 8 | esperaba PROGRAM | 18 | se encontró = en lugar de un operador relacional |
| 9 | esperaba el nombre del programa | 20 | instrucción después de END PROGRAM |
| 10 | esperaba `* ,` después de READ o PRINT | | |

Semánticos:

| | | | |
|---|---|---|---|
| 1 | ambigüedad: la variable ya tiene otro tipo | 9 | EXIT o CYCLE fuera de un ciclo |
| 2 | variable ya declarada | 10 | asignación a un PARAMETER |
| 3 | variable no declarada | 11 | PARAMETER sin valor |
| 4 | tipos incompatibles en la asignación | 12 | división entre cero |
| 5 | tipos incompatibles en la operación | 13 | función desconocida o argumentos incorrectos |
| 6 | la condición debe ser LOGICAL | 14 | el valor inicial debe ser constante |
| 7 | la variable del DO debe ser INTEGER | 15 | el paso del DO no puede ser cero |
| 8 | se modifica la variable del DO dentro del ciclo | | |

Además hay advertencias: variable usada antes de tener valor, variable que no se usa,
valor real que se trunca a entero, cadena que se recorta y tipo implícito.

## Código objeto

```
.DATA
VAR n INTEGER
.CODE
PUSHA n          apila la direccion de n
PUSHC 5          apila la constante 5
STORE            guarda el valor en la direccion
LOAD             cambia la direccion del tope por su valor
```

| Instrucción | Acción |
|---|---|
| `PUSHC c`, `PUSHA x`, `LOAD`, `STORE` | constantes, direcciones y memoria |
| `ADD MUL DIV IDIV POW NEG` | aritmética (la resta es `NEG` + `ADD`; `IDIV` es la división entera) |
| `EQ NE LT LE GT GE` | comparaciones |
| `AND OR NOT EQV NEQV CONCAT` | operaciones lógicas y de cadenas |
| `CVTI CVTR` | conversión a entero y a real |
| `CALL f n` | función intrínseca con n argumentos |
| `INPUT x`, `OUTPUT`, `NEWLINE` | entrada y salida |
| `LABEL L`, `JMP L`, `JMPF L` | etiquetas y saltos (JMPF salta si el tope es falso) |
| `HALT`, `END` | fin del programa |

## Ejemplos

En `ejemplos/`: `hola`, `factorial`, `promedio`, `fibonacci`, `primos`, `tablas` y tres archivos con
errores léxicos, sintácticos y semánticos.

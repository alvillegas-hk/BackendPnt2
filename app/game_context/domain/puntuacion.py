"""
Regla de puntaje por respuesta. Es la misma que usa el frontend (calcularPuntos).

- Respuesta incorrecta: 0 puntos.
- Respuesta correcta: 10 + 5 * (racha - 1), donde racha es la racha actual
  incluyendo esta respuesta (1ª correcta = 10, 2ª = 15, 3ª = 20, ...).
"""


def calcular_puntos(acerto: bool, racha: int) -> int:
    if not acerto:
        return 0
    return 10 + 5 * (racha - 1)

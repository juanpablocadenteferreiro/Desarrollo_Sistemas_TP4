# Auditoría

# Sección 1: Los tests de la IA (`test_checkout_ia.py`)

| Métrica | Valor |
|---|---|
| Tests | 8, los 8 en verde |
| Cobertura de líneas (`pytest test_checkout_ia.py --cov=checkout`) | 77% (62 sentencias, 14 sin cubrir) |
| Cobertura de ramas (`--cov-branch`) | 73% (26 ramas, 6 parciales) |
| Mutación (`python mutar.py --tests test_checkout_ia.py`) | 58,6% (29 mutantes, 17 muertos, 12 sobrevivientes) |
| Fallas reales de `checkout.py` que detecta | 0 |

## 1. Clasificación de cada test

| # | Test | Clasificación | Por qué |
|---|---|---|---|
| 1 | `test_subtotal` | Tautológico | El esperado es `CATALOGO["buzo"] * 2`: usa el mismo dato y la misma aritmética `float` que el código, así que el código se compara consigo mismo y no detecta un precio mal cargado ni el `float` en lugar de `Decimal`. |
| 2 | `test_total_funciona` | Inútil | Solo verifica `is not None`: cualquier diccionario, con todos los montos mal, pasa. |
| 3 | `test_total_positivo` | Débil | Solo verifica `total > 0`: un descuento sumado en vez de restado o un envío equivocado siguen dando positivo. |
| 4 | `test_cupon_egresados` | Tautológico | El esperado `100000 * 0.15` repite la fórmula del código en `float`, con un subtotal sin medio centavo y una fecha lejos del vencimiento: no ve ni el redondeo (R7) ni el borde del 30/11 (R6). |
| 5 | `test_envio_caba` | Útil (limitado) | Es el único con un esperado que sale de la especificación (CABA = 2.500), aunque usa un subtotal lejos del borde de 60.000 y una sola zona. |
| 6 | `test_descuento_por_cantidad` | Débil | Prueba 6 prendas, el interior de la partición, en vez del borde 5: no detecta el `> 5` que debería ser `>= 5`. |
| 7 | `test_talle_valido` | Inútil | No tiene `assert`: solo comprueba que un ítem perfecto no explota, y no ve que `validar_item` modifica el ítem. |
| 8 | `test_no_explota_con_varios_productos` | Inútil | Atrapa `Exception` y la descarta, y no tiene `assert`: no puede fallar nunca. |

Resumen: 1 útil, 2 débiles, 2 tautológicos, 3 inútiles.

## 2. Puntaje de mutación

```
python mutar.py --tests test_checkout_ia.py

Mutantes generados : 29
Muertos            : 17
Sobrevivientes     : 12
Puntaje de mutación: 58.6%

  línea  40  '<' → '<='              if not (1 <= item["cantidad"] < 10):
  línea  40  10 → 11                 if not (1 <= item["cantidad"] < 10):
  línea  60  '>' → '>='              if cantidad_prendas > 5:
  línea  72  '<' → '<='              if not fecha < datos["vence"]:
  línea  76  '==' → '!='             elif datos["tipo"] == "fijo":
  línea  77  '<' → '<='              if subtotal < datos["minimo"]:
  línea  82  '+' → '-'               descuento += datos["valor"]
  línea  96  '>=' → '>'              if subtotal >= 60000:
  línea  96  60000 → 60001           if subtotal >= 60000:
  línea 107  '+' → '-'               prendas = prendas + item["cantidad"]
  línea 111  '+' → '-'               total = subtotal - descuento + envio
  línea 111  '-' → '+'               total = subtotal - descuento + envio
```

## 3. ¿Por qué casi un 80% de cobertura no detecta ninguna falla?

La cobertura mide qué líneas se ejecutaron, no qué resultados se
verificaron. Los tests de la IA pasan por casi todo `checkout.py`, pero
con asserts que no comprometen nada (`is not None`, `> 0`, ningún assert o
un `except: pass`) o con esperados copiados de la propia implementación
(`CATALOGO["buzo"] * 2`, `100000 * 0.15`), así que el código "se evalúa a sí
mismo" y siempre coincide, incluso en `float`. Además todas las entradas
están en el interior cómodo de cada partición (6 prendas, fecha 1/10,
subtotal 10.000 o 100.000) y ninguna toca un borde (5 prendas, 30/11,
60.000, cantidad 10), que es justamente donde están los `<` que debían ser
`<=`. Tampoco hay un solo caso inválido (talle con espacios, cupón en
minúscula, zona inexistente, carrito vacío) ni se verifica que el carrito
quede sin modificar. Una línea ejecutada con un dato que no la exige y un
assert que no la juzga cuenta como "cubierta" igual que una línea bien
probada. Por eso la mutación (58,6%) es mejor indicador: muestra que 4 de
cada 10 cambios al código pasan desapercibidos.

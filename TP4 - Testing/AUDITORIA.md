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

# Sección 2: Hallazgos

## 1. Linter

```
ruff check checkout.py

F401 [*] `json` imported but unused            --> checkout.py:1:8
E722 Do not use bare `except`                  --> checkout.py:50:9
B008 Do not perform function call `date.today` in argument defaults
                                               --> checkout.py:57:70
E711 Comparison to `None` should be `cond is not None`
                                               --> checkout.py:63:17
B008 Do not perform function call `date.today` in argument defaults
                                               --> checkout.py:102:53
Found 5 errors.
```

## 2. Fallas encontradas

### checkout.py

#### H-01: El dinero se maneja en `float` en todo el módulo

- Archivo y línea: checkout.py, líneas 12-16 (`CATALOGO`), 20-24 (`CUPONES`), 26-31 (`ENVIOS`), 45, 61, 74
- Categoría: numéricos
- Regla: R7 ("todos los importes se manejan como `Decimal`. Nunca `float`") y sección 1 (los montos son `Decimal`)
- Qué pasa: `calcular_total([buzo M ×2], "CABA")` devuelve `{'subtotal': 49999.8, 'descuento': 0, 'envio': 2500, 'total': 52499.8}` (`float` e `int`); se esperaba `Decimal("49999.80")`, `Decimal("0.00")`, `Decimal("2500.00")` y `Decimal("52499.80")`.
- Cómo la encontré: lectura del código (los precios son literales `float`) y ejecutando el ejemplo de la sección 5 de la especificación
- Severidad: alta (es la base de todos los cálculos de dinero y rompe el contrato con `pedidos.py` y la API)

#### H-02: El redondeo no es comercial

- Archivo y línea: checkout.py, líneas 54, 84 y 117 (`round(x, 2)`)
- Categoría: numéricos
- Regla: R7 (el medio centavo redondea hacia arriba)
- Qué pasa: `calcular_descuento(11999.50, 1, "EGRESADOS2026", date(2026, 11, 1))` devuelve `1799.92`; se esperaba `Decimal("1799.93")`, el ejemplo literal de R7. `round()` sobre `float` trabaja con 1799,92499… y sobre `Decimal` usa redondeo bancario: en ningún caso es `ROUND_HALF_UP`.
- Cómo la encontré: lectura del código y el ejemplo explícito de R7
- Severidad: alta (el ejemplo de la propia especificación da un centavo de menos)

#### H-03: Se usa el precio que manda el cliente

- Archivo y línea: checkout.py, línea 49 (`item.get("precio", CATALOGO[...])`)
- Categoría: seguridad
- Regla: R1 ("el precio sale siempre del catálogo")
- Qué pasa: `calcular_subtotal([{"producto": "buzo", "talle": "M", "cantidad": 1, "precio": 1}])` devuelve `1`; se esperaba `Decimal("24999.90")`.
- Cómo la encontré: lectura del código
- Severidad: alta (cualquiera compra un buzo a $1 editando el request)

#### H-04: Un producto inexistente se saltea en silencio

- Archivo y línea: checkout.py, líneas 48-51 (`try` / `except:` / `continue`)
- Categoría: manejo de errores
- Regla: R1 (`PRODUCTO_INEXISTENTE`)
- Qué pasa: `calcular_subtotal([item("pantalon", "M", 1)])` devuelve `0` sin lanzar nada; se esperaba `CheckoutError` con `code == "PRODUCTO_INEXISTENTE"`. El `except:` desnudo esconde además cualquier otro error.
- Cómo la encontré: lectura del código; ruff marca el `except` desnudo (E722)
- Severidad: alta (se puede crear un pedido de $0 + envío con productos que no existen)

#### H-05: `validar_item` no valida el producto

- Archivo y línea: checkout.py, líneas 34-41
- Categoría: lógica y límites
- Regla: R1 y sección 3 (cada ítem se valida en orden: producto, talle, cantidad)
- Qué pasa: `validar_item(item("pantalon", "XXXL", 1))` lanza `TALLE_INVALIDO`; se esperaba `PRODUCTO_INEXISTENTE`. `validar_item(item("pantalon", "M", 1))` no lanza nada.
- Cómo la encontré: lectura del código contra la sección 3
- Severidad: media (se informa el error equivocado y se dejan pasar ítems inválidos)

#### H-06: Producto de otro tipo o ausente no da `PRODUCTO_INEXISTENTE`

- Archivo y línea: checkout.py, líneas 48-51
- Categoría: tipos
- Regla: R1 y sección 1 ("nunca otro tipo de excepción")
- Qué pasa: `calcular_subtotal([item(["buzo"], "M", 1)])` y un ítem sin la clave `"producto"` devuelven `0` (el `TypeError` / `KeyError` se traga); se esperaba `PRODUCTO_INEXISTENTE`.
- Cómo la encontré: lectura del código y ejecución
- Severidad: media (datos mal formados terminan en pedidos de $0)

#### H-07: `validar_item` modifica el ítem, y por lo tanto el carrito

- Archivo y línea: checkout.py, línea 35 (`item["talle"] = item["talle"].upper()`)
- Categoría: efectos laterales
- Regla: R4 ("ninguna función modifica el carrito que recibe")
- Qué pasa: `it = item("buzo", "m", 1); validar_item(it)` deja `it["talle"] == "M"`; se esperaba que siga siendo `"m"`. Lo mismo pasa a través de `calcular_subtotal` y `calcular_total`.
- Cómo la encontré: lectura del código
- Severidad: alta (el frontend reutiliza ese objeto y espera encontrarlo igual)

#### H-08: Un talle con espacios alrededor se rechaza

- Archivo y línea: checkout.py, línea 35 (solo `.upper()`, falta `.strip()`)
- Categoría: strings
- Regla: R2 ("se ignoran los espacios al principio y al final")
- Qué pasa: `validar_item(item("buzo", "  M ", 1))` lanza `TALLE_INVALIDO`; se esperaba que sea válido.
- Cómo la encontré: lectura del código
- Severidad: media (se rechazan compras válidas)

#### H-09: Talle de otro tipo da `AttributeError`

- Archivo y línea: checkout.py, línea 35
- Categoría: tipos
- Regla: R2 y sección 1
- Qué pasa: `validar_item(item("buzo", None, 1))` lanza `AttributeError: 'NoneType' object has no attribute 'upper'`; se esperaba `TALLE_INVALIDO`.
- Cómo la encontré: lectura del código y ejecución
- Severidad: media (por la API termina en un 500)

#### H-10: La cantidad 10 se rechaza

- Archivo y línea: checkout.py, línea 40 (`1 <= cantidad < 10`)
- Categoría: lógica y límites
- Regla: R3 ("entre 1 y 10, ambos inclusive")
- Qué pasa: `validar_item(item("buzo", "M", 10))` lanza `CANTIDAD_INVALIDA`; se esperaba que sea válido.
- Cómo la encontré: lectura del código (el mensaje dice "entre 1 y 10" y la condición excluye el 10)
- Severidad: media (no se pueden vender 10 unidades)

#### H-11: Las cantidades no enteras se aceptan o explotan

- Archivo y línea: checkout.py, línea 40
- Categoría: tipos
- Regla: R3 ("cualquier otro valor, incluidos los no enteros")
- Qué pasa: cantidad `2.0` o `True` se aceptan; `"2"` lanza `TypeError`. Se esperaba `CANTIDAD_INVALIDA` en todos los casos.
- Cómo la encontré: lectura del código y ejecución
- Severidad: media (el JSON `2.5` genera subtotales absurdos y el `TypeError` termina en un 500)

#### H-12: El carrito vacío no se rechaza

- Archivo y línea: checkout.py, líneas 44-54 y 102-107 (no hay ningún `CARRITO_VACIO` en el módulo)
- Categoría: lógica y límites
- Regla: R4 (`CARRITO_VACIO`)
- Qué pasa: `calcular_total([], "CABA")` devuelve `{'subtotal': 0, 'descuento': 0, 'envio': 2500, 'total': 2500}`; `calcular_total(None, "CABA")` lanza `TypeError`. Se esperaba `CARRITO_VACIO`.
- Cómo la encontré: lectura del código
- Severidad: media (se pueden crear pedidos vacíos que solo cobran el envío)

#### H-13: Descuento por cantidad con `> 5` en lugar de `>= 5`

- Archivo y línea: checkout.py, línea 60
- Categoría: lógica y límites
- Regla: R5 ("5 o más")
- Qué pasa: `calcular_descuento(59997.50, 5)` devuelve `0`; se esperaba `Decimal("5999.75")`.
- Cómo la encontré: lectura del código (y es un mutante que sobrevive a la suite de la IA)
- Severidad: media (quien compra exactamente 5 prendas paga $6.000 de más)

#### H-14: El cupón y el descuento por cantidad se acumulan

- Archivo y línea: checkout.py, líneas 61, 74 y 82 (`descuento +=` en las tres ramas)
- Categoría: lógica y límites
- Regla: R6 ("no se acumula con el descuento por cantidad… se aplica el mayor")
- Qué pasa: `calcular_descuento(71997.00, 6, "EGRESADOS2026", date(2026, 11, 1))` devuelve `17999.25` (25%); se esperaba `Decimal("10799.55")` (15%, el mayor).
- Cómo la encontré: lectura del código
- Severidad: alta (se regala dinero en todas las compras grandes con cupón)

#### H-15: El cupón distingue mayúsculas

- Archivo y línea: checkout.py, línea 64 (solo `.strip()`, falta `.upper()`)
- Categoría: strings
- Regla: R6 ("no se distingue mayúscula de minúscula")
- Qué pasa: `calcular_descuento(11999.50, 1, "egresados2026", date(2026, 11, 1))` lanza `CUPON_INVALIDO`; se esperaba `Decimal("1799.93")`.
- Cómo la encontré: lectura del código
- Severidad: media (se rechaza un cupón válido)

#### H-16: Un cupón `""` o de solo espacios da `CUPON_INVALIDO`

- Archivo y línea: checkout.py, líneas 63-67 (`if cupon != None`)
- Categoría: strings
- Regla: R6 ("`None`, `""` o un texto de solo espacios equivalen a no usar cupón. No es un error")
- Qué pasa: `calcular_descuento(11999.50, 1, "")` y con `"   "` lanzan `CUPON_INVALIDO`; se esperaba `Decimal("0.00")`.
- Cómo la encontré: lectura del código; ruff marca la comparación `!= None` (E711)
- Severidad: alta (todo pedido con el campo de cupón vacío falla)

#### H-17: Cupón secreto `DEBUG100` con 100% de descuento

- Archivo y línea: checkout.py, línea 23
- Categoría: seguridad
- Regla: R6 ("estos son los únicos dos cupones que existen")
- Qué pasa: `calcular_total([remera M ×1], "CABA", "DEBUG100")` devuelve `descuento 11999.5` (todo el subtotal); se esperaba `CUPON_INVALIDO`.
- Cómo la encontré: lectura del código, comparando `CUPONES` con la tabla de R6 (ruff no lo marca)
- Severidad: alta (cualquiera que lo descubra se lleva todo gratis)

#### H-18: El descuento puede superar el subtotal

- Archivo y línea: checkout.py, líneas 57-84 (no hay ningún tope)
- Categoría: lógica y límites
- Regla: R6 ("el descuento nunca puede superar el subtotal")
- Qué pasa: `calcular_total([remera M ×6], "CABA", "DEBUG100")` devuelve `descuento 79196.7` sobre `subtotal 71997.0` y `total -7199.7`; se esperaba un descuento menor o igual al subtotal.
- Cómo la encontré: lectura del código (combinación de H-14 y H-17)
- Severidad: alta (la tienda le debería plata al comprador)

#### H-19: `EGRESADOS2026` se rechaza el 30/11

- Archivo y línea: checkout.py, línea 72 (`if not fecha < datos["vence"]`)
- Categoría: lógica y límites
- Regla: R6 ("válido hasta el 30/11/2026 inclusive")
- Qué pasa: `calcular_descuento(11999.50, 1, "EGRESADOS2026", date(2026, 11, 30))` lanza `CUPON_VENCIDO`; se esperaba `Decimal("1799.93")`.
- Cómo la encontré: lectura del código (y es un mutante que sobrevive a la suite de la IA)
- Severidad: media (el último día de la promoción el cupón no anda)

#### H-20: `fecha=None` explícita explota

- Archivo y línea: checkout.py, líneas 57, 72 y 102; lo dispara pedidos.py, línea 50, que siempre pasa `fecha` (por defecto `None`)
- Categoría: fechas
- Regla: R6 ("si no se recibe `fecha`, se usa la fecha del día") y sección 1 (`fecha: date | None = None`)
- Qué pasa: `calcular_descuento(11999.50, 1, "EGRESADOS2026", None)` lanza `TypeError: '<' not supported between instances of 'NoneType' and 'datetime.date'`. Por eso `guardar_pedido(con, "b@a.com", carrito, "CABA", "EGRESADOS2026")` sin fecha también explota. Se esperaba que use la fecha del día.
- Cómo la encontré: lectura del código, comparando la firma con la llamada de `pedidos.guardar_pedido`
- Severidad: alta (todo pedido con cupón que no mande fecha falla)

#### H-21: La fecha por defecto se calcula una sola vez, al importar el módulo

- Archivo y línea: checkout.py, líneas 57 y 102 (`fecha=date.today()`)
- Categoría: fechas
- Regla: R6 ("la fecha del día en que se hace la llamada")
- Qué pasa: si el servidor arranca el 30/11 y sigue corriendo el 1/12, `calcular_descuento(..., "EGRESADOS2026")` sin fecha sigue aplicando el 15%; se esperaba `CUPON_VENCIDO`.
- Cómo la encontré: linter (B008, dos veces) y lectura del código
- Severidad: media (el cupón no vence mientras no se reinicie el servidor)

#### H-22: El envío se calcula sobre el subtotal sin descuento

- Archivo y línea: checkout.py, línea 110 (`calcular_envio(subtotal, zona)`)
- Categoría: lógica y límites
- Regla: R8 ("el subtotal ya con el descuento aplicado")
- Qué pasa: 2 buzos + 1 remera (61.999,30) con `BIENVENIDA` a CABA devuelve `envio 0` y `total 58999.3`; se esperaba envío `Decimal("2500.00")` (la base es 58.999,30, menor a 60.000) y total `Decimal("61499.30")`.
- Cómo la encontré: lectura del código contra R8
- Severidad: media (se regala el envío)

#### H-23: Método inventado `dict_keys.join`

- Archivo y línea: checkout.py, línea 93 (`ENVIOS.keys().join(', ')`)
- Categoría: alucinación
- Regla: R8 (`ZONA_INVALIDA`) y sección 1
- Qué pasa: `calcular_envio(1000, "MARTE")` lanza `AttributeError: 'dict_keys' object has no attribute 'join'`; se esperaba `CheckoutError` con `ZONA_INVALIDA`. Lo correcto es `", ".join(ENVIOS)`.
- Cómo la encontré: lectura del código y ejecución (ruff no lo detecta porque no infiere el tipo)
- Severidad: alta (una zona mal escrita tumba el request con un 500)

#### H-24: Zona de otro tipo da `AttributeError`

- Archivo y línea: checkout.py, línea 88 (`zona.strip()`)
- Categoría: tipos
- Regla: R8 y sección 1
- Qué pasa: `calcular_envio(1000, None)` lanza `AttributeError`; se esperaba `ZONA_INVALIDA`.
- Cómo la encontré: lectura del código
- Severidad: baja (en la práctica la zona llega como texto, pero `checkout` no debe depender de eso)

#### H-25: Cupón de otro tipo da `AttributeError`

- Archivo y línea: checkout.py, línea 64 (`cupon.strip()`)
- Categoría: tipos
- Regla: R6 y sección 1
- Qué pasa: `calcular_descuento(11999.50, 1, 123)` lanza `AttributeError`; se esperaba `CUPON_INVALIDO`.
- Cómo la encontré: lectura del código
- Severidad: media (un JSON con `"cupon": 123` tumba el request)

#### H-26: El parámetro de `calcular_envio` no se llama como en el contrato

- Archivo y línea: checkout.py, línea 87 (`def calcular_envio(subtotal, zona)`)
- Categoría: code smell
- Regla: sección 1 (`calcular_envio(subtotal_con_descuento: Decimal, zona: str)`)
- Qué pasa: `calcular_envio(subtotal_con_descuento=1000, zona="CABA")` lanza `TypeError: unexpected keyword argument`. El nombre `subtotal` además induce la falla H-22.
- Cómo la encontré: lectura del código comparando con la sección 1
- Severidad: baja (solo afecta a quien llame por nombre)

#### H-27: Code smells varios

- Archivo y línea: checkout.py, líneas 1 (`import json` sin usar), 63 (`!= None`) y 40, 60 y 96 (números `10`, `5` y `60000` sueltos)
- Categoría: code smell
- Regla: -
- Qué pasa: no rompe hoy, pero deja código muerto y esconde reglas de negocio en literales.
- Cómo la encontré: linter (F401, E711) y lectura del código
- Severidad: baja

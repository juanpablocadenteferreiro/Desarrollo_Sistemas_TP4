# CASOS.md — Parte 1: casos de prueba de caja negra

Diseñados **solo a partir de `ESPECIFICACION.md`**, antes de abrir
`checkout.py`, `pedidos.py` o `api.py`. Para cada regla de R1 a R11 hay una
tabla con:

- **Partición** y **Tipo**: el grupo de entradas y si es una partición
  válida o inválida según la especificación.
- **Límites**: el valor del borde exacto y los valores a cada lado, cuando
  la regla tiene un borde.
- **Caso** y **Esperado**: la entrada concreta y el resultado que debería
  dar.
- **Nivel**: el nivel de test en el que conviene probarlo (unitario,
  integración o E2E).

Convenciones:

- Los importes se escriben como `Decimal` con dos decimales (`D("2500.00")`).
- `item(p, t, c)` abrevia `{"producto": p, "talle": t, "cantidad": c}`.
- "→ `CODIGO`" significa que se espera `CheckoutError` con `code == "CODIGO"`
  (y **nunca** otro tipo de excepción).
- Fecha de referencia para los cupones cuando no importa: `date(2026, 11, 1)`.
- Precios: buzo 24.999,90 · remera 11.999,50 · campera 47.999,99.

---

## R1 — Catálogo y precios

| Partición | Tipo | Límites | Caso | Esperado | Nivel |
|---|---|---|---|---|---|
| Producto válido `buzo` | válida | — | `calcular_subtotal([item("buzo","M",1)])` | `D("24999.90")` | unitario |
| Producto válido `remera` | válida | — | `calcular_subtotal([item("remera","M",1)])` | `D("11999.50")` | unitario |
| Producto válido `campera` | válida | — | `calcular_subtotal([item("campera","M",1)])` | `D("47999.99")` | unitario |
| Varios ítems, subtotal = Σ precio × cantidad | válida | — | `[item("buzo","M",2), item("remera","S",1)]` | `D("61999.30")` | unitario |
| El precio enviado por el cliente se ignora | válida | — | `[{"producto":"buzo","talle":"M","cantidad":1,"precio":1}]` | `D("24999.90")` | unitario |
| Ídem con `precio_unitario` | válida | — | `[{... "precio_unitario": "0.01"}]` | `D("24999.90")` | unitario |
| Claves extra se ignoran | válida | — | `{"producto":"remera","talle":"M","cantidad":1,"color":"azul"}` | válido, `D("11999.50")` | unitario |
| Producto inexistente | inválida | — | `item("pantalon","M",1)` | → `PRODUCTO_INEXISTENTE` | unitario |
| Producto con mayúscula (debe ir exacto) | inválida | — | `item("Buzo","M",1)` | → `PRODUCTO_INEXISTENTE` | unitario |
| Producto con espacios (debe ir exacto) | inválida | — | `item(" buzo ","M",1)` | → `PRODUCTO_INEXISTENTE` | unitario |
| Producto vacío | inválida | `""` | `item("","M",1)` | → `PRODUCTO_INEXISTENTE` | unitario |
| Producto de otro tipo | inválida | — | `item(None,"M",1)`, `item(["buzo"],"M",1)`, `item(5,"M",1)` | → `PRODUCTO_INEXISTENTE` (nunca `TypeError`) | unitario |
| Falta la clave producto | inválida | — | `{"talle":"M","cantidad":1}` | → `PRODUCTO_INEXISTENTE` (nunca `KeyError`) | unitario |
| El subtotal es `Decimal` | válida | — | cualquier carrito válido | `type(...) is Decimal` | unitario |
| Precio guardado = catálogo aunque el cliente mande otro | válida | — | `guardar_pedido(..., [{"producto":"buzo",...,"precio":1}])` → `obtener_pedido` | `precio_unitario == D("24999.90")` | integración |
| Precio enviado por HTTP se ignora | válida | — | `POST` con `"precio": 1` en el ítem | `subtotal == "24999.90"` | E2E |

## R2 — Talles

| Partición | Tipo | Límites | Caso | Esperado | Nivel |
|---|---|---|---|---|---|
| Talles válidos en mayúscula | válida | `XS` y `XXL` (extremos de la lista) | `validar_item(item("buzo",t,1))` para `XS, S, M, L, XL, XXL` | no lanza | unitario |
| Talle en minúscula | válida | — | `"m"`, `"xxl"`, `"Xl"` | válido | unitario |
| Talle con espacios alrededor | válida | — | `"  M "`, `"\tl\n"` | válido | unitario |
| Talle inexistente | inválida | uno más allá de `XXL` | `"XXXL"` | → `TALLE_INVALIDO` | unitario |
| Talle inexistente | inválida | uno antes de `XS` | `"XXS"` | → `TALLE_INVALIDO` | unitario |
| Talle con espacio en el medio | inválida | — | `"X L"` | → `TALLE_INVALIDO` | unitario |
| Talle vacío / solo espacios | inválida | `""`, `"   "` | — | → `TALLE_INVALIDO` | unitario |
| Talle de otro tipo | inválida | — | `None`, `2`, `["M"]` | → `TALLE_INVALIDO` (nunca `AttributeError`) | unitario |
| Falta la clave talle | inválida | — | `{"producto":"buzo","cantidad":1}` | → `TALLE_INVALIDO` | unitario |
| Talle se guarda normalizado | válida | — | `guardar_pedido` con talle `" m "` | ítem guardado con `"M"` | integración |

## R3 — Cantidad

| Partición | Tipo | Límites | Caso | Esperado | Nivel |
|---|---|---|---|---|---|
| Entero en rango | válida | 1 (borde inferior) | `item("remera","M",1)` | válido | unitario |
| Entero en rango | válida | 10 (borde superior) | `item("remera","M",10)` | válido; subtotal `D("119995.00")` | unitario |
| Entero en rango, interior | válida | 2, 9 | — | válido | unitario |
| Debajo del rango | inválida | 0 (justo debajo), -1 | — | → `CANTIDAD_INVALIDA` | unitario |
| Encima del rango | inválida | 11 (justo encima), 100 | — | → `CANTIDAD_INVALIDA` | unitario |
| No entero numérico | inválida | — | `2.0`, `1.5`, `Decimal("2")` | → `CANTIDAD_INVALIDA` | unitario |
| Texto | inválida | — | `"2"` | → `CANTIDAD_INVALIDA` | unitario |
| Booleano (subclase de `int` en Python) | inválida | — | `True`, `False` | → `CANTIDAD_INVALIDA` | unitario |
| Nulo / falta la clave | inválida | — | `None`, sin `"cantidad"` | → `CANTIDAD_INVALIDA` | unitario |
| Cantidad enviada como texto por HTTP | inválida | — | `POST` con `"cantidad": "2"` | 422 `CANTIDAD_INVALIDA` | E2E |

## R4 — Carrito

| Partición | Tipo | Límites | Caso | Esperado | Nivel |
|---|---|---|---|---|---|
| Carrito vacío | inválida | 0 ítems | `calcular_total([], "CABA")` | → `CARRITO_VACIO` | unitario |
| Carrito vacío en `calcular_subtotal` | inválida | 0 ítems | `calcular_subtotal([])` | → `CARRITO_VACIO` | unitario |
| Carrito nulo | inválida | — | `calcular_total(None, "CABA")` | → `CARRITO_VACIO` | unitario |
| Carrito con 1 ítem | válida | 1 (borde) | `[item("remera","M",1)]` | válido | unitario |
| No se modifica el carrito (`calcular_total`) | válida | — | carrito con talle `" m "`, cupón y precio extra; comparar con `copy.deepcopy` previo | idéntico al original | unitario |
| No se modifica el carrito (`calcular_subtotal` / `validar_item`) | válida | — | ídem | idéntico | unitario |
| No se modifica el carrito aunque falle | inválida | — | carrito con un ítem inválido al final | idéntico tras el error | unitario |
| Llamar dos veces con el mismo carrito da lo mismo | válida | — | `calcular_total(c, ...)` ×2 | resultados iguales | unitario |
| `guardar_pedido` no modifica el carrito | válida | — | ídem a través de `pedidos` | idéntico | integración |
| Carrito vacío por HTTP | inválida | — | `POST` con `"carrito": []` | 422 `CARRITO_VACIO` | E2E |

## R5 — Descuento por cantidad

| Partición | Tipo | Límites | Caso | Esperado | Nivel |
|---|---|---|---|---|---|
| Menos de 5 prendas: sin descuento | válida | 4 (justo debajo) | `calcular_descuento(D("47998.00"), 4)` | `D("0.00")` | unitario |
| 5 o más prendas: 10% | válida | 5 (borde) | `calcular_descuento(D("59997.50"), 5)` | `D("5999.75")` | unitario |
| 5 o más prendas | válida | 6 (justo encima) | `calcular_descuento(D("71997.00"), 6)` | `D("7199.70")` | unitario |
| Prendas sumadas entre ítems | válida | 2+3 = 5 | `calcular_total([item("remera","M",2), item("remera","L",3)], "CABA")` | descuento `D("5999.75")` | unitario |
| Prendas sumadas, 4 ítems de 1 | válida | 1+1+1+1 = 4 | 4 ítems distintos de cantidad 1 | descuento `D("0.00")` | unitario |
| Ítems distintos, no ítems: 2 ítems × cantidad 3 | válida | 6 prendas | `[item("buzo","M",3), item("remera","M",3)]` | 10% de `D("110998.20")` = `D("11099.82")` | unitario |
| 10% con medio centavo | válida | — | `calcular_descuento(D("0.05"), 5)` (10% = 0.005) | `D("0.01")` | unitario |

## R6 — Cupones

| Partición | Tipo | Límites | Caso | Esperado | Nivel |
|---|---|---|---|---|---|
| Sin cupón: `None` | válida | — | `calcular_descuento(D("11999.50"), 1, None)` | `D("0.00")` | unitario |
| Sin cupón: `""` | válida | — | ídem con `""` | `D("0.00")` | unitario |
| Sin cupón: solo espacios | válida | — | ídem con `"   "` | `D("0.00")` | unitario |
| `EGRESADOS2026` vigente | válida | 30/11/2026 (borde) | `calcular_descuento(D("11999.50"),1,"EGRESADOS2026",date(2026,11,30))` | `D("1799.93")` | unitario |
| `EGRESADOS2026` vigente | válida | 29/11/2026 (justo antes) | ídem `date(2026,11,29)` | `D("1799.93")` | unitario |
| `EGRESADOS2026` vencido | inválida | 01/12/2026 (justo después) | ídem `date(2026,12,1)` | → `CUPON_VENCIDO` | unitario |
| `EGRESADOS2026` vencido (año siguiente) | inválida | — | `date(2027,1,1)` | → `CUPON_VENCIDO` | unitario |
| Cupón en minúscula y con espacios | válida | — | `"  egresados2026 "`, `" bienvenida"` | válidos | unitario |
| `BIENVENIDA` sin alcanzar el mínimo | inválida | 19.999,99 (justo debajo) | `calcular_descuento(D("19999.99"),1,"BIENVENIDA")` | → `CUPON_MINIMO_NO_ALCANZADO` | unitario |
| `BIENVENIDA` en el mínimo | válida | 20.000,00 (borde) | `calcular_descuento(D("20000.00"),1,"BIENVENIDA")` | `D("3000.00")` | unitario |
| `BIENVENIDA` sobre el mínimo | válida | 20.000,01 | ídem | `D("3000.00")` | unitario |
| Cupón inexistente | inválida | — | `"DESCUENTO50"`, `"EGRESADOS2025"`, `"EGRESADOS"` | → `CUPON_INVALIDO` | unitario |
| Cupón de otro tipo | inválida | — | `123` | → `CUPON_INVALIDO` (nunca `AttributeError`) | unitario |
| Cupón vs. cantidad: gana el cupón | válida | 5 remeras + `EGRESADOS2026` | 15% = `D("8999.63")` vs 10% = `D("5999.75")` | `D("8999.63")` (no la suma) | unitario |
| Cupón vs. cantidad: gana la cantidad | válida | 5 remeras + `BIENVENIDA` | 3.000 vs `D("5999.75")` | `D("5999.75")` (no la suma 8.999,75) | unitario |
| Solo cupón (menos de 5 prendas) | válida | 2 remeras (`D("23999.00")`) + `BIENVENIDA` | — | `D("3000.00")` | unitario |
| Descuento ≤ subtotal | válida | — | `calcular_descuento(s, n, cupon)` para varios casos | `descuento <= subtotal` | unitario |
| Fecha por defecto = día de la llamada | inválida | hoy simulado 01/12/2026 | `calcular_descuento(..., "EGRESADOS2026")` sin fecha | → `CUPON_VENCIDO` (se evalúa en cada llamada, no al importar) | unitario |
| Fecha por defecto, dentro de la vigencia | válida | hoy simulado 30/11/2026 | ídem | `D("1799.93")` | unitario |
| Cupón vencido por HTTP | inválida | — | `POST` con `"fecha": "2026-12-01"` | 422 `CUPON_VENCIDO` | E2E |
| Cupón normalizado al guardar | válida | — | `guardar_pedido(..., cupon=" egresados2026 ")` | `cupon == "EGRESADOS2026"` | integración |
| Cupón vacío al guardar | válida | — | `cupon=""` / `"   "` | `cupon is None` | integración |

## R7 — Dinero y redondeo

| Partición | Tipo | Límites | Caso | Esperado | Nivel |
|---|---|---|---|---|---|
| Medio centavo redondea hacia arriba | válida | ,xx5 | 15% de `D("11999.50")` = 1799,925 | `D("1799.93")` (no `1799.92`) | unitario |
| Medio centavo con 10% | válida | ,xx5 | 10% de `D("0.05")` | `D("0.01")` | unitario |
| Menos de medio centavo redondea hacia abajo | válida | ,xx4 | 15% de `D("0.03")` = 0,0045 | `D("0.00")` | unitario |
| Todos los importes son `Decimal` | válida | — | `calcular_total(...)` | los 4 valores `isinstance(..., Decimal)` y no `float` | unitario |
| Importes con dos decimales | válida | — | `calcular_total(...)` | `str(total)` termina en 2 decimales (`"52499.80"`) | unitario |
| Sin errores de float | válida | — | 3 × remera = `D("35998.50")` exacto | `== D("35998.50")` | unitario |
| Montos persistidos sin pérdida | válida | — | guardar y leer el pedido con 15% (`1799.93`) | `Decimal` idéntico, `type is Decimal` | integración |
| Montos por HTTP como texto | válida | — | `POST` / `GET` | `"1799.93"` (str), nunca número JSON | E2E |

## R8 — Envío

| Partición | Tipo | Límites | Caso | Esperado | Nivel |
|---|---|---|---|---|---|
| CABA | válida | — | `calcular_envio(D("1000"), "CABA")` | `D("2500.00")` | unitario |
| GBA | válida | — | `calcular_envio(D("1000"), "GBA")` | `D("4000.00")` | unitario |
| INTERIOR | válida | — | `calcular_envio(D("1000"), "INTERIOR")` | `D("6500.00")` | unitario |
| RETIRO | válida | — | `calcular_envio(D("1000"), "RETIRO")` | `D("0.00")` | unitario |
| Zona en minúscula / mezcla | válida | — | `"gba"`, `"Interior"` | `D("4000.00")`, `D("6500.00")` | unitario |
| Zona con espacios | válida | — | `"  caba "` | `D("2500.00")` | unitario |
| Envío pago: base < 60.000 | válida | 59.999,99 (justo debajo) | `calcular_envio(D("59999.99"), "CABA")` | `D("2500.00")` | unitario |
| Envío gratis: base ≥ 60.000 | válida | 60.000,00 (borde) | `calcular_envio(D("60000.00"), "INTERIOR")` | `D("0.00")` | unitario |
| Envío gratis | válida | 60.000,01 (justo encima) | ídem | `D("0.00")` | unitario |
| La base es el subtotal **con descuento** | válida | subtotal 61.999,30 − 3.000 = 58.999,30 | `calcular_total([item("buzo","M",2), item("remera","M",1)], "CABA", "BIENVENIDA")` | envío `D("2500.00")` (no gratis) | unitario |
| Mismo carrito sin cupón | válida | 61.999,30 ≥ 60.000 | ídem sin cupón | envío `D("0.00")` | unitario |
| Zona inexistente | inválida | — | `"MARTE"`, `"CAPITAL"` | → `ZONA_INVALIDA` | unitario |
| Zona vacía / solo espacios | inválida | — | `""`, `"  "` | → `ZONA_INVALIDA` | unitario |
| Zona de otro tipo | inválida | — | `None`, `1` | → `ZONA_INVALIDA` (nunca `AttributeError`) | unitario |
| Zona normalizada al guardar | válida | — | `guardar_pedido(..., zona=" gba ")` | `zona == "GBA"` | integración |

## R9 — Total

| Partición | Tipo | Límites | Caso | Esperado | Nivel |
|---|---|---|---|---|---|
| Ejemplo de la especificación | válida | — | `calcular_total([item("buzo","M",2)], "CABA")` | `{"subtotal": D("49999.80"), "descuento": D("0.00"), "envio": D("2500.00"), "total": D("52499.80")}` | unitario |
| Total con cupón 15% | válida | — | `calcular_total([item("remera","M",1)], "CABA", "EGRESADOS2026", date(2026,11,30))` | total `D("12699.57")` | unitario |
| Total con descuento por cantidad | válida | 5 remeras | `calcular_total([item("remera","M",5)], "GBA")` | subtotal `59997.50`, desc `5999.75`, envío `4000.00`, total `D("57997.75")` | unitario |
| Total con envío gratis | válida | — | `[item("campera","M",1), item("buzo","M",1)]`, `"INTERIOR"` | total `D("72999.89")` | unitario |
| Total con retiro | válida | — | `[item("remera","M",1)]`, `"RETIRO"` | total `D("11999.50")` | unitario |
| Claves exactas del resultado | válida | — | cualquier caso válido | `set(r) == {"subtotal","descuento","envio","total"}` | unitario |
| Total por HTTP coincide con `calcular_total` | válida | — | `POST` válido | `"12699.57"` | E2E |

## R10 — Persistencia (`pedidos.py`)

Todos con una base SQLite real en un archivo dentro de `tmp_path`, una base
nueva por test, y la verificación hecha con **otra conexión** cuando importa
la visibilidad.

| Partición | Tipo | Límites | Caso | Esperado | Nivel |
|---|---|---|---|---|---|
| Error de negocio: se propaga | inválida | — | `guardar_pedido(con, "a@a.com", [item("remera","XXXL",1)], "CABA")` | → `CheckoutError` `TALLE_INVALIDO` | integración |
| Error de negocio: no queda nada | inválida | error en el 2º ítem | carrito con un ítem válido y uno inválido; contar filas de pedidos e ítems con otra conexión | 0 pedidos, 0 ítems | integración |
| Error en zona/cupón: no queda nada | inválida | — | zona `"MARTE"`, cupón vencido | 0 filas | integración |
| Pedido definitivo: visible desde otra conexión | válida | — | guardar con `con1`; leer con `conectar(ruta)` nuevo | pedido completo con todos los ítems | integración |
| Pedido con varios ítems | válida | 3 ítems | ídem | los 3 ítems, en orden, con producto/talle/cantidad | integración |
| Montos idénticos a `calcular_total` | válida | 15% con medio centavo | remera + `EGRESADOS2026` 30/11 | `subtotal 11999.50`, `descuento 1799.93`, `envio 2500.00`, `total 12699.57`, todos `Decimal` | integración |
| Montos con centavos que el float no representa | válida | — | 3 buzos + 1 campera, etc. | iguales a `calcular_total`, `type is Decimal` | integración |
| `precio_unitario` del catálogo | válida | — | ítem con `"precio": 1`, `"precio_unitario": 5` | `precio_unitario == D("24999.90")` | integración |
| Email normalizado | válida | — | `"  Ana@Mail.COM "` | `"ana@mail.com"` | integración |
| Zona / talle / cupón normalizados | válida | — | `" caba "`, `" m "`, `" egresados2026 "` | `"CABA"`, `"M"`, `"EGRESADOS2026"` | integración |
| Cupón vacío → `None` | válida | `""`, `"   "`, `None` | — | `cupon is None` | integración |
| `obtener_pedido` de id inexistente | inválida | id 999, id 0 | — | `None` | integración |
| `guardar_pedido` devuelve el id | válida | — | dos pedidos | ids distintos y `obtener_pedido(id)["id"] == id` | integración |
| `pedidos_de` sin distinguir mayúsculas/espacios | válida | — | guardar con `"ana@mail.com"`, buscar `" ANA@Mail.com "` | encuentra el pedido | integración |
| `pedidos_de` ordenado del más reciente al más antiguo | válida | 3 pedidos | guardar p1, p2, p3 | `[p3, p2, p1]` | integración |
| `pedidos_de` sin pedidos | válida | — | email sin compras | `[]` | integración |
| `pedidos_de` no mezcla clientes | válida | — | pedidos de dos emails | solo los del email pedido | integración |
| Inyección SQL en el email | inválida | — | `pedidos_de(con, "x' OR '1'='1")` | `[]`, sin excepción, sin pedidos ajenos | integración |
| Email con comilla legítima | válida | — | `"o'brien@mail.com"` | se guarda y se recupera | integración |

## R11 — API HTTP (`api.py`)

Servidor real con `crear_servidor(str(tmp_path / "tienda.db"), 0)`, requests
HTTP de verdad con `urllib.request`.

| Partición | Tipo | Límites | Caso | Esperado | Nivel |
|---|---|---|---|---|---|
| POST válido con cupón | válida | — | body del ejemplo de la spec | 201, `{"id", "subtotal":"11999.50", "descuento":"1799.93", "envio":"2500.00", "total":"12699.57"}` | E2E |
| POST válido sin cupón ni fecha | válida | — | solo email, zona, carrito | 201 | E2E |
| Montos como texto | válida | — | POST y GET | `isinstance(valor, str)` para todos los montos y `precio_unitario` | E2E |
| GET del pedido creado | válida | — | `GET /api/v1/pedidos/{id}` | 200, mismo contenido que el POST, items correctos, datos normalizados | E2E |
| Error de negocio | inválida | — | talle `"XXXL"` | 422 `{"error":{"code":"TALLE_INVALIDO","message":...}}` y el pedido **no** se crea | E2E |
| Cada código de negocio → 422 | inválida | — | producto, talle, cantidad, carrito vacío, cupón inválido/vencido/mínimo, zona | 422 con el `code` correspondiente | E2E |
| JSON inválido | inválida | — | body `"{no es json"` | 400 `JSON_INVALIDO` | E2E |
| Body JSON que no es objeto | inválida | — | `[]`, `"texto"` | 400 `DATOS_INCOMPLETOS` | E2E |
| Falta email / zona / carrito | inválida | — | body sin cada uno | 400 `DATOS_INCOMPLETOS` | E2E |
| Campo con otro tipo | inválida | — | `"carrito": "buzo"`, `"email": 5`, `"zona": null` | 400 `DATOS_INCOMPLETOS` | E2E |
| Fecha mal formada | inválida | — | `"30/11/2026"`, `"2026-13-01"`, `"hoy"` | 400 `FECHA_INVALIDA` | E2E |
| Fecha bien formada | válida | `"2026-11-30"` | — | 201 con 15% | E2E |
| GET de id inexistente | inválida | — | `/api/v1/pedidos/999` | 404 `PEDIDO_INEXISTENTE` | E2E |
| GET con id no numérico | inválida | — | `/api/v1/pedidos/abc` | 404 (nunca 500) | E2E |
| Ruta inexistente | inválida | — | `GET /api/v1/otra`, `POST /api/v1/otra` | 404 `RUTA_INEXISTENTE` | E2E |
| Formato de error uniforme | inválida | — | todos los errores | `{"error": {"code": str, "message": str}}` | E2E |
| Nunca 500 | inválida | — | todos los anteriores | status ≠ 500 | E2E |

---

## Orden de validación (sección 3)

| Caso | Problemas presentes | Esperado | Nivel |
|---|---|---|---|
| Carrito vacío + zona inválida + cupón inválido | 1, 3, 4 | `CARRITO_VACIO` | unitario |
| Ítem 1 con producto inválido, ítem 2 con talle inválido | 2 (ítems en orden) | `PRODUCTO_INEXISTENTE` | unitario |
| Ítem 1 con talle inválido, ítem 2 con producto inválido | 2 (ítems en orden) | `TALLE_INVALIDO` | unitario |
| Un ítem con producto, talle y cantidad inválidos | 2 (producto primero) | `PRODUCTO_INEXISTENTE` | unitario |
| Un ítem con talle y cantidad inválidos | 2 (talle antes que cantidad) | `TALLE_INVALIDO` | unitario |
| Cantidad inválida + cupón inválido | 2 antes que 3 | `CANTIDAD_INVALIDA` | unitario |
| Cupón inválido + zona inválida | 3 antes que 4 | `CUPON_INVALIDO` | unitario |
| Cupón vencido + zona inválida | 3 antes que 4 | `CUPON_VENCIDO` | unitario |
| `BIENVENIDA` sin mínimo + zona inválida | 3 antes que 4 | `CUPON_MINIMO_NO_ALCANZADO` | unitario |
| Zona inválida sola | 4 | `ZONA_INVALIDA` | unitario |

## Cobertura de códigos de error

| `code` | Casos que lo cubren (unitario) | Integración | E2E |
|---|---|---|---|
| `PRODUCTO_INEXISTENTE` | R1 | — | 422 |
| `TALLE_INVALIDO` | R2 | propagación en R10 | 422 |
| `CANTIDAD_INVALIDA` | R3 | — | 422 |
| `CARRITO_VACIO` | R4 | — | 422 |
| `CUPON_INVALIDO` | R6 | — | 422 |
| `CUPON_VENCIDO` | R6 | rollback en R10 | 422 |
| `CUPON_MINIMO_NO_ALCANZADO` | R6 | — | 422 |
| `ZONA_INVALIDA` | R8 | rollback en R10 | 422 |
| `JSON_INVALIDO` | — | — | 400 |
| `DATOS_INCOMPLETOS` | — | — | 400 |
| `FECHA_INVALIDA` | — | — | 400 |
| `PEDIDO_INEXISTENTE` | — | — | 404 |
| `RUTA_INEXISTENTE` | — | — | 404 |

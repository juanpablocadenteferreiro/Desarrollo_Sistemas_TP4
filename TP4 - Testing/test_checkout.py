from datetime import date
from decimal import Decimal

import pytest

import checkout
from checkout import (
    CheckoutError,
    calcular_descuento,
    calcular_envio,
    calcular_subtotal,
    calcular_total,
    validar_item,
)

HOY_VIGENTE = date(2026, 10, 1)


def item(producto="buzo", talle="M", cantidad=1, **extra):
    return {"producto": producto, "talle": talle, "cantidad": cantidad, **extra}


def codigo_de_error(funcion, *args):
    with pytest.raises(CheckoutError) as error:
        funcion(*args)
    return error.value.code


def test_cantidad_cero_es_invalida():
    assert codigo_de_error(validar_item, item(cantidad=0)) == "CANTIDAD_INVALIDA"


def test_el_ejemplo_de_la_especificacion_devuelve_los_importes_en_decimal():
    carrito = [item("buzo", "M", 2)]

    resultado = calcular_total(carrito, "CABA")

    assert resultado == {
        "subtotal": Decimal("49999.80"),
        "descuento": Decimal("0.00"),
        "envio": Decimal("2500.00"),
        "total": Decimal("52499.80"),
    }
    assert all(type(valor) is Decimal for valor in resultado.values())


def test_el_15_por_ciento_redondea_el_medio_centavo_hacia_arriba():
    subtotal = Decimal("11999.50")

    descuento = calcular_descuento(subtotal, 1, "EGRESADOS2026", HOY_VIGENTE)

    assert descuento == Decimal("1799.93")


def test_el_precio_que_manda_el_cliente_se_ignora():
    carrito = [item("buzo", "M", 1, precio=1)]

    subtotal = calcular_subtotal(carrito)

    assert subtotal == Decimal("24999.90")


def test_un_producto_que_no_esta_en_el_catalogo_es_inexistente():
    carrito = [item("pantalon", "M", 1)]

    codigo = codigo_de_error(calcular_subtotal, carrito)

    assert codigo == "PRODUCTO_INEXISTENTE"


def test_validar_item_informa_el_producto_antes_que_el_talle():
    invalido = item("pantalon", "XXXL", 1)

    codigo = codigo_de_error(validar_item, invalido)

    assert codigo == "PRODUCTO_INEXISTENTE"


@pytest.mark.parametrize(
    "invalido",
    [
        item(["buzo"], "M", 1),
        {"talle": "M", "cantidad": 1},
    ],
)
def test_un_producto_de_otro_tipo_o_ausente_es_inexistente(invalido):
    codigo = codigo_de_error(validar_item, invalido)

    assert codigo == "PRODUCTO_INEXISTENTE"


def test_calcular_total_no_modifica_el_carrito():
    carrito = [item("buzo", "m", 2), item("remera", "l", 1)]

    calcular_total(carrito, "CABA")

    assert carrito == [item("buzo", "m", 2), item("remera", "l", 1)]


def test_un_talle_con_espacios_alrededor_es_valido():
    carrito = [item("buzo", "  M ", 1)]

    subtotal = calcular_subtotal(carrito)

    assert subtotal == Decimal("24999.90")


@pytest.mark.parametrize(
    "invalido",
    [
        item("buzo", None, 1),
        item("buzo", 2, 1),
        {"producto": "buzo", "cantidad": 1},
    ],
)
def test_un_talle_de_otro_tipo_o_ausente_es_invalido(invalido):
    codigo = codigo_de_error(validar_item, invalido)

    assert codigo == "TALLE_INVALIDO"


@pytest.mark.parametrize(
    "cantidad, esperado",
    [
        (1, Decimal("11999.50")),
        (10, Decimal("119995.00")),
    ],
)
def test_las_cantidades_1_y_10_son_validas(cantidad, esperado):
    carrito = [item("remera", "M", cantidad)]

    subtotal = calcular_subtotal(carrito)

    assert subtotal == esperado


@pytest.mark.parametrize("cantidad", [2.0, 1.5, True, "2", None])
def test_una_cantidad_que_no_es_entera_es_invalida(cantidad):
    invalido = item("remera", "M", cantidad)

    codigo = codigo_de_error(validar_item, invalido)

    assert codigo == "CANTIDAD_INVALIDA"


@pytest.mark.parametrize("carrito", [[], None])
def test_un_carrito_vacio_lanza_carrito_vacio(carrito):
    codigo = codigo_de_error(calcular_total, carrito, "CABA")

    assert codigo == "CARRITO_VACIO"


@pytest.mark.parametrize(
    "prendas, subtotal, esperado",
    [
        (4, Decimal("47998.00"), Decimal("0.00")),
        (5, Decimal("59997.50"), Decimal("5999.75")),
        (6, Decimal("71997.00"), Decimal("7199.70")),
    ],
)
def test_desde_5_prendas_se_aplica_el_10_por_ciento(prendas, subtotal, esperado):
    descuento = calcular_descuento(subtotal, prendas, None, HOY_VIGENTE)

    assert descuento == esperado


def hoy_simulado(monkeypatch, dia):
    class FechaFija(date):
        @classmethod
        def today(cls):
            return dia

    monkeypatch.setattr(checkout, "date", FechaFija)


@pytest.mark.parametrize(
    "producto, esperado",
    [
        ("buzo", Decimal("24999.90")),
        ("remera", Decimal("11999.50")),
        ("campera", Decimal("47999.99")),
    ],
)
def test_cada_producto_cuesta_lo_que_dice_el_catalogo(producto, esperado):
    carrito = [item(producto, "M", 1)]

    subtotal = calcular_subtotal(carrito)

    assert subtotal == esperado


def test_el_subtotal_suma_precio_por_cantidad_de_todos_los_items():
    carrito = [item("buzo", "M", 2), item("remera", "S", 1)]

    subtotal = calcular_subtotal(carrito)

    assert subtotal == Decimal("61999.30")


@pytest.mark.parametrize("producto", ["Buzo", " buzo ", ""])
def test_el_producto_se_escribe_exacto_en_minuscula(producto):
    invalido = item(producto, "M", 1)

    codigo = codigo_de_error(validar_item, invalido)

    assert codigo == "PRODUCTO_INEXISTENTE"


def test_un_item_que_no_es_un_diccionario_es_inexistente():
    carrito = ["buzo"]

    codigo = codigo_de_error(calcular_subtotal, carrito)

    assert codigo == "PRODUCTO_INEXISTENTE"


@pytest.mark.parametrize("talle", ["XS", "S", "M", "L", "XL", "XXL", "m", "xxl", "\tl\n"])
def test_los_talles_validos_no_distinguen_mayusculas(talle):
    carrito = [item("remera", talle, 1)]

    subtotal = calcular_subtotal(carrito)

    assert subtotal == Decimal("11999.50")


@pytest.mark.parametrize("talle", ["XXXL", "XXS", "X L", "", "   "])
def test_un_talle_que_no_existe_es_invalido(talle):
    invalido = item("buzo", talle, 1)

    codigo = codigo_de_error(validar_item, invalido)

    assert codigo == "TALLE_INVALIDO"


@pytest.mark.parametrize("cantidad", [0, -1, 11, 100])
def test_una_cantidad_fuera_de_1_a_10_es_invalida(cantidad):
    invalido = item("remera", "M", cantidad)

    codigo = codigo_de_error(validar_item, invalido)

    assert codigo == "CANTIDAD_INVALIDA"


def test_validar_item_no_modifica_el_item():
    original = item("buzo", " m ", 1)

    validar_item(original)

    assert original == item("buzo", " m ", 1)


def test_el_carrito_no_se_modifica_aunque_haya_un_error():
    carrito = [item("buzo", "m", 1), item("remera", "XXXL", 1)]

    codigo_de_error(calcular_total, carrito, "CABA")

    assert carrito == [item("buzo", "m", 1), item("remera", "XXXL", 1)]


def test_las_prendas_se_suman_entre_todos_los_items():
    carrito = [item("remera", "M", 2), item("remera", "L", 3)]

    resultado = calcular_total(carrito, "CABA", None, HOY_VIGENTE)

    assert resultado["descuento"] == Decimal("5999.75")


def test_cuatro_items_de_una_prenda_no_tienen_descuento():
    carrito = [item("remera", "M", 1)] * 4

    resultado = calcular_total(carrito, "CABA", None, HOY_VIGENTE)

    assert resultado["descuento"] == Decimal("0.00")


@pytest.mark.parametrize("cupon", [None, "", "   "])
def test_sin_cupon_no_hay_descuento(cupon):
    subtotal = Decimal("11999.50")

    descuento = calcular_descuento(subtotal, 1, cupon, HOY_VIGENTE)

    assert descuento == Decimal("0.00")


@pytest.mark.parametrize("dia", [date(2026, 11, 29), date(2026, 11, 30)])
def test_egresados2026_vale_hasta_el_30_de_noviembre_inclusive(dia):
    subtotal = Decimal("11999.50")

    descuento = calcular_descuento(subtotal, 1, "EGRESADOS2026", dia)

    assert descuento == Decimal("1799.93")


@pytest.mark.parametrize("dia", [date(2026, 12, 1), date(2027, 1, 1)])
def test_egresados2026_despues_del_30_de_noviembre_esta_vencido(dia):
    subtotal = Decimal("11999.50")

    codigo = codigo_de_error(calcular_descuento, subtotal, 1, "EGRESADOS2026", dia)

    assert codigo == "CUPON_VENCIDO"


@pytest.mark.parametrize("cupon", ["egresados2026", "  Egresados2026 "])
def test_el_cupon_no_distingue_mayusculas_ni_espacios(cupon):
    subtotal = Decimal("11999.50")

    descuento = calcular_descuento(subtotal, 1, cupon, HOY_VIGENTE)

    assert descuento == Decimal("1799.93")


@pytest.mark.parametrize("subtotal", [Decimal("20000.00"), Decimal("20000.01")])
def test_bienvenida_desde_20000_descuenta_3000(subtotal):
    descuento = calcular_descuento(subtotal, 1, " bienvenida", HOY_VIGENTE)

    assert descuento == Decimal("3000.00")


def test_bienvenida_debajo_de_20000_no_alcanza_el_minimo():
    subtotal = Decimal("19999.99")

    codigo = codigo_de_error(calcular_descuento, subtotal, 1, "BIENVENIDA", HOY_VIGENTE)

    assert codigo == "CUPON_MINIMO_NO_ALCANZADO"


@pytest.mark.parametrize("cupon", ["DEBUG100", "DESCUENTO50", "EGRESADOS2025", 123])
def test_un_cupon_que_no_existe_es_invalido(cupon):
    subtotal = Decimal("11999.50")

    codigo = codigo_de_error(calcular_descuento, subtotal, 1, cupon, HOY_VIGENTE)

    assert codigo == "CUPON_INVALIDO"


@pytest.mark.parametrize(
    "cupon, esperado",
    [
        ("EGRESADOS2026", Decimal("8999.63")),
        ("BIENVENIDA", Decimal("5999.75")),
    ],
)
def test_el_cupon_y_el_descuento_por_cantidad_no_se_acumulan(cupon, esperado):
    subtotal = Decimal("59997.50")

    descuento = calcular_descuento(subtotal, 5, cupon, HOY_VIGENTE)

    assert descuento == esperado


def test_un_cupon_fijo_con_menos_de_5_prendas_descuenta_3000():
    carrito = [item("remera", "M", 2)]

    resultado = calcular_total(carrito, "CABA", "BIENVENIDA", HOY_VIGENTE)

    assert resultado["descuento"] == Decimal("3000.00")


def test_sin_fecha_el_30_de_noviembre_el_cupon_esta_vigente(monkeypatch):
    hoy_simulado(monkeypatch, date(2026, 11, 30))
    subtotal = Decimal("11999.50")

    descuento = calcular_descuento(subtotal, 1, "EGRESADOS2026")

    assert descuento == Decimal("1799.93")


def test_sin_fecha_el_1_de_diciembre_el_cupon_esta_vencido(monkeypatch):
    hoy_simulado(monkeypatch, date(2026, 12, 1))
    subtotal = Decimal("11999.50")

    codigo = codigo_de_error(calcular_descuento, subtotal, 1, "EGRESADOS2026")

    assert codigo == "CUPON_VENCIDO"


def test_con_fecha_none_se_usa_el_dia_de_la_llamada(monkeypatch):
    hoy_simulado(monkeypatch, date(2026, 12, 1))
    subtotal = Decimal("11999.50")

    codigo = codigo_de_error(calcular_descuento, subtotal, 1, "EGRESADOS2026", None)

    assert codigo == "CUPON_VENCIDO"


@pytest.mark.parametrize(
    "subtotal, cupon, esperado",
    [
        (20000, "BIENVENIDA", Decimal("3000.00")),
        (11999.50, "EGRESADOS2026", Decimal("1799.93")),
    ],
)
def test_un_subtotal_que_no_es_decimal_se_calcula_en_decimal(subtotal, cupon, esperado):
    descuento = calcular_descuento(subtotal, 1, cupon, HOY_VIGENTE)

    assert descuento == esperado
    assert type(descuento) is Decimal


@pytest.mark.parametrize(
    "subtotal, prendas, cupon, esperado",
    [
        (Decimal("0.05"), 5, None, Decimal("0.01")),
        (Decimal("0.03"), 1, "EGRESADOS2026", Decimal("0.00")),
    ],
)
def test_el_redondeo_es_comercial_al_centavo(subtotal, prendas, cupon, esperado):
    descuento = calcular_descuento(subtotal, prendas, cupon, HOY_VIGENTE)

    assert descuento == esperado


@pytest.mark.parametrize(
    "zona, esperado",
    [
        ("CABA", Decimal("2500.00")),
        ("GBA", Decimal("4000.00")),
        ("INTERIOR", Decimal("6500.00")),
        ("RETIRO", Decimal("0.00")),
        ("gba", Decimal("4000.00")),
        ("  Interior ", Decimal("6500.00")),
    ],
)
def test_el_envio_depende_de_la_zona(zona, esperado):
    envio = calcular_envio(Decimal("1000.00"), zona)

    assert envio == esperado


@pytest.mark.parametrize(
    "subtotal, esperado",
    [
        (Decimal("59999.99"), Decimal("2500.00")),
        (Decimal("60000.00"), Decimal("0.00")),
        (Decimal("60000.01"), Decimal("0.00")),
    ],
)
def test_el_envio_es_gratis_desde_60000(subtotal, esperado):
    envio = calcular_envio(subtotal, "CABA")

    assert envio == esperado


@pytest.mark.parametrize("zona", ["MARTE", "CAPITAL", "", "  ", None, 1])
def test_una_zona_que_no_existe_es_invalida(zona):
    codigo = codigo_de_error(calcular_envio, Decimal("1000.00"), zona)

    assert codigo == "ZONA_INVALIDA"


def test_el_envio_se_calcula_sobre_el_subtotal_con_descuento():
    carrito = [item("buzo", "M", 2), item("remera", "M", 1)]

    resultado = calcular_total(carrito, "CABA", "BIENVENIDA", HOY_VIGENTE)

    assert resultado["envio"] == Decimal("2500.00")
    assert resultado["total"] == Decimal("61499.30")


def test_sin_descuento_el_mismo_carrito_tiene_envio_gratis():
    carrito = [item("buzo", "M", 2), item("remera", "M", 1)]

    resultado = calcular_total(carrito, "CABA", None, HOY_VIGENTE)

    assert resultado["envio"] == Decimal("0.00")
    assert resultado["total"] == Decimal("61999.30")


@pytest.mark.parametrize(
    "carrito, zona, cupon, esperado",
    [
        ([item("remera", "M", 1)], "CABA", "EGRESADOS2026", {
            "subtotal": Decimal("11999.50"),
            "descuento": Decimal("1799.93"),
            "envio": Decimal("2500.00"),
            "total": Decimal("12699.57"),
        }),
        ([item("remera", "M", 5)], "GBA", None, {
            "subtotal": Decimal("59997.50"),
            "descuento": Decimal("5999.75"),
            "envio": Decimal("4000.00"),
            "total": Decimal("57997.75"),
        }),
        ([item("campera", "M", 1), item("buzo", "M", 1)], "INTERIOR", None, {
            "subtotal": Decimal("72999.89"),
            "descuento": Decimal("0.00"),
            "envio": Decimal("0.00"),
            "total": Decimal("72999.89"),
        }),
        ([item("remera", "M", 1)], "RETIRO", None, {
            "subtotal": Decimal("11999.50"),
            "descuento": Decimal("0.00"),
            "envio": Decimal("0.00"),
            "total": Decimal("11999.50"),
        }),
    ],
)
def test_el_total_es_subtotal_menos_descuento_mas_envio(carrito, zona, cupon, esperado):
    resultado = calcular_total(carrito, zona, cupon, date(2026, 11, 30))

    assert resultado == esperado


@pytest.mark.parametrize(
    "carrito, zona, cupon, esperado",
    [
        ([], "MARTE", "NOEXISTE", "CARRITO_VACIO"),
        ([item("pantalon", "M", 1), item("buzo", "XXXL", 1)], "CABA", None, "PRODUCTO_INEXISTENTE"),
        ([item("buzo", "XXXL", 1), item("pantalon", "M", 1)], "CABA", None, "TALLE_INVALIDO"),
        ([item("pantalon", "XXXL", 0)], "CABA", None, "PRODUCTO_INEXISTENTE"),
        ([item("buzo", "XXXL", 0)], "CABA", None, "TALLE_INVALIDO"),
        ([item("buzo", "M", 0)], "CABA", "NOEXISTE", "CANTIDAD_INVALIDA"),
        ([item("buzo", "M", 1)], "MARTE", "NOEXISTE", "CUPON_INVALIDO"),
        ([item("remera", "M", 1)], "MARTE", "BIENVENIDA", "CUPON_MINIMO_NO_ALCANZADO"),
        ([item("buzo", "M", 1)], "MARTE", None, "ZONA_INVALIDA"),
    ],
)
def test_se_informa_el_primer_error_segun_el_orden_de_validacion(carrito, zona, cupon, esperado):
    codigo = codigo_de_error(calcular_total, carrito, zona, cupon, HOY_VIGENTE)

    assert codigo == esperado


def test_un_cupon_vencido_se_informa_antes_que_la_zona():
    carrito = [item("buzo", "M", 1)]

    codigo = codigo_de_error(calcular_total, carrito, "MARTE", "EGRESADOS2026", date(2026, 12, 1))

    assert codigo == "CUPON_VENCIDO"

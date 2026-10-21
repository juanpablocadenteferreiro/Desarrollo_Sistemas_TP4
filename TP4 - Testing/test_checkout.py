from datetime import date
from decimal import Decimal

import pytest

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

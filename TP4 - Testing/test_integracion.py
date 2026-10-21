from datetime import date
from decimal import Decimal

import pytest

import pedidos
from checkout import CheckoutError

HOY_VIGENTE = date(2026, 10, 1)


@pytest.fixture
def ruta(tmp_path):
    return str(tmp_path / "tienda.db")


@pytest.fixture
def con(ruta):
    conexion = pedidos.conectar(ruta)
    pedidos.crear_esquema(conexion)
    yield conexion
    conexion.close()


def item(producto="buzo", talle="M", cantidad=1, **extra):
    return {"producto": producto, "talle": talle, "cantidad": cantidad, **extra}


def contar(ruta, tabla):
    assert tabla in ("pedidos", "items")
    otra = pedidos.conectar(ruta)
    try:
        return otra.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
    finally:
        otra.close()


def test_un_id_inexistente_devuelve_none(con):
    assert pedidos.obtener_pedido(con, 999) is None


def test_un_error_de_negocio_no_deja_ni_el_pedido_ni_sus_items(ruta, con):
    carrito = [item("remera", "M", 1), item("remera", "XXXL", 1)]

    with pytest.raises(CheckoutError) as error:
        pedidos.guardar_pedido(con, "ana@mail.com", carrito, "CABA", None, HOY_VIGENTE)

    assert error.value.code == "TALLE_INVALIDO"
    assert contar(ruta, "pedidos") == 0
    assert contar(ruta, "items") == 0


def test_el_pedido_guardado_se_ve_completo_desde_otra_conexion(ruta, con):
    carrito = [item("buzo", "M", 2), item("remera", "L", 1)]
    pedido_id = pedidos.guardar_pedido(con, "ana@mail.com", carrito, "CABA", None, HOY_VIGENTE)

    otra = pedidos.conectar(ruta)
    try:
        pedido = pedidos.obtener_pedido(otra, pedido_id)
    finally:
        otra.close()

    assert pedido["total"] == Decimal("61999.30")
    assert pedido["items"] == [
        {"producto": "buzo", "talle": "M", "cantidad": 2, "precio_unitario": Decimal("24999.90")},
        {"producto": "remera", "talle": "L", "cantidad": 1, "precio_unitario": Decimal("11999.50")},
    ]


def test_los_montos_guardados_se_leen_como_decimal_sin_perdida(con):
    carrito = [item("remera", "M", 1)]
    pedido_id = pedidos.guardar_pedido(
        con, "ana@mail.com", carrito, "CABA", "EGRESADOS2026", date(2026, 11, 30)
    )

    pedido = pedidos.obtener_pedido(con, pedido_id)

    montos = {clave: pedido[clave] for clave in ("subtotal", "descuento", "envio", "total")}
    assert montos == {
        "subtotal": Decimal("11999.50"),
        "descuento": Decimal("1799.93"),
        "envio": Decimal("2500.00"),
        "total": Decimal("12699.57"),
    }
    assert [str(valor) for valor in montos.values()] == ["11999.50", "1799.93", "2500.00", "12699.57"]


def test_pedidos_de_no_se_puede_alterar_con_inyeccion_sql(con):
    pedidos.guardar_pedido(con, "ana@mail.com", [item("buzo", "M", 1)], "CABA", None, HOY_VIGENTE)

    encontrados = pedidos.pedidos_de(con, "x' OR '1'='1")

    assert encontrados == []

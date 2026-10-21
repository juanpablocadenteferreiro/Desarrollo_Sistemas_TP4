from datetime import date
from decimal import ROUND_HALF_UP, Decimal


class CheckoutError(Exception):
    def __init__(self, code, mensaje):
        super().__init__(mensaje)
        self.code = code
        self.mensaje = mensaje


CATALOGO = {
    "buzo": Decimal("24999.90"),
    "remera": Decimal("11999.50"),
    "campera": Decimal("47999.99"),
}

CENTAVO = Decimal("0.01")
SIN_DESCUENTO = Decimal("0.00")

TALLES = ["XS", "S", "M", "L", "XL", "XXL"]

CANTIDAD_MINIMA = 1
CANTIDAD_MAXIMA = 10

PRENDAS_PARA_DESCUENTO = 5
DESCUENTO_POR_CANTIDAD = Decimal("0.10")

CUPONES = {
    "EGRESADOS2026": {"tipo": "porcentaje", "valor": Decimal("0.15"), "vence": date(2026, 11, 30)},
    "BIENVENIDA": {"tipo": "fijo", "valor": Decimal("3000.00"), "minimo": Decimal("20000.00")},
}

ENVIOS = {
    "CABA": Decimal("2500.00"),
    "GBA": Decimal("4000.00"),
    "INTERIOR": Decimal("6500.00"),
    "RETIRO": Decimal("0.00"),
}

MINIMO_ENVIO_GRATIS = Decimal("60000.00")


def redondear(monto):
    return monto.quantize(CENTAVO, ROUND_HALF_UP)


def validar_item(item):
    producto = item.get("producto") if isinstance(item, dict) else None
    if not isinstance(producto, str) or producto not in CATALOGO:
        raise CheckoutError("PRODUCTO_INEXISTENTE", f"Producto inexistente: {producto}")

    talle = item.get("talle")

    if not isinstance(talle, str) or talle.strip().upper() not in TALLES:
        raise CheckoutError("TALLE_INVALIDO", f"Talle inválido: {talle}")

    cantidad = item.get("cantidad")

    if type(cantidad) is not int or not (CANTIDAD_MINIMA <= cantidad <= CANTIDAD_MAXIMA):
        raise CheckoutError("CANTIDAD_INVALIDA", "La cantidad debe estar entre 1 y 10")


def calcular_subtotal(carrito):
    if not carrito:
        raise CheckoutError("CARRITO_VACIO", "El carrito está vacío")

    subtotal = Decimal("0.00")
    for item in carrito:
        validar_item(item)
        subtotal += CATALOGO[item["producto"]] * item["cantidad"]

    return redondear(subtotal)


def descuento_del_cupon(subtotal, cupon, fecha):
    if cupon is None:
        return SIN_DESCUENTO

    if not isinstance(cupon, str):
        raise CheckoutError("CUPON_INVALIDO", f"El cupón no existe: {cupon}")

    codigo = cupon.strip().upper()

    if codigo == "":
        return SIN_DESCUENTO

    if codigo not in CUPONES:
        raise CheckoutError("CUPON_INVALIDO", f"El cupón no existe: {cupon}")

    datos = CUPONES[codigo]

    if datos["tipo"] == "porcentaje":
        if fecha > datos["vence"]:
            raise CheckoutError("CUPON_VENCIDO", "El cupón está vencido")
        return redondear(subtotal * datos["valor"])

    if subtotal < datos["minimo"]:
        raise CheckoutError(
            "CUPON_MINIMO_NO_ALCANZADO",
            f"El cupón requiere una compra mínima de ${datos['minimo']}",
        )
    return datos["valor"]


def calcular_descuento(subtotal, cantidad_prendas, cupon=None, fecha=None):
    if fecha is None:
        fecha = date.today()

    if not isinstance(subtotal, Decimal):
        subtotal = Decimal(str(subtotal))

    descuento_cantidad = SIN_DESCUENTO
    if cantidad_prendas >= PRENDAS_PARA_DESCUENTO:
        descuento_cantidad = redondear(subtotal * DESCUENTO_POR_CANTIDAD)

    descuento_cupon = descuento_del_cupon(subtotal, cupon, fecha)

    return min(max(descuento_cantidad, descuento_cupon), subtotal)


def calcular_envio(subtotal, zona):
    codigo = zona.strip().upper() if isinstance(zona, str) else None

    if codigo not in ENVIOS:
        raise CheckoutError(
            "ZONA_INVALIDA",
            f"Zona inválida. Opciones: {', '.join(ENVIOS)}",
        )

    if subtotal >= MINIMO_ENVIO_GRATIS:
        return SIN_DESCUENTO

    return ENVIOS[codigo]


def calcular_total(carrito, zona, cupon=None, fecha=None):
    subtotal = calcular_subtotal(carrito)

    prendas = 0
    for item in carrito:
        prendas = prendas + item["cantidad"]

    descuento = calcular_descuento(subtotal, prendas, cupon, fecha)
    envio = calcular_envio(subtotal - descuento, zona)
    total = subtotal - descuento + envio

    resultado = {
        "subtotal": subtotal,
        "descuento": descuento,
        "envio": envio,
        "total": redondear(total),
    }
    return resultado

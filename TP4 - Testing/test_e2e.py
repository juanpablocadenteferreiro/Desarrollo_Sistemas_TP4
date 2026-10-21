import json
import threading
import urllib.error
import urllib.request

import pytest

import api

RUTA = "/api/v1/pedidos"


@pytest.fixture
def url(tmp_path):
    servidor = api.crear_servidor(str(tmp_path / "tienda.db"), 0)
    threading.Thread(target=servidor.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    yield f"http://127.0.0.1:{servidor.server_address[1]}"
    servidor.shutdown()
    servidor.server_close()


def pedir(url, metodo, ruta, cuerpo=None, crudo=None):
    datos = crudo if crudo is not None else (json.dumps(cuerpo).encode() if cuerpo is not None else None)
    req = urllib.request.Request(url + ruta, data=datos, method=metodo,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def compra(**cambios):
    cuerpo = {"email": "ana@mail.com", "zona": "CABA",
              "carrito": [{"producto": "buzo", "talle": "M", "cantidad": 1}]}
    cuerpo.update(cambios)
    return cuerpo


def test_una_ruta_inexistente_devuelve_404(url):
    status, cuerpo = pedir(url, "GET", "/api/v1/otra")
    assert status == 404
    assert cuerpo["error"]["code"] == "RUTA_INEXISTENTE"


def test_post_crea_el_pedido_y_devuelve_los_montos_como_texto(url):
    nueva = compra()

    status, cuerpo = pedir(url, "POST", RUTA, nueva)

    assert status == 201
    assert type(cuerpo["id"]) is int
    assert {clave: valor for clave, valor in cuerpo.items() if clave != "id"} == {
        "subtotal": "24999.90",
        "descuento": "0.00",
        "envio": "2500.00",
        "total": "27499.90",
    }


def test_get_devuelve_el_pedido_creado_completo(url):
    _, creado = pedir(url, "POST", RUTA, compra(email=" Ana@Mail.com ", zona="caba"))

    status, pedido = pedir(url, "GET", f"{RUTA}/{creado['id']}")

    assert status == 200
    assert pedido == {
        "id": creado["id"],
        "email": "ana@mail.com",
        "zona": "CABA",
        "cupon": None,
        "subtotal": "24999.90",
        "descuento": "0.00",
        "envio": "2500.00",
        "total": "27499.90",
        "items": [
            {"producto": "buzo", "talle": "M", "cantidad": 1, "precio_unitario": "24999.90"},
        ],
    }


def test_un_error_de_negocio_devuelve_422_con_su_codigo(url):
    invalida = compra(carrito=[{"producto": "buzo", "talle": "XXXL", "cantidad": 1}])

    status, cuerpo = pedir(url, "POST", RUTA, invalida)

    assert status == 422
    assert cuerpo["error"]["code"] == "TALLE_INVALIDO"
    assert type(cuerpo["error"]["message"]) is str


def test_un_cuerpo_que_no_es_json_devuelve_400(url):
    status, cuerpo = pedir(url, "POST", RUTA, crudo=b"{no es json")

    assert status == 400
    assert cuerpo["error"]["code"] == "JSON_INVALIDO"


def test_si_falta_el_email_devuelve_400(url):
    incompleta = compra()
    del incompleta["email"]

    status, cuerpo = pedir(url, "POST", RUTA, incompleta)

    assert status == 400
    assert cuerpo["error"]["code"] == "DATOS_INCOMPLETOS"


def test_un_pedido_que_no_existe_devuelve_404(url):
    status, cuerpo = pedir(url, "GET", f"{RUTA}/999")

    assert status == 404
    assert cuerpo["error"]["code"] == "PEDIDO_INEXISTENTE"

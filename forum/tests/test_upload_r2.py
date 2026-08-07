"""
Tests de `upload_r2`: la clave del objeto en R2.

Las 2527 imágenes migradas antes de que el comando entrara al repo viven en
`imagenes/<basename>`. Si el comando escribe en otra ruta, el bucket queda
partido en dos esquemas y la reanudación de los 2249 pendientes no cuadra.
"""

import pytest

from forum.management.commands.upload_r2 import clave_r2


@pytest.mark.parametrize(
    "url_final,ext,esperado",
    [
        # El basename sale de la URL FINAL: archive.org redirige a otra captura.
        (
            "https://web.archive.org/web/2020im_/https://i.imgur.com/9vqZ4rF.gif",
            ".gif",
            "imagenes/9vqZ4rF.gif",
        ),
        # Emoticonos del tema de SMF: el caso mayoritario del archivo.
        (
            "https://www.boombang.nl/forum/Themes/boombang/images/post/xx.gif",
            ".gif",
            "imagenes/xx.gif",
        ),
        # La query string de Discord no debe acabar en la clave.
        (
            "https://cdn.discordapp.com/attachments/33/60/unknown.png?ex=1",
            ".png",
            "imagenes/unknown.png",
        ),
    ],
)
def test_respeta_el_esquema_ya_migrado(url_final, ext, esperado):
    assert clave_r2(url_final, ext, 1) == esperado


@pytest.mark.parametrize(
    "url_final",
    [
        "https://ejemplo.com/ruta/",  # sin basename
        "https://ejemplo.com/../../etc/passwd",  # traversal
        "https://ejemplo.com/.hidden",  # sin extensión real
    ],
)
def test_cae_al_id_cuando_el_nombre_no_sirve(url_final):
    assert clave_r2(url_final, ".jpg", 42) == "imagenes/42.jpg"


def test_sanea_los_caracteres_raros():
    clave = clave_r2("https://ejemplo.com/imagen con espacios.png", ".png", 1)
    assert clave == "imagenes/imagen_con_espacios.png"


def test_la_clave_nunca_escapa_del_prefijo():
    for url in ("https://e.com/a/../../b.gif", "https://e.com//x.gif"):
        assert clave_r2(url, ".gif", 1).count("/") == 1

#!/usr/bin/env python
"""Captura el estado visual del foro para comparar antes/después de un cambio de CSS.

Guarda, por cada página: una captura de pantalla completa y los estilos computados
de una muestra de elementos. Con eso se puede verificar que una refactorización de
estilos no altera el resultado renderizado.

Uso:
    python scripts/capturar_visual.py <etiqueta> [--base http://127.0.0.1:8010]
    python scripts/capturar_visual.py --comparar antes despues

Requiere el servidor levantado y `playwright` instalado.
"""

import argparse
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SALIDA = RAIZ / ".visual"

# Páginas públicas representativas de cada plantilla.
PAGINAS = {
    "portada": "/",
    "categorias": "/categorias/",
    "categoria": "/categoria/general/",
    "buscar": "/buscar/?q=demo",
    "login": "/accounts/login/",
    "signup": "/accounts/signup/",
    "perfil": "/perfil/demo/",
    "password_reset": "/accounts/password/reset/",
}

# Selectores cuyo estilo computado se compara. Cubren navbar, tipografía,
# tarjetas, botones y formularios: donde se notaría cualquier regresión.
SELECTORES = [
    "body", "nav", "header", "footer", "main",
    "h1", "h2", "a", "button", "input", "form",
    ".card-sunset", ".btn-sunset", ".form-sunset", ".form-input-sunset",
    ".form-btn-primary", ".stat-number", ".hero-title", ".navbar-sunset",
    "article", "section",
]

# Propiedades que definen "el aspecto". Se omiten las geométricas dependientes
# del contenido (width/height), que varían por datos y no por CSS.
PROPIEDADES = [
    "color", "backgroundColor", "backgroundImage", "fontFamily", "fontSize",
    "fontWeight", "lineHeight", "letterSpacing", "textTransform",
    "borderRadius", "borderColor", "borderWidth", "borderStyle",
    "boxShadow", "opacity", "padding", "margin", "display",
    "flexDirection", "justifyContent", "alignItems", "gap", "textAlign",
]

JS_ESTILOS = """
([selectores, propiedades]) => {
  const salida = {};
  for (const sel of selectores) {
    const nodos = Array.from(document.querySelectorAll(sel)).slice(0, 3);
    salida[sel] = nodos.map(n => {
      const s = getComputedStyle(n);
      const o = {};
      for (const p of propiedades) o[p] = s[p];
      return o;
    });
  }
  return salida;
}
"""


def capturar(etiqueta, base, temas=("dark", "light")):
    from playwright.sync_api import sync_playwright

    destino = SALIDA / etiqueta
    destino.mkdir(parents=True, exist_ok=True)
    estilos = {}

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        for tema in temas:
            pagina = navegador.new_page(viewport={"width": 1280, "height": 900})
            # El toggle guarda el tema en localStorage; se fija antes de cargar.
            pagina.add_init_script(f"localStorage.setItem('theme', '{tema}')")
            for nombre, ruta in PAGINAS.items():
                url = base.rstrip("/") + ruta
                try:
                    pagina.goto(url, wait_until="networkidle", timeout=30000)
                except Exception as e:  # noqa: BLE001
                    print(f"  ⚠ {nombre} ({tema}): {type(e).__name__}")
                    continue
                pagina.wait_for_timeout(400)  # fuentes y Alpine
                clave = f"{nombre}-{tema}"
                pagina.screenshot(path=str(destino / f"{clave}.png"), full_page=True)
                estilos[clave] = pagina.evaluate(JS_ESTILOS, [SELECTORES, PROPIEDADES])
                print(f"  ✓ {clave}")
            pagina.close()
        navegador.close()

    (destino / "estilos.json").write_text(
        json.dumps(estilos, indent=1, sort_keys=True), encoding="utf-8"
    )
    print(f"\nGuardado en {destino}")


def comparar(a, b):
    da, db = SALIDA / a, SALIDA / b
    ea = json.loads((da / "estilos.json").read_text(encoding="utf-8"))
    eb = json.loads((db / "estilos.json").read_text(encoding="utf-8"))

    diferencias = []
    for clave in sorted(set(ea) | set(eb)):
        if clave not in ea or clave not in eb:
            diferencias.append(f"{clave}: solo en {a if clave in ea else b}")
            continue
        for sel in sorted(set(ea[clave]) | set(eb[clave])):
            la, lb = ea[clave].get(sel, []), eb[clave].get(sel, [])
            if len(la) != len(lb):
                diferencias.append(f"{clave} {sel}: {len(la)} → {len(lb)} elementos")
                continue
            for i, (na, nb) in enumerate(zip(la, lb)):
                for prop in na:
                    if na[prop] != nb.get(prop):
                        diferencias.append(
                            f"{clave} {sel}[{i}].{prop}: {na[prop]!r} → {nb.get(prop)!r}"
                        )

    # Comparación de píxeles
    pixeles = []
    for png in sorted(da.glob("*.png")):
        otro = db / png.name
        if not otro.exists():
            pixeles.append(f"{png.name}: falta en {b}")
            continue
        if png.read_bytes() != otro.read_bytes():
            pixeles.append(png.name)

    print(f"=== Estilos computados: {len(diferencias)} diferencias ===")
    for d in diferencias[:60]:
        print("  •", d)
    if len(diferencias) > 60:
        print(f"  … y {len(diferencias) - 60} más")

    print(f"\n=== Capturas distintas byte a byte: {len(pixeles)} ===")
    for p in pixeles:
        print("  •", p)
    print("\n(Una captura distinta no implica regresión: el antialiasing de fuentes")
    print(" varía entre ejecuciones. Lo determinante son los estilos computados.)")
    return 1 if diferencias else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("etiqueta", nargs="?")
    ap.add_argument("--base", default="http://127.0.0.1:8010")
    ap.add_argument("--comparar", nargs=2, metavar=("ANTES", "DESPUES"))
    args = ap.parse_args()

    if args.comparar:
        sys.exit(comparar(*args.comparar))
    if not args.etiqueta:
        ap.error("hace falta una etiqueta, o --comparar A B")
    capturar(args.etiqueta, args.base)

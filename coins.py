"""Catálogo de monedas colombianas (serie vigente 2012+ y serie anterior 1989-2012)
y clasificador por diámetro + peso.

Fuente de las medidas: Banco de la República / Wikipedia (Peso colombiano).
Verifica con calibrador y balanza antes de calibrar los sensores: hay tolerancia
de fabricación y desgaste en monedas circuladas.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

SILVER = "#c5c8cc"
ALPACA = "#d3cfbd"
BRASS = "#c9a24a"
BRONZE = "#b98a4b"


@dataclass(frozen=True)
class Coin:
    denom: int
    serie: str            # "nueva" (2012+) | "antigua" (1989-2012)
    d: float              # diámetro exterior, mm
    w: float              # peso, g
    esp: float            # espesor, mm
    metal: str
    ring: str             # color del anillo / cuerpo
    core: str | None = None      # color del núcleo si es bimetálica
    d_core: float | None = None  # diámetro del núcleo, mm

    @property
    def key(self) -> str:
        return f"{self.denom}_{self.serie}"

    @property
    def bimetal(self) -> bool:
        return self.core is not None

    @property
    def label(self) -> str:
        return f"${self.denom:,}".replace(",", ".") + f" · {self.serie}"


CATALOGO: list[Coin] = [
    # --- serie nueva (2012+) ---
    Coin(50, "nueva", 17.0, 2.00, 1.17, "Acero, recub. níquel", SILVER),
    Coin(100, "nueva", 20.3, 3.34, 1.35, "Acero, recub. latón", BRASS),
    Coin(200, "nueva", 22.4, 4.61, 2.10, "Alpaca (Cu-Zn-Ni)", ALPACA),
    Coin(500, "nueva", 23.7, 7.14, 2.10, "Bimetálica: corona alpaca / núcleo Cu-Al-Ni", SILVER, BRASS, 17.0),
    Coin(1000, "nueva", 26.7, 9.95, 2.20, "Bimetálica: corona alpaca amarilla / núcleo alpaca blanca", BRASS, SILVER, 17.5),
    # --- serie antigua (1989-2012) ---
    Coin(50, "antigua", 21.0, 4.00, 1.30, "65% Cu, 20% Zn, 15% Ni", ALPACA),
    Coin(100, "antigua", 23.0, 5.31, 1.50, "92% Cu, 6% Al, 2% Ni", BRONZE),
    Coin(200, "antigua", 24.4, 7.10, 1.70, "65% Cu, 20% Zn, 15% Ni", ALPACA),
    Coin(500, "antigua", 23.5, 7.40, 2.00, "Bimetálica: corona Cu-Zn-Ni / núcleo Cu-Al-Ni", SILVER, BRASS, None),
]

POR_KEY = {c.key: c for c in CATALOGO}

# Ruido típico esperado en los sensores (ajustar tras calibrar)
SIGMA_D = 0.12   # mm  (sensor lineal de ancho)
SIGMA_W = 0.06   # g   (HX711 + celda de 100 g)


def clasificar(d: float, w: float, umbral: float = 3.0) -> Coin | None:
    """Devuelve la moneda más cercana en el plano (diámetro, peso) o None.

    La distancia se normaliza por la tolerancia de cada sensor. El diámetro
    separa casi todo (p.ej. $200 nueva 22.4 vs $50 antigua 21.0). El caso
    difícil es $500 nueva vs antigua (23.7 vs 23.5 mm): ahí decide el peso
    (7.14 vs 7.40 g), por eso se miden ambas magnitudes.
    """
    mejor, mejor_dist = None, math.inf
    for c in CATALOGO:
        dist = math.hypot((d - c.d) / (SIGMA_D * 2.5), (w - c.w) / (SIGMA_W * 2.5))
        if dist < mejor_dist:
            mejor, mejor_dist = c, dist
    return mejor if mejor_dist <= umbral / 2.5 else None


def resumen(conteo: dict[str, int]) -> dict:
    """Totales de cantidad, valor ($COP) y peso (g) a partir del conteo por clave."""
    cantidad = sum(conteo.values())
    valor = sum(POR_KEY[k].denom * n for k, n in conteo.items() if k in POR_KEY)
    peso = sum(POR_KEY[k].w * n for k, n in conteo.items() if k in POR_KEY)
    return {"cantidad": cantidad, "valor": valor, "peso_monedas_g": peso}


def cop(v: float) -> str:
    return "$ " + f"{v:,.0f}".replace(",", ".")


def coin_svg(c: Coin, px_por_mm: float = 5.0, etiqueta: bool = True) -> str:
    """Moneda dibujada a escala real (px_por_mm). Sirve para comparar antigua vs nueva."""
    r = c.d * px_por_mm / 2
    pad = 4
    size = 2 * r + 2 * pad
    cx = cy = size / 2
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size:.0f}" height="{size:.0f}" '
        f'viewBox="0 0 {size:.1f} {size:.1f}">',
        f'<circle cx="{cx}" cy="{cy}" r="{r:.2f}" fill="{c.ring}" stroke="#4a4f57" stroke-width="1.2"/>',
    ]
    if c.bimetal:
        rc = (c.d_core / 2 if c.d_core else c.d * 0.34) * px_por_mm
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{rc:.2f}" fill="{c.core}" stroke="#4a4f57" stroke-width="1"/>')
    else:
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r*0.84:.2f}" fill="none" stroke="#4a4f57" stroke-opacity=".35" stroke-width="1"/>')
    if etiqueta:
        fs = max(9, r * 0.5)
        parts.append(
            f'<text x="{cx}" y="{cy + fs*0.35:.1f}" text-anchor="middle" font-family="Barlow Condensed,sans-serif" '
            f'font-weight="700" font-size="{fs:.1f}" fill="#2b2f36">{c.denom}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)

"""Lámina 7 — Matriz de confusión del sensor de color y regla de errores (datos: experimentos_confusion.py)."""
import json
import os

import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from estilo import *

RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados_confusion.json")
CMAP = LinearSegmentedColormap.from_list("m", ["#ffffff", "#f3d9c4", "#b8480f"])
ETIQ = ["$50", "$100", "$200", "$500", "$1.000"]


def heat(fig, rect_, M, titulo, subtitulo):
    ax = fig.add_axes(rect_)
    M = np.array(M, dtype=float)
    P = M / M.sum(axis=1, keepdims=True).clip(min=1) * 100
    ax.imshow(P, cmap=CMAP, vmin=0, vmax=100, aspect="equal")
    for i in range(5):
        for j in range(5):
            c = "white" if P[i, j] > 55 else INK
            ax.text(j, i, f"{int(M[i, j])}\n{P[i, j]:.0f} %", ha="center", va="center", fontsize=8.6, color=c,
                    fontweight="bold" if i == j else "normal")
    ax.set_xticks(range(5)); ax.set_xticklabels(ETIQ, fontsize=9)
    ax.set_yticks(range(5)); ax.set_yticklabels(ETIQ, fontsize=9)
    ax.xaxis.tick_top(); ax.xaxis.set_label_position("top")
    ax.set_xlabel("PREDICHO por el TCS3200", fontsize=9.5, fontweight="bold", labelpad=8)
    ax.set_ylabel("DENOMINACIÓN REAL del vaso", fontsize=9.5, fontweight="bold")
    for s in ax.spines.values():
        s.set_color(INK)
    ax.set_title(titulo, fontsize=11.5, fontweight="bold", loc="left", pad=44)
    ax.text(-0.5, -1.35, subtitulo, fontsize=8.6, color=GRIS, va="center", transform=ax.transData)
    return ax


def regla(fig, R):
    ax = fig.add_axes([0.665, 0.105, 0.325, 0.765]); ax.axis("off"); ax.set_xlim(-0.08, 1); ax.set_ylim(0, 1)
    ax.text(0.0, 1.0, "REGLA DE ERRORES (idea del profe)", fontsize=12, fontweight="bold", va="top")
    pasos = [("EXPLORAR", "#e8f0f4"), ("LEER COLOR (hasta 5 lecturas)", "#e8f0f4"), ("TRANSPORTAR al nido", "#e8f0f4"),
             ("NIDO: la báscula verifica", "#fbf0d0"), ("¿errores ≥ E_MAX = 2?", "#f3d9c4"), ("RECALIBRAR (tarjeta blanca)", "#dcebe8")]
    y = 0.90
    for i, (t, c) in enumerate(pasos):
        ax.add_patch(Rectangle((0.02, y - 0.05), 0.60, 0.06, fc=c, ec=INK, lw=1.0))
        ax.text(0.32, y - 0.02, t, fontsize=8.8, ha="center", va="center", fontweight="bold" if i in (4, 5) else "normal")
        if i < len(pasos) - 1:
            flecha(ax, (0.32, y - 0.05), (0.32, y - 0.075), color=INK, lw=1.1, estilo="-|>")
        y -= 0.095
    ax.text(0.64, 0.90 - 0.095 * 4 - 0.02, "sí →", fontsize=8.4, color=ACC, fontweight="bold", va="center")
    ax.text(0.64, 0.90 - 0.095 * 3 - 0.07, "no → sigue\nexplorando", fontsize=8.0, color=GRIS, va="center")
    ax.plot([0.02, -0.02, -0.02, 0.02], [0.90 - 0.095 * 5 - 0.02, 0.90 - 0.095 * 5 - 0.02, 0.88, 0.88], color=GRIS, lw=1.0)
    flecha(ax, (-0.02, 0.88), (0.02, 0.88), color=GRIS, lw=1.0, estilo="-|>")
    ax.text(0.65, 0.90 - 0.095 * 5 + 0.0, "reinicia el contador\ny vuelve a EXPLORAR", fontsize=8.0, color=GRIS, va="center")
    ax.text(0.0, 0.29, "Resultado en simulación (6 corridas de 30 min, paleta actual):", fontsize=9, fontweight="bold", va="center")
    ax.add_patch(Rectangle((0, 0.04), 1, 0.2, fc="white", ec=INK, lw=0.9))
    cab = [("deriva del sensor", 0.01), ("regla", 0.30), ("entregas OK", 0.46), ("mal", 0.62), ("% mal", 0.72), ("recal.", 0.88)]
    for t, x in cab:
        ax.text(x, 0.225, t, fontsize=7.6, fontweight="bold", va="center")
    y = 0.19
    for r in R["regla"]:
        pm = 100 * r["mal"] / max(1, r["ok"] + r["mal"])
        fila_ = [("baja" if r["deriva"] < 0.001 else "alta", 0.01), ("sin regla" if r["e_max"] is None else f"E_MAX = {r['e_max']}", 0.30),
                 (str(r["ok"]), 0.46), (str(r["mal"]), 0.62), (f"{pm:.1f} %", 0.72), (str(r["recal"]), 0.88)]
        for t, x in fila_:
            ax.text(x, y, t, fontsize=8.0, va="center")
        y -= 0.035
    return ax


def conclusiones(fig, R):
    A, B = R["A"], R["B"]
    pmA = 100 * A["mal"] / max(1, A["ok"] + A["mal"]); pmB = 100 * B["mal"] / max(1, B["ok"] + B["mal"])
    ax = fig.add_axes([0.02, 0.04, 0.64, 0.15]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    r_lo = [r for r in R["regla"] if r["deriva"] < 0.001]; r_hi = [r for r in R["regla"] if r["deriva"] >= 0.001]
    def pm(r): return 100 * r["mal"] / max(1, r["ok"] + r["mal"])
    def frase_regla():
        partes = []
        for nombre, par in (("deriva alta", r_hi), ("deriva baja", r_lo)):
            sin, con = par
            d = pm(sin) - pm(con)
            if d > 1.0:
                efecto = f"las entregas equivocadas bajan de {pm(sin):.1f} % a {pm(con):.1f} %"
            elif d < -1.0:
                efecto = f"las entregas equivocadas SUBEN de {pm(sin):.1f} % a {pm(con):.1f} %"
            else:
                efecto = f"casi no cambia ({pm(sin):.1f} % → {pm(con):.1f} %)"
            partes.append(f"con {nombre} {efecto} y las entregas correctas pasan de {sin['ok']} a {con['ok']}")
        return "• Regla de E_MAX: " + "; ".join(partes) + " (6 corridas de 30 min; diferencias de ~1 punto porcentual pueden ser ruido entre corridas)."
    txt = [
        f"• La matriz muestra que el error está casi todo en un par: $50 plateado ↔ $200 beige (cromaticidad casi igual). Exactitud de lectura {100 * A['exactitud']:.0f} %.",
        f"• Con pegatinas blanco / amarillo / azul / rojo / verde la exactitud sube a {100 * B['exactitud']:.0f} % y las entregas equivocadas pasan de {pmA:.1f} % a {pmB:.1f} %.",
        frase_regla(),
        "• Es una simulación con ruido supuesto del sensor: hay que repetir la medida con el TCS3200 real (comando serial '0'..'4' del firmware) antes de fijar umbrales.",
    ]
    y = 0.95
    import textwrap
    for t in txt:
        l = textwrap.wrap(t, 158, subsequent_indent="   ")
        ax.text(0.0, y, "\n".join(l).replace("$", r"\$"), fontsize=8.5, va="top", linespacing=1.15)
        y -= 0.205 * len(l)


def generar(salida="07_matriz_confusion"):
    with open(RUTA, encoding="utf-8") as f:
        R = json.load(f)
    fig = lamina("Matriz de confusión del sensor de color y regla de errores", "7/7", "s/e",
                 "Filas = denominación real · columnas = lo que predijo el TCS3200 · diagonal = acierto · datos de swarm.py (5 carritos, 6 × 30 min simulados)")
    A, B = R["A"], R["B"]
    heat(fig, [0.07, 0.27, 0.26, 0.52], A["matriz"], "Paleta actual (plateado, dorado, beige, rojo, verde)",
         f"{A['lecturas']} lecturas · exactitud {100 * A['exactitud']:.1f} % · entregas equivocadas {A['mal']} de {A['ok'] + A['mal']}")
    heat(fig, [0.37, 0.27, 0.26, 0.52], B["matriz"], "Paleta recomendada (blanco, amarillo, azul, rojo, verde)",
         f"{B['lecturas']} lecturas · exactitud {100 * B['exactitud']:.1f} % · entregas equivocadas {B['mal']} de {B['ok'] + B['mal']}")
    regla(fig, R); conclusiones(fig, R)
    guardar(fig, salida)


if __name__ == "__main__":
    generar()

"""Lámina 2 — Distribución interna del carrito por pisos (a escala) con centro de gravedad."""
from matplotlib.patches import Polygon

from estilo import *
import datos_carrito as D

N = D.NUM
P = {p["id"]: p for p in D.PARTES}


def parte(ax, pid, fc=None, z=4, alpha=1.0, ls="-"):
    p = P[pid]
    rectc(ax, p["x"], p["y"], p["dx"], p["dy"], fc=fc or p["c"], ec=INK, lw=0.9, z=z, alpha=alpha, ls=ls)


def fantasma(ax, pid):
    p = P[pid]
    rectc(ax, p["x"], p["y"], p["dx"], p["dy"], fc="none", ec=GRIS, lw=0.8, ls="--", z=2.5)


def piso_inferior(fig):
    ax = vista(fig, [0.02, 0.30, 0.47, 0.58], (-28, 192), (-78, 78),
               "PISO INFERIOR (sobre la placa de 3 mm) y zona de pinza entre placas", invert_y=True)
    rect(ax, 0, -50, D.L, 100, fc="#e8f0f4", lw=1.6, z=1)
    for s in (-1, 1):
        for x in (8, 118):
            circ(ax, x, s * 42, 3, fc="#b0b0b0", ec=INK, lw=0.8, z=3)          # separadores M3
        rectc(ax, D.X_EJE, s * 55, 42, 15, fc="#333", ec=INK, lw=1.0, z=3)       # ruedas
    for pid in ("MOI", "MOD", "BAT", "DRV", "SVL", "SVR", "TCS"):
        parte(ax, pid)
    circ(ax, D.X_LOCA, 0, 5, fc="#777", ec=INK, z=3)
    for s in (-1, 1):
        ax.add_patch(Polygon([(116, s * 17), (150, s * 31), (172, s * 29), (172, s * 33), (150, s * 36), (112, s * 23)],
                             closed=True, fc="#f0f0e8", ec=INK, lw=0.9, zorder=5))
    # cableado de potencia (dibujo esquemático)
    ax.plot([54, 80, 82], [0, 0, 0], color="#c0392b", lw=2, zorder=6)                  # batería -> driver (VM)
    ax.plot([62, 50, 50], [-6, -6, -12], color="#c0392b", lw=1.2, ls=":", zorder=6)
    for s in (-1, 1):
        ax.plot([102, 104.5], [s * 4, s * 14], color=GRIS, lw=1.0, zorder=6)
    (cx0, cy0, _), _ = D.centro_de_gravedad(False)
    (cx1, cy1, _), _ = D.centro_de_gravedad(True)
    ax.plot([cx0], [cy0], marker="P", color="#2a56b0", mec="white", mew=1.4, ms=11, zorder=12)
    ax.plot([cx1], [cy1], marker="P", color=ACC, mec="white", mew=1.4, ms=11, zorder=12)
    # globos
    globo(ax, 50, -23, N["MOI"], dx=-22, dy=-1, r=4.8, fs=8)
    globo(ax, 50, 23, N["MOD"], dx=-22, dy=1, r=4.8, fs=8)
    globo(ax, 50, -55, N["RUE"], dx=0, dy=-17, r=4.8, fs=8)
    globo(ax, 124, 0, N["RLO"], dx=-12, dy=0, r=4.8, fs=8)
    globo(ax, 26, 0, N["BAT"], dx=0, dy=0, r=4.8, fs=8)
    globo(ax, 92, 0, N["DRV"], dx=0, dy=0, r=4.8, fs=8)
    globo(ax, 116, -20, N["SVL"], dx=0, dy=-20, r=4.8, fs=8)
    globo(ax, 116, 20, N["SVR"], dx=0, dy=20, r=4.8, fs=8)
    globo(ax, 134, 0, N["TCS"], dx=14, dy=0, r=4.8, fs=8)
    globo(ax, 150, 32, N["DED"], dx=4, dy=18, r=4.8, fs=8)
    globo(ax, 8, 42, N["SEP"], dx=0, dy=14, r=4.8, fs=8)
    texto(ax, 150, 70, "FRENTE →", fs=9, color=ACC, bold=True)
    cota_h(ax, 0, 130, 68, "130", ext=(62.5, 62.5), fs=8.5)
    return ax


def piso_superior(fig):
    ax = vista(fig, [0.51, 0.30, 0.47, 0.58], (-28, 192), (-78, 78), "PISO SUPERIOR (sobre la placa de 2 mm)", invert_y=True)
    rect(ax, 0, -50, D.L, 100, fc="#e8f0f4", lw=1.6, z=1)
    for pid in ("MOI", "MOD", "BAT", "DRV", "SVL", "SVR"):
        fantasma(ax, pid)
    for s in (-1, 1):
        rectc(ax, D.X_EJE, s * 55, 42, 15, fc="#333", ec=INK, lw=1.0, z=3, alpha=0.5)
        for x in (8, 118):
            circ(ax, x, s * 42, 3, fc="#b0b0b0", ec=INK, lw=0.8, z=3)
    circ(ax, D.X_LOCA, 0, 5, fc="#777", ec=INK, z=3, alpha=0.5)
    for pid in ("ESP", "MPU", "BUC", "SWI", "LED", "TOF", "TCS"):
        parte(ax, pid, z=5)
    # cableado esquemático
    ax.plot([14, 14, 18], [18, 6, -12], color="#c0392b", lw=1.6, zorder=6)                      # interruptor -> buck
    ax.plot([29, 36], [-22, -10], color="#c0392b", lw=1.6, zorder=6)                            # buck -> ESP32 (5 V)
    ax.plot([88, 100], [0, -20], color=GRIS, lw=1.2, zorder=6)                                 # I2C ESP32 -> MPU
    ax.plot([88, 103], [0, 0], color=GRIS, lw=1.2, zorder=6)                                   # I2C -> VL53L0X
    (cx0, cy0, _), _ = D.centro_de_gravedad(False)
    (cx1, cy1, _), _ = D.centro_de_gravedad(True)
    ax.plot([cx0], [cy0], marker="P", color="#2a56b0", mec="white", mew=1.4, ms=11, zorder=12)
    ax.plot([cx1], [cy1], marker="P", color=ACC, mec="white", mew=1.4, ms=11, zorder=12)
    globo(ax, 62, 0, N["ESP"], dx=0, dy=-24, r=4.8, fs=8)
    globo(ax, 100, -28, N["MPU"], dx=0, dy=-18, r=4.8, fs=8)
    globo(ax, 18, -22, N["BUC"], dx=-4, dy=-16, r=4.8, fs=8)
    globo(ax, 14, 25, N["SWI"], dx=0, dy=18, r=4.8, fs=8)
    globo(ax, 8, 0, N["LED"], dx=-14, dy=0, r=4.8, fs=8)
    globo(ax, 105, 0, N["TOF"], dx=0, dy=22, r=4.8, fs=8)
    globo(ax, 134, 0, N["TCS"], dx=14, dy=0, r=4.8, fs=8)
    texto(ax, 85, 71, "FRENTE →", fs=9, color=ACC, bold=True)
    texto(ax, -26, -72, "✚ CG vacío", fs=8.5, ha="left", color="#2a56b0", bold=True)
    texto(ax, 28, -72, "✚ CG con vaso $1.000", fs=8.5, ha="left", color=ACC, bold=True)
    return ax


def generar(salida="02_distribucion_interna"):
    fig = lamina("Distribución interna del carrito — dos pisos", "2/7", "1:1",
                 "Cómo se organiza todo adentro · ✚ = centro de gravedad · los números son los mismos de la tabla de pesos (lámina 3)")
    piso_inferior(fig); piso_superior(fig)
    inf = [(N[i], P[i]["nombre"]) for i in ("MOI", "MOD", "RUE", "RLO", "BAT", "DRV", "SVL", "SVR", "TCS", "DED", "SEP")]
    sup = [(N[i], P[i]["nombre"]) for i in ("ESP", "MPU", "BUC", "SWI", "LED", "TOF")]
    leyenda(fig, [0.03, 0.02, 0.47, 0.25], "PISO INFERIOR / PINZA", inf, fs=9.3, col=2, paso=0.145)
    leyenda(fig, [0.52, 0.02, 0.22, 0.25], "PISO SUPERIOR", sup, fs=9.3, col=1, paso=0.115, dx_texto=0.12)
    guardar(fig, salida)


if __name__ == "__main__":
    generar()

"""Lámina 1 — Vistas del carrito (planta, lateral, frontal) con cotas, globos y leyenda."""
from matplotlib.patches import Polygon

from estilo import *
import datos_carrito as D

# numeración de globos (igual en todas las vistas)
LEYENDA = [
    (1, "Motorreductor N20 + encoder (2)"), (2, "Rueda Ø42 × 15 (2)"), (3, "Rueda loca (bola Ø10)"),
    (4, "VL53L0X: distancia / detecta vasos"), (5, "TCS3200: color del vaso (en la palma)"),
    (6, "Servo SG90 de la pinza (2)"), (7, "Dedos de pinza impresos (2)"), (8, "Vaso con 10 monedas (Ø60 × 70)"),
]


def oculto(ax, cx, cy, w, h):
    rectc(ax, cx, cy, w, h, fc="none", ec=GRIS, lw=0.9, ls="--", z=2.5)


def planta(fig):
    ax = vista(fig, [0.02, 0.33, 0.52, 0.53], (-42, 232), (-92, 80),
               "PLANTA — placa superior transparente; en línea punteada lo que queda debajo", invert_y=True)
    rect(ax, 0, -50, D.L, 100, fc="#e8f0f4", lw=1.6, z=1)
    oculto(ax, D.P_BAT["x"], 0, D.P_BAT["dx"], D.P_BAT["dy"])   # batería
    oculto(ax, 92, 0, 20, 20)                 # driver
    for s in (-1, 1):
        oculto(ax, D.X_EJE, s * 23, 12, 45)   # motores N20
        oculto(ax, 116, s * 20, 23, 12)       # servos
        rectc(ax, D.X_EJE, s * 55, 42, 15, fc="#333", ec=INK, lw=1.0, z=3)   # ruedas
    circ(ax, D.X_LOCA, 0, 5, fc="#777", ec=INK, z=3)
    rectc(ax, 62, 0, 51, 28, fc="#2b3445", ec=INK, lw=0.9, z=4)            # ESP32
    rectc(ax, 100, -28, 20, 16, fc="#7a5fd0", ec=INK, lw=0.8, z=4)         # MPU6050
    rectc(ax, 18, -22, 22, 17, fc="#c14fae", ec=INK, lw=0.8, z=4)          # buck
    rectc(ax, 14, 25, 20, 14, fc="#aa2222", ec=INK, lw=0.8, z=4)           # interruptor
    rectc(ax, 8, 0, 10, 10, fc="#eeeeee", ec=INK, lw=0.8, z=4)             # LED
    rectc(ax, 105, 0, 4, 18, fc="#d94f4f", ec=INK, lw=0.9, z=6)            # VL53L0X
    rectc(ax, 134, 0, 10, 28, fc="#1f6f6b", ec=INK, lw=0.9, z=6)           # TCS3200
    for s in (-1, 1):
        ax.add_patch(Polygon([(116, s * 17), (150, s * 31), (172, s * 29), (172, s * 33), (150, s * 36), (112, s * 23)],
                             closed=True, fc="#f0f0e8", ec=INK, lw=0.9, zorder=5))
        ax.plot([116, 160, 186], [s * 20, s * 50, s * 58], color=GRIS, lw=0.9, ls="--", zorder=4)
    circ(ax, D.X_VASO, 0, 30, fc="#fbf0d0", ec=INK, lw=1.1, z=3)
    circ(ax, D.X_VASO, 0, 22.5, fc="none", ec=INK, lw=0.6, ls=":", z=3)
    ax.plot([-42, 232], [0, 0], color=GRIS, lw=0.5, ls="-.", zorder=1)
    flecha(ax, (190, 70), (228, 70), color=ACC, lw=1.6, estilo="-|>")
    texto(ax, 209, 76, "FRENTE", fs=9, color=ACC, bold=True)
    cota_h(ax, 0, 130, -86, "130", ext=(-62.5, -62.5))
    cota_h(ax, 0, 50, -74, "50 (eje)", ext=(-62.5, -62.5), fs=8.5)
    cota_h(ax, 130, 180, 58, "50", ext=(50, 30), fs=8.5)
    cota_v(ax, -6, -50, 50, "100", ext=(0, 0))
    cota_v(ax, -18, -55, 55, "110 trocha", ext=(D.X_EJE - 21, D.X_EJE - 21), color=ACC)
    cota_v(ax, -30, -62.5, 62.5, "125 total", ext=(D.X_EJE - 21, D.X_EJE - 21))
    globo(ax, 50, -34, 1, dx=-22, dy=0); globo(ax, 63, -55, 2, dx=22, dy=0); globo(ax, 124, 0, 3, dx=0, dy=22)
    globo(ax, 105, 0, 4, dx=-4, dy=-20); globo(ax, 134, 8, 5, dx=0, dy=20); globo(ax, 116, 20, 6, dx=-8, dy=16)
    globo(ax, 160, 33, 7, dx=0, dy=14); globo(ax, 200, -18, 8, dx=14, dy=-12)
    return ax


def lateral(fig):
    ax = vista(fig, [0.55, 0.49, 0.44, 0.42], (-40, 235), (-18, 92), "VISTA LATERAL (el frente sale por la derecha)")
    ax.plot([-40, 232], [0, 0], color=INK, lw=1.4, zorder=1)
    rect(ax, 0, 13, 130, 3, fc="#d8e6ee", lw=1.2)
    rect(ax, 0, 46, 130, 2, fc="#d8e6ee", lw=1.2)
    for x in (6, 118):
        rect(ax, x, 16, 5, 30, fc="#b0b0b0", lw=0.7)
    rect(ax, D.P_BAT["x"] - D.P_BAT["dx"] / 2, 16, D.P_BAT["dx"], 11, fc="#f3d98a", lw=0.9)   # batería
    rect(ax, 82, 16, 20, 4, fc="#8fcf9f", lw=0.9)                        # driver
    circ(ax, D.X_EJE, D.Z_EJE, 21, fc="#3a3f48", lw=1.2, z=4)           # rueda
    circ(ax, D.X_EJE, D.Z_EJE, 6, fc="#bbb", lw=0.8, z=5)
    rect(ax, 119, 8, 10, 5, fc="#777", lw=0.7)
    circ(ax, D.X_LOCA, 5, 5, fc="#999", lw=1.0, z=4)                     # rueda loca
    rect(ax, 36, 48, 51, 13, fc="#2b3445", lw=0.9)                       # ESP32
    rect(ax, 90, 48, 20, 3, fc="#7a5fd0", lw=0.8)
    rect(ax, 7, 48, 22, 4, fc="#c14fae", lw=0.8)
    rect(ax, 4, 48, 20, 12, fc="#aa2222", lw=0.8, z=2.2)
    rect(ax, 3, 52, 10, 4, fc="#e6e6e6", lw=0.8, z=2.5)
    rect(ax, 103, 50, 4, 13, fc="#d94f4f", lw=0.9)                       # VL53L0X
    rect(ax, 104.5, 18, 23, 27, fc="#3a6fb0", lw=0.9)                    # servo
    rect(ax, 130, 20, 45, 30, fc="#f0f0e8", lw=0.9, z=3)                 # dedos
    rect(ax, 129, 22, 10, 28, fc="#1f6f6b", lw=1.0, z=5)                 # TCS3200
    ax.add_patch(Polygon([(157.5, 0), (202.5, 0), (210, 70), (150, 70)], closed=True, fc="#fbf0d0", ec=INK, lw=1.2,
                         zorder=2.8, alpha=0.9))
    flecha(ax, (107, 56), (230, 56), color="#d94f4f", lw=1.0, estilo="->", ls="--")
    texto(ax, 214, 62, "haz VL53L0X ≤ 250", fs=8, color="#d94f4f")
    flecha(ax, (139, 36), (152, 36), color="#1f6f6b", lw=1.4, estilo="->", ls="--")
    (cx0, _, cz0), _ = D.centro_de_gravedad(False)
    (cx1, _, cz1), _ = D.centro_de_gravedad(True)
    ax.plot([cx0], [cz0], marker="P", color="#2a56b0", ms=9, zorder=12)
    ax.plot([cx1], [cz1], marker="P", color=ACC, ms=9, zorder=12)
    texto(ax, -38, 86, f"✚ CG vacío (x={cx0:.0f}, z={cz0:.0f})", fs=8.5, ha="left", color="#2a56b0", bold=True)
    texto(ax, -38, 78, f"✚ CG con vaso de $1.000 (x={cx1:.0f}, z={cz1:.0f})", fs=8.5, ha="left", color=ACC, bold=True)
    cota_v(ax, -12, 0, 48, "48", ext=(0, 0), fs=8.5)
    cota_v(ax, -26, 0, 13, "13", ext=(0, 0), fs=8)
    cota_v(ax, 224, 0, 70, "70", ext=(0, 0), fs=8.5)
    cota_h(ax, 0, 130, -9, "130", ext=(0, 0), fs=8.5)
    cota_h(ax, 0, D.X_EJE, -15, "50", ext=(0, 0), fs=8)
    cota_h(ax, 130, 180, -9, "50", ext=(0, 0), fs=8)
    texto(ax, 50, 21, "Ø42", fs=8, color="white", bold=True, z=12)
    globo(ax, 60, 33, 2, dx=0, dy=0, r=4.6, fs=8)
    globo(ax, 124, 5, 3, dx=12, dy=-9, r=4.6, fs=8)
    globo(ax, 105, 60, 4, dx=-6, dy=14, r=4.6, fs=8)
    globo(ax, 134, 45, 5, dx=14, dy=22, r=4.6, fs=8)
    globo(ax, 116, 24, 6, dx=-2, dy=-12, r=4.6, fs=8)
    globo(ax, 165, 46, 7, dx=0, dy=14, r=4.6, fs=8)
    globo(ax, 195, 14, 8, dx=0, dy=-12, r=4.6, fs=8)
    return ax


def frontal(fig):
    ax = vista(fig, [0.55, 0.06, 0.22, 0.38], (-85, 85), (-16, 82), "VISTA FRONTAL")
    ax.plot([-80, 80], [0, 0], color=INK, lw=1.4)
    rect(ax, -50, 13, 100, 3, fc="#d8e6ee", lw=1.2)
    rect(ax, -50, 46, 100, 2, fc="#d8e6ee", lw=1.2)
    for s in (-1, 1):
        rect(ax, s * 55 - 7.5, 0, 15, 42, fc="#3a3f48", lw=1.1, z=4)
        rectc(ax, s * 20, 31.5, 12, 27, fc="#3a6fb0", lw=0.9, z=3)
        rect(ax, s * 40 - 3, 20, 6, 30, fc="#f0f0e8", lw=0.8, z=3)
    rectc(ax, 0, 36, 28, 28, fc="#1f6f6b", lw=1.0, z=5)
    rectc(ax, 0, 56.5, 18, 13, fc="#d94f4f", lw=0.9, z=5)
    rectc(ax, 0, 54.5, 28, 13, fc="#2b3445", lw=0.8, z=2)
    ax.add_patch(Polygon([(-22.5, 0), (22.5, 0), (30, 70), (-30, 70)], closed=True, fc="#fbf0d0", ec=INK, lw=1.1, zorder=2,
                         alpha=0.8))
    circ(ax, 0, 5, 5, fc="#999", z=2.4)
    cota_h(ax, -62.5, 62.5, -8, "125 (con ruedas)", ext=(0, 0), fs=8.5)
    cota_h(ax, -50, 50, 76, "100", ext=(48, 48), fs=8.5)
    cota_v(ax, 74, 0, 63, "63", ext=(0, 63), fs=8.5)
    globo(ax, -55, 30, 2, dx=-18, dy=6, r=4.6, fs=8)
    globo(ax, 0, 5, 3, dx=-24, dy=-4, r=4.6, fs=8)
    globo(ax, 0, 58, 4, dx=22, dy=10, r=4.6, fs=8)
    globo(ax, 0, 36, 5, dx=-30, dy=22, r=4.6, fs=8)
    globo(ax, -20, 31, 6, dx=-16, dy=-20, r=4.6, fs=8)
    globo(ax, 40, 42, 7, dx=16, dy=18, r=4.6, fs=8)
    return ax


def notas(fig):
    ax = fig.add_axes([0.275, 0.03, 0.27, 0.27]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    e = D.estabilidad(True)
    lineas = [
        "NOTAS",
        f"• Chasis de 2 placas (130×100; 3 y 2 mm), separadas {D.SEPARACION:.0f} mm.",
        "• Tracción diferencial, trocha 110 mm, eje a 50 mm del borde trasero.",
        "• TCS3200 en la palma de la pinza, a ≈15 mm del vaso (su rango útil).",
        "• VL53L0X atrás (x=105): con el vaso agarrado lee ≈45 mm (mín. fiable ≈30).",
        f"• Peso vacío {D.MASA_VACIO:.0f} g; cargado {D.MASA_CARGADO:.0f} g (vaso + 10×$1.000).",
        f"• CG con vaso en x={e['cg'][0]:.0f} (entre eje 50 y loca 124): no vuelca",
        f"  (límite ≥ {min(e['a_frente'], e['a_atras']):.1f} m/s²; el carrito usa < 1 m/s²).",
        "• Medidas del vaso y de los N20/ruedas: supuestas, verificar con las piezas.",
    ]
    y = 0.98
    for i, s in enumerate(lineas):
        ax.text(0.0, y, s, fontsize=9.6 if i else 12, fontweight="bold" if i == 0 else "normal", va="top")
        y -= 0.105 if i else 0.12
    return ax


def generar(salida="01_vistas_carrito"):
    fig = lamina("Carrito hormiga — vistas y cotas", "1/7", "1:1 por vista",
                 "Medidas en mm · tracción diferencial · pinza frontal con sensor de color en la palma")
    planta(fig); lateral(fig); frontal(fig); notas(fig)
    leyenda(fig, [0.025, 0.03, 0.24, 0.27], "LEYENDA", LEYENDA, fs=9.6, paso=0.105)
    guardar(fig, salida)


if __name__ == "__main__":
    generar()

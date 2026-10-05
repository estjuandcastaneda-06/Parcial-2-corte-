"""Lámina 4 — Plano de la arena donde se mueven los carritos (2100 x 1200 mm)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matplotlib.patches import Polygon

from estilo import *
import datos_carrito as D
import swarm as S

C = S.CELL_M * 1000          # 50 mm por celda
AW, AH = S.W * C, S.H * C    # 2100 x 1200


def mm(c):
    return c * C


def arena(fig):
    ax = vista(fig, [0.02, 0.215, 0.96, 0.64], (-150, AW + 90), (-130, AH + 130), None, invert_y=True)
    fig.text(0.02, 0.885, "VISTA SUPERIOR — arena de 2100 × 1200 mm (1 hoja de MDF de 1220 × 2440 mm)", fontsize=12, fontweight="bold")
    # piso y paredes
    rect(ax, 0, 0, AW, AH, fc="#ffffff", lw=1.0, z=1)
    for i in range(0, S.W + 1):
        ax.plot([i * C, i * C], [0, AH], color="#ece7da", lw=0.4, zorder=1.1)
    for j in range(0, S.H + 1):
        ax.plot([0, AW], [j * C, j * C], color="#ece7da", lw=0.4, zorder=1.1)
    for x in range(0, int(AW) + 1, 300):
        ax.plot([x, x], [0, AH], color="#d7d0bd", lw=0.7, zorder=1.2)
    for y in range(0, int(AH) + 1, 300):
        ax.plot([0, AW], [y, y], color="#d7d0bd", lw=0.7, zorder=1.2)
    for (x, y, w, h) in ((-20, -20, AW + 40, 20), (-20, AH, AW + 40, 20), (-20, 0, 20, AH), (AW, 0, 20, AH)):
        rect(ax, x, y, w, h, fc="#8a8f98", ec=INK, lw=0.8, hatch="////", z=3)

    # zonas
    rect(ax, 0, mm(8), mm(5), mm(8), fc="#dcebe8", ec=CAD, lw=1.4, ls="--", z=2)
    texto(ax, mm(2.5), mm(8) + 38, "NIDO / META", fs=10, bold=True, color=CAD)
    texto(ax, mm(2.5), mm(16) - 38, "salida de la banda", fs=8, color=CAD)
    rect(ax, mm(30), mm(1), mm(11), mm(22), fc="#fbf2dc", ec="#c9a24a", lw=1.2, ls="--", z=2)
    texto(ax, 1895, 105, "ZONA DE VASOS\n(x ≥ 1500)", fs=9.5, bold=True, color="#8a6d1c")
    ax.plot([mm(S.ZONA_X)] * 2, [0, AH], color="#8a6d1c", lw=1.0, ls=":", zorder=2.5)
    texto(ax, mm(S.ZONA_X), AH + 40, "x = 1700: aquí empieza la búsqueda libre", fs=8, color="#8a6d1c")

    # obstáculos (slalom)
    for k, (ox, oy, ow, oh) in enumerate(S.OBSTACULOS, 1):
        rect(ax, mm(ox), mm(oy), mm(ow), mm(oh), fc="#b5482e", ec=INK, lw=1.2, hatch="xx", z=4)
        texto(ax, mm(ox + ow / 2), mm(oy + oh / 2), f"OBSTÁCULO {k}", fs=9.5, color="white", bold=True, rot=90, bg="#8f2d1b")
    # corredor dado (nido -> zona) con flechas
    pts = [(mm(x), mm(y)) for x, y in S.CORREDOR]
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=CAD, lw=2.2, ls="--", zorder=5)
    for a, b in zip(pts[:-1], pts[1:]):
        flecha(ax, ((a[0] + b[0]) / 2 - (b[0] - a[0]) * 0.02, (a[1] + b[1]) / 2 - (b[1] - a[1]) * 0.02),
               ((a[0] + b[0]) / 2 + (b[0] - a[0]) * 0.03, (a[1] + b[1]) / 2 + (b[1] - a[1]) * 0.03), color=CAD, lw=1.6, estilo="-|>")
    for i, (x, y) in enumerate(pts):
        circ(ax, x, y, 14, fc="white", ec=CAD, lw=1.4, z=6)
        texto(ax, x, y, str(i), fs=7, color=CAD, bold=True)
    # posiciones iniciales de los 5 carritos y su denominación
    inicios = [(4, 3), (4, S.H - 4), (4, S.H // 2), (7, 6), (7, S.H - 7)]
    for k, (cx, cy) in enumerate(inicios):
        x, y = mm(cx), mm(cy)
        rectc(ax, x, y, 130, 100, fc=S.COLORES_CARRO[k], ec=INK, lw=1.2, z=7)
        texto(ax, x, y, f"C{k + 1}", fs=9.5, color="white", bold=True, z=8)
        texto(ax, x + 15, y + 78, f"busca ${S.DENOMS[k]}", fs=8, bg="white")
    # vasos de muestra (uno por denominación) en la zona
    muestra = [(1560, 220, 50), (1840, 330, 100), (1950, 640, 200), (1580, 760, 500), (1880, 1020, 1000)]
    for (x, y, d) in muestra:
        circ(ax, x, y, 30, fc=S.COLOR[d], ec=INK, lw=1.2, z=7)
        texto(ax, x, y + 52, f"${d}", fs=8, bg="white")
    # cotas
    cota_h(ax, 0, AW, AH + 85, "2100", ext=(AH + 20, AH + 20))
    cota_v(ax, -95, 0, AH, "1200", ext=(0, 0))
    cota_h(ax, 0, mm(18), -60, "900", ext=(0, 0), fs=8.5)
    cota_h(ax, mm(18), mm(20), -30, "100", ext=(0, 0), fs=8)
    cota_v(ax, mm(20) + 70, 750, 1200, "hueco 450", ext=(1000, 1000), fs=8.5, color=ACC)
    cota_v(ax, mm(28) + 70, 0, 450, "hueco 450", ext=(1400, 1400), fs=8.5, color=ACC)
    cota_v(ax, mm(35) + 70, 750, 1200, "hueco 450", ext=(1750, 1750), fs=8.5, color=ACC)
    cota_v(ax, mm(18) - 40, 0, 750, "750", ext=(900, 900), fs=8.5)
    return ax


def tabla(fig):
    ax = fig.add_axes([0.03, 0.03, 0.70, 0.17]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.text(0.0, 1.0, "COORDENADAS (mm; origen en la esquina superior izquierda, x → derecha, y ↓ abajo)", fontsize=10.5, fontweight="bold", va="top")
    items = [
        f"Nido / meta: (100, 600) · bahía de entrega 250 × 400",
        "Obstáculo 1: x 900–1000, y 0–750 · Obstáculo 2: x 1300–1400, y 450–1200 · Obstáculo 3: x 1650–1750, y 0–750",
        "Corredor 0→8: " + " ".join(f"({int(x * C)},{int(y * C)})" for x, y in S.CORREDOR),
        "Salidas: C1 (200,150) · C2 (200,1000) · C3 (200,600) · C4 (350,300) · C5 (350,850)  →  cada carrito busca UNA denominación",
        "Paredes de 60 mm de alto (el VL53L0X las ve y el campo potencial las evita). Piso mate claro, sin brillos (TCS3200).",
        "Cuadrícula de la simulación: 42 × 24 celdas de 50 mm (línea fina); cada 300 mm línea gruesa.",
    ]
    y = 0.80
    for t in items:
        ax.text(0.0, y, "• " + t, fontsize=9.3, va="center")
        y -= 0.135


def leyenda_arena(fig):
    ax = fig.add_axes([0.745, 0.108, 0.245, 0.10]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.text(0.0, 1.05, "LEYENDA", fontsize=10.5, fontweight="bold", va="bottom")
    for i, (col, txt) in enumerate((("#b5482e", "obstáculo (pared 60 mm)"), (CAD, "corredor nido → zona"), ("#fbf2dc", "zona de vasos"), ("#dcebe8", "nido / meta"))):
        cx, cy = (i % 2) * 0.5, 0.62 - (i // 2) * 0.38
        ax.add_patch(Rectangle((cx, cy - 0.13), 0.06, 0.26, fc=col, ec=INK, lw=0.8))
        ax.text(cx + 0.08, cy, txt, fontsize=8.4, va="center")


def generar(salida="04_arena"):
    fig = lamina("Plano de la arena de los carritos", "4/7", "≈ 1:10", "Mismas coordenadas que usa la simulación (swarm.py) y el URDF de PyBullet · cotas en mm")
    arena(fig); tabla(fig); leyenda_arena(fig)
    guardar(fig, salida)


if __name__ == "__main__":
    generar()

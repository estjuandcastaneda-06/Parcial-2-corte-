"""Lámina 6 — Esquema eléctrico y de comunicación de TODO el proyecto:
estación central (contador + banda + brazo + báscula del nido) + red ESP-NOW de 5 carritos + PC con Streamlit."""
import textwrap

from matplotlib.patches import Rectangle

from estilo import *
from lamina5_esquema_carrito import caja, etiqueta_pin, flag, U

COL = dict(cnt=U["gold"], bas=U["violet"], ban=U["blue"], bra=U["orange"])
EX0, EX1 = 60, 98                         # caja del ESP32 de la estación

# pines de la estación: (GPIO, función, y, sentido visto desde el ESP32)
IZQ = [(34, "DIAM", 29, "IN"), (27, "IR", 39, "IN"), (16, "HX1_DT", 49, "IN"), (17, "HX1_SCK", 53, "OUT"),
       (21, "HX2_DT", 72, "IN"), (22, "HX2_SCK", 77, "OUT")]
DER = [(25, "ENA", 29, "OUT"), (32, "IN1", 35, "OUT"), (33, "IN2", 41, "OUT"),
       (18, "S_BASE", 60, "OUT"), (19, "S_HOMBRO", 68, "OUT"), (23, "S_PINZA", 76, "OUT")]


def flecha_h(ax, x_ini, x_fin, y, color, lw=1.5, z=4):
    ax.plot([x_ini, x_fin], [y, y], color=color, lw=lw, zorder=z, solid_capstyle="round")
    d = 1.3 if x_fin > x_ini else -1.3
    ax.fill([x_fin, x_fin - d, x_fin - d], [y, y - 0.55, y + 0.55], color=color, zorder=5)


def estacion(ax):
    ax.text(2, 11.3, "ESTACIÓN CENTRAL (ESP32 #0): contador + banda + brazo de embalaje + báscula del nido", fontsize=10.5, fontweight="bold", va="center")
    caja(ax, EX0, 18.5, EX1, 84.0, None, fc="#1d2430", lw=1.6)
    ax.text((EX0 + EX1) / 2, 21.4, "ESP32 DevKit V1 · estación", fontsize=9, fontweight="bold", color="white", ha="center", va="center", zorder=6)
    for g, s, y, d in IZQ:
        ax.plot([EX0, EX0 + 3], [y, y], color="#c7ccd6", lw=1.2, zorder=5)
        ax.text(EX0 + 3.5, y, f"GPIO{g}", fontsize=7.2, color="white", va="center", fontweight="bold", zorder=6)
        ax.text(EX0 + 12.5, y, s, fontsize=6.6, color="#e08a4a", va="center", zorder=6)
    for g, s, y, d in DER:
        ax.plot([EX1 - 3, EX1], [y, y], color="#c7ccd6", lw=1.2, zorder=5)
        ax.text(EX1 - 3.5, y, f"GPIO{g}", fontsize=7.2, color="white", va="center", ha="right", fontweight="bold", zorder=6)
        ax.text(EX1 - 12.5, y, s, fontsize=6.6, color="#e08a4a", va="center", ha="right", zorder=6)
    for y, nom, net, col in ((58, "VIN", "5V", U["red"]), (62, "3V3", "3V3", U["teal"]), (66, "GND", "GND", INK)):
        ax.plot([EX0, EX0 + 3], [y, y], color="#c7ccd6", lw=1.2, zorder=5)
        ax.text(EX0 + 3.5, y, nom, fontsize=7.2, color="white", va="center", fontweight="bold", zorder=6)
        flag(ax, EX0, y, net, col, lado="izq")
    ax.text((EX0 + EX1) / 2, 80, "Wi-Fi (AP, canal 1) + ESP-NOW", fontsize=6.8, color="#c7ccd6", ha="center", va="center", zorder=6)

    # ---- CONTADOR (izquierda arriba)
    caja(ax, 4, 19.5, 52, 60, "CONTADOR DE MONEDAS", fc="#f6f2ea", ec=COL["cnt"], lw=1.2, fs=8, tc=COL["cnt"])
    sub = [(24.5, 33.5, "Slider lineal 10 kΩ", "diámetro (0 a 3,3 V)"), (34.5, 43.5, "Barrera IR", "pasó una moneda"),
           (44.5, 58.0, "HX711 + celda 100 g", "peso de la moneda")]
    for y0, y1, t, d in sub:
        caja(ax, 6, y0, 31, y1, None, fc="white", ec=COL["cnt"])
        ax.text(7, y0 + 2.6, t, fontsize=7, fontweight="bold", va="center", zorder=6)
        ax.text(7, y0 + 5.4, d, fontsize=6.3, color=GRIS, va="center", zorder=6)
    ax.text(7, 55.5, "VCC 3V3 · GND", fontsize=6.0, color=GRIS, va="center", zorder=6)
    for g, s, y, d in IZQ[:4]:
        if d == "IN":
            flecha_h(ax, 31, EX0, y, COL["cnt"])
        else:
            flecha_h(ax, EX0, 31, y, COL["cnt"])
        ax.text(33, y - 1.5, {"DIAM": "OUT", "IR": "OUT", "HX1_DT": "DT", "HX1_SCK": "SCK"}[s], fontsize=6.3, color=COL["cnt"])

    # ---- BÁSCULA DEL NIDO (izquierda abajo)
    caja(ax, 4, 62.5, 52, 84, "BÁSCULA DEL NIDO (verifica cada vaso)", fc="#f6f2ea", ec=COL["bas"], lw=1.2, fs=7.6, tc=COL["bas"])
    caja(ax, 6, 66, 31, 82, None, fc="white", ec=COL["bas"])
    ax.text(7, 68.4, "HX711 + celda 500 g", fontsize=7, fontweight="bold", va="center", zorder=6)
    ax.text(7, 71.6, "pesa el vaso entregado:", fontsize=6.2, color=GRIS, va="center", zorder=6)
    ax.text(7, 74.2, "10 monedas de cada denom.", fontsize=6.2, color=GRIS, va="center", zorder=6)
    ax.text(7, 76.8, "pesan distinto", fontsize=6.2, color=GRIS, va="center", zorder=6)
    ax.text(7, 80, "→ denominación REAL", fontsize=6.3, color=COL["bas"], va="center", zorder=6, fontweight="bold")
    for g, s, y, d in IZQ[4:]:
        if d == "IN":
            flecha_h(ax, 31, EX0, y, COL["bas"])
        else:
            flecha_h(ax, EX0, 31, y, COL["bas"])
        ax.text(33, y - 1.5, "DT" if s.endswith("DT") else "SCK", fontsize=6.3, color=COL["bas"])

    # ---- BANDA (derecha arriba)
    caja(ax, 104, 19.5, 152, 49, "BANDA TRANSPORTADORA", fc="#f6f2ea", ec=COL["ban"], lw=1.2, fs=8, tc=COL["ban"])
    caja(ax, 106, 24, 130, 46, None, fc="white", ec=COL["ban"])
    ax.text(118, 25.8, "Driver L298N", fontsize=7.0, fontweight="bold", ha="center", va="center", zorder=6)
    for g, s, y, d in DER[:3]:
        flecha_h(ax, EX1, 106, y, COL["ban"])
        etiqueta_pin(ax, 106, y, s, "izq", fs=6.8)
    ax.text(129, 44, "+12 V · GND", fontsize=6.0, color=U["red"], ha="right", va="center", zorder=6)
    caja(ax, 138, 29, 150, 43, None, fc="white", ec=COL["ban"])
    ax.text(144, 36, "Motor DC\n12 V +\nreductor", fontsize=6, ha="center", va="center", zorder=6, linespacing=1.1)
    ax.plot([130, 138], [32, 32], color=COL["ban"], lw=1.4, zorder=4); ax.plot([130, 138], [40, 40], color=COL["ban"], lw=1.4, zorder=4)
    ax.text(134, 30.2, "OUT1", fontsize=5.6, ha="center", color=GRIS); ax.text(134, 42.2, "OUT2", fontsize=5.6, ha="center", color=GRIS)

    # ---- BRAZO (derecha abajo)
    caja(ax, 104, 52.5, 152, 84, "BRAZO DE EMBALAJE (tapa los vasos)", fc="#f6f2ea", ec=COL["bra"], lw=1.2, fs=8, tc=COL["bra"])
    for (g, s, y, d), nom in zip(DER[3:], ("servo base", "servo hombro", "servo pinza")):
        caja(ax, 106, y - 3.4, 132, y + 3.4, None, fc="white", ec=COL["bra"], lw=1.0)
        flecha_h(ax, EX1, 106, y, COL["bra"])
        etiqueta_pin(ax, 106, y, "señal · " + nom, "izq", fs=6.6)
    ax.text(150, 66.8, "V+ 5 V\naparte\n(buck 3 A)\nGND común", fontsize=6.0, color=U["red"], ha="right", va="center", zorder=6, linespacing=1.1)

    # ---- ALIMENTACIÓN
    ax.text(2, 90, "ALIMENTACIÓN DE LA ESTACIÓN", fontsize=9, fontweight="bold", va="center")
    caja(ax, 2, 93.5, 24, 104, None, fc=U["bat"], lw=1.2)
    ax.text(13, 98.7, "Fuente\n12 V / 5 A", fontsize=7.2, ha="center", va="center", fontweight="bold", zorder=6, linespacing=1.2)
    ax.plot([24, 30], [98.5, 98.5], color=U["red"], lw=1.6, zorder=4)
    caja(ax, 30, 94.5, 46, 102.5, None, fc="white", lw=1.1)
    ax.text(38, 98.5, "SW + fusible\n5 A", fontsize=6.6, ha="center", va="center", zorder=6, fontweight="bold", linespacing=1.15)
    ax.plot([46, 54], [98.5, 98.5], color=U["red"], lw=1.6, zorder=4)
    ax.plot([54], [98.5], marker="o", ms=3.4, color=U["red"], zorder=6)
    ax.text(54, 91.6, "+12 V → L298N y motor de la banda", fontsize=6.4, color=U["red"], va="center")
    ax.plot([54, 60], [98.5, 98.5], color=U["red"], lw=1.6, zorder=4)
    caja(ax, 60, 94.5, 84, 102.5, None, fc="white", ec="#c14fae", lw=1.2)
    ax.text(72, 98.5, "Buck 12→5 V / 3 A", fontsize=6.8, ha="center", va="center", fontweight="bold", color="#c14fae", zorder=6)
    ax.plot([84, 90], [98.5, 98.5], color=U["red"], lw=1.6, zorder=4)
    ax.text(91, 98.5, "5 V → ESP32 (VIN) · servos del brazo · HX711 · C 1000 µF", fontsize=6.6, color=U["red"], va="center")
    ax.text(91, 102.2, "GND común de toda la estación en un solo punto", fontsize=6.4, color=GRIS, va="center")
    return ax


def red(ax):
    x0, x1 = 156, 190
    xc = (x0 + x1) / 2
    ax.text(x0, 11.3, "RED Y COMUNICACIÓN", fontsize=10.5, fontweight="bold", va="center")
    caja(ax, x0, 15.5, x1, 28, None, fc="white", ec=INK, lw=1.2)
    ax.text(xc, 19.3, "PC / portátil", fontsize=8.6, fontweight="bold", ha="center", va="center", zorder=6)
    ax.text(xc, 24.0, "Streamlit: dashboard + chatbot", fontsize=6.6, ha="center", va="center", zorder=6)
    ax.annotate("", xy=(xc, 39), xytext=(xc, 28), arrowprops=dict(arrowstyle="<->", color=U["teal"], lw=1.6), zorder=5)
    ax.text(xc + 1.8, 33.5, "Wi-Fi: AP «monedas»\nHTTP GET /data (JSON)", fontsize=6.2, color=U["teal"], va="center", linespacing=1.15)
    caja(ax, x0 + 3, 39, x1 - 3, 49, None, fc="#1d2430", ec=INK, lw=1.4)
    ax.text(xc, 42.6, "ESTACIÓN (ESP32 #0)", fontsize=7.8, color="white", fontweight="bold", ha="center", va="center", zorder=6)
    ax.text(xc, 46.4, "192.168.4.1", fontsize=6.4, color="#e08a4a", ha="center", va="center", zorder=6)
    cols = ["#b8480f", "#1f6f6b", "#c9a24a", "#6a5fd8", "#c14fae"]
    xs = [x0 + 5 + i * 6.3 for i in range(5)]
    for i, (cx, c) in enumerate(zip(xs, cols)):
        ax.plot([xc, cx], [49, 59], color=U["violet"], lw=1.0, zorder=3)
        ax.add_patch(Rectangle((cx - 2.6, 59), 5.2, 4.2, fc=c, ec=INK, lw=1.0, zorder=4))
        ax.text(cx, 61.1, f"C{i + 1}", fontsize=6, color="white", ha="center", va="center", fontweight="bold", zorder=6)
    for a, b in zip(xs[:-1], xs[1:]):
        ax.plot([a + 2.6, b - 2.6], [64.6, 64.6], color=U["violet"], lw=0.9, ls=":", zorder=3)
    ax.text(xc, 67.4, "malla ESP-NOW · canal 1 · broadcast", fontsize=6.6, color=U["violet"], ha="center", va="center", fontweight="bold")
    ax.text(x0, 71.2, "MENSAJES (≤ 250 B)", fontsize=8.0, fontweight="bold", va="center")
    msgs = [("DEPÓSITO · 5 B", "carrito → todos: id, celda (x,y), cantidad de feromona"),
            ("TELEMETRÍA · 15 B", "carrito → todos: estado, errores, entregas bien/mal, falsos por denominación"),
            ("VERIFICACIÓN · 3 B", "estación → carrito: denominación REAL pesada en el nido")]
    y = 74.4
    for t, d in msgs:
        ax.text(x0, y, t, fontsize=6.7, fontweight="bold", va="center", color=U["violet"])
        lineas = textwrap.wrap(d, 52)
        ax.text(x0, y + 1.9, "\n".join(lineas), fontsize=6.1, va="top", color="#3a4150", linespacing=1.05)
        y += 3.4 + 2.15 * len(lineas)
    return ax


def generar(salida="06_esquema_sistema"):
    fig = lamina("Esquema eléctrico y de comunicación de todo el proyecto", "6/7", "s/e",
                 "Estación central + red ESP-NOW de 5 carritos + PC · los pines de la estación son diseño: su firmware aún está pendiente")
    ax = fig.add_axes([0, 0, 1, 1], facecolor="none"); ax.set_xlim(0, 192); ax.set_ylim(108, 0); ax.axis("off")
    estacion(ax); red(ax)
    guardar(fig, salida)


if __name__ == "__main__":
    generar()

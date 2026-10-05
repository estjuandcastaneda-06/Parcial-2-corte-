"""Lámina 5 — Esquema eléctrico del carrito: cada GPIO del ESP32 cableado a su módulo + alimentación.
Los pines salen de datos_carrito.PINES (misma fuente que el firmware)."""
from matplotlib.patches import Rectangle

from estilo import *
import datos_carrito as D

U = dict(blue="#2a56b0", teal="#1f6f6b", gold="#b8892b", violet="#7a5fd0", orange="#d9822b", pink="#c14fae", red="#aa2222",
         bat="#e0b040")
X_ESP0, X_ESP1 = 46, 74            # caja del ESP32
X_PIN = X_ESP1
X_MOD = 98                          # borde izquierdo de los módulos


def fila(i):
    g = 0 if i <= 10 else (1 if i <= 13 else (2 if i <= 15 else (3 if i <= 17 else (4 if i == 18 else 5))))
    return 20.6 + 3.25 * i + 3.6 * g


# orden de filas (arriba -> abajo), agrupadas por módulo
ORDEN = [25, 26, 27, 14, 32, 4, 13,          # TB6612
         36, 39, 34, 35,                      # encoders: motor DER (arriba) y IZQ (abajo)
         18, 19, 23,                          # TCS3200
         21, 22,                              # I2C
         16, 17,                              # servos
         5,                                   # LED
         33]                                  # divisor de batería
GRUPO_COLOR = [U["blue"]] * 7 + [U["teal"]] * 4 + [U["gold"]] * 3 + [U["violet"]] * 2 + [U["orange"]] * 2 + [U["pink"]] + [U["red"]]
PIN = {g: (d, s, m, pm) for g, d, s, m, pm in D.PINES}


def caja(ax, x0, y0, x1, y1, titulo=None, fc="white", ec=INK, lw=1.2, fs=8.5, tc=INK):
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=fc, ec=ec, lw=lw, zorder=3))
    if titulo:
        ax.text(x0 + 1.2, y0 + 1.7, titulo, fontsize=fs, fontweight="bold", va="center", ha="left", color=tc, zorder=6)


def etiqueta_pin(ax, x, y, s, lado="izq", fs=7.4, color=INK, bold=False):
    ax.text(x + (1.0 if lado == "izq" else -1.0), y, s, fontsize=fs, ha="left" if lado == "izq" else "right", va="center",
            color=color, zorder=6, fontweight="bold" if bold else "normal")


def flag(ax, x, y, nombre, color, lado="izq"):
    """Bandera de potencia / net label."""
    ax.plot([x, x + (-1.2 if lado == "izq" else 1.2)], [y, y], color=color, lw=1.2, zorder=4)
    ax.text(x + (-1.5 if lado == "izq" else 1.5), y, nombre, fontsize=7.2, ha="right" if lado == "izq" else "left", va="center",
            color=color, fontweight="bold", zorder=6)


def wire(ax, x0, x1, y, color, entra=False, lw=1.5, z=4):
    ax.plot([x0, x1], [y, y], color=color, lw=lw, zorder=z, solid_capstyle="round")
    xr = x0 if entra else x1
    d = -1.3 if entra else 1.3
    ax.fill([xr, xr - d, xr - d], [y, y - 0.55, y + 0.55], color=color, zorder=5)


def dibujar(fig):
    ax = fig.add_axes([0, 0, 1, 1], facecolor="none")
    ax.set_xlim(0, 192); ax.set_ylim(108, 0); ax.axis("off")
    ax.text(X_MOD - 2, 11.4, "Flechas: salida del ESP32 → módulo (OUT) · módulo → ESP32 (IN: encoders y OUT del TCS3200) · punto = bus compartido",
            fontsize=7.4, color=GRIS, va="center")

    # ------------------------------------------------------------ ESP32
    caja(ax, X_ESP0, 12.5, X_ESP1, 104.0, None, fc="#1d2430", ec=INK, lw=1.6)
    ax.text((X_ESP0 + X_ESP1) / 2, 14.6, "ESP32 DevKit V1", fontsize=10, fontweight="bold", color="white", ha="center", va="center", zorder=6)
    ax.text((X_ESP0 + X_ESP1) / 2, 17.4, "30 pines · WROOM-32", fontsize=7.2, color="#c7ccd6", ha="center", va="center", zorder=6)
    for i, g in enumerate(ORDEN):
        y = fila(i)
        d, s, mod, pm = PIN[g]
        ax.plot([X_PIN - 3.0, X_PIN], [y, y], color="#c7ccd6", lw=1.2, zorder=5)
        ax.text(X_PIN - 3.4, y, f"GPIO{g}", fontsize=7.4, color="white", ha="right", va="center", zorder=6, fontweight="bold")
        ax.text(X_PIN - 11.6, y, s, fontsize=7.0, color="#e08a4a", ha="right", va="center", zorder=6)
    # pines de alimentación (izquierda del ESP32)
    for y, nom, col, net in ((62, "VIN", U["red"], "5V"), (67, "3V3", U["teal"], "3V3"), (72, "GND", INK, "GND")):
        ax.plot([X_ESP0, X_ESP0 + 3.2], [y, y], color="#c7ccd6", lw=1.2, zorder=5)
        ax.text(X_ESP0 + 3.6, y, nom, fontsize=7.4, color="white", va="center", fontweight="bold", zorder=6)
        flag(ax, X_ESP0, y, net, col, lado="izq")
    ax.text(X_ESP0 - 1.6, 79, "GPIO0/2/12/15: libres\n(pines de arranque)", fontsize=6.4, color=GRIS, ha="right", va="center", zorder=6, linespacing=1.15)

    # ------------------------------------------------------------ cables ESP32 -> módulos (cada uno termina en el borde de su módulo)
    destino = {0: X_MOD + 2, 1: X_MOD + 2, 2: X_MOD + 2, 3: X_MOD + 2, 4: X_MOD + 2, 5: X_MOD + 2, 6: X_MOD + 2,
               7: X_MOD + 36, 8: X_MOD + 36, 9: X_MOD + 36, 10: X_MOD + 36, 11: X_MOD - 2, 12: X_MOD - 2, 13: X_MOD - 2,
               16: X_MOD - 2, 17: X_MOD - 2, 18: X_MOD - 2}
    for i, g in enumerate(ORDEN):
        d = PIN[g][0]
        if i in destino:
            wire(ax, X_PIN, destino[i], fila(i), GRUPO_COLOR[i], entra=(d == "IN"))

    # ------------------------------------------------------------ BLOQUE DE TRACCIÓN
    caja(ax, X_MOD - 2, 13.4, 176, fila(10) + 3.6, "BLOQUE DE TRACCIÓN — TB6612FNG + 2 motorreductores N20 con encoder",
         fc="#f6f2ea", lw=1.1, fs=8, tc=U["blue"])
    caja(ax, X_MOD + 2, 16.6, X_MOD + 24, fila(6) + 3.2, None, fc="white")
    ax.text(X_MOD + 13, fila(3) + 0.2, "TB6612FNG", fontsize=8.6, fontweight="bold", ha="center", va="center", zorder=6)
    for i, nom in enumerate(("PWMA", "AIN1", "AIN2", "PWMB", "BIN1", "BIN2", "STBY")):
        etiqueta_pin(ax, X_MOD + 2, fila(i), nom, "izq")
    for r, nom in {1: "AO1", 2: "AO2", 4: "BO1", 5: "BO2"}.items():
        ax.plot([X_MOD + 24, X_MOD + 26.5], [fila(r), fila(r)], color=U["blue"], lw=1.4, zorder=4)
        etiqueta_pin(ax, X_MOD + 24, fila(r), nom, "der")
    ax.text(X_MOD + 13, fila(6) + 1.8, "VM←VBAT · VCC←3V3 · GND", fontsize=5.6, color=GRIS, ha="center", va="center", zorder=6)
    # motores (DER arriba, IZQ abajo)
    caja(ax, X_MOD + 36, fila(7) - 3.0, X_MOD + 56, fila(8) + 1.4, None, fc="white")
    caja(ax, X_MOD + 36, fila(9) - 1.4, X_MOD + 56, fila(10) + 2.4, None, fc="white")
    ax.text(X_MOD + 46, fila(7) - 1.4, "Motor DER N20", fontsize=7, fontweight="bold", ha="center", va="center", zorder=6)
    ax.text(X_MOD + 46, fila(9) - 0.2, "Motor IZQ N20", fontsize=7, fontweight="bold", ha="center", va="center", zorder=6)
    for r, nom in ((7, "Hall A"), (8, "Hall B"), (9, "Hall A"), (10, "Hall B")):
        etiqueta_pin(ax, X_MOD + 36, fila(r), nom, "izq", fs=6.8)
    for r, nom in ((7, "M−"), (8, "M+"), (9, "M−"), (10, "M+")):
        etiqueta_pin(ax, X_MOD + 56, fila(r), nom, "der", fs=6.8)
    # cableado de potencia de los motores (rutas anidadas, sin cruces)
    for src, dst, xt in ((1, 10, 165), (2, 9, 162), (4, 8, 159), (5, 7, 156)):
        ys, yd = fila(src), fila(dst)
        ax.plot([X_MOD + 26.5, xt, xt, X_MOD + 56], [ys, ys, yd, yd], color=U["blue"], lw=1.4, zorder=4)
        ax.plot([xt], [yd], marker="o", ms=2.6, color=U["blue"], zorder=5)

    # ------------------------------------------------------------ TCS3200
    caja(ax, X_MOD - 2, fila(11) - 2.6, X_MOD + 40, fila(13) + 2.8, "TCS3200 (color)", fc="white", ec=U["gold"], fs=8.3, tc=U["gold"])
    for r, nom in ((11, "S2"), (12, "S3"), (13, "OUT")):
        etiqueta_pin(ax, X_MOD - 2, fila(r), nom, "izq")
    ax.text(X_MOD + 38.5, fila(12) + 0.6, "S0→3V3 · S1→GND\nVCC→3V3 · LED→3V3\nOE→GND · GND", fontsize=6.2, color=GRIS, ha="right", va="center", zorder=6, linespacing=1.15)

    # ------------------------------------------------------------ I2C: VL53L0X + MPU6050 (bus compartido)
    for r in (14, 15):
        ax.plot([X_PIN, X_MOD + 28], [fila(r), fila(r)], color=U["violet"], lw=1.5, zorder=2.5)
        ax.plot([X_MOD - 2, X_MOD + 28], [fila(r), fila(r)], color=U["violet"], lw=1.5, zorder=2.5)
        ax.plot([X_MOD - 2], [fila(r)], marker="o", ms=3.2, color=U["violet"], zorder=6)
        ax.plot([X_MOD + 28], [fila(r)], marker="o", ms=3.2, color=U["violet"], zorder=6)
    caja(ax, X_MOD - 2, fila(14) - 3.2, X_MOD + 22, fila(15) + 2.8, "VL53L0X (ToF)", fc="white", ec=U["violet"], fs=7.8, tc=U["violet"])
    caja(ax, X_MOD + 28, fila(14) - 3.2, X_MOD + 52, fila(15) + 2.8, "MPU6050", fc="white", ec=U["violet"], fs=7.8, tc=U["violet"])
    for r, nom in ((14, "SDA"), (15, "SCL")):
        etiqueta_pin(ax, X_MOD - 2, fila(r), nom, "izq"); etiqueta_pin(ax, X_MOD + 28, fila(r), nom, "izq")
    ax.text(X_MOD + 56, fila(14) + 1.6, "bus I2C compartido\n0x29 (ToF) · 0x68 (IMU)\nVCC → 3V3", fontsize=6.4, color=GRIS, va="center", linespacing=1.15)

    # ------------------------------------------------------------ servos
    caja(ax, X_MOD - 2, fila(16) - 3.0, X_MOD + 32, fila(17) + 2.8, "2× servo SG90 (pinza)", fc="white", ec=U["orange"], fs=7.8, tc=U["orange"])
    for r, nom in ((16, "señal izq."), (17, "señal der.")):
        etiqueta_pin(ax, X_MOD - 2, fila(r), nom, "izq")
    ax.text(X_MOD + 30.5, fila(16) + 2.0, "V+ → 5V\nGND", fontsize=6.4, color=U["red"], ha="right", va="center", zorder=6, linespacing=1.15)

    # ------------------------------------------------------------ LED
    caja(ax, X_MOD - 2, fila(18) - 2.6, X_MOD + 32, fila(18) + 2.6, "WS2812", fc="white", ec=U["pink"], fs=7.8, tc=U["pink"])
    etiqueta_pin(ax, X_MOD - 2, fila(18), "DIN", "izq")
    ax.text(X_MOD + 30.5, fila(18) + 0.0, "5V · GND", fontsize=6.4, color=U["red"], ha="right", va="center", zorder=6)
    wire(ax, X_PIN, X_MOD - 2, fila(18), U["pink"])

    # ------------------------------------------------------------ divisor de batería (GPIO33)
    yv = fila(19)
    wire(ax, X_PIN, X_MOD + 6, yv, U["red"], entra=True)
    ax.plot([X_MOD + 6], [yv], marker="o", ms=3, color=U["red"], zorder=6)
    rect(ax, X_MOD + 8, yv - 1.0, 9, 2.0, fc="white", ec=U["red"], lw=1.2, z=4)           # R1 100k (horizontal)
    ax.plot([X_MOD + 6, X_MOD + 8], [yv, yv], color=U["red"], lw=1.5, zorder=4)
    ax.plot([X_MOD + 17, X_MOD + 20], [yv, yv], color=U["red"], lw=1.5, zorder=4)
    ax.text(X_MOD + 21.5, yv, "VBAT (7,4 V)", fontsize=6.8, color=U["red"], va="center", fontweight="bold")
    ax.text(X_MOD + 12.5, yv - 2.6, "R1 100k", fontsize=6.2, ha="center", va="center", color=U["red"])
    rect(ax, X_MOD + 5.0, yv + 1.4, 2.0, 3.2, fc="white", ec=U["red"], lw=1.2, z=4)        # R2 47k (vertical)
    ax.plot([X_MOD + 6, X_MOD + 6], [yv, yv + 1.4], color=U["red"], lw=1.5, zorder=4)
    ax.plot([X_MOD + 6, X_MOD + 6], [yv + 4.6, yv + 5.6], color=U["red"], lw=1.5, zorder=4)
    ax.text(X_MOD + 8.5, yv + 3.0, "R2 47k", fontsize=6.2, va="center", color=U["red"])
    flag(ax, X_MOD + 6, yv + 5.6, "GND", INK, lado="der")

    # ------------------------------------------------------------ ALIMENTACIÓN
    ax.text(2, 15, "ALIMENTACIÓN", fontsize=10, fontweight="bold", va="center")
    rect(ax, 2, 22, 11, 8, fc=U["bat"], ec=INK, lw=1.2, z=4)                           # batería
    ax.text(7.5, 26, "LiPo 2S\n850 mAh", fontsize=6.4, ha="center", va="center", zorder=6, fontweight="bold", linespacing=1.1)
    ax.text(14.0, 22.4, "+", fontsize=9, color=U["red"], fontweight="bold", va="center")
    ax.text(14.0, 29.0, "−", fontsize=9, va="center", fontweight="bold")
    ax.plot([13, 16], [24, 24], color=U["red"], lw=1.6, zorder=4)
    caja(ax, 16, 21.5, 21.5, 26.5, None, fc="white", lw=1.1)
    ax.text(18.75, 24, "SW", fontsize=7, ha="center", va="center", zorder=6, fontweight="bold")
    ax.plot([21.5, 24], [24, 24], color=U["red"], lw=1.6, zorder=4)
    caja(ax, 24, 22, 30, 26, None, fc="white", lw=1.1)
    ax.text(27, 24, "F 3A", fontsize=6.6, ha="center", va="center", zorder=6, fontweight="bold")
    ax.plot([30, 32], [24, 24], color=U["red"], lw=1.6, zorder=4)
    ax.plot([32], [24], marker="o", ms=3.4, color=U["red"], zorder=6)
    ax.plot([32, 32], [24, 47], color=U["red"], lw=1.6, zorder=4)
    ax.text(32, 20.4, "VBAT", fontsize=7.2, color=U["red"], fontweight="bold", va="center", ha="center")
    ax.text(30.6, 36, "→ VM del TB6612\n→ divisor R1", fontsize=6.2, color=U["red"], va="center", ha="right", linespacing=1.15)
    ax.plot([7.5, 7.5], [30, 33.5], color=INK, lw=1.4, zorder=4)
    flag(ax, 7.5, 33.5, "GND", INK, lado="der")
    caja(ax, 16, 44, 30, 56, None, fc="white", ec="#c14fae", lw=1.3)                    # buck
    ax.text(23, 47.6, "MP1584", fontsize=7.8, ha="center", va="center", fontweight="bold", color="#c14fae", zorder=6)
    ax.text(23, 51.0, "buck 3 A → 5,0 V", fontsize=6.0, ha="center", va="center", zorder=6)
    ax.plot([30, 32], [47, 47], color=U["red"], lw=1.6, zorder=4)
    ax.text(29.2, 45.4, "IN+", fontsize=5.8, ha="right", va="center", color=GRIS, zorder=6)
    ax.plot([16, 8, 8], [53, 53, 62], color=U["red"], lw=1.6, zorder=4)
    ax.text(16.8, 54.4, "OUT+", fontsize=5.8, ha="left", va="center", color=GRIS, zorder=6)
    ax.plot([8], [57], marker="o", ms=3.4, color=U["red"], zorder=6)
    flag(ax, 8, 62, "5V", U["red"], lado="der")
    ax.plot([8, 12], [57, 57], color=U["red"], lw=1.4, zorder=4)                        # C1 1000 µF en el riel de 5 V
    ax.plot([12, 12], [54.8, 59.2], color=INK, lw=1.8, zorder=4)
    ax.plot([14, 14], [54.8, 59.2], color=INK, lw=1.8, zorder=4)
    ax.plot([14, 16.5], [57, 57], color=INK, lw=1.4, zorder=4)
    flag(ax, 16.5, 57, "GND", INK, lado="der")
    ax.text(13.5, 60.8, "C1 1000 µF/16 V", fontsize=6.0, ha="left", va="center")
    # qué cuelga de cada riel
    ax.text(2, 70, "5V  →  ESP32 (VIN), 2× SG90 (V+), WS2812", fontsize=7.0, color=U["red"], va="center")
    ax.text(2, 75.5, "3V3 →  TCS3200, VL53L0X, MPU6050, Hall de los N20 y\n          VCC lógico del TB6612FNG (regulador del ESP32)", fontsize=6.8, color=U["teal"], va="center", linespacing=1.2)
    ax.text(2, 82, "VBAT →  VM del TB6612FNG (motores) y divisor de batería", fontsize=7.0, color=U["red"], va="center")
    ax.text(2, 87.5, "GND común: batería, buck, ESP32 y todos los módulos,\nunidos en UN solo punto (estrella) junto al buck.", fontsize=6.8, va="center", linespacing=1.2)
    ax.text(2, 94, "Los picos de 2×500 mA de los servos caen del riel de 5 V:\nC1 evita que reinicien el ESP32.", fontsize=6.7, va="center", color=GRIS, linespacing=1.2)
    ax.text(2, 100, "PWM de motores limitado al 80 % (N20 de 6 V con batería de 7,4 V).", fontsize=6.7, va="center", color=GRIS)
    return ax


def generar(salida="05_esquema_carrito"):
    fig = lamina("Esquema eléctrico del carrito — conexiones al ESP32", "5/7", "s/e",
                 "Cada GPIO va a su módulo; los pines salen de datos_carrito.py (la misma tabla que usa el firmware) · la hoja 5b es la tabla de conexiones")
    dibujar(fig)
    guardar(fig, salida)


if __name__ == "__main__":
    generar()

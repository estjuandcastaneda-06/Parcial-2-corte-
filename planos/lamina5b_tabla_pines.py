"""Lámina 5b — Tabla de conexiones del carrito (pines del ESP32 y redes de alimentación)."""
import textwrap

from estilo import *
import datos_carrito as D

NOTAS = {
    25: "PWM 20 kHz (LEDC canal 4) · velocidad motor izq.", 26: "dirección motor izq. (con AIN2)", 27: "dirección motor izq. (con AIN1)",
    14: "PWM 20 kHz (LEDC canal 5) · velocidad motor der. · saca PWM al arrancar", 32: "dirección motor der. (con BIN2)",
    4: "dirección motor der. (con BIN1)", 13: "STBY: alto = habilita el puente H (bajo al arrancar)",
    34: "solo entrada · interrupción (flancos de A)", 35: "solo entrada · sentido de giro del motor izq.",
    36: "solo entrada (VP) · interrupción (flancos de A)", 39: "solo entrada (VN) · sentido de giro del motor der.",
    18: "elige el filtro de color (con S3)", 19: "elige el filtro de color (con S2)", 23: "salida del TCS3200: frecuencia → pulseIn()",
    21: "I2C 400 kHz · VL53L0X (0x29) + MPU6050 (0x68)", 22: "I2C 400 kHz", 16: "PWM 50 Hz · ESP32Servo", 17: "PWM 50 Hz · ESP32Servo",
    5: "1 LED WS2812; pin de arranque: parpadea al reiniciar", 33: "ADC1_CH5 · 7,4 V × 47/147 = 2,4 V (máx. 8,4 V → 2,7 V). Nunca ADC2 con Wi-Fi/ESP-NOW",
}
GRUPOS = {"TB6612FNG": "#2a56b0", "Motor izq. N20": "#1f6f6b", "Motor der. N20": "#1f6f6b", "TCS3200": "#b8892b",
          "VL53L0X + MPU6050": "#7a5fd0", "Servo SG90 izq.": "#d9822b", "Servo SG90 der.": "#d9822b", "WS2812": "#c14fae",
          "Divisor 100k/47k": "#aa2222"}


def tabla_senales(fig):
    ax = fig.add_axes([0.02, 0.07, 0.60, 0.80]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.text(0.0, 1.0, "SEÑALES DEL ESP32 (DevKit V1, 30 pines)", fontsize=12.5, fontweight="bold", va="top")
    cols = [(0.005, "GPIO", "left"), (0.075, "Dir.", "left"), (0.135, "Señal", "left"), (0.27, "Módulo", "left"), (0.44, "Pin del módulo", "left"), (0.57, "Nota", "left")]
    y0, dy = 0.945, 0.0425
    ax.add_patch(Rectangle((0, y0 - dy * 0.55), 1, dy, fc=INK, ec="none"))
    for x, t, ha in cols:
        ax.text(x, y0 - dy * 0.05, t, fontsize=9.2, color="white", fontweight="bold", ha=ha, va="center")
    for i, (g, d, s, m, pm) in enumerate(D.PINES):
        y = y0 - dy * (i + 1.1)
        if i % 2 == 0:
            ax.add_patch(Rectangle((0, y - dy * 0.5), 1, dy, fc="#efe8d6", ec="none"))
        ax.add_patch(Rectangle((0, y - dy * 0.5), 0.004, dy, fc=GRUPOS.get(m, INK), ec="none"))
        ax.text(0.012, y, str(g), fontsize=9, fontweight="bold", va="center")
        ax.text(0.075, y, d, fontsize=8.6, va="center", color=ACC if d == "IN" else INK)
        ax.text(0.135, y, s, fontsize=8.8, va="center")
        ax.text(0.27, y, m, fontsize=8.6, va="center")
        ax.text(0.44, y, pm, fontsize=8.6, va="center")
        ax.text(0.57, y, "\n".join(textwrap.wrap(NOTAS[g], 52)), fontsize=7.2, va="center", color="#3a4150", linespacing=1.05)
    return ax


def tabla_potencia(fig):
    ax = fig.add_axes([0.64, 0.45, 0.345, 0.42]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.text(0.0, 1.0, "REDES DE ALIMENTACIÓN", fontsize=12.5, fontweight="bold", va="top")
    filas = [
        ("VBAT\n7,4 V", "LiPo 2S → interruptor → fusible 3 A", "TB6612 (VM) · entrada del buck MP1584 · R1 del divisor", "#aa2222"),
        ("5 V", "salida del buck MP1584 (3 A) + C1 1000 µF", "ESP32 (VIN) · 2× SG90 (V+) · WS2812 (VDD)", "#aa2222"),
        ("3V3", "regulador del ESP32 (≈80 mA de carga)", "TCS3200 (VCC, S0, LED) · VL53L0X · MPU6050 · Hall de los N20 · TB6612 (VCC)", "#1f6f6b"),
        ("GND", "un solo punto (estrella) junto al buck", "todos los módulos; los servos y motores regresan por cables gruesos", INK),
    ]
    y = 0.88
    for net, origen, dest, col in filas:
        ax.add_patch(Rectangle((0, y - 0.19), 1, 0.2, fc="white", ec=INK, lw=0.9))
        ax.add_patch(Rectangle((0, y - 0.19), 0.17, 0.2, fc=col, ec=INK, lw=0.9))
        ax.text(0.085, y - 0.09, net, fontsize=10, fontweight="bold", color="white", ha="center", va="center")
        ax.text(0.19, y - 0.045, origen, fontsize=8, va="center", fontweight="bold")
        ax.text(0.19, y - 0.13, "\n".join(textwrap.wrap(dest, 56)), fontsize=7.4, va="center", color="#3a4150", linespacing=1.1)
        y -= 0.225
    return ax


def notas(fig):
    ax = fig.add_axes([0.64, 0.07, 0.345, 0.36]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.text(0.0, 1.0, "OBSERVACIONES DE CABLEADO", fontsize=12.5, fontweight="bold", va="top")
    items = [
        "Motor izquierdo en los canales A del TB6612 (AO1/AO2) y derecho en los B (BO1/BO2). Si un motor gira al revés, se invierten sus cables o el signo en el firmware.",
        "Los encoders se alimentan con 3V3 (no con 5 V) para que sus salidas sean seguras para el ESP32.",
        "S0 va fijo a 3V3 y S1 a GND (escala de frecuencia 20 %): ahorra 2 pines.",
        "GPIO34/35/36/39 son solo entrada y sin pull-up interno: si el encoder de tus N20 es de colector abierto, ponle 10 kΩ a 3V3.",
        "GPIO0, 2, 12 y 15 quedan sin usar: son pines de arranque y pueden impedir que el ESP32 inicie.",
        "El canal Wi-Fi/ESP-NOW es el 1 en los 5 carritos y en la estación del nido.",
    ]
    y = 0.92
    for t in items:
        lineas = textwrap.wrap(t, 70, subsequent_indent="  ")
        ax.text(0.0, y, "• " + "\n".join(lineas), fontsize=8.2, va="top", linespacing=1.18)
        y -= 0.055 * len(lineas) + 0.022
    return ax


def generar(salida="05b_tabla_conexiones"):
    fig = lamina("Tabla de conexiones del carrito", "5b/7", "s/e", "Complemento del esquema eléctrico: qué va a cada pin y de dónde sale cada riel de alimentación")
    tabla_senales(fig); tabla_potencia(fig); notas(fig)
    guardar(fig, salida)


if __name__ == "__main__":
    generar()

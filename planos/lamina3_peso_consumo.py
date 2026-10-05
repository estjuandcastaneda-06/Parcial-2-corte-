"""Lámina 3 — Tabla de pesos, balance de potencia, autonomía y estabilidad."""
import textwrap

from estilo import *
import datos_carrito as D

PISO = {"inf": "inferior", "med": "pinza", "sup": "superior"}


def tabla_pesos(fig):
    ax = fig.add_axes([0.02, 0.07, 0.42, 0.80]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.text(0.0, 1.0, "PESO POR COMPONENTE (g)", fontsize=13, fontweight="bold", va="top")
    n = len(D.PARTES)
    y0, dy = 0.945, 0.0345
    ax.add_patch(Rectangle((0, y0 - dy * 0.55), 1, dy, fc=INK, ec="none", transform=ax.transData))
    for x, t, ha in ((0.01, "N°", "left"), (0.07, "Componente", "left"), (0.78, "Piso", "left"), (0.99, "Masa", "right")):
        ax.text(x, y0 - dy * 0.05, t, fontsize=9.5, color="white", fontweight="bold", ha=ha, va="center")
    for i, p in enumerate(D.PARTES):
        y = y0 - dy * (i + 1.1)
        if i % 2 == 0:
            ax.add_patch(Rectangle((0, y - dy * 0.5), 1, dy, fc="#efe8d6", ec="none"))
        ax.text(0.01, y, str(i + 1), fontsize=9, va="center")
        ax.text(0.07, y, p["nombre"], fontsize=9.2, va="center")
        ax.text(0.78, y, PISO[p["piso"]], fontsize=8.8, va="center", color=GRIS)
        ax.text(0.99, y, f'{p["m"]:.1f}'.rstrip("0").rstrip("."), fontsize=9.2, va="center", ha="right")
    y = y0 - dy * (n + 1.25)
    ax.plot([0, 1], [y + dy * 0.45, y + dy * 0.45], color=INK, lw=1.3)
    ax.text(0.07, y, "MASA DEL CARRITO VACÍO", fontsize=10.5, fontweight="bold", va="center")
    ax.text(0.99, y, f"{D.MASA_VACIO:.0f} g", fontsize=10.5, fontweight="bold", va="center", ha="right", color=ACC)
    y -= dy * 1.05
    ax.text(0.07, y, f"+ vaso ({D.VASO_MASA:.0f} g) con 10 monedas de $1.000 (9,95 g c/u)", fontsize=9.4, va="center")
    ax.text(0.99, y, f"{D.MASA_PAYLOAD_MAX:.0f} g", fontsize=9.6, va="center", ha="right")
    y -= dy * 1.05
    ax.text(0.07, y, "MASA CARGADO (peor caso)", fontsize=10.5, fontweight="bold", va="center")
    ax.text(0.99, y, f"{D.MASA_CARGADO:.0f} g", fontsize=10.5, fontweight="bold", va="center", ha="right", color=ACC)
    y -= dy * 1.5
    ax.text(0.0, y, "Carga útil por denominación (vaso de 12 g + 10 monedas):  " +
            "   ".join(f"${d}: {D.vaso_masa(d):.0f} g" for d in (50, 100, 200, 500, 1000)), fontsize=8.6, va="center", color=GRIS)
    return ax


def grafico_potencia(fig):
    pw = D.balance_potencia()
    ax = fig.add_axes([0.52, 0.52, 0.25, 0.33])
    nombres = ["2× motor N20", "ESP32 + ESP-NOW", "Sensores (color,\nToF, IMU, enc.)", "2× servo SG90\n(uso medio)", "LED WS2812"]
    vals = [pw["pm_med"], pw["p_esp"], pw["p_sens"], pw["p_serv"], pw["p_led"]]
    cols = ["#b8480f", "#1d2430", "#1f6f6b", "#3a6fb0", "#c9a24a"]
    y = range(len(vals))[::-1]
    ax.barh(list(y), vals, color=cols, height=0.62)
    for yi, v in zip(y, vals):
        ax.text(v + 0.03, yi, f"{v:.2f} W", va="center", fontsize=9.5, fontweight="bold")
    ax.set_yticks(list(y)); ax.set_yticklabels(nombres, fontsize=9)
    ax.set_xlim(0, 2.2); ax.set_xlabel("potencia media tomada de la batería (W)", fontsize=9)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="x", labelsize=8.5)
    ax.set_title(f"CONSUMO MEDIO TOTAL ≈ {pw['p_med']:.2f} W", fontsize=12, fontweight="bold", loc="left", pad=10)
    return ax


def rieles(fig):
    pw = D.balance_potencia()
    ax = fig.add_axes([0.46, 0.07, 0.31, 0.40]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.text(0.0, 1.0, "CORRIENTES Y DIMENSIONAMIENTO", fontsize=12, fontweight="bold", va="top")
    filas = [
        ("Riel 5 V (ESP32 + sensores + servos + LED)", f"{pw['i5_med']*1000:.0f} mA", f"{pw['i5_pico']*1000:.0f} mA"),
        ("Batería 7,4 V (todo, con pérdidas del buck/driver)", f"{pw['i_med']*1000:.0f} mA", f"{pw['i_pico']*1000:.0f} mA"),
        ("Potencia total", f"{pw['p_med']:.1f} W", f"{pw['p_pico']:.1f} W"),
    ]
    ax.text(0.80, 0.88, "media", fontsize=9.5, fontweight="bold", ha="right")
    ax.text(0.99, 0.88, "pico", fontsize=9.5, fontweight="bold", ha="right")
    y = 0.80
    for t, a, b in filas:
        ax.text(0.0, y, t, fontsize=9.2, va="center"); ax.text(0.80, y, a, fontsize=9.5, ha="right", va="center", fontweight="bold")
        ax.text(0.99, y, b, fontsize=9.5, ha="right", va="center", color=ACC, fontweight="bold")
        y -= 0.1
    ax.plot([0, 1], [y + 0.04, y + 0.04], color=GRIS, lw=0.8)
    notas = [
        f"• Batería LiPo 2S 850 mAh = {pw['wh']:.2f} Wh; usable 80 % → autonomía ≈ {pw['autonomia_h']:.1f} h (teórica; esperar ≈1 h real).",
        "• Pico = ambos motores bloqueados (600 mA c/u) + ambos servos a 500 mA: dura < 1 s.",
        "• Buck MP1584 (3 A) con condensador de 1000 µF en el riel de 5 V: los servos NO deben reiniciar el ESP32.",
        "• Fusible de 3 A en la batería; motores N20 de 6 V con PWM limitado al 80 % (batería 7,4 V).",
        "• TB6612FNG: 1,2 A continuos por canal: sobra para 2 N20 (< 0,6 A de pico).",
    ]
    y -= 0.04
    for t in notas:
        lineas = textwrap.wrap(t, 66, subsequent_indent="   ")
        ax.text(0.0, y, "\n".join(lineas), fontsize=9.0, va="top", linespacing=1.35)
        y -= 0.050 * len(lineas) + 0.018
    return ax


def kpis(fig):
    e = D.estabilidad(True)
    pw = D.balance_potencia()
    ax = fig.add_axes([0.785, 0.12, 0.195, 0.75]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.text(0.0, 1.0, "RESUMEN", fontsize=13, fontweight="bold", va="top")
    bloques = [
        (f"{D.MASA_VACIO:.0f} g", "vacío"), (f"{D.MASA_CARGADO:.0f} g", "con vaso de $1.000 (peor caso)"),
        (f"{pw['p_med']:.1f} W", f"consumo medio ({pw['i_med']*1000:.0f} mA a 7,4 V)"),
        (f"≈ {pw['autonomia_h']:.1f} h", "autonomía teórica"),
        (f"x = {e['cg'][0]:.0f} mm", f"CG con vaso (eje {D.X_EJE:.0f} · loca {D.X_LOCA:.0f})"),
        (f"{min(e['a_frente'], e['a_atras']):.1f} m/s²", "aceleración que haría volcar (uso real < 1)"),
    ]
    y = 0.90
    for big, small in bloques:
        ax.add_patch(Rectangle((0, y - 0.115), 1, 0.125, fc="white", ec=INK, lw=1.0))
        ax.text(0.05, y - 0.035, big, fontsize=17, fontweight="bold", color=ACC, va="center")
        ax.text(0.05, y - 0.092, small, fontsize=8.6, color=INK, va="center")
        y -= 0.145
    return ax


def generar(salida="03_pesos_consumo"):
    fig = lamina("Peso, consumo y estabilidad del carrito", "3/7", "s/e",
                 "Valores estimados con hojas de datos típicas: hay que pesar y medir las piezas reales")
    tabla_pesos(fig); grafico_potencia(fig); rieles(fig); kpis(fig)
    guardar(fig, salida)


if __name__ == "__main__":
    generar()

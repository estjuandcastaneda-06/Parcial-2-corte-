"""Fuente única de datos del carrito hormiga: medidas, pesos, posiciones, consumo y pines.
Los planos (generar_planos.py), el firmware y las diapositivas salen de estos números.

Sistema de coordenadas del carrito (mm):
  x = hacia adelante, 0 en el borde trasero del chasis (el chasis mide 130 mm de largo)
  y = lateral, 0 en el eje central (izquierda del carrito = y negativa en la planta)
  z = altura sobre el piso
Todo lo marcado como "estimado" sale de hojas de datos típicas; hay que PESAR y MEDIR las
piezas reales antes de dar los números como definitivos.
"""
from __future__ import annotations

# ------------------------------------------------------------------ geometría general
L, A = 130.0, 100.0            # chasis: largo x ancho (mm)
Z_PLACA_INF = (13.0, 16.0)     # placa inferior 3 mm (z0, z1)
Z_PLACA_SUP = (46.0, 48.0)     # placa superior 2 mm
ALTO_CHASIS = Z_PLACA_SUP[1] - Z_PLACA_INF[0]     # 35 mm de placa a placa (con espesores)
SEPARACION = Z_PLACA_SUP[0] - Z_PLACA_INF[1]      # 30 mm entre placas (separadores M3 x 30)
RUEDA_D, RUEDA_ANCHO = 42.0, 15.0
TROCHA = 110.0                 # distancia entre centros de rueda
X_EJE = 50.0                   # eje de las ruedas medido desde el borde trasero
Z_EJE = RUEDA_D / 2            # 21 mm
X_LOCA = 124.0                 # rueda loca (bola Ø10)
CASTER_D = 10.0
# vaso objetivo (verificar con el vaso real)
VASO_D_BOCA, VASO_D_BASE, VASO_ALTO, VASO_MASA = 60.0, 45.0, 70.0, 12.0
X_VASO = 180.0                 # centro del vaso sujeto por la pinza (desde el borde trasero)
PINZA_APERTURA_MAX = 100.0     # mm entre puntas de los dedos abiertos

# ------------------------------------------------------------------ componentes
# id, nombre, masa (g), piso, x, y (centro), dx, dy, dz, z0, color
PARTES = [
    # --- piso inferior (sobre la placa inferior)
    dict(id="PLI", nombre="Placa inferior acrílico 3 mm", m=46.0, piso="inf", x=65, y=0, dx=130, dy=100, dz=3, z0=13, c="#d8e6ee", marca=False),
    dict(id="MOI", nombre="Motorreductor N20 + encoder (izq.)", m=14.0, piso="inf", x=50, y=-23, dx=12, dy=45, dz=10, z0=16, c="#b8480f"),
    dict(id="MOD", nombre="Motorreductor N20 + encoder (der.)", m=14.0, piso="inf", x=50, y=23, dx=12, dy=45, dz=10, z0=16, c="#b8480f"),
    dict(id="SMO", nombre="Soportes de motor (2)", m=6.0, piso="inf", x=50, y=0, dx=0, dy=0, dz=0, z0=16, c="#888", marca=False),
    dict(id="RUE", nombre="Ruedas Ø42 x 15 (2)", m=22.0, piso="inf", x=50, y=0, dx=0, dy=0, dz=0, z0=0, c="#333", marca=False),
    dict(id="RLO", nombre="Rueda loca (bola Ø10 + soporte)", m=6.0, piso="inf", x=124, y=0, dx=14, dy=14, dz=10, z0=3, c="#555"),
    dict(id="BAT", nombre="Batería LiPo 2S 850 mAh (de lado)", m=55.0, piso="inf", x=21, y=0, dx=30, dy=56, dz=11, z0=16, c="#e0b040"),
    dict(id="DRV", nombre="Driver TB6612FNG", m=3.0, piso="inf", x=92, y=0, dx=20, dy=20, dz=4, z0=16, c="#2f7f4f"),
    dict(id="SEP", nombre="Separadores M3 x30 (4) + tornillería", m=14.0, piso="inf", x=65, y=0, dx=0, dy=0, dz=0, z0=16, c="#999", marca=False),
    # --- entre placas (frente): pinza
    dict(id="SVL", nombre="Servo SG90 izq. (pinza)", m=9.0, piso="med", x=116, y=-20, dx=23, dy=12, dz=27, z0=18, c="#3a6fb0"),
    dict(id="SVR", nombre="Servo SG90 der. (pinza)", m=9.0, piso="med", x=116, y=20, dx=23, dy=12, dz=27, z0=18, c="#3a6fb0"),
    dict(id="DED", nombre="Dedos de pinza impresos (2)", m=8.0, piso="med", x=150, y=0, dx=45, dy=60, dz=30, z0=20, c="#f0f0e8", marca=False),
    dict(id="TCS", nombre="Sensor de color TCS3200", m=12.0, piso="med", x=134, y=0, dx=10, dy=28, dz=28, z0=22, c="#1f6f6b"),
    # --- piso superior (sobre la placa superior)
    dict(id="PLS", nombre="Placa superior acrílico 2 mm", m=31.0, piso="sup", x=65, y=0, dx=130, dy=100, dz=2, z0=46, c="#d8e6ee", marca=False),
    dict(id="ESP", nombre="ESP32 DevKit V1", m=10.0, piso="sup", x=62, y=0, dx=51, dy=28, dz=13, z0=48, c="#1d2430"),
    dict(id="MPU", nombre="Giroscopio MPU6050", m=3.0, piso="sup", x=100, y=-28, dx=20, dy=16, dz=3, z0=48, c="#7a5fd0"),
    dict(id="BUC", nombre="Regulador buck MP1584 (5 V)", m=2.0, piso="sup", x=18, y=-22, dx=22, dy=17, dz=4, z0=48, c="#c14fae"),
    dict(id="SWI", nombre="Interruptor + portafusible", m=8.0, piso="sup", x=14, y=25, dx=20, dy=14, dz=12, z0=48, c="#aa2222"),
    dict(id="LED", nombre="LED WS2812 + R/C/divisor", m=4.0, piso="sup", x=8, y=0, dx=10, dy=10, dz=4, z0=48, c="#e6e6e6"),
    dict(id="TOF", nombre="Sensor de distancia VL53L0X", m=1.5, piso="sup", x=105, y=0, dx=4, dy=18, dz=13, z0=50, c="#d94f4f"),
    dict(id="CAB", nombre="Cableado y terminales", m=12.0, piso="sup", x=65, y=0, dx=0, dy=0, dz=0, z0=30, c="#999", marca=False),
]
for p in PARTES:
    p.setdefault("marca", True)

P_BAT = [p for p in PARTES if p["id"] == "BAT"][0]
NUM = {p["id"]: i + 1 for i, p in enumerate(PARTES)}      # número de parte en planos y tablas
MASA_VACIO = sum(p["m"] for p in PARTES)


def vaso_masa(denom: int) -> float:
    """Vaso + 10 monedas de una denominación (serie nueva)."""
    peso_moneda = {50: 2.00, 100: 3.34, 200: 4.61, 500: 7.14, 1000: 9.95}[denom]
    return VASO_MASA + 10 * peso_moneda


MASA_PAYLOAD_MAX = vaso_masa(1000)
MASA_CARGADO = MASA_VACIO + MASA_PAYLOAD_MAX


def centro_de_gravedad(con_vaso: bool = False):
    """CG (x, y, z) en mm; el vaso va sujeto delante, con su centro a Z=VASO_ALTO/2."""
    masas = [(p["m"], p["x"], p["y"], p["z0"] + p["dz"] / 2) for p in PARTES]
    # las piezas sin tamaño (ruedas, soportes, separadores, cableado) usan un z representativo
    ajustes = {"RUE": 21, "SMO": 21, "SEP": 31, "CAB": 32}
    masas = [(m, x, y, ajustes.get(p["id"], z)) for (m, x, y, z), p in zip(masas, PARTES)]
    if con_vaso:
        masas.append((MASA_PAYLOAD_MAX, X_VASO, 0.0, VASO_ALTO / 2))
    mt = sum(m for m, *_ in masas)
    return tuple(sum(m * c[i] for m, *c in masas) / mt for i in range(3)), mt


def estabilidad(con_vaso: bool = True):
    (x, y, z), m = centro_de_gravedad(con_vaso)
    g = 9810.0  # mm/s^2
    # vuelco hacia adelante sobre la rueda loca / hacia atrás sobre el eje
    a_frente = g * (X_LOCA - x) / z
    a_atras = g * (x - X_EJE) / z
    a_lateral = g * (TROCHA / 2) / z
    return dict(cg=(x, y, z), masa=m, a_frente=a_frente / 1000, a_atras=a_atras / 1000, a_lateral=a_lateral / 1000,
                x_ok=(X_EJE < x < X_LOCA))


# ------------------------------------------------------------------ consumo (corriente por riel)
V_BAT = 7.4          # LiPo 2S nominal
CAP_MAH = 850
USABLE = 0.80
EFIC_BUCK = 0.88
EFIC_DRV = 0.90

# (nombre, riel, corriente_media_mA, corriente_pico_mA, nota)
CONSUMOS = [
    ("2× motor N20 (a ≤80 % PWM, ≈6 V)", "motor", 240.0, 1200.0, "media 120 mA c/u; pico = rotor bloqueado 600 mA c/u"),
    ("ESP32 con ESP-NOW", "5V", 160.0, 350.0, "radio activa, sin conexión Wi-Fi"),
    ("TCS3200 (LEDs encendidos)", "5V", 40.0, 40.0, "alimentado desde 3V3 del ESP32"),
    ("VL53L0X", "5V", 19.0, 19.0, "alimentado desde 3V3"),
    ("MPU6050", "5V", 4.0, 4.0, "alimentado desde 3V3"),
    ("Encoders Hall (2)", "5V", 16.0, 16.0, "alimentados desde 3V3"),
    ("2× servo SG90", "5V", 40.0, 1000.0, "media con ≈5 % de uso; pico = 2 × 500 mA"),
    ("LED WS2812 (atenuado)", "5V", 10.0, 20.0, ""),
]


def balance_potencia():
    i5_med = sum(c[2] for c in CONSUMOS if c[1] == "5V") / 1000       # A en el riel de 5 V
    i5_pico = sum(c[3] for c in CONSUMOS if c[1] == "5V") / 1000
    p5_med, p5_pico = 5.0 * i5_med, 5.0 * i5_pico
    mot_med = [c for c in CONSUMOS if c[1] == "motor"][0]
    pm_med = 6.0 * mot_med[2] / 1000 / EFIC_DRV                       # motores a ≈6 V efectivos
    pm_pico = 6.0 * mot_med[3] / 1000 / EFIC_DRV
    p_med = p5_med / EFIC_BUCK + pm_med
    p_pico = p5_pico / EFIC_BUCK + pm_pico
    i_med, i_pico = p_med / V_BAT, p_pico / V_BAT
    wh = CAP_MAH / 1000 * V_BAT
    autonomia_h = wh * USABLE / p_med
    return dict(i5_med=i5_med, i5_pico=i5_pico, p5_med=p5_med, pm_med=pm_med, p_med=p_med, p_pico=p_pico,
                i_med=i_med, i_pico=i_pico, wh=wh, autonomia_h=autonomia_h,
                p_esp=5.0 * 0.160 / EFIC_BUCK, p_sens=5.0 * (0.040 + 0.019 + 0.004 + 0.016) / EFIC_BUCK,
                p_serv=5.0 * 0.040 / EFIC_BUCK, p_led=5.0 * 0.010 / EFIC_BUCK)


# ------------------------------------------------------------------ pines del ESP32 DevKit V1 (30 pines)
# (gpio, dirección vista desde el ESP32, señal, módulo, pin del módulo)
PINES = [
    (25, "OUT", "PWMA", "TB6612FNG", "PWMA"),
    (26, "OUT", "AIN1", "TB6612FNG", "AIN1"),
    (27, "OUT", "AIN2", "TB6612FNG", "AIN2"),
    (14, "OUT", "PWMB", "TB6612FNG", "PWMB"),
    (32, "OUT", "BIN1", "TB6612FNG", "BIN1"),
    (4, "OUT", "BIN2", "TB6612FNG", "BIN2"),
    (13, "OUT", "STBY", "TB6612FNG", "STBY"),
    (34, "IN", "ENC_I_A", "Motor izq. N20", "Hall A"),
    (35, "IN", "ENC_I_B", "Motor izq. N20", "Hall B"),
    (36, "IN", "ENC_D_A", "Motor der. N20", "Hall A"),
    (39, "IN", "ENC_D_B", "Motor der. N20", "Hall B"),
    (18, "OUT", "TCS_S2", "TCS3200", "S2"),
    (19, "OUT", "TCS_S3", "TCS3200", "S3"),
    (23, "IN", "TCS_OUT", "TCS3200", "OUT"),
    (21, "I/O", "SDA", "VL53L0X + MPU6050", "SDA"),
    (22, "OUT", "SCL", "VL53L0X + MPU6050", "SCL"),
    (16, "OUT", "SERVO_I", "Servo SG90 izq.", "señal"),
    (17, "OUT", "SERVO_D", "Servo SG90 der.", "señal"),
    (5, "OUT", "LED", "WS2812", "DIN"),
    (33, "IN", "VBAT_ADC", "Divisor 100k/47k", "punto medio"),
]

if __name__ == "__main__":
    est = estabilidad(True)
    pw = balance_potencia()
    print(f"masa vacío {MASA_VACIO:.0f} g · payload máx {MASA_PAYLOAD_MAX:.1f} g · cargado {MASA_CARGADO:.0f} g")
    print("CG vacío", [round(v, 1) for v in centro_de_gravedad(False)[0]], " con vaso", [round(v, 1) for v in est['cg']])
    print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in est.items() if k != 'cg'})
    print({k: round(v, 2) for k, v in pw.items()})

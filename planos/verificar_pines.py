"""Comprueba que los pines escritos en el firmware (PIN_*) coinciden con la tabla PINES de datos_carrito.py,
que es la que dibujan las láminas 5 y 5b. Uso:  python verificar_pines.py"""
import os
import re
import sys

import datos_carrito as D

INO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "firmware", "carrito_hormiga", "carrito_hormiga.ino")
# señal de la tabla -> nombre de la constante en el firmware
MAPA = {"PWMA": "PIN_PWMA", "AIN1": "PIN_AIN1", "AIN2": "PIN_AIN2", "PWMB": "PIN_PWMB", "BIN1": "PIN_BIN1", "BIN2": "PIN_BIN2",
        "STBY": "PIN_STBY", "ENC_I_A": "PIN_ENC_I_A", "ENC_I_B": "PIN_ENC_I_B", "ENC_D_A": "PIN_ENC_D_A", "ENC_D_B": "PIN_ENC_D_B",
        "TCS_S2": "PIN_TCS_S2", "TCS_S3": "PIN_TCS_S3", "TCS_OUT": "PIN_TCS_OUT", "SDA": "PIN_SDA", "SCL": "PIN_SCL",
        "SERVO_I": "PIN_SERVO_I", "SERVO_D": "PIN_SERVO_D", "LED": "PIN_LED", "VBAT_ADC": "PIN_VBAT"}
src = open(INO, encoding="utf-8").read()
valores = {n: int(v) for n, v in re.findall(r"\b(PIN_[A-Z0-9_]+)\s*=\s*(\d+)", src)}
mal = 0
for gpio, _dir, senal, _mod, _pin in D.PINES:
    nombre = MAPA[senal]
    if valores.get(nombre) != gpio:
        print(f"DIFERENTE: {senal}: la tabla dice GPIO{gpio} y el firmware dice {valores.get(nombre)} ({nombre})")
        mal += 1
repetidos = [g for g in {p[0] for p in D.PINES} if sum(1 for p in D.PINES if p[0] == g) > 1 and g not in (21,)]
print("pines repetidos:", repetidos or "ninguno")
print("OK: los", len(D.PINES), "pines coinciden" if not mal else f"{mal} diferencias")
sys.exit(1 if mal else 0)

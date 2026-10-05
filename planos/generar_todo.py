"""Genera todas las láminas (PNG + PDF) en esta carpeta. La 7 necesita resultados_confusion.json
(se crea con ../experimentos_confusion.py)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import lamina1_vistas, lamina2_distribucion, lamina3_peso_consumo, lamina4_arena
import lamina5_esquema_carrito, lamina5b_tabla_pines, lamina6_sistema, lamina7_confusion

for m in (lamina1_vistas, lamina2_distribucion, lamina3_peso_consumo, lamina4_arena,
          lamina5_esquema_carrito, lamina5b_tabla_pines, lamina6_sistema, lamina7_confusion):
    try:
        m.generar()
        print("ok", m.__name__)
    except FileNotFoundError as e:
        print("falta", m.__name__, e)

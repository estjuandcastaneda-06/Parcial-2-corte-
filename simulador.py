"""Simulador del ESP32: genera el MISMO JSON que debe publicar el firmware
(ver firmware/esp32_monedas/esp32_monedas.ino), para poder desarrollar la
interfaz sin hardware. Las monedas simuladas se miden con ruido y se pasan por
el mismo clasificador que usa la app.
"""
from __future__ import annotations

import random
import time

from coins import CATALOGO, POR_KEY, SIGMA_D, SIGMA_W, clasificar

VASO_CAP = 10          # monedas por vaso
TARA_VASO_G = 14.0     # peso del vaso vacío
T_BANDA = 6.0          # s en la banda hasta la estación de tapado
T_TAPA = 3.0           # s de tapado por el brazo
DRON_CARGA = 2         # vasos que lleva el dron por viaje
T_RUTA = 70.0          # s para recorrer la pista completa
OBSTACULOS = (0.25, 0.55, 0.82)   # posición (0-1) de los 3 obstáculos
RATE = 1.4             # monedas/s que entran al contador
# Mezcla de monedas: más pequeñas más frecuentes
PESOS = {"50_nueva": 3, "100_nueva": 3, "200_nueva": 3, "500_nueva": 2, "1000_nueva": 1,
         "50_antigua": 2, "100_antigua": 2, "200_antigua": 1, "500_antigua": 1}


class Simulador:
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.reset()

    def reset(self):
        self.t0 = self.last = time.time()
        self.conteo = {c.key: 0 for c in CATALOGO}
        self.rechazadas = 0
        self.ultima = None
        self.en_vaso = 0
        self.vasos_llenos: list[float] = []   # instante en que se llenó cada vaso
        self.dron_estado = "espera"
        self.dron_prog = 0.0
        self.dron_carga = 0
        self.dron_sup = 0
        self.entregados = 0
        self.t_meta = 0.0
        self.acum = 0.0
        self.peso_g = 0.0

    # -- avance temporal -------------------------------------------------
    def _medir_moneda(self):
        keys, w = zip(*PESOS.items())
        real = POR_KEY[self.rng.choices(keys, w)[0]]
        d = self.rng.gauss(real.d, SIGMA_D)
        p = self.rng.gauss(real.w, SIGMA_W)
        if self.rng.random() < 0.02:          # moneda extranjera / ficha
            d, p = self.rng.uniform(15, 28), self.rng.uniform(1.5, 9)
        cls = clasificar(d, p)
        self.ultima = {"d_mm": round(d, 2), "w_g": round(p, 2), "clase": cls.key if cls else None}
        if cls is None:
            self.rechazadas += 1
            return
        self.conteo[cls.key] += 1
        self.peso_g += cls.w
        self.en_vaso += 1
        if self.en_vaso >= VASO_CAP:
            self.en_vaso = 0
            self.vasos_llenos.append(time.time())

    def step(self):
        now = time.time()
        dt = min(now - self.last, 5.0)
        self.last = now
        self.acum += dt * RATE
        while self.acum >= 1:
            self.acum -= 1
            self._medir_moneda()
        self._dron(dt, now)

    def _etapas(self, now):
        banda = tapa = listos = 0
        for t in self.vasos_llenos:
            edad = now - t
            if edad < T_BANDA:
                banda += 1
            elif edad < T_BANDA + T_TAPA:
                tapa += 1
            else:
                listos += 1
        return banda, tapa, listos

    def _dron(self, dt, now):
        if self.dron_estado == "espera":
            _, _, listos = self._etapas(now)
            if listos >= DRON_CARGA:
                # retira los DRON_CARGA vasos más antiguos ya tapados
                idx = [i for i, t in enumerate(self.vasos_llenos) if now - t >= T_BANDA + T_TAPA][:DRON_CARGA]
                for i in reversed(idx):
                    self.vasos_llenos.pop(i)
                self.dron_carga, self.dron_prog, self.dron_sup = DRON_CARGA, 0.0, 0
                self.dron_estado = "ruta"
        elif self.dron_estado == "ruta":
            prev = self.dron_prog
            self.dron_prog = min(1.0, prev + dt / T_RUTA)
            self.dron_sup += sum(prev < o <= self.dron_prog for o in OBSTACULOS)
            if self.dron_prog >= 1.0:
                self.dron_estado, self.t_meta = "meta", now
                self.entregados += self.dron_carga
                self.dron_carga = 0
        elif self.dron_estado == "meta" and now - self.t_meta > 5:
            self.dron_estado, self.dron_prog, self.dron_sup = "espera", 0.0, 0

    # -- payload idéntico al del firmware -------------------------------
    def estado(self) -> dict:
        self.step()
        now = time.time()
        banda, tapa, listos = self._etapas(now)
        brazo = "tapando" if tapa else ("esperando vaso" if not banda else "en reposo")
        return {
            "ts": round(now, 2),
            "uptime_s": int(now - self.t0),
            "contador": {"conteo": dict(self.conteo), "rechazadas": self.rechazadas,
                         "ultima": self.ultima, "peso_g": round(self.peso_g, 2)},
            "vaso": {"monedas": self.en_vaso, "capacidad": VASO_CAP},
            "embalaje": {"en_banda": banda, "en_tapa": tapa, "listos": listos,
                         "brazo": brazo, "vasos_totales": self.entregados + self.dron_carga + len(self.vasos_llenos)},
            "dron": {"estado": self.dron_estado, "progreso": round(self.dron_prog, 4),
                     "obstaculos_superados": self.dron_sup, "vasos_cargados": self.dron_carga,
                     "entregados": self.entregados},
        }

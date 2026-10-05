from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

W, H = 42, 24              # celdas de la grilla
CELL_M = 0.05               # 1 celda = 50 mm  ->  arena 2100 x 1200 mm
NIDO = (2, H // 2)          # el enjambre entrega aquí (salida de la banda)
N_CARRITOS = 5
VASO_CAP = 10                # monedas por vaso
SENSOR_R = 5.0               # celdas (250 mm): alcance útil de detección del VL53L0X
VEL = 5.0                    # celdas/s = 250 mm/s (el N20 150 RPM con rueda Ø42 llega a ~330 mm/s)
RHO = 0.045                  # evaporación de feromona por segundo
DEPOSITO_BASE = 26.0          # feromona depositada al volver con una moneda
DIFUSION = 0.02              # difusión leve hacia celdas vecinas
COLISION_R = 2.4             # celdas (120 mm): separación mínima entre carritos
OFFSET_PINZA = 2.3           # celdas (115 mm): del centro del carrito al centro del vaso sujeto

T_LECTURA = 1.0              # s detenido leyendo el color
T_RELECTURA = 0.8            # s extra si la lectura fue dudosa
T_RECAL = 6.0                # s recalibrando en el nido
T_ACERCAR_MAX = 14.0          # s máximos acercándose a un vaso antes de abandonarlo
T_VETO = 45.0                # s que una hormiga no vuelve a inspeccionar un vaso que rechazó

SIGMA_COLOR = 0.020          # ruido de la cromaticidad del TCS3200 a ~15 mm
DERIVA = 0.0006              # deriva del sensor (desv. por √s) por temperatura/luz ambiente
MARGEN_DUDA = 0.70           # (d2-d1)/d2 por debajo de esto => lectura dudosa -> se relee y se promedia
MAX_LECTURAS = 5             # relecturas máximas por vaso (cada una cuesta T_RELECTURA)
E_MAX = 2                    # errores CONFIRMADOS (vaso equivocado visto en el nido) para recalibrar

OBSTACULOS = [                 # 3 obstáculos en slalom, como pide el enunciado general:
    (18, 0, 2, 15),             # (x, y, ancho, alto) en celdas · deja SIEMPRE un hueco de paso
    (26, 9, 2, 15),             # obstáculo 1 y 3: cierran por arriba, hueco abajo
    (33, 0, 2, 15),             # obstáculo 2: cierra por abajo, hueco arriba (zig-zag real)
]

DENOMS = [50, 100, 200, 500, 1000]
# color de la pegatina de cada vaso (lo que lee el TCS3200)
COLOR = {50: "#c5c8cc", 100: "#c9a24a", 200: "#d3cfbd", 500: "#8f2d1b", 1000: "#1f6f6b"}


def cromaticidad(hexcolor: str) -> tuple[float, float, float]:
    r, g, b = (int(hexcolor[i:i + 2], 16) for i in (1, 3, 5))
    s = (r + g + b) or 1
    return (r / s, g / s, b / s)


CROM = {d: cromaticidad(c) for d, c in COLOR.items()}   # centroides de calibración

# Pegatinas más separables entre sí (blanco, amarillo, azul, rojo, verde): la matriz de confusión
# muestra que $50 plateado y $200 beige casi no se distinguen para el TCS3200.
PALETA_RECOMENDADA = {50: "#e8e8e8", 100: "#d9b300", 200: "#2a56b0", 500: "#b02a2a", 1000: "#2a8f4a"}


def usar_paleta(paleta: dict) -> None:
    """Cambia los colores de las pegatinas (y los centroides de calibración) en caliente."""
    COLOR.update(paleta)
    CROM.update({d: cromaticidad(c) for d, c in paleta.items()})

# Trayectoria dada que cruza los 3 obstáculos en slalom (nido -> zona de vasos).
CORREDOR = [(2, 12), (13, 12), (15, 20), (22, 20), (24.5, 4), (29.5, 4), (31, 19), (37, 19), (38, 12)]
ZONA_X = 34.0


def en_obstaculo(x, y, margen=0.4):
    for ox, oy, ow, oh in OBSTACULOS:
        if ox - margen <= x <= ox + ow + margen and oy - margen <= y <= oy + oh + margen:
            return True
    return not (0 <= x <= W and 0 <= y <= H)


@dataclass
class Vaso:
    id: int
    x: float
    y: float
    denom: int
    reclamado: bool = False


@dataclass
class Carrito:
    id: int
    x: float
    y: float
    color: str
    denom_obj: int = 50

    estado: str = "explorar"
    objetivo: Vaso | None = None
    entregados: int = 0
    valor_entregado: int = 0
    dist_recorrida: float = 0.0
    dir_x: float = 1.0
    dir_y: float = 0.0
    rumbo: float = 0.0
    atascado: float = 0.0
    # --- sensor de color / matriz de confusión
    sesgo: list = field(default_factory=lambda: [0.0, 0.0, 0.0])
    errores: int = 0                 # contador que dispara el retorno a recalibrar
    falsos_ok: int = 0               # vasos equivocados descubiertos en el nido
    lecturas_dudosas: int = 0
    rechazos: int = 0
    recalibraciones: int = 0
    lecturas: list = field(default_factory=list)
    t_estado: float = 0.0            # tiempo que lleva en el estado actual
    t_lectura_total: float = T_LECTURA
    pidio_recal: bool = False
    veto: dict = field(default_factory=dict)


COLORES_CARRO = ["#b8480f", "#1f6f6b", "#c9a24a", "#5a4fcf", "#c14fae"]


def _dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


class Enjambre:
    def __init__(self, seed: int | None = None, e_max: int | None = E_MAX):
        self.rng = random.Random(seed)
        self.e_max = e_max          # None => nunca recalibra (para comparar)
        self.reset()

    def reset(self):
        self.t = 0.0
        self.tau = [[0.0] * W for _ in range(H)]     # mapa de feromona
        posiciones = [(4, 3), (4, H - 4), (4, H // 2), (7, 6), (7, H - 7)][:N_CARRITOS]
        self.carritos = [
            Carrito(i, x, y, COLORES_CARRO[i % len(COLORES_CARRO)], denom_obj=DENOMS[i],
                    rumbo=self.rng.uniform(0, 2 * math.pi))
            for i, (x, y) in enumerate(posiciones)
        ]
        self.vasos: list[Vaso] = []
        self._next_vaso_id = 0
        self._acum_spawn = 0.0
        self.entregados_total = 0
        self.entregados_ok = 0
        self.entregados_err = 0
        self.valor_total = 0
        self.hist_tiempos: list[float] = []
        self._t_reclamo: dict[int, float] = {}
        self.conf = {a: {b: 0 for b in DENOMS} for a in DENOMS}

    def _spawn_vaso(self):
        presentes = {d: sum(1 for v in self.vasos if v.denom == d) for d in DENOMS}
        minimo = min(presentes.values())
        elegibles = [d for d in DENOMS if presentes[d] == minimo]
        for _ in range(40):
            x = self.rng.uniform(30, W - 3.5)
            y = self.rng.uniform(3.5, H - 3.5)
            if en_obstaculo(x, y, 3.5):
                continue
            if any(math.hypot(v.x - x, v.y - y) < 3.0 for v in self.vasos):
                continue
            self.vasos.append(Vaso(self._next_vaso_id, x, y, self.rng.choice(elegibles)))
            self._next_vaso_id += 1
            return

    def _evaporar_difundir(self, dt):
        tau = self.tau
        f = max(0.0, 1 - RHO * dt)
        for y in range(H):
            row = tau[y]
            for x in range(W):
                row[x] *= f
        if DIFUSION > 0:
            nuevo = [row[:] for row in tau]
            for y in range(1, H - 1):
                for x in range(1, W - 1):
                    v = tau[y][x]
                    if v < 0.05:
                        continue
                    vecinos = (tau[y][x - 1] + tau[y][x + 1] + tau[y - 1][x] + tau[y + 1][x]) / 4
                    nuevo[y][x] = v * (1 - DIFUSION) + vecinos * DIFUSION
            self.tau = nuevo

    def _depositar(self, x, y, cant):
        xi, yi = int(x), int(y)
        if 0 <= yi < H and 0 <= xi < W:
            self.tau[yi][xi] = min(300.0, self.tau[yi][xi] + cant)

    def _leer_color(self, c: Carrito, v: Vaso):
        base = CROM[v.denom]
        amb = self.rng.uniform(0.0, 0.12)            # luz blanca ambiente mezclada
        return [(1 - amb) * base[i] + amb / 3 + c.sesgo[i] + self.rng.gauss(0, SIGMA_COLOR) for i in range(3)]

    @staticmethod
    def _clasificar(lectura):
        """Centroide más cercano. Devuelve (denominación predicha, margen de confianza)."""
        ds = sorted((_dist(lectura, CROM[d]), d) for d in DENOMS)
        d1, d2 = ds[0][0], ds[1][0]
        margen = (d2 - d1) / d2 if d2 > 0 else 1.0
        return ds[0][1], margen

    def _registrar_error(self, c: Carrito):
        c.errores += 1
        if self.e_max is not None and c.errores >= self.e_max:
            c.pidio_recal = True

    def matriz_confusion(self) -> dict:
        n = len(DENOMS)
        m = [[self.conf[a][b] for b in DENOMS] for a in DENOMS]
        total = sum(map(sum, m))
        acc = sum(m[i][i] for i in range(n)) / total if total else None
        prec, rec = [], []
        for j in range(n):
            col = sum(m[i][j] for i in range(n))
            fila = sum(m[j])
            prec.append(m[j][j] / col if col else None)
            rec.append(m[j][j] / fila if fila else None)
        return {"etiquetas": DENOMS, "matriz": m, "total": total, "exactitud": acc,
                "precision": prec, "sensibilidad": rec}


    def _hito(self, x: float, hacia_zona: bool):
        """Próximo punto del corredor dado (cruce de obstáculos) hacia donde dirigirse.
        None => ya se llegó al tramo libre (zona de vasos, o el nido de vuelta)."""
        if hacia_zona:
            for wx, wy in CORREDOR[1:]:
                if wx > x + 1.0:
                    return wx, wy
            return None
        for wx, wy in reversed(CORREDOR[:-1]):
            if wx < x - 1.0:
                return wx, wy
        return None

    def _sensar_vaso(self, c: Carrito):
        mejor, mejor_d = None, SENSOR_R
        for v in self.vasos:
            if v.reclamado or c.veto.get(v.id, 0) > self.t:
                continue
            d = math.hypot(v.x - c.x, v.y - c.y)
            if d <= mejor_d:
                mejor, mejor_d = v, d
        return mejor

    def _gradiente_feromona(self, c: Carrito):
        """Lee el gradiente de feromona en las celdas vecinas (estigmergia)."""
        xi, yi = int(c.x), int(c.y)
        mejor_dx, mejor_dy, mejor_v = 0, 0, -1
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = xi + dx, yi + dy
                if 0 <= nx < W and 0 <= ny < H and not en_obstaculo(nx, ny):
                    v = self.tau[ny][nx]
                    if v > mejor_v:
                        mejor_v, mejor_dx, mejor_dy = v, dx, dy
        return mejor_dx, mejor_dy, mejor_v

    def _repulsion_obstaculos(self, x, y, radio=3.2):
        rx = ry = 0.0
        xi, yi = int(x), int(y)
        R = int(radio) + 1
        for dy in range(-R, R + 1):
            for dx in range(-R, R + 1):
                d = math.hypot(dx, dy)
                if d == 0 or d > radio:
                    continue
                if en_obstaculo(xi + dx, yi + dy, margen=0.3):
                    w = (radio - d) / radio
                    rx -= dx / d * w
                    ry -= dy / d * w
        return rx, ry

    def _paso_hacia(self, c: Carrito, tx, ty, dt, evitar_choque=True):
        dx, dy = tx - c.x, ty - c.y
        d = math.hypot(dx, dy) or 1e-6
        vx, vy = dx / d * VEL, dy / d * VEL
        if evitar_choque:
            for o in self.carritos:
                if o is c:
                    continue
                od = math.hypot(o.x - c.x, o.y - c.y)
                if od < COLISION_R:
                    rx, ry = c.x - o.x, c.y - o.y
                    rn = math.hypot(rx, ry) or 1e-6
                    vx += rx / rn * VEL * 0.9
                    vy += ry / rn * VEL * 0.9
        rx, ry = self._repulsion_obstaculos(c.x, c.y)
        vx += rx * VEL * 1.6
        vy += ry * VEL * 1.6
        if c.atascado > 0.6:
            perp = (1 if c.id % 2 == 0 else -1)
            vx, vy = vx - perp * vy * 0.9, vy + perp * vx * 0.9
        vn = math.hypot(vx, vy) or 1e-6
        vx, vy = vx / vn * VEL, vy / vn * VEL
        nx, ny = c.x + vx * dt, c.y + vy * dt
        if en_obstaculo(nx, c.y):
            nx = c.x
        if en_obstaculo(c.x, ny):
            ny = c.y
        avance = math.hypot(nx - c.x, ny - c.y)
        c.atascado = 0.0 if avance > 0.35 * VEL * dt else min(3.0, c.atascado + dt)
        c.dist_recorrida += avance
        c.dir_x, c.dir_y = vx / VEL, vy / VEL
        c.x, c.y = nx, ny
        return math.hypot(tx - c.x, ty - c.y)

    def _cambiar(self, c: Carrito, estado: str):
        c.estado = estado
        c.t_estado = 0.0

    def _colocar_vaso(self, c: Carrito):
        """El vaso sujeto va delante del carrito (entre los dedos de la pinza)."""
        v = c.objetivo
        n = math.hypot(c.dir_x, c.dir_y) or 1.0
        v.x = c.x + c.dir_x / n * OFFSET_PINZA
        v.y = c.y + c.dir_y / n * OFFSET_PINZA

    def _ir_al_nido(self, c: Carrito, dt, deposito=False):
        hito = self._hito(c.x, hacia_zona=False)
        tx, ty = hito if hito is not None else NIDO
        self._paso_hacia(c, tx, ty, dt)
        if deposito:
            # marca más fuerte cuanto más lejos del nido: el rastro "apunta" hacia donde hubo vasos
            lejos = min(1.0, math.hypot(c.x - NIDO[0], c.y - NIDO[1]) / 35.0)
            self._depositar(c.x, c.y, DEPOSITO_BASE * dt * 4 * (0.5 + 1.5 * lejos))
        return math.hypot(NIDO[0] - c.x, NIDO[1] - c.y)

    def _step_carrito(self, c: Carrito, dt):
        c.t_estado += dt
        for i in range(3):
            c.sesgo[i] += self.rng.gauss(0, DERIVA * math.sqrt(dt))

        if c.estado == "explorar":
            if c.pidio_recal:
                self._cambiar(c, "retorno")
                return
            v = self._sensar_vaso(c)
            if v is not None:
                v.reclamado = True
                c.objetivo = v
                self._t_reclamo[v.id] = self.t
                self._cambiar(c, "acercar")
                return
            hito = self._hito(c.x, hacia_zona=True) if c.x < ZONA_X else None
            if hito is not None:
                self._paso_hacia(c, hito[0], hito[1] + self.rng.uniform(-0.6, 0.6), dt)
                return
            dx, dy, val = self._gradiente_feromona(c)
            if val > 2.0:
                c.rumbo = math.atan2(dy, dx)
            else:
                c.rumbo += self.rng.uniform(-0.7, 0.7)
            paso = 3.2
            tx = min(max(c.x + math.cos(c.rumbo) * paso, ZONA_X - 2), W - 1)
            ty = min(max(c.y + math.sin(c.rumbo) * paso, 0), H - 1)
            self._paso_hacia(c, tx, ty, dt)

        elif c.estado == "acercar":
            v = c.objetivo
            d = math.hypot(v.x - c.x, v.y - c.y)
            if d <= OFFSET_PINZA + 0.3:               
                c.lecturas = []
                c.t_lectura_total = T_LECTURA
                self._cambiar(c, "leyendo")
                return
            if c.t_estado > T_ACERCAR_MAX:           
                c.veto[v.id] = self.t + T_VETO
                v.reclamado = False
                self._t_reclamo.pop(v.id, None)
                c.objetivo = None
                c.rumbo += math.pi
                self._cambiar(c, "explorar")
                return
            self._paso_hacia(c, v.x, v.y, dt, evitar_choque=False)

        elif c.estado == "leyendo":
            v = c.objetivo
            if not c.lecturas:
                c.lecturas.append(self._leer_color(c, v))
            if c.t_estado < c.t_lectura_total:
                return
            prom = [sum(l[i] for l in c.lecturas) / len(c.lecturas) for i in range(3)]
            pred, margen = self._clasificar(prom)
            if margen < MARGEN_DUDA and len(c.lecturas) < MAX_LECTURAS:
                # lectura dudosa: relee y promedia (el ruido baja con √n). No es un "error":
                # solo se cuenta como lectura dudosa para el reporte.
                if len(c.lecturas) == 1:
                    c.lecturas_dudosas += 1
                c.lecturas.append(self._leer_color(c, v))
                c.t_lectura_total += T_RELECTURA
                return
            self.conf[v.denom][pred] += 1               # matriz de confusión (verdad vs predicho)
            if pred == c.denom_obj:
                self._cambiar(c, "transportar")        
            else:
                c.rechazos += 1
                c.veto[v.id] = self.t + T_VETO
                v.reclamado = False
                self._t_reclamo.pop(v.id, None)
                c.objetivo = None
                c.rumbo += math.pi / 2                  # se aparta y sigue explorando
                self._cambiar(c, "explorar")

        elif c.estado == "transportar":
            self._colocar_vaso(c)
            restante = self._ir_al_nido(c, dt, deposito=True)
            if restante < 0.9:
                self._cambiar(c, "entregando")

        elif c.estado == "entregando":
            v = c.objetivo
            c.entregados += 1
            c.valor_entregado += VASO_CAP * v.denom          # cada vaso lleva 10 monedas de su denominación
            self.entregados_total += 1
            self.valor_total += VASO_CAP * v.denom
            if v.denom == c.denom_obj:                  # verificación en la báscula del nido
                self.entregados_ok += 1
            else:
                self.entregados_err += 1
                c.falsos_ok += 1
                self._registrar_error(c)
            t0 = self._t_reclamo.pop(v.id, self.t)
            self.hist_tiempos.append(self.t - t0)
            if len(self.hist_tiempos) > 200:
                self.hist_tiempos.pop(0)
            self.vasos.remove(v)
            self._depositar(*NIDO, DEPOSITO_BASE * 6)
            c.objetivo = None
            self._cambiar(c, "recalibrando" if c.pidio_recal else "explorar")

        elif c.estado == "retorno":
            # demasiados errores: abandona la búsqueda y va al objetivo (nido) a recalibrar
            if self._ir_al_nido(c, dt) < 0.9:
                self._cambiar(c, "recalibrando")

        elif c.estado == "recalibrando":
            if c.t_estado >= T_RECAL:
                c.sesgo = [self.rng.gauss(0, 0.002) for _ in range(3)]
                c.errores = 0
                c.pidio_recal = False
                c.recalibraciones += 1
                c.veto.clear()
                self._cambiar(c, "explorar")

    def step(self, dt: float):
        n = max(1, math.ceil(dt / 0.1))
        h = dt / n
        for _ in range(n):
            self._step(h)

    def _step(self, dt: float):
        self.t += dt
        self._acum_spawn += dt
        if self._acum_spawn > self.rng.uniform(3.0, 5.5) and len(self.vasos) < 6:
            self._acum_spawn = 0.0
            self._spawn_vaso()
        for c in self.carritos:
            self._step_carrito(c, dt)
        self._evaporar_difundir(dt)

    def heatmap(self, paso=2):
        mx = max((max(r) for r in self.tau), default=1) or 1
        return [[round(self.tau[y][x] / mx, 3) for x in range(0, W, paso)] for y in range(0, H, paso)]

    def estado(self) -> dict:
        return {
            "t": round(self.t, 1), "w": W, "h": H, "cell_m": CELL_M, "nido": NIDO, "obstaculos": OBSTACULOS,
            "carritos": [{"id": c.id, "x": round(c.x, 2), "y": round(c.y, 2), "color": c.color,
                         "denom_obj": c.denom_obj, "estado": c.estado,
                         "objetivo": c.objetivo.id if c.objetivo else None,
                         "entregados": c.entregados, "valor": c.valor_entregado,
                         "errores": c.errores, "falsos_ok": c.falsos_ok, "dudosas": c.lecturas_dudosas,
                         "rechazos": c.rechazos, "recalibraciones": c.recalibraciones} for c in self.carritos],
            "vasos": [{"id": v.id, "x": round(v.x, 2), "y": round(v.y, 2), "denom": v.denom,
                      "color": COLOR[v.denom], "reclamado": v.reclamado} for v in self.vasos],
            "entregados_total": self.entregados_total, "entregados_ok": self.entregados_ok,
            "entregados_err": self.entregados_err, "valor_total": self.valor_total,
            "tiempo_medio_entrega": round(sum(self.hist_tiempos[-30:]) / len(self.hist_tiempos[-30:]), 1) if self.hist_tiempos else None,
            "confusion": self.matriz_confusion(),
            "heatmap": self.heatmap(),
        }

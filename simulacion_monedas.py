#!/usr/bin/env python3
"""
Sistema de Logística de Monedas Inteligentes - simulación en PyBullet
=====================================================================
Flujo simulado:
  1. Tres vasos con monedas salen uno a uno sobre la cinta transportadora
     (cinta en "S": seg1 -> seg2 -> seg3, medidas tomadas de maqueta.urdf).
  2. Al final de la cinta los vasos caen en la canastilla del carro recolector.
  3. El carro planifica una ruta (A*) que esquiva 3 obstáculos y llega a la META.
  4. Se registra en CSV la ruta, el peso, la cantidad y el valor transportado
     (datos listos para el dashboard de Streamlit).

Uso:
    python simulacion_monedas.py            # sin ventana (rápido), guarda PNG y CSV
    python simulacion_monedas.py --gui      # con ventana de PyBullet en tiempo real
"""
import argparse
import csv
import heapq
import math
import os
import random
import time

import numpy as np
import pybullet as p
import pybullet_data

# ----------------------------------------------------------------------------
# PARÁMETROS (ajústalos a tu diseño)
# ----------------------------------------------------------------------------
DT = 1.0 / 240.0
BELT_Z = 0.5                      # altura del eje de la cinta (como en el URDF)
BELT_TOP = BELT_Z + 0.08 + 0.025  # superficie de la banda de caucho
BELT_SPEED = 0.5                  # m/s
CUP_R, CUP_H = 0.07, 0.30
CUP_MASS = 0.10                   # kg, vaso vacío
N_CUPS = 3
SPAWN_EVERY = 4.0                 # s entre vasos

# Línea central de la cinta en S (x, y). Los vasos entran por (2.8, 0).
BELT_PATH = [(2.8, 0.0), (-1.0, 0.0), (-1.0, -4.0), (3.0, -4.0)]

CART_START = (3.3, -4.0)          # carro parado bajo el final de la cinta
GOAL = (7.0, -11.0)               # META
GOAL_TOL = 0.25
OBSTACLES = [(4.8, -6.0, 0.35),   # (x, y, radio)
             (6.2, -8.0, 0.35),
             (4.6, -9.6, 0.35)]
CART_V = 0.6                      # m/s
CART_HALF_DIAG = 0.72             # semidiagonal del chasis 1.2 x 0.8
SAFETY = 0.15                     # margen extra al inflar obstáculos

# Monedas colombianas: denominación (COP) -> masa (kg). VALORES DE EJEMPLO:
# reemplázalos por los que midas con tu sensor / báscula.
COIN_MASS = {50: 0.0046, 100: 0.0053, 200: 0.0070, 500: 0.0074, 1000: 0.0092}

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "salida")


# ----------------------------------------------------------------------------
# UTILIDADES DE ESCENA
# ----------------------------------------------------------------------------
def make_box(half, pos, yaw=0.0, rgba=(1, 1, 1, 1), collide=True, mass=0.0):
    col = p.createCollisionShape(p.GEOM_BOX, halfExtents=half) if collide else -1
    vis = p.createVisualShape(p.GEOM_BOX, halfExtents=half, rgbaColor=rgba)
    return p.createMultiBody(mass, col, vis, pos, p.getQuaternionFromEuler([0, 0, yaw]))


def make_cyl(radius, height, pos, rgba, collide=True, mass=0.0):
    col = (p.createCollisionShape(p.GEOM_CYLINDER, radius=radius, height=height)
           if collide else -1)
    vis = p.createVisualShape(p.GEOM_CYLINDER, radius=radius, length=height, rgbaColor=rgba)
    return p.createMultiBody(mass, col, vis, pos)


def build_scene():
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.81)
    p.setTimeStep(DT)
    p.loadURDF("plane.urdf")

    blue = (0.05, 0.15, 0.35, 1)
    black = (0.05, 0.05, 0.05, 1)
    white = (0.95, 0.95, 0.98, 1)

    # Máquina contadora de monedas (medidas del URDF)
    make_box((1.0, 0.6, 0.05), (-3.0, 0.0, 0.10), rgba=blue)
    make_box((0.9, 0.6, 0.75), (-3.0, 0.0, 0.85), rgba=white)
    for i, r in enumerate([0.05, 0.06, 0.07, 0.08, 0.09]):      # 5 pulsadores
        make_cyl(r, 0.05, (-3.0 - 0.6 + 0.3 * i, 0.0, 1.625), black, collide=False)

    # Cinta en S: (centro x, centro y, largo, yaw)
    for cx, cy, L, yaw in [(1.0, 0.0, 4.0, 0.0),
                           (-1.0, -2.0, 4.4, math.pi / 2),   # 4.4 para cubrir las esquinas
                           (1.0, -4.0, 4.0, 0.0)]:
        make_box((L / 2, 0.20, 0.05), (cx, cy, BELT_Z), yaw, blue)
        make_box((L / 2 - 0.05, 0.15, 0.025), (cx, cy, BELT_Z + 0.08), yaw, black)

    # Obstáculos (rojos) y meta (verde, sin colisión)
    obs_ids = [make_cyl(r, 0.8, (x, y, 0.4), (0.9, 0.1, 0.1, 1)) for x, y, r in OBSTACLES]
    make_cyl(GOAL_TOL, 0.02, (GOAL[0], GOAL[1], 0.01), (0.1, 0.8, 0.2, 1), collide=False)
    return obs_ids


def build_cart():
    """Carro recolector: chasis + canastilla abierta (forma compuesta) + ruedas visuales."""
    z0 = 0.15  # el origen del cuerpo queda en la cara superior del chasis
    cols_pos, cols_half, vis_pos, vis_half, vis_rgba = [], [], [], [], []

    def add(half, pos, rgba):
        cols_half.append(half); cols_pos.append(pos)
        vis_half.append(half); vis_pos.append(pos); vis_rgba.append(rgba)

    carro = (0.10, 0.30, 0.60, 1)
    add((0.6, 0.4, 0.075), (0, 0, -0.075), carro)              # chasis
    add((0.4, 0.02, 0.12), (0, 0.30, 0.12), carro)             # paredes canastilla
    add((0.4, 0.02, 0.12), (0, -0.30, 0.12), carro)
    add((0.02, 0.30, 0.12), (0.38, 0, 0.12), carro)
    add((0.02, 0.30, 0.12), (-0.38, 0, 0.12), carro)

    col = p.createCollisionShapeArray(
        shapeTypes=[p.GEOM_BOX] * len(cols_half), halfExtents=cols_half,
        collisionFramePositions=cols_pos)
    vis = p.createVisualShapeArray(
        shapeTypes=[p.GEOM_BOX] * len(vis_half), halfExtents=vis_half,
        visualFramePositions=vis_pos, rgbaColors=vis_rgba)
    cart = p.createMultiBody(20.0, col, vis,
                             (CART_START[0], CART_START[1], z0 + 0.005),
                             p.getQuaternionFromEuler([0, 0, 0]))
    p.changeDynamics(cart, -1, lateralFriction=0.9, linearDamping=0.0, angularDamping=0.0)

    # ruedas (solo visual, un cuerpo aparte sería innecesario: se dibujan como parte del chasis)
    return cart


# ----------------------------------------------------------------------------
# CINTA: los vasos siguen la línea central con velocidad constante
# ----------------------------------------------------------------------------
class Belt:
    def __init__(self, pts, speed):
        self.speed = speed
        self.segs = []
        acc = 0.0
        for a, b in zip(pts[:-1], pts[1:]):
            a, b = np.array(a), np.array(b)
            L = float(np.linalg.norm(b - a))
            self.segs.append((a, (b - a) / L, L, acc))
            acc += L
        self.length = acc

    def query(self, x, y):
        """Devuelve (velocidad deseada xy, progreso s a lo largo de la cinta)."""
        pos = np.array([x, y])
        best = None
        for a, d, L, s0 in self.segs:
            s = float(np.clip(np.dot(pos - a, d), 0.0, L))
            closest = a + d * s
            dist = float(np.linalg.norm(closest - pos))
            if best is None or dist <= best[0] + 1e-9:       # empate -> segmento posterior
                best = (dist, d, closest, s0 + s)
        _, d, closest, s_total = best
        err = closest - pos
        err -= np.dot(err, d) * d                            # solo corrección lateral
        return d * self.speed + 2.0 * err, s_total


def spawn_cup(idx, coins, belt):
    mass = CUP_MASS + sum(COIN_MASS[c] for c in coins)
    col = p.createCollisionShape(p.GEOM_CYLINDER, radius=CUP_R, height=CUP_H)
    palette = [(0.05, 0.15, 0.35, 1), (0.15, 0.15, 0.15, 1), (0.8, 0.5, 0.1, 1)]
    vis = p.createVisualShape(p.GEOM_CYLINDER, radius=CUP_R, length=CUP_H,
                              rgbaColor=palette[idx % 3])
    x0, y0 = belt.segs[0][0]
    cup = p.createMultiBody(mass, col, vis, (x0, y0, BELT_TOP + CUP_H / 2 + 0.01))
    p.changeDynamics(cup, -1, lateralFriction=0.8)
    return cup, mass


# ----------------------------------------------------------------------------
# PLANIFICADOR A* + seguimiento (pure pursuit)
# ----------------------------------------------------------------------------
def plan_path(start, goal, res=0.1, xr=(1.5, 9.0), yr=(-13.0, -2.5)):
    infl = CART_HALF_DIAG + SAFETY
    nx, ny = int((xr[1] - xr[0]) / res) + 1, int((yr[1] - yr[0]) / res) + 1
    to_cell = lambda x, y: (int(round((x - xr[0]) / res)), int(round((y - yr[0]) / res)))
    to_xy = lambda i, j: (xr[0] + i * res, yr[0] + j * res)

    def free(x, y):
        return all(math.hypot(x - ox, y - oy) > orr + infl for ox, oy, orr in OBSTACLES)

    blocked = np.zeros((nx, ny), bool)
    for i in range(nx):
        for j in range(ny):
            blocked[i, j] = not free(*to_xy(i, j))

    s, g = to_cell(*start), to_cell(*goal)
    openq = [(0.0, s)]
    came, cost = {s: None}, {s: 0.0}
    nbrs = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
    while openq:
        _, cur = heapq.heappop(openq)
        if cur == g:
            break
        for di, dj in nbrs:
            n = (cur[0] + di, cur[1] + dj)
            if not (0 <= n[0] < nx and 0 <= n[1] < ny) or blocked[n]:
                continue
            c = cost[cur] + math.hypot(di, dj)
            if n not in cost or c < cost[n]:
                cost[n] = c
                came[n] = cur
                h = math.hypot(n[0] - g[0], n[1] - g[1])
                heapq.heappush(openq, (c + h, n))
    if g not in came:
        raise RuntimeError("A* no encontró ruta: revisa obstáculos/meta")
    path, cur = [], g
    while cur is not None:
        path.append(to_xy(*cur))
        cur = came[cur]
    path.reverse()

    # simplificar por línea de vista
    def los(a, b):
        n = int(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.05) + 1
        return all(free(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
                   for k in range(n + 1))

    simp, i = [path[0]], 0
    while i < len(path) - 1:
        j = len(path) - 1
        while j > i + 1 and not los(path[i], path[j]):
            j -= 1
        simp.append(path[j])
        i = j

    # re-muestrear cada 0.3 m para un seguimiento suave
    dense = [simp[0]]
    for a, b in zip(simp[:-1], simp[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        for k in range(1, max(1, int(L / 0.3)) + 1):
            t = min(1.0, k * 0.3 / L)
            dense.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return simp, dense


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


# ----------------------------------------------------------------------------
# SALIDAS
# ----------------------------------------------------------------------------
def snapshot(name):
    view = p.computeViewMatrixFromYawPitchRoll((2.5, -5.0, 0.3), 15, 90, -55, 0, 2)
    proj = p.computeProjectionMatrixFOV(60, 1.6, 0.1, 50)
    w, h, rgb, _, _ = p.getCameraImage(960, 600, view, proj, renderer=p.ER_TINY_RENDERER)
    import matplotlib.image as mpimg
    img = np.reshape(np.array(rgb, dtype=np.uint8), (h, w, 4))[:, :, :3]
    mpimg.imsave(os.path.join(OUT_DIR, name), img)


def plot_route(simp, dense, trail):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 8))
    bx, by = zip(*BELT_PATH)
    ax.plot(bx, by, color="#0d2659", lw=10, alpha=0.35, solid_capstyle="butt", label="Cinta (S)")
    infl = CART_HALF_DIAG + SAFETY
    for k, (x, y, r) in enumerate(OBSTACLES):
        ax.add_patch(plt.Circle((x, y), r, color="tab:red", label="Obstáculo" if k == 0 else None))
        ax.add_patch(plt.Circle((x, y), r + infl, fill=False, ls="--", color="tab:red", alpha=0.4))
    ax.plot(*zip(*simp), "o-", color="tab:orange", label="Ruta A*")
    ax.plot(*zip(*trail), color="tab:blue", lw=2, label="Trayectoria real del carro")
    ax.plot(*CART_START, "ks", label="Inicio del carro")
    ax.plot(*GOAL, "g*", ms=18, label="META")
    ax.set_aspect("equal"); ax.grid(alpha=0.3)
    ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]")
    ax.set_title("Pista para llegar a la meta")
    ax.legend(loc="upper right", fontsize=8)
    fig.savefig(os.path.join(OUT_DIR, "trayectoria.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)


# ----------------------------------------------------------------------------
# PRINCIPAL
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gui", action="store_true", help="abrir ventana de PyBullet")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--tmax", type=float, default=120.0)
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    random.seed(args.seed)

    p.connect(p.GUI if args.gui else p.DIRECT)
    if args.gui:
        p.resetDebugVisualizerCamera(12, 40, -40, (2.5, -5.0, 0.3))
    obs_ids = build_scene()
    cart = build_cart()
    belt = Belt(BELT_PATH, BELT_SPEED)
    simp, dense = plan_path(CART_START, GOAL)

    # contenido aleatorio de cada vaso
    cups, cup_info = [], []
    plan_coins = [[random.choice(list(COIN_MASS)) for _ in range(random.randint(2, 5))]
                  for _ in range(N_CUPS)]

    t, spawned, on_belt = 0.0, 0, set()
    last_exit_t, state, wp = None, "CARGANDO", 0
    trail, log_rows, collisions = [], [], 0
    snaps = {"1_cinta.png": False, "2_carga.png": False, "3_meta.png": False}
    reached_t = None

    while t < args.tmax:
        # 1) aparición de vasos
        if spawned < N_CUPS and t >= spawned * SPAWN_EVERY:
            cup, mass = spawn_cup(spawned, plan_coins[spawned], belt)
            cups.append(cup)
            cup_info.append({"vaso": spawned + 1, "monedas": plan_coins[spawned],
                             "cantidad": len(plan_coins[spawned]),
                             "valor_cop": sum(plan_coins[spawned]), "peso_kg": round(mass, 4)})
            on_belt.add(cup)
            spawned += 1

        # 2) cinta: arrastra los vasos que están apoyados sobre ella
        for cup in list(on_belt):
            (x, y, z), _ = p.getBasePositionAndOrientation(cup)
            v_xy, s = belt.query(x, y)
            if s >= belt.length - 0.02:            # salió de la cinta
                on_belt.discard(cup)
                last_exit_t = t
                continue
            vz = p.getBaseVelocity(cup)[0][2]
            p.resetBaseVelocity(cup, [v_xy[0], v_xy[1], vz], [0, 0, 0])

        # 3) máquina de estados del carro
        (cx, cy, cz), corn = p.getBasePositionAndOrientation(cart)
        yaw = p.getEulerFromQuaternion(corn)[2]
        vz = p.getBaseVelocity(cart)[0][2]
        vcmd, wcmd = 0.0, 0.0

        if state == "CARGANDO":
            if spawned == N_CUPS and not on_belt and last_exit_t is not None \
                    and t - last_exit_t > 2.0:
                state = "NAVEGANDO"
        elif state == "NAVEGANDO":
            while wp < len(dense) - 1 and math.hypot(dense[wp][0] - cx, dense[wp][1] - cy) < 0.5:
                wp += 1
            tx, ty = dense[wp]
            err = wrap(math.atan2(ty - cy, tx - cx) - yaw)
            wcmd = float(np.clip(2.5 * err, -1.5, 1.5))
            vcmd = CART_V * max(0.0, math.cos(err)) ** 3
            if math.hypot(GOAL[0] - cx, GOAL[1] - cy) < GOAL_TOL:
                state, reached_t = "META", t
        if state == "META":
            vcmd = wcmd = 0.0
        p.resetBaseVelocity(cart, [vcmd * math.cos(yaw), vcmd * math.sin(yaw), vz], [0, 0, wcmd])

        p.stepSimulation()
        t += DT
        if args.gui:
            time.sleep(DT)

        # 4) colisiones con obstáculos
        for o in obs_ids:
            if p.getContactPoints(cart, o):
                collisions += 1

        # 5) registro cada 0.1 s
        if int(round(t / DT)) % 24 == 0:
            c, s_ = math.cos(-yaw), math.sin(-yaw)
            n_in, peso, valor = 0, 0.0, 0
            for cup, info in zip(cups, cup_info):
                (px, py, pz), _ = p.getBasePositionAndOrientation(cup)
                lx, ly = (px - cx) * c - (py - cy) * s_, (px - cx) * s_ + (py - cy) * c
                if abs(lx) < 0.42 and abs(ly) < 0.32 and pz < 0.6:
                    n_in += 1; peso += info["peso_kg"]; valor += info["valor_cop"]
            monedas = sum(i["cantidad"] for c_, i in zip(cups, cup_info)
                          if abs(p.getBasePositionAndOrientation(c_)[0][0] - cx) < 0.5
                          and abs(p.getBasePositionAndOrientation(c_)[0][1] - cy) < 0.5)
            log_rows.append([round(t, 2), state, round(cx, 3), round(cy, 3), round(yaw, 3),
                             n_in, monedas, round(peso, 4), valor])
            trail.append((cx, cy))

            if not snaps["1_cinta.png"] and spawned >= 2 and state == "CARGANDO":
                snapshot("1_cinta.png"); snaps["1_cinta.png"] = True
            if not snaps["2_carga.png"] and state == "NAVEGANDO" and wp > 3:
                snapshot("2_carga.png"); snaps["2_carga.png"] = True

        if reached_t is not None and t - reached_t > 1.0:
            break

    snapshot("3_meta.png")

    with open(os.path.join(OUT_DIR, "log_ruta.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "estado", "x_m", "y_m", "yaw_rad", "vasos_en_carro",
                    "monedas_en_carro", "peso_kg", "valor_cop"])
        w.writerows(log_rows)
    with open(os.path.join(OUT_DIR, "vasos.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["vaso", "monedas_cop", "cantidad", "valor_cop", "peso_kg"])
        for i in cup_info:
            w.writerow([i["vaso"], "+".join(map(str, i["monedas"])), i["cantidad"],
                        i["valor_cop"], i["peso_kg"]])
    plot_route(simp, dense, trail)

    fin = log_rows[-1]
    print(f"Estado final: {state}  (t = {t:.1f} s)")
    print(f"Posición final del carro: ({fin[2]}, {fin[3]})  meta = {GOAL}")
    print(f"Vasos en el carro: {fin[5]}/{N_CUPS} | monedas: {sum(i['cantidad'] for i in cup_info)}"
          f" | peso: {fin[7]} kg | valor: ${fin[8]} COP")
    print(f"Pasos con contacto carro-obstáculo: {collisions}")
    print(f"Archivos en: {OUT_DIR}")
    p.disconnect()


if __name__ == "__main__":
    main()

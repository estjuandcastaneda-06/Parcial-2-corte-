"""Simulación en PyBullet del enjambre de 5 carritos (hormigas) recolectando
vasos con monedas, cruzando los 3 obstáculos en slalom y entregando en el nido.

NO PROBADO EN EL ENTORNO DE DESARROLLO de este chat (pybullet no instala aquí:
requiere Visual C++ Build Tools en Windows con Python 3.14). Sí se validó por
separado la lógica de decisión (swarm.py, con 12 000 pasos sin errores) y el
URDF (bien formado; se recorrió su árbol de links/joints con ElementTree).
Pruébalo en el entorno del curso, donde ya usan pybullet en el repo
U_Militar (normalmente Python 3.10/3.11):

    pip install pybullet
    python swarm_pybullet.py

La lógica de ALTO NIVEL (a qué vaso ir, cuándo volver, la feromona) la calcula
swarm.Enjambre exactamente igual que en el dashboard — es el mismo "cerebro"
que luego se porta al ESP32 de cada carrito. Este script solo mueve el CUERPO
físico de cada carrito en PyBullet hacia el punto que decide swarm.py, con un
control de velocidad diferencial (igual que haría el ESP32 con el L298N/TB6612
sobre las ruedas reales).
"""
from __future__ import annotations

import math
import os
import sys
import time

import pybullet as p
import pybullet_data

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from swarm import CELL_M, NIDO, OBSTACULOS, W, H, Enjambre  # noqa: E402

URDF_DIR = os.path.dirname(os.path.abspath(__file__))

# -- geometría del carrito real (debe coincidir con carrito.urdf) ----------
TROCHA = 0.110        # m, separación entre ruedas motrices (eje a eje)
R_RUEDA = 0.021        # m, radio de rueda
V_MAX = 6.0            # rad/s máximo de las ruedas (referencia de un TT motor a 1:48 sin carga)
KP_ANG = 3.2           # ganancia del control de rumbo
KP_LIN = 2.4           # ganancia del control de avance


def grid_a_mundo(gx, gy):
    """Convierte coordenadas de la grilla de swarm.py a metros en PyBullet (Z=0, plano XY)."""
    return gx * CELL_M, gy * CELL_M


def construir_escenario():
    p.connect(p.GUI)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.81)
    p.loadURDF("plane.urdf")
    p.resetDebugVisualizerCamera(cameraDistance=3.6, cameraYaw=35, cameraPitch=-52,
                                 cameraTargetPosition=grid_a_mundo(W / 2, H / 2) + (0,))

    # nido / banda de entrega, como referencia visual
    nx, ny = grid_a_mundo(*NIDO)
    p.createMultiBody(baseVisualShapeIndex=p.createVisualShape(
        p.GEOM_BOX, halfExtents=[0.18, 0.18, 0.01], rgbaColor=[0.12, 0.44, 0.42, 1]),
        basePosition=[nx, ny, 0.005])

    # los 3 obstáculos en slalom (mismas celdas que swarm.OBSTACULOS)
    for ox, oy, ow, oh in OBSTACULOS:
        cx, cy = grid_a_mundo(ox + ow / 2, oy + oh / 2)
        hx, hy = ow / 2 * CELL_M, oh / 2 * CELL_M
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[hx, hy, 0.09])
        vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[hx, hy, 0.09], rgbaColor=[0.56, 0.18, 0.11, 1])
        p.createMultiBody(baseMass=0, baseCollisionShapeIndex=col, baseVisualShapeIndex=vis,
                          basePosition=[cx, cy, 0.09])


def spawn_carritos(n=5):
    ids = []
    inicios = [(4, 3), (4, H - 4), (4, H // 2), (7, 6), (7, H - 7)][:n]
    for gx, gy in inicios:
        x, y = grid_a_mundo(gx, gy)
        cid = p.loadURDF(os.path.join(URDF_DIR, "carrito.urdf"), [x, y, 0.02],
                         p.getQuaternionFromEuler([0, 0, 0]))
        ids.append(cid)
    return ids


def joint_index(body_id, nombre):
    for i in range(p.getNumJoints(body_id)):
        if p.getJointInfo(body_id, i)[1].decode() == nombre:
            return i
    raise ValueError(f"No se encontró el joint {nombre}")


def controlar_diferencial(body_id, ji_izq, ji_der, tx, ty, dt):
    """Traduce (ir hacia tx,ty) a velocidades de rueda, como lo haría el firmware del ESP32."""
    pos, orn = p.getBasePositionAndOrientation(body_id)
    yaw = p.getEulerFromQuaternion(orn)[2]
    dx, dy = tx - pos[0], ty - pos[1]
    dist = math.hypot(dx, dy)
    rumbo_obj = math.atan2(dy, dx)
    err_ang = (rumbo_obj - yaw + math.pi) % (2 * math.pi) - math.pi

    v = min(KP_LIN * dist, 0.5)                 # m/s, techo de velocidad lineal
    w = max(-2.5, min(2.5, KP_ANG * err_ang))     # rad/s

    if abs(err_ang) > 1.2:                        # si está muy desalineado, gira en el sitio
        v *= 0.15

    w_izq = (v - w * TROCHA / 2) / R_RUEDA
    w_der = (v + w * TROCHA / 2) / R_RUEDA
    w_izq = max(-V_MAX, min(V_MAX, w_izq))
    w_der = max(-V_MAX, min(V_MAX, w_der))
    p.setJointMotorControl2(body_id, ji_izq, p.VELOCITY_CONTROL, targetVelocity=w_izq, force=3)
    p.setJointMotorControl2(body_id, ji_der, p.VELOCITY_CONTROL, targetVelocity=w_der, force=3)


def main(pasos=6000, dt=1 / 60):
    construir_escenario()
    ids = spawn_carritos(5)
    j_izq = [joint_index(i, "rueda_izq_joint") for i in ids]
    j_der = [joint_index(i, "rueda_der_joint") for i in ids]

    enjambre = Enjambre(seed=7)
    t_logica = 0.0
    DT_LOGICA = 0.2   # el "cerebro" (swarm.py) decide 5 veces por segundo, como el ESP32

    for paso in range(pasos):
        t_logica += dt
        if t_logica >= DT_LOGICA:
            t_logica = 0.0
            enjambre.step(DT_LOGICA)

        for k, cid in enumerate(ids):
            c = enjambre.carritos[k]
            # sincroniza la posición 2D "lógica" del carrito con la física real de pybullet,
            # para que la próxima decisión de swarm.py parta de dónde está el cuerpo de verdad
            pos, _ = p.getBasePositionAndOrientation(cid)
            c.x, c.y = pos[0] / CELL_M, pos[1] / CELL_M
            tx, ty = grid_a_mundo(c.x + c.dir_x, c.y + c.dir_y) if (c.dir_x or c.dir_y) else pos[:2]
            controlar_diferencial(cid, j_izq[k], j_der[k], tx, ty, dt)

        p.stepSimulation()
        time.sleep(dt)

    entregados = enjambre.entregados_total
    print(f"Simulación terminada: {entregados} vasos entregados, "
          f"$ {enjambre.valor_total:,} recolectados".replace(",", "."))
    p.disconnect()


if __name__ == "__main__":
    main()

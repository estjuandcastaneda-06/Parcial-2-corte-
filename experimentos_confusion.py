"""Experimentos de la matriz de confusión del enjambre -> planos/resultados_confusion.json
  A) paleta actual (plateado/beige...)   B) paleta recomendada (blanco/amarillo/azul/rojo/verde)
  C) regla de errores (E_MAX=2 vs sin regla) con poca y mucha deriva del sensor
Uso:  python experimentos_confusion.py        (tarda varios minutos)"""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import swarm
from swarm import DENOMS, Enjambre

SEMILLAS = range(6)
T_SIM = 1800          # s simulados por corrida
PALETA_ORIGINAL = copy.deepcopy(swarm.COLOR)


def corrida(paleta, deriva, e_max):
    swarm.usar_paleta(paleta)
    swarm.DERIVA = deriva
    ok = mal = recal = 0
    M = [[0] * 5 for _ in range(5)]
    for s in SEMILLAS:
        e = Enjambre(s, e_max=e_max)
        for _ in range(int(T_SIM / 0.2)):
            e.step(0.2)
        ok += e.entregados_ok; mal += e.entregados_err
        recal += sum(c.recalibraciones for c in e.carritos)
        m = e.matriz_confusion()["matriz"]
        for i in range(5):
            for j in range(5):
                M[i][j] += m[i][j]
    n = sum(map(sum, M))
    return dict(matriz=M, ok=ok, mal=mal, recal=recal, lecturas=n, exactitud=sum(M[i][i] for i in range(5)) / n if n else None)


if __name__ == "__main__":
    res = {"denoms": DENOMS, "semillas": len(SEMILLAS), "t_sim_s": T_SIM,
           "params": dict(SIGMA_COLOR=swarm.SIGMA_COLOR, MARGEN_DUDA=swarm.MARGEN_DUDA, MAX_LECTURAS=swarm.MAX_LECTURAS, E_MAX=swarm.E_MAX)}
    print("A) paleta actual", flush=True)
    res["A"] = corrida(PALETA_ORIGINAL, 0.0006, swarm.E_MAX)
    print(res["A"]["ok"], res["A"]["mal"], flush=True)
    print("B) paleta recomendada", flush=True)
    res["B"] = corrida(swarm.PALETA_RECOMENDADA, 0.0006, swarm.E_MAX)
    print(res["B"]["ok"], res["B"]["mal"], flush=True)
    res["regla"] = []
    for deriva in (0.0006, 0.0020):
        for e_max in (None, swarm.E_MAX):
            r = corrida(PALETA_ORIGINAL, deriva, e_max)
            r.update(deriva=deriva, e_max=e_max)
            res["regla"].append(r)
            print("regla", deriva, e_max, r["ok"], r["mal"], r["recal"], flush=True)
    swarm.usar_paleta(PALETA_ORIGINAL)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "planos", "resultados_confusion.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("guardado", out)

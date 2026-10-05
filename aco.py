"""Colonia de hormigas (ACO) para planear la recolección de vasos.

Nodos: 0 = base del dron, 1..n = vasos (cada uno con un valor en $ según sus monedas),
n+1 = meta. Se busca el recorrido base -> todos los vasos -> meta más corto.
"""
from __future__ import annotations

import numpy as np


def generar_vasos(n: int, seed: int = 7):
    rng = np.random.default_rng(seed)
    pts = rng.uniform([0.08, 0.15], [0.92, 0.85], size=(n, 2))
    valores = rng.choice([500, 1000, 1500, 2200, 3000, 4200], size=n)
    base = np.array([[0.03, 0.5]])
    meta = np.array([[0.97, 0.5]])
    return np.vstack([base, pts, meta]), valores


def longitud(ruta, D):
    return float(sum(D[a, b] for a, b in zip(ruta[:-1], ruta[1:])))


def resolver(coords, n_hormigas=20, iteraciones=60, alfa=1.0, beta=3.0, rho=0.4, q=1.0, seed=1):
    rng = np.random.default_rng(seed)
    N = len(coords)
    D = np.linalg.norm(coords[:, None] - coords[None], axis=2) + np.eye(N) * 1e9
    eta = 1.0 / D
    tau = np.ones((N, N))
    meta = N - 1
    mejor, mejor_L = None, np.inf
    hist_mejor, hist_media = [], []
    for _ in range(iteraciones):
        rutas, Ls = [], []
        for _h in range(n_hormigas):
            ruta, libres = [0], set(range(1, N - 1))
            while libres:
                i = ruta[-1]
                cand = np.array(sorted(libres))
                p = (tau[i, cand] ** alfa) * (eta[i, cand] ** beta)
                p /= p.sum()
                j = int(rng.choice(cand, p=p))
                ruta.append(j)
                libres.remove(j)
            ruta.append(meta)
            L = longitud(ruta, D)
            rutas.append(ruta)
            Ls.append(L)
            if L < mejor_L:
                mejor, mejor_L = ruta, L
        tau *= (1 - rho)
        for ruta, L in zip(rutas, Ls):
            for a, b in zip(ruta[:-1], ruta[1:]):
                tau[a, b] += q / L
                tau[b, a] += q / L
        hist_mejor.append(mejor_L)
        hist_media.append(float(np.mean(Ls)))
    return {"ruta": mejor, "L": mejor_L, "tau": tau, "mejor": hist_mejor, "media": hist_media}

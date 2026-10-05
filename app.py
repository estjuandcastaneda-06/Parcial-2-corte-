"""Sistema logístico de monedas inteligentes — interfaz Streamlit.

Fuente de datos: simulador interno o ESP32 real por WiFi (GET /data).
Ejecutar:  streamlit run app.py
"""
from __future__ import annotations

import json
import math
import time

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import aco
import esp32_client
from coins import CATALOGO, POR_KEY, cop, coin_svg, resumen
from simulador import DRON_CARGA, OBSTACULOS, T_BANDA, T_TAPA, VASO_CAP, Simulador

st.set_page_config(page_title="Logística de Monedas · ESP32", page_icon="🪙", layout="wide")

INK, PAPER, ORANGE, TEAL, RUST = "#1d2430", "#f3efe6", "#b8480f", "#1f6f6b", "#8f2d1b"

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Barlow:wght@400;500&display=swap');
html, body, [class*="css"], .stMarkdown, p, li { font-family: 'Barlow', sans-serif; }
h1, h2, h3, h4 { font-family: 'Barlow Condensed', sans-serif !important; letter-spacing: .01em; }
h1 { font-weight: 700 !important; font-size: 2.6rem !important; margin-bottom: 0 !important; }
.block-container { padding-top: 2.2rem; max-width: 1280px; }
.kicker { font-family: 'IBM Plex Mono', monospace; font-size: .72rem; letter-spacing: .14em;
          text-transform: uppercase; color: #6b6558; }
.plate { border: 1.5px solid #1d2430; background: #faf7f0; padding: 14px 16px; border-radius: 2px;
         box-shadow: 3px 3px 0 #1d243022; }
.plate .lbl { font-family:'IBM Plex Mono',monospace; font-size:.68rem; letter-spacing:.12em;
              text-transform:uppercase; color:#6b6558; }
.plate .val { font-family:'Barlow Condensed',sans-serif; font-weight:700; font-size:2.3rem; line-height:1.05; }
.plate .sub { font-family:'IBM Plex Mono',monospace; font-size:.75rem; color:#4a4f57; }
.tag { display:inline-block; font-family:'IBM Plex Mono',monospace; font-size:.7rem; padding:2px 8px;
       border:1px solid #1d2430; border-radius:2px; letter-spacing:.06em; }
.tag.on { background:#1f6f6b; color:#fff; border-color:#1f6f6b; }
.tag.warn { background:#b8480f; color:#fff; border-color:#b8480f; }
.tag.off { background:#e8e2d3; }
[data-testid="stTabs"] button { font-family:'Barlow Condensed',sans-serif; font-size:1.15rem; letter-spacing:.03em; }
section[data-testid="stSidebar"] { border-right: 1.5px solid #1d2430; }
.mono { font-family:'IBM Plex Mono',monospace; }
.coinrow { display:flex; align-items:flex-end; gap:18px; flex-wrap:wrap; }
.coincell { text-align:center; font-family:'IBM Plex Mono',monospace; font-size:.68rem; color:#4a4f57; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- estado / datos
if "sim" not in st.session_state:
    st.session_state.sim = Simulador()
    st.session_state.hist = []          # (t, valor, cantidad, peso)
    st.session_state.cache = (0.0, None, None)
    st.session_state.chat = [
        {"role": "assistant", "content": "Hola, soy el asistente del sistema de monedas. Pregúntame por el valor procesado, "
                                        "el peso, la cantidad, el estado del dron o la ruta."}
    ]
    st.session_state.speak = None

with st.sidebar:
    st.markdown("### Conexión")
    fuente = st.radio("Fuente de datos", ["Simulador interno", "ESP32 por WiFi"], label_visibility="collapsed")
    host = st.text_input("IP / host del ESP32", "192.168.1.50", disabled=fuente != "ESP32 por WiFi",
                         help="El ESP32 debe responder JSON en http://<host>/data. Para probar sin hardware: "
                              "python mock_esp32.py y usa localhost:8080")
    refresco = st.slider("Refresco (s)", 1, 5, 1)
    voz = st.toggle("Chatbot habla por voz", value=True)
    if st.button("Reiniciar conteo", width="stretch"):
        if fuente == "ESP32 por WiFi":
            try:
                esp32_client.enviar_comando(host, "reset")
            except esp32_client.ESP32Error as e:
                st.error(f"No se pudo reiniciar: {e}")
        else:
            st.session_state.sim.reset()
        st.session_state.hist = []
    st.divider()
    st.caption("Serie nueva = 2012+ · Serie antigua = 1989-2012. Medidas: Banco de la República.")


def obtener_estado() -> tuple[dict | None, str | None]:
    """Un solo GET compartido entre fragments (cache de ~0.8 s)."""
    t, est, err = st.session_state.cache
    if time.time() - t < 0.8 and (est or err):
        return est, err
    est, err = None, None
    if fuente == "Simulador interno":
        est = st.session_state.sim.estado()
    else:
        try:
            est = esp32_client.leer(host)
        except esp32_client.ESP32Error as e:
            err = str(e)
    st.session_state.cache = (time.time(), est, err)
    if est:
        r = resumen(est["contador"]["conteo"])
        h = st.session_state.hist
        if not h or est["ts"] != h[-1][0]:
            h.append((est["ts"], r["valor"], r["cantidad"], est["contador"].get("peso_g", r["peso_monedas_g"])))
            del h[:-600]
    return est, err


def plate(lbl, val, sub=""):
    return f'<div class="plate"><div class="lbl">{lbl}</div><div class="val">{val}</div><div class="sub">{sub}</div></div>'


def fragmento(fn):
    """Envuelve una vista en un fragment con auto-refresco."""
    def run():
        est, err = obtener_estado()
        if err:
            st.error(f"Sin respuesta del ESP32 en {host}: {err}")
            return
        fn(est)
    return st.fragment(run, run_every=refresco)


# ---------------------------------------------------------------- vistas
def pista_xy(t):
    """Trayectoria en S de la pista (t en 0..1)."""
    x = 10 * t
    y = 1.6 * np.sin(2 * math.pi * 1.5 * t + 0.3) * (1 - 0.15 * t)
    return x, y


def vista_panel(est):
    conteo = est["contador"]["conteo"]
    r = resumen(conteo)
    peso = est["contador"].get("peso_g", r["peso_monedas_g"])
    dron = est["dron"]
    c = st.columns(4)
    c[0].markdown(plate("Valor procesado", cop(r["valor"]), "COP acumulado"), unsafe_allow_html=True)
    c[1].markdown(plate("Cantidad", f'{r["cantidad"]}', f'{est["contador"]["rechazadas"]} rechazadas'), unsafe_allow_html=True)
    c[2].markdown(plate("Peso", f"{peso:,.1f} g", "monedas contadas"), unsafe_allow_html=True)
    c[3].markdown(plate("Dron", dron["estado"].upper(), f'{dron["progreso"]*100:.0f}% · obstáculos {dron["obstaculos_superados"]}/3'),
                  unsafe_allow_html=True)
    st.write("")
    a, b = st.columns([1.15, 1])
    with a:
        st.markdown("#### Ruta del dron")
        st.plotly_chart(fig_pista(dron), width="stretch", key="pista_panel")
    with b:
        st.markdown("#### Valor por denominación")
        df = pd.DataFrame([{"Moneda": POR_KEY[k].label, "Cantidad": n, "Valor": POR_KEY[k].denom * n,
                            "serie": POR_KEY[k].serie} for k, n in conteo.items()])
        fig = go.Figure(go.Bar(
            x=df["Valor"], y=df["Moneda"], orientation="h",
            marker_color=[ORANGE if s == "nueva" else TEAL for s in df["serie"]],
            text=[cop(v) for v in df["Valor"]], textposition="outside", cliponaxis=False))
        fig.update_layout(height=340, margin=dict(l=0, r=60, t=6, b=0), paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", yaxis=dict(autorange="reversed"),
                          font=dict(family="IBM Plex Mono", size=11, color=INK), xaxis=dict(showgrid=True, gridcolor="#d9d2c0"))
        st.plotly_chart(fig, width="stretch", key="bar_panel")
        st.caption("Naranja = serie nueva · Verde azulado = serie antigua")
    h = st.session_state.hist
    if len(h) > 2:
        st.markdown("#### Evolución en el tiempo")
        d = pd.DataFrame(h, columns=["ts", "valor", "cant", "peso"])
        d["s"] = d["ts"] - d["ts"].iloc[0]
        fig = go.Figure()
        fig.add_scatter(x=d["s"], y=d["valor"], name="Valor ($)", line=dict(color=ORANGE, width=2.5))
        fig.add_scatter(x=d["s"], y=d["peso"], name="Peso (g)", yaxis="y2", line=dict(color=TEAL, width=2, dash="dot"))
        fig.update_layout(height=260, margin=dict(l=0, r=0, t=6, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font=dict(family="IBM Plex Mono", size=11, color=INK), legend=dict(orientation="h", y=1.15),
                          yaxis=dict(title="$", gridcolor="#d9d2c0"), yaxis2=dict(title="g", overlaying="y", side="right", showgrid=False),
                          xaxis=dict(title="s"))
        st.plotly_chart(fig, width="stretch", key="hist_panel")


def fig_pista(dron):
    t = np.linspace(0, 1, 240)
    x, y = pista_xy(t)
    f = go.Figure()
    f.add_scatter(x=x, y=y, mode="lines", line=dict(color="#3b3f46", width=34), hoverinfo="skip", showlegend=False)
    f.add_scatter(x=x, y=y, mode="lines", line=dict(color="#e9e4d8", width=2, dash="dash"), hoverinfo="skip", showlegend=False)
    ox, oy = pista_xy(np.array(OBSTACULOS))
    f.add_scatter(x=ox, y=oy, mode="markers+text", text=["Obst. 1", "Obst. 2", "Obst. 3"], textposition="top center",
                  marker=dict(symbol="square", size=26, color=RUST, line=dict(color="#fff", width=2)),
                  name="Obstáculo", textfont=dict(color=RUST, family="IBM Plex Mono", size=11))
    sx, sy = pista_xy(np.array([0.0]))
    ex, ey = pista_xy(np.array([1.0]))
    f.add_scatter(x=sx, y=sy, mode="markers+text", text=["SALIDA"], textposition="bottom center",
                  marker=dict(size=10, color=TEAL), showlegend=False, textfont=dict(family="IBM Plex Mono", size=10))
    f.add_scatter(x=ex, y=ey, mode="markers+text", text=["META"], textposition="top center",
                  marker=dict(symbol="star", size=20, color=ORANGE), showlegend=False, textfont=dict(family="IBM Plex Mono", size=11))
    px, py = pista_xy(np.array([dron["progreso"]]))
    f.add_scatter(x=px, y=py, mode="markers", marker=dict(symbol="diamond", size=18, color="#ffd23f", line=dict(color=INK, width=2.5)),
                  name="Dron")
    f.update_layout(height=340, margin=dict(l=0, r=0, t=6, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(visible=False, range=[-0.6, 10.6]), yaxis=dict(visible=False, range=[-2.6, 2.8], scaleanchor="x"),
                    legend=dict(orientation="h", y=-0.02, font=dict(family="IBM Plex Mono", size=11)))
    return f


def vista_contador(est):
    cont = est["contador"]
    conteo = cont["conteo"]
    ult = cont.get("ultima")
    st.markdown("#### Última moneda medida")
    a, b = st.columns([1, 2])
    with a:
        if ult and ult.get("clase") in POR_KEY:
            c = POR_KEY[ult["clase"]]
            st.markdown(f'<div class="plate" style="text-align:center">{coin_svg(c, 6)}'
                        f'<div class="val">{c.label}</div><div class="sub">{ult["d_mm"]:.2f} mm · {ult["w_g"]:.2f} g</div></div>',
                        unsafe_allow_html=True)
        elif ult:
            st.markdown(plate("Rechazada", "—", f'{ult["d_mm"]:.2f} mm · {ult["w_g"]:.2f} g (no coincide con el catálogo)'),
                        unsafe_allow_html=True)
        else:
            st.info("Esperando la primera moneda…")
    with b:
        st.markdown(f'<span class="tag on">SENSORES OK</span> <span class="tag">clasificación por diámetro + peso</span>',
                    unsafe_allow_html=True)
        st.write("")
        rows = []
        for cn in CATALOGO:
            n = conteo.get(cn.key, 0)
            rows.append({"Moneda": cn.label, "Diám. (mm)": cn.d, "Peso (g)": cn.w, "Cantidad": n,
                         "Valor": cop(cn.denom * n), "Peso acum. (g)": round(cn.w * n, 2)})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", height=360)
    v = est["vaso"]
    st.markdown(f"**Vaso en llenado:** {v['monedas']}/{v['capacidad']} monedas")
    st.progress(v["monedas"] / v["capacidad"])


def vista_transporte(est):
    e = est["embalaje"]
    v = est["vaso"]
    st.markdown(f'<span class="tag {"on" if e["en_tapa"] else "off"}">BRAZO: {e["brazo"].upper()}</span> '
                f'<span class="tag">vasos totales: {e["vasos_totales"]}</span>', unsafe_allow_html=True)
    st.write("")
    W, H = 900, 300
    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="IBM Plex Mono">']
    s.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#faf7f0" stroke="{INK}" stroke-width="1.5"/>')
    # banda
    s.append(f'<rect x="30" y="170" width="560" height="14" fill="#3b3f46"/>')
    for i in range(0, 560, 28):
        s.append(f'<circle cx="{44+i}" cy="177" r="3" fill="#8a8f98"/>')
    s.append('<text x="30" y="205" font-size="12" fill="#4a4f57">BANDA TRANSPORTADORA</text>')

    def vaso(x, y, lleno=True, tapa=False, fill=0.8):
        g = f'<rect x="{x}" y="{y}" width="34" height="46" fill="#e7f0f0" stroke="{INK}" stroke-width="1.5" rx="3"/>'
        if lleno:
            g += f'<rect x="{x+2}" y="{y+46-44*fill:.0f}" width="30" height="{44*fill:.0f}" fill="#c9a24a" opacity=".85"/>'
        if tapa:
            g += f'<rect x="{x-3}" y="{y-6}" width="40" height="7" fill="{ORANGE}" stroke="{INK}" stroke-width="1.2"/>'
        return g

    # vaso en llenado bajo el contador
    s.append(f'<rect x="40" y="40" width="130" height="56" fill="#e8e2d3" stroke="{INK}" stroke-width="1.5"/>'
             f'<text x="105" y="62" text-anchor="middle" font-size="12" fill="{INK}">CONTADOR</text>'
             f'<text x="105" y="82" text-anchor="middle" font-size="14" font-weight="600" fill="{ORANGE}">{v["monedas"]}/{v["capacidad"]}</text>')
    s.append(vaso(88, 124, True, False, v["monedas"] / v["capacidad"]))
    # en banda
    for i in range(e["en_banda"]):
        s.append(vaso(190 + i * 70, 124))
    # estación de tapado
    s.append(f'<rect x="600" y="70" width="6" height="110" fill="{INK}"/>')
    s.append(f'<rect x="600" y="70" width="70" height="8" fill="{INK}"/>')
    s.append(f'<path d="M 640 78 L 690 40 L 740 60" stroke="{ORANGE}" stroke-width="10" fill="none" stroke-linecap="round"/>')
    s.append(f'<circle cx="640" cy="78" r="9" fill="{INK}"/><circle cx="690" cy="40" r="7" fill="{INK}"/>')
    s.append('<text x="600" y="205" font-size="12" fill="#4a4f57">TAPADO (BRAZO)</text>')
    if e["en_tapa"]:
        s.append(vaso(612, 124, True, True))
        s.append(f'<path d="M 725 66 L 735 92" stroke="{INK}" stroke-width="3"/>')
    # listos
    for i in range(e["listos"]):
        s.append(vaso(700 + (i % 4) * 46, 226 - (i // 4) * 0, True, True))
    s.append(f'<text x="700" y="290" font-size="12" fill="#4a4f57">LISTOS PARA EL DRON ({e["listos"]})</text>')
    s.append("</svg>")
    st.markdown("".join(s), unsafe_allow_html=True)
    c = st.columns(3)
    c[0].markdown(plate("En banda", e["en_banda"], f"~{T_BANDA:.0f} s de trayecto"), unsafe_allow_html=True)
    c[1].markdown(plate("En tapado", e["en_tapa"], f"~{T_TAPA:.0f} s por vaso"), unsafe_allow_html=True)
    c[2].markdown(plate("Listos", e["listos"], f"el dron carga {DRON_CARGA} por viaje"), unsafe_allow_html=True)


def vista_dron(est):
    d = est["dron"]
    a, b = st.columns([2.2, 1])
    with a:
        st.plotly_chart(fig_pista(d), width="stretch", key="pista_dron")
    with b:
        st.markdown(plate("Estado", d["estado"].upper(), f'carga: {d["vasos_cargados"]} vasos'), unsafe_allow_html=True)
        st.write("")
        st.markdown(plate("Obstáculos superados", f'{d["obstaculos_superados"]} / 3', "Ubicados al 25 %, 55 % y 82 % del trazado"),
                    unsafe_allow_html=True)
        st.write("")
        st.markdown(plate("Entregados en meta", d["entregados"], "vasos"), unsafe_allow_html=True)
        st.progress(min(1.0, d["progreso"]), text=f'{d["progreso"]*100:.0f} % del recorrido')
        if d["estado"] == "meta":
            st.success("¡Llegó a la meta!")


def vista_monedas():
    st.markdown("#### Diámetros reales, antigua vs. nueva (a escala 1 mm = 5 px)")
    st.caption("Las imágenes están a escala: puedes poner una moneda física sobre la pantalla para compararla. "
               "Datos: Banco de la República.")
    for denom in (50, 100, 200, 500, 1000):
        grupo = [c for c in CATALOGO if c.denom == denom]
        cel = ""
        for c in sorted(grupo, key=lambda c: c.serie):
            cel += (f'<div class="coincell">{coin_svg(c, 5)}<br><b>{c.serie.upper()}</b><br>{c.d} mm · {c.w} g<br>'
                    f'esp. {c.esp} mm</div>')
        st.markdown(f'<div class="plate" style="margin-bottom:10px"><div class="lbl">Moneda de ${denom}</div>'
                    f'<div class="coinrow">{cel}</div></div>', unsafe_allow_html=True)
    df = pd.DataFrame([{"Moneda": c.label, "Diámetro (mm)": c.d, "Espesor (mm)": c.esp, "Peso (g)": c.w, "Composición": c.metal}
                       for c in CATALOGO])
    st.dataframe(df, hide_index=True, width="stretch")
    st.info("**Caso crítico $500:** antigua 23.5 mm / 7.40 g vs nueva 23.7 mm / 7.14 g. El diámetro casi no ayuda; "
            "se separan por peso (Δ≈0.26 g) y por el núcleo bimetálico. Necesita una celda de carga bien calibrada. "
            "La $1000 de la serie antigua no está en el catálogo.")


@st.cache_data
def _aco(n, hormigas, iters, alfa, beta, rho, seed):
    co, val = aco.generar_vasos(n, seed)
    return co, val, aco.resolver(co, hormigas, iters, alfa, beta, rho, seed=seed)


def vista_aco():
    st.markdown("#### Recolección de vasos con colonia de hormigas (ACO)")
    st.caption("Cada hormiga construye un recorrido base → todos los vasos → meta. Las mejores rutas depositan más feromona.")
    c = st.columns(6)
    n = c[0].slider("Vasos", 4, 14, 8)
    hormigas = c[1].slider("Hormigas", 5, 50, 20)
    iters = c[2].slider("Iteraciones", 10, 150, 60)
    alfa = c[3].slider("α (feromona)", 0.5, 3.0, 1.0, 0.1)
    beta = c[4].slider("β (distancia)", 1.0, 6.0, 3.0, 0.5)
    rho = c[5].slider("ρ evaporación", 0.1, 0.9, 0.4, 0.05)
    seed = st.number_input("Semilla", 0, 999, 7)
    co, val, res = _aco(n, hormigas, iters, alfa, beta, rho, int(seed))
    a, b = st.columns([1.3, 1])
    with a:
        f = go.Figure()
        tau = res["tau"]
        mx = tau.max()
        for i in range(len(co)):
            for j in range(i + 1, len(co)):
                w = tau[i, j] / mx
                if w > 0.12:
                    f.add_scatter(x=[co[i, 0], co[j, 0]], y=[co[i, 1], co[j, 1]], mode="lines",
                                  line=dict(color=f"rgba(31,111,107,{min(.7, w):.2f})", width=1 + 5 * w),
                                  hoverinfo="skip", showlegend=False)
        r = res["ruta"]
        f.add_scatter(x=co[r, 0], y=co[r, 1], mode="lines", line=dict(color=ORANGE, width=3), name="Mejor ruta")
        f.add_scatter(x=co[1:-1, 0], y=co[1:-1, 1], mode="markers+text", text=[cop(v) for v in val],
                      textposition="top center", marker=dict(size=16, color="#c9a24a", line=dict(color=INK, width=2)),
                      name="Vasos", textfont=dict(family="IBM Plex Mono", size=10))
        f.add_scatter(x=[co[0, 0]], y=[co[0, 1]], mode="markers+text", text=["BASE"], textposition="middle right",
                      marker=dict(size=14, color=TEAL, symbol="square"), name="Base")
        f.add_scatter(x=[co[-1, 0]], y=[co[-1, 1]], mode="markers+text", text=["META"], textposition="middle left",
                      marker=dict(size=18, color=ORANGE, symbol="star"), name="Meta")
        f.update_layout(height=430, margin=dict(l=0, r=0, t=6, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#faf7f0",
                        xaxis=dict(visible=False, range=[-0.05, 1.05]), yaxis=dict(visible=False, range=[0, 1]),
                        legend=dict(orientation="h", y=-0.02))
        st.plotly_chart(f, width="stretch")
    with b:
        st.markdown(plate("Longitud de la mejor ruta", f'{res["L"]:.3f}', "unidades de plano (0-1)"), unsafe_allow_html=True)
        st.write("")
        st.markdown(plate("Valor recolectado", cop(int(val.sum())), f"{n} vasos"), unsafe_allow_html=True)
        st.write("")
        g = go.Figure()
        g.add_scatter(y=res["mejor"], name="Mejor", line=dict(color=ORANGE, width=2.5))
        g.add_scatter(y=res["media"], name="Media de la colonia", line=dict(color=TEAL, width=1.5, dash="dot"))
        g.update_layout(height=250, margin=dict(l=0, r=0, t=6, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        xaxis=dict(title="iteración"), yaxis=dict(title="longitud", gridcolor="#d9d2c0"),
                        legend=dict(orientation="h", y=1.15), font=dict(family="IBM Plex Mono", size=11))
        st.plotly_chart(g, width="stretch")
        st.write("Orden: " + " → ".join("Base" if i == 0 else "Meta" if i == len(co) - 1 else f"V{i}" for i in res["ruta"]))


# ---------------------------------------------------------------- chatbot
def responder(q: str, est: dict | None) -> str:
    if est is None:
        return "No tengo datos del ESP32 en este momento. Revisa la conexión en la barra lateral."
    ql = q.lower()
    cont, dron, emb = est["contador"], est["dron"], est["embalaje"]
    r = resumen(cont["conteo"])
    peso = cont.get("peso_g", r["peso_monedas_g"])
    partes = []
    if any(w in ql for w in ("valor", "dinero", "plata", "cuánto", "cuanto", "total")):
        partes.append(f"Se han procesado {cop(r['valor'])} en {r['cantidad']} monedas.")
    if any(w in ql for w in ("peso", "gramos", "pesa")):
        partes.append(f"El peso acumulado de las monedas es {peso:.1f} gramos.")
    if any(w in ql for w in ("cantidad", "cuántas", "cuantas", "monedas")) and not partes:
        partes.append(f"Van {r['cantidad']} monedas contadas y {cont['rechazadas']} rechazadas.")
    if any(w in ql for w in ("nueva", "antigua", "vieja", "serie")):
        n = sum(v for k, v in cont["conteo"].items() if k.endswith("nueva"))
        a = sum(v for k, v in cont["conteo"].items() if k.endswith("antigua"))
        partes.append(f"Hay {n} monedas de la serie nueva y {a} de la antigua.")
    for d in (50, 100, 200, 500, 1000):
        if str(d) in ql:
            n = cont["conteo"].get(f"{d}_nueva", 0) + cont["conteo"].get(f"{d}_antigua", 0)
            partes.append(f"De ${d} hay {n} monedas: {cont['conteo'].get(f'{d}_nueva',0)} nuevas y "
                          f"{cont['conteo'].get(f'{d}_antigua',0)} antiguas.")
    if any(w in ql for w in ("dron", "ruta", "pista", "meta", "obst")):
        partes.append(f"El dron está en estado {dron['estado']}, al {dron['progreso']*100:.0f} por ciento de la ruta, "
                      f"con {dron['obstaculos_superados']} de 3 obstáculos superados y {dron['entregados']} vasos entregados.")
    if any(w in ql for w in ("vaso", "banda", "tapa", "embalaje", "brazo")):
        partes.append(f"Hay {emb['en_banda']} vasos en la banda, {emb['en_tapa']} en tapado y {emb['listos']} listos. "
                      f"El brazo está {emb['brazo']}. En total se han llenado {emb['vasos_totales']} vasos.")
    if any(w in ql for w in ("resumen", "estado", "proyecto", "todo", "hola")) or not partes:
        partes = [f"Resumen: {cop(r['valor'])} procesados, {r['cantidad']} monedas, {peso:.1f} gramos. "
                  f"Dron {dron['estado']} al {dron['progreso']*100:.0f} por ciento; {emb['vasos_totales']} vasos empacados."]
    return " ".join(partes)


def voz_html(texto: str) -> str:
    return f"""
<div style="font-family:IBM Plex Mono,monospace;font-size:12px">
<button id="b" style="cursor:pointer;padding:5px 12px;border:1.5px solid #1d2430;background:#faf7f0;border-radius:2px">🔊 Escuchar</button>
</div>
<script>
const t = {json.dumps(texto)};
function hablar() {{
  try {{
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(t); u.lang = 'es-CO'; u.rate = 1.0;
    const v = speechSynthesis.getVoices().find(v => v.lang.startsWith('es'));
    if (v) u.voice = v;
    speechSynthesis.speak(u);
  }} catch (e) {{}}
}}
document.getElementById('b').onclick = hablar;
hablar();
</script>"""


def vista_chat():
    est, err = obtener_estado()
    for m in st.session_state.chat:
        with st.chat_message(m["role"]):
            st.write(m["content"])
    q = st.chat_input("Pregunta por el valor, peso, cantidad, dron, banda…")
    if q:
        ans = responder(q, est)
        st.session_state.chat += [{"role": "user", "content": q}, {"role": "assistant", "content": ans}]
        st.session_state.speak = ans
        st.rerun()
    if st.session_state.speak and voz:
        st.iframe(voz_html(st.session_state.speak), height=40)
    with st.expander("Datos crudos que recibe la app"):
        st.json(est or {"error": err})


def vista_arquitectura():
    st.markdown("#### Arquitectura del sistema")
    st.graphviz_chart("""
digraph G {
  rankdir=LR; bgcolor="transparent"; node [shape=box, style="filled", fillcolor="#faf7f0", color="#1d2430", fontname="Helvetica"];
  edge [color="#1d2430"];
  mon [label="Contador de monedas\\n(slider diámetro + HX711)"];
  esp [label="ESP32\\nclasifica + servidor HTTP", fillcolor="#f0c9a8"];
  banda [label="Banda + brazo de tapado\\n(motor DC / servos)"];
  dron [label="Dron\\n(pista, 3 obstáculos)"];
  st [label="Streamlit\\nDashboard + chatbot", fillcolor="#bcd9d6"];
  mon -> esp; esp -> banda; banda -> dron; dron -> esp [style=dashed, label="telemetría"];
  esp -> st [label="WiFi  GET /data (JSON)"];
}""")
    st.markdown("""
**Flujo de datos:** el ESP32 mide diámetro y peso de cada moneda, la clasifica (serie nueva/antigua), cuenta y publica
un JSON en `/data`. La app lo consulta cada segundo. Con *Simulador interno* la app genera el mismo JSON.

**Requerimientos no funcionales sugeridos:** latencia de actualización ≤ 2 s, precisión de clasificación ≥ 98 %,
reconexión automática al perder WiFi, alimentación 5 V / 2 A compartida con tierra común entre motores y ESP32.
""")
    st.markdown("#### Contrato JSON del ESP32")
    st.code(json.dumps(Simulador(1).estado(), indent=2), language="json")


# ---------------------------------------------------------------- layout
st.markdown('<div class="kicker">Micros · Proyecto de logística · ESP32 + Streamlit</div>', unsafe_allow_html=True)
st.title("Sistema logístico de monedas colombianas")
_est, _err = obtener_estado()
st.markdown(
    f'<span class="tag {"on" if not _err else "warn"}">{"EN LÍNEA" if not _err else "SIN CONEXIÓN"}</span> '
    f'<span class="tag off">{fuente}{" · " + host if fuente != "Simulador interno" else ""}</span>',
    unsafe_allow_html=True,
)
st.write("")
tabs = st.tabs(["Panel en vivo", "Contador", "Transporte y embalaje", "Dron y pista", "Monedas (escala real)",
                "Recolección ACO", "Asistente", "Arquitectura"])
with tabs[0]:
    fragmento(vista_panel)()
with tabs[1]:
    fragmento(vista_contador)()
with tabs[2]:
    fragmento(vista_transporte)()
with tabs[3]:
    fragmento(vista_dron)()
with tabs[4]:
    vista_monedas()
with tabs[5]:
    vista_aco()
with tabs[6]:
    vista_chat()
with tabs[7]:
    vista_arquitectura()

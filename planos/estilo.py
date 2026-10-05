"""Utilidades de dibujo técnico para los planos (matplotlib): láminas 16:9, cajetín y cotas."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon, Ellipse, FancyBboxPatch

INK = "#1d2430"
CAD = "#1f6f6b"      # cotas
ACC = "#b8480f"      # resaltes
GRIS = "#8891a0"
PAPEL = "#faf7f0"
FIG = (19.2, 10.8)
DPI = 100
FECHA = "2026-10-04"
GRUPO = "[Integrantes del grupo]"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": INK,
    "text.color": INK,
    "figure.facecolor": PAPEL,
    "savefig.facecolor": PAPEL,
})


def lamina(titulo: str, numero: str, escala: str = "s/e", subtitulo: str = ""):
    """Figura 16:9 con marco, título arriba y cajetín abajo a la derecha."""
    fig = plt.figure(figsize=FIG, dpi=DPI)
    marco = fig.add_axes([0.005, 0.01, 0.99, 0.98])
    marco.set_xlim(0, 1); marco.set_ylim(0, 1); marco.axis("off")
    marco.add_patch(Rectangle((0, 0), 1, 1, fill=False, ec=INK, lw=2.0))
    fig.text(0.02, 0.955, titulo, fontsize=22, fontweight="bold", va="center")
    if subtitulo:
        fig.text(0.02, 0.918, subtitulo, fontsize=12, color=GRIS, va="center")
    # cajetín
    x0, y0, w, h = 0.745, 0.013, 0.248, 0.082
    marco.add_patch(Rectangle((x0 - 0.005, y0 - 0.003), w, h, fill=True, fc="white", ec=INK, lw=1.3))
    xx = x0 - 0.005
    marco.plot([xx, xx + w], [y0 - 0.003 + h / 2, y0 - 0.003 + h / 2], color=INK, lw=0.8)
    marco.plot([xx + 0.15, xx + 0.15], [y0 - 0.003, y0 - 0.003 + h], color=INK, lw=0.8)
    fig.text(xx + 0.006, y0 + h * 0.72, "ENJAMBRE DE CARRITOS HORMIGA", fontsize=9, fontweight="bold")
    fig.text(xx + 0.006, y0 + h * 0.23, f"Lám. {numero}  ·  Esc. {escala}  ·  mm", fontsize=8.5)
    fig.text(xx + 0.156, y0 + h * 0.72, f"Fecha {FECHA}", fontsize=8.5)
    fig.text(xx + 0.156, y0 + h * 0.23, GRUPO, fontsize=8.5)
    return fig


def vista(fig, rect, xlim, ylim, titulo=None, invert_y=False):
    """Eje con escala 1:1 en mm. rect = [l, b, w, h] en fracción de figura."""
    ax = fig.add_axes(rect)
    ax.set_xlim(*xlim); ax.set_ylim(*(ylim[::-1] if invert_y else ylim))
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    if titulo:
        ax.set_title(titulo, fontsize=12, fontweight="bold", loc="left", color=INK, pad=6)
    return ax


def rect(ax, x, y, w, h, fc="white", ec=INK, lw=1.0, ls="-", z=2, alpha=1.0, **kw):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=lw, ls=ls, zorder=z, alpha=alpha, **kw))


def rectc(ax, cx, cy, w, h, **kw):
    rect(ax, cx - w / 2, cy - h / 2, w, h, **kw)


def circ(ax, cx, cy, r, fc="white", ec=INK, lw=1.0, ls="-", z=2, **kw):
    ax.add_patch(Circle((cx, cy), r, fc=fc, ec=ec, lw=lw, ls=ls, zorder=z, **kw))


def texto(ax, x, y, s, fs=9, ha="center", va="center", color=INK, bold=False, bg=None, z=10, rot=0):
    bb = dict(fc=bg, ec="none", pad=1.2) if bg else None
    ax.text(x, y, s, fontsize=fs, ha=ha, va=va, color=color, fontweight="bold" if bold else "normal",
            bbox=bb, zorder=z, rotation=rot)


def flecha(ax, p, q, color=INK, lw=1.0, estilo="->", z=9, ls="-"):
    ax.annotate("", xy=q, xytext=p, zorder=z,
                arrowprops=dict(arrowstyle=estilo, color=color, lw=lw, shrinkA=0, shrinkB=0, ls=ls))


def cota_h(ax, x1, x2, y, s, ext=(None, None), off_txt=0, fs=9.5, color=CAD):
    """Cota horizontal entre x1 y x2 a la altura y. ext = (y_ref1, y_ref2): líneas de extensión."""
    for xi, yr in zip((x1, x2), ext):
        if yr is not None:
            ax.plot([xi, xi], [yr, y], color=color, lw=0.7, zorder=8)
    flecha(ax, (x1, y), (x2, y), color=color, lw=1.1, estilo="<->")
    texto(ax, (x1 + x2) / 2, y + off_txt, s, fs=fs, color=color, bg="white", bold=True)


def cota_v(ax, x, y1, y2, s, ext=(None, None), off_txt=0, fs=9.5, color=CAD, rot=90):
    for yi, xr in zip((y1, y2), ext):
        if xr is not None:
            ax.plot([xr, x], [yi, yi], color=color, lw=0.7, zorder=8)
    flecha(ax, (x, y1), (x, y2), color=color, lw=1.1, estilo="<->")
    texto(ax, x + off_txt, (y1 + y2) / 2, s, fs=fs, color=color, bg="white", bold=True, rot=rot)


def llamada(ax, punto, destino, s, fs=9, ha="left", color=INK):
    """Etiqueta con línea de guía desde 'punto' (en el dibujo) hasta 'destino' (texto)."""
    ax.plot([punto[0], destino[0]], [punto[1], destino[1]], color=color, lw=0.8, zorder=9)
    circ(ax, punto[0], punto[1], 1.2, fc=color, ec=color, z=11)
    texto(ax, destino[0] + (2 if ha == "left" else -2), destino[1], s, fs=fs, ha=ha, bg="white")


def guardar(fig, nombre):
    fig.savefig(f"{nombre}.png", dpi=DPI)
    fig.savefig(f"{nombre}.pdf")
    plt.close(fig)


def globo(ax, x, y, n, dx=0.0, dy=0.0, r=5.2, fs=9, color=INK):
    """Globo numerado de plano de ensamble: círculo con número unido por una línea al punto (x, y)."""
    gx, gy = x + dx, y + dy
    if dx or dy:
        ax.plot([x, gx], [y, gy], color=color, lw=0.8, zorder=11)
    circ(ax, x, y, 1.1, fc=color, ec=color, z=12)
    circ(ax, gx, gy, r, fc="white", ec=color, lw=1.1, z=13)
    ax.text(gx, gy, str(n), fontsize=fs, ha="center", va="center", color=color, fontweight="bold", zorder=14)


def leyenda(fig, rect_, titulo, items, fs=10.5, col=1, paso=0.115, dx_texto=0.05):
    """Lista numerada (globo -> descripción) en un eje propio. items = [(n, texto)]."""
    ax = fig.add_axes(rect_); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.text(0.0, 0.98, titulo, fontsize=fs + 1.5, fontweight="bold", va="top")
    por_col = (len(items) + col - 1) // col
    for i, (n, t) in enumerate(items):
        c, r = divmod(i, por_col)
        x = c / col
        y = 0.86 - r * paso
        ax.text(x + 0.018, y, str(n), fontsize=fs - 1, ha="center", va="center", fontweight="bold",
                bbox=dict(boxstyle="circle,pad=0.28", fc="white", ec=INK, lw=1.0))
        ax.text(x + dx_texto, y, t, fontsize=fs, va="center")
    return ax

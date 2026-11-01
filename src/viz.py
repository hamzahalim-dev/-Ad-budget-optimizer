"""viz.py — Shared chart style and helpers (consistent look across notebooks)."""
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

PLATFORM_COLORS = {"Facebook": "#1877F2", "Instagram": "#C13584", "Google": "#34A853",
                   "TikTok": "#222222", "YouTube": "#FF0000"}
PLATFORM_ORDER = list(PLATFORM_COLORS)
NEUTRAL = "#9AA3B2"
ACCENT = "#2F3B52"


def apply_style():
    plt.rcParams.update({
        "figure.dpi": 110, "savefig.dpi": 150, "savefig.bbox": "tight",
        "figure.facecolor": "white", "axes.facecolor": "white",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.alpha": 0.3, "axes.axisbelow": True,
        "axes.titleweight": "bold", "axes.titlesize": 11, "font.size": 10,
    })


def colors_for(names):
    return [PLATFORM_COLORS.get(n, NEUTRAL) for n in names]


def platform_legend(ax, **kw):
    ax.legend(handles=[Patch(color=c, label=p) for p, c in PLATFORM_COLORS.items()], **kw)


def save(fig, folder, name):
    path = Path(folder) / f"{name}.png"
    fig.savefig(path, facecolor="white")
    return path

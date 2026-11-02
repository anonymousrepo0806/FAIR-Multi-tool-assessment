import os
import matplotlib.pyplot as plt
import matplotlib.figure as mfigure
from matplotlib.colors import LinearSegmentedColormap

BLUE = "#0072B2"
ORANGE = "#E69F00"
GREEN = "#009E73"
SKY = "#56B4E9"
VERMILLION = "#D55E00"
PURPLE = "#CC79A7"
INK = "#222222"
MUTED = "#BBBBBB"
GRID = "#E6E6E6"
BASE = "#F7F7F7"

TOOL_COLOR = {"FAIR-Checker": BLUE, "F-UJI": ORANGE, "KGHeartBeat": GREEN,
              "FC": BLUE, "FU": ORANGE, "KG": GREEN}
PAIR_COLOR = {"FC-FU": PURPLE, "FC-KG": SKY, "FU-KG": VERMILLION}
DIM_COLOR = {"F": SKY, "A": ORANGE, "I": GREEN, "R": PURPLE}
FAIL = VERMILLION
PASS = BLUE
UP = BLUE
DOWN = VERMILLION

DIVERGING = LinearSegmentedColormap.from_list("oi_diverging", [VERMILLION, BASE, BLUE])
SEQUENTIAL = LinearSegmentedColormap.from_list("oi_sequential", [BASE, BLUE])
FAIL_SEQ = LinearSegmentedColormap.from_list("oi_fail", [BASE, VERMILLION])
PASS_SEQ = SEQUENTIAL


def apply():
    if os.environ.get("EXTRA_FIGURES") != "1":
        mfigure.Figure.savefig = lambda self, *args, **kwargs: None
    plt.rcParams.update({"font.size": 7, "font.family": "DejaVu Sans", "axes.linewidth": 0.5,
                         "axes.edgecolor": INK, "xtick.color": INK, "ytick.color": INK,
                         "axes.labelcolor": INK, "text.color": INK, "pdf.fonttype": 42})


def light(color, alpha="40"):
    return color + alpha

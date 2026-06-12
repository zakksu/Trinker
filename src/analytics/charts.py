"""
Matplotlib trend charts for Dashboard Performance Hub.
"""

from __future__ import annotations

from PySide6.QtGui import QImage, QPixmap

try:
    import io

    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    _MPL_OK = True
except Exception:
    _MPL_OK = False

PALETTE = ["#c9a227", "#6aab55", "#d4843a", "#9b7bb8", "#4a7ab8", "#c45c5c"]


def charts_available() -> bool:
    return _MPL_OK


def _render_fig(fig: Figure) -> QPixmap:
    canvas = FigureCanvasAgg(fig)
    buf = io.BytesIO()
    canvas.draw()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), dpi=100)
    buf.seek(0)
    return QPixmap.fromImage(QImage.fromData(buf.read()))


def _dark_fig(width=7.5, height=2.8) -> tuple[Figure, object]:
    fig = Figure(figsize=(width, height), facecolor="#1e1812")
    ax = fig.add_subplot(111, facecolor="#2e261c")
    ax.tick_params(colors="#b8a88a", labelsize=8)
    ax.spines[:].set_color("#6b4c3b")
    ax.grid(True, alpha=0.15, color="#6b4c3b")
    return fig, ax


def render_feudal_trend(trend: list[dict]) -> QPixmap | None:
    if not _MPL_OK or not trend:
        return None
    fig, ax = _dark_fig()
    xs = list(range(len(trend)))
    ys = [
        t.get("feudal_time_sec") or t.get("feudal_sec") or 0 for t in reversed(trend)
    ]
    ax.plot(xs, ys, color=PALETTE[0], marker="o", linewidth=2, markersize=4)
    ax.set_ylabel("Feudal (sec)", color="#b8a88a", fontsize=9)
    ax.set_title("Feudal Time Trend", color="#e8c547", fontsize=10, pad=8)
    ax.invert_yaxis()
    pix = _render_fig(fig)
    plt.close(fig)
    return pix


def render_accuracy_trend(trend: list[dict]) -> QPixmap | None:
    if not _MPL_OK or not trend:
        return None
    fig, ax = _dark_fig()
    xs = list(range(len(trend)))
    ys = [float(t.get("accuracy_pct") or 0) for t in reversed(trend)]
    ax.plot(xs, ys, color=PALETTE[1], marker="s", linewidth=2, markersize=4)
    ax.set_ylabel("Accuracy %", color="#b8a88a", fontsize=9)
    ax.set_ylim(0, 100)
    ax.set_title("Accuracy Trend", color="#e8c547", fontsize=10, pad=8)
    pix = _render_fig(fig)
    plt.close(fig)
    return pix


def render_win_rate_bar(stats_by_result: dict[str, int]) -> QPixmap | None:
    if not _MPL_OK or not stats_by_result:
        return None
    fig, ax = _dark_fig(height=2.2)
    labels = list(stats_by_result.keys())
    vals = list(stats_by_result.values())
    def _bar_color(key: str) -> str:
        if key == "win":
            return PALETTE[1]
        if key == "loss":
            return PALETTE[5]
        if key == "practice":
            return PALETTE[2]
        return PALETTE[3]

    colors = [_bar_color(k) for k in labels]
    ax.bar(labels, vals, color=colors, edgecolor="#6b4c3b")
    ax.set_title("Results Breakdown", color="#e8c547", fontsize=10, pad=8)
    pix = _render_fig(fig)
    plt.close(fig)
    return pix

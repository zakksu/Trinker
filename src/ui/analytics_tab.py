"""
TRINKER - Analytics Dashboard Tab
Rich data visualization for practice session history:
  - Overview stats (win rate, avg timings, improvement trends)
  - Session history table with filters
  - Personal bests and progress charts
  - Heatmap of practice activity
  - Export to CSV/JSON
  - AI coaching recommendations
"""

from datetime import date, timedelta
from typing import Optional

from PySide6.QtCore import Qt, QThread, QObject, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QGroupBox, QFormLayout, QTabWidget, QTextEdit, QFrame,
    QDateEdit, QCheckBox, QSizePolicy, QScrollArea,
)
from PySide6.QtCore import QDate

from ..analytics.session import (
    get_sessions, get_summary_stats, get_feudal_time_trend,
    get_accuracy_trend, get_most_practiced_builds, get_activity_heatmap,
    delete_session,
)
from ..analytics.exporter import export_sessions_csv, export_sessions_json
from ..build_orders.manager import get_all_build_orders
from ..core.logger import logger

try:
    import matplotlib
    matplotlib.use("Qt5Agg" if False else "Agg")   # use Agg backend, embed via QLabel
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    import io
    from PySide6.QtGui import QPixmap, QImage
    _MPL_OK = True
except Exception:
    _MPL_OK = False

STYLE = """
QWidget { background: #111113; color: #ecf0f1; }
QTableWidget {
    background: #15151a; border: 1px solid #2c2c2e;
    gridline-color: #1e1e22; border-radius: 6px;
}
QTableWidget::item { padding: 5px 8px; }
QTableWidget::item:selected { background: #1c3a5c; }
QHeaderView::section {
    background: #1e1e22; color: #7f8c8d;
    border: none; padding: 5px 8px; font-size: 11px; letter-spacing: 1px;
}
QGroupBox {
    border: 1px solid #2c2c2e; border-radius: 8px;
    margin-top: 10px; padding: 10px 8px 8px 8px;
}
QGroupBox::title { color: #7f8c8d; padding: 0 8px; font-size: 11px; letter-spacing: 1px; }
QComboBox, QDateEdit {
    background: #1e1e22; border: 1px solid #2c2c2e;
    border-radius: 6px; padding: 4px 8px; color: #ecf0f1;
}
QPushButton {
    background: #1e1e22; border: 1px solid #2c2c2e;
    border-radius: 6px; padding: 6px 14px; color: #ecf0f1;
}
QPushButton:hover { background: #25252c; border-color: #3498db; }
QTabWidget::pane { border: 1px solid #2c2c2e; border-radius: 6px; }
QTabBar::tab { background: #1e1e22; color: #7f8c8d; padding: 8px 16px; border-radius: 4px; margin-right: 2px; }
QTabBar::tab:selected { background: #1c3a5c; color: #3498db; }
QTextEdit { background: #1a1a20; border: 1px solid #2c2c2e; border-radius: 6px; color: #ecf0f1; }
"""

PALETTE = ["#3498db", "#2ecc71", "#e74c3c", "#f1c40f", "#9b59b6", "#1abc9c"]


def _sec_to_mmss(sec) -> str:
    if sec is None:
        return "—"
    sec = int(sec)
    return f"{sec // 60}:{sec % 60:02d}"


def _pct(val) -> str:
    if val is None:
        return "—"
    return f"{float(val):.1f}%"


# ---------------------------------------------------------------------------
# Matplotlib chart rendering helper (renders to QPixmap, embeds in QLabel)
# ---------------------------------------------------------------------------

def _render_chart(fig: "Figure") -> "QPixmap":
    """Render a matplotlib figure to a QPixmap for display in Qt."""
    canvas = FigureCanvasAgg(fig)
    buf = io.BytesIO()
    canvas.draw()
    fig.savefig(buf, format="png", bbox_inches="tight",
                facecolor=fig.get_facecolor(), dpi=100)
    buf.seek(0)
    data = buf.read()
    qimg = QImage.fromData(data)
    return QPixmap.fromImage(qimg)


def _dark_fig(width=8, height=3.5):
    """Return a matplotlib Figure with dark background."""
    fig = Figure(figsize=(width, height), facecolor="#111113")
    ax  = fig.add_subplot(111, facecolor="#1a1a20")
    ax.tick_params(colors="#7f8c8d")
    ax.spines[:].set_color("#2c2c2e")
    ax.xaxis.label.set_color("#7f8c8d")
    ax.yaxis.label.set_color("#7f8c8d")
    ax.title.set_color("#ecf0f1")
    return fig, ax


# ---------------------------------------------------------------------------
# Stat card widget
# ---------------------------------------------------------------------------

class StatCard(QFrame):
    def __init__(self, title: str, value: str = "—", color: str = "#3498db", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: #1a1a20; border: 1px solid #2c2c2e;
                border-radius: 10px; padding: 8px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        self.lbl_val = QLabel(value)
        self.lbl_val.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold; font-family: monospace;")
        self.lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("color: #7f8c8d; font-size: 11px; letter-spacing: 1px;")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.lbl_val)
        layout.addWidget(self.lbl_title)

    def set_value(self, value: str) -> None:
        self.lbl_val.setText(value)


# ---------------------------------------------------------------------------
# AI recommendation worker
# ---------------------------------------------------------------------------

class _AIWorker(QObject):
    finished = Signal(str)
    error    = Signal(str)

    def __init__(self, stats: dict, mistakes: list):
        super().__init__()
        self.stats   = stats
        self.mistakes = mistakes

    def run(self) -> None:
        try:
            from ..ai_coach.coach import get_build_recommendations
            result = get_build_recommendations(self.stats, self.mistakes)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# Analytics Tab
# ---------------------------------------------------------------------------

class AnalyticsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLE)
        self._ai_thread = None
        self._ai_worker = None
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ── Top tabs ──────────────────────────────────────────────────────
        tabs = QTabWidget()
        tabs.addTab(self._build_overview_tab(), "Overview")
        tabs.addTab(self._build_history_tab(), "Session History")
        tabs.addTab(self._build_charts_tab(), "Progress Charts")
        tabs.addTab(self._build_leaderboard_tab(), "Most Practiced")
        tabs.addTab(self._build_ai_tab(), "AI Coach")
        root.addWidget(tabs)

    # ── Overview tab ──────────────────────────────────────────────────────

    def _build_overview_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Filter row
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Build Order:"))
        self.cb_bo_filter = QComboBox()
        self.cb_bo_filter.addItem("All builds", None)
        self.cb_bo_filter.currentIndexChanged.connect(self._refresh_overview)
        filter_row.addWidget(self.cb_bo_filter)
        filter_row.addStretch()
        btn_refresh = QPushButton("↺ Refresh")
        btn_refresh.clicked.connect(self.refresh)
        filter_row.addWidget(btn_refresh)
        layout.addLayout(filter_row)

        # Stat cards row
        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)
        self.card_sessions  = StatCard("SESSIONS", "0", "#3498db")
        self.card_winrate   = StatCard("WIN RATE", "—", "#2ecc71")
        self.card_feudal    = StatCard("AVG FEUDAL", "—", "#e67e22")
        self.card_castle    = StatCard("AVG CASTLE", "—", "#9b59b6")
        self.card_accuracy  = StatCard("AVG ACCURACY", "—", "#1abc9c")
        self.card_days      = StatCard("PRACTICE DAYS", "0", "#f1c40f")
        for card in [self.card_sessions, self.card_winrate, self.card_feudal,
                     self.card_castle, self.card_accuracy, self.card_days]:
            cards_row.addWidget(card)
        layout.addLayout(cards_row)

        # Heatmap placeholder
        heatmap_group = QGroupBox("Practice Activity")
        heatmap_layout = QVBoxLayout(heatmap_group)
        self.lbl_heatmap = QLabel("Loading…")
        self.lbl_heatmap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_heatmap.setMinimumHeight(80)
        heatmap_layout.addWidget(self.lbl_heatmap)
        layout.addWidget(heatmap_group)

        layout.addStretch()
        return w

    def _build_history_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Filters
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Result:"))
        self.cb_hist_result = QComboBox()
        self.cb_hist_result.addItems(["All", "win", "loss", "draw", "practice"])
        self.cb_hist_result.currentTextChanged.connect(self._refresh_history)

        filter_row.addWidget(self.cb_hist_result)
        filter_row.addSpacing(16)
        filter_row.addWidget(QLabel("From:"))
        self.de_from = QDateEdit(QDate.currentDate().addDays(-90))
        self.de_from.setCalendarPopup(True)
        filter_row.addWidget(self.de_from)
        filter_row.addWidget(QLabel("To:"))
        self.de_to = QDateEdit(QDate.currentDate())
        self.de_to.setCalendarPopup(True)
        filter_row.addWidget(self.de_to)
        btn_apply = QPushButton("Apply")
        btn_apply.clicked.connect(self._refresh_history)
        filter_row.addWidget(btn_apply)
        filter_row.addStretch()

        btn_csv  = QPushButton("⬇ CSV")
        btn_csv.clicked.connect(lambda: self._export("csv"))
        btn_json = QPushButton("⬇ JSON")
        btn_json.clicked.connect(lambda: self._export("json"))
        btn_del  = QPushButton("🗑 Delete")
        btn_del.setStyleSheet("QPushButton { color: #e74c3c; }")
        btn_del.clicked.connect(self._on_delete_session)
        filter_row.addWidget(btn_csv)
        filter_row.addWidget(btn_json)
        filter_row.addWidget(btn_del)
        layout.addLayout(filter_row)

        # Table
        self.history_table = QTableWidget(0, 8)
        self.history_table.setHorizontalHeaderLabels([
            "Date", "Build Order", "Duration", "Feudal", "Castle", "Accuracy", "Result", "Notes"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.history_table)
        return w

    def _build_charts_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        ctrl_row = QHBoxLayout()
        ctrl_row.addWidget(QLabel("Build Order:"))
        self.cb_chart_bo = QComboBox()
        self.cb_chart_bo.addItem("All builds", None)
        self.cb_chart_bo.currentIndexChanged.connect(self._refresh_charts)
        ctrl_row.addWidget(self.cb_chart_bo)
        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)
        chart_layout.setSpacing(16)

        self.lbl_feudal_chart  = QLabel("Charts will appear after practice sessions are recorded.")
        self.lbl_feudal_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_feudal_chart.setStyleSheet("color: #7f8c8d;")
        self.lbl_feudal_chart.setMinimumHeight(220)

        self.lbl_accuracy_chart = QLabel("")
        self.lbl_accuracy_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_accuracy_chart.setMinimumHeight(220)

        chart_layout.addWidget(QLabel("Feudal Time Trend"))
        chart_layout.addWidget(self.lbl_feudal_chart)
        chart_layout.addWidget(QLabel("Accuracy Trend"))
        chart_layout.addWidget(self.lbl_accuracy_chart)
        chart_layout.addStretch()

        scroll.setWidget(chart_widget)
        layout.addWidget(scroll)
        return w

    def _build_leaderboard_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(QLabel("Most Practiced Build Orders"))

        self.leaderboard_table = QTableWidget(0, 5)
        self.leaderboard_table.setHorizontalHeaderLabels(
            ["Build Order", "Civ", "Sessions", "Avg Accuracy", "Best Feudal"]
        )
        self.leaderboard_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.leaderboard_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.leaderboard_table)
        layout.addStretch()
        return w

    def _build_ai_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        info = QLabel(
            "AI Coach analyzes your session history and suggests build orders to improve your weaknesses.\n"
            "Requires Ollama running locally (enable in Settings → AI Coaching)."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        layout.addWidget(info)

        btn_ask = QPushButton("🤖 Ask AI Coach for Recommendations")
        btn_ask.setStyleSheet("QPushButton { background: #1c3a5c; color: #3498db; border: 1px solid #2c5a8c; border-radius: 6px; padding: 10px 20px; font-weight: bold; font-size: 13px; }")
        btn_ask.clicked.connect(self._on_ai_recommend)
        layout.addWidget(btn_ask)

        self.ai_output = QTextEdit()
        self.ai_output.setReadOnly(True)
        self.ai_output.setPlaceholderText("AI coaching recommendations will appear here…")
        layout.addWidget(self.ai_output)
        return w

    # ── Refresh / populate ────────────────────────────────────────────────

    def refresh(self) -> None:
        """Reload all data from DB."""
        self._populate_bo_filters()
        self._refresh_overview()
        self._refresh_history()
        self._refresh_charts()
        self._refresh_leaderboard()

    def _populate_bo_filters(self) -> None:
        bos = get_all_build_orders()
        for cb in [self.cb_bo_filter, self.cb_chart_bo]:
            current = cb.currentData()
            cb.blockSignals(True)
            cb.clear()
            cb.addItem("All builds", None)
            for bo in bos:
                cb.addItem(f"{bo.name} ({bo.civ})", bo.id)
            if current:
                for i in range(cb.count()):
                    if cb.itemData(i) == current:
                        cb.setCurrentIndex(i)
                        break
            cb.blockSignals(False)

    def _refresh_overview(self) -> None:
        bo_id = self.cb_bo_filter.currentData()
        stats = get_summary_stats(bo_id)

        self.card_sessions.set_value(str(stats.get("total_sessions", 0)))
        self.card_winrate.set_value(f"{stats.get('win_rate', 0):.1f}%")
        self.card_feudal.set_value(_sec_to_mmss(stats.get("avg_feudal_sec")))
        self.card_castle.set_value(_sec_to_mmss(stats.get("avg_castle_sec")))
        self.card_accuracy.set_value(_pct(stats.get("avg_accuracy")))
        self.card_days.set_value(str(stats.get("practice_days", 0)))

        self._render_heatmap()

    def _render_heatmap(self) -> None:
        """Render a simple text-based practice heatmap."""
        data = get_activity_heatmap()
        if not data:
            self.lbl_heatmap.setText("No practice data yet. Complete sessions to see activity.")
            return

        # Simple text heatmap
        today = date.today()
        lines = []
        for week_offset in range(16, -1, -1):
            week_dates = [today - timedelta(days=today.weekday()) - timedelta(weeks=week_offset) + timedelta(days=d) for d in range(7)]
            week_str = ""
            for d in week_dates:
                cnt = data.get(d.isoformat(), 0)
                if cnt == 0:   char = "░"
                elif cnt == 1: char = "▒"
                elif cnt <= 3: char = "▓"
                else:          char = "█"
                week_str += char
            lines.append(week_str)

        heatmap_text = "  ".join(lines)
        self.lbl_heatmap.setText(f"<pre style='color: #3498db; font-size: 14px; letter-spacing: 3px;'>{heatmap_text}</pre>")
        self.lbl_heatmap.setTextFormat(Qt.TextFormat.RichText)

    def _refresh_history(self) -> None:
        result = self.cb_hist_result.currentText()
        result_filter = None if result == "All" else result
        date_from = self.de_from.date().toString("yyyy-MM-dd")
        date_to   = self.de_to.date().toString("yyyy-MM-dd")

        sessions = get_sessions(result=result_filter, date_from=date_from, date_to=date_to)
        bos = {bo.id: bo for bo in get_all_build_orders()}

        self.history_table.setRowCount(0)
        for s in sessions:
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)
            bo = bos.get(s.build_order_id)
            bo_name = bo.name if bo else f"BO #{s.build_order_id}"

            self.history_table.setItem(row, 0, QTableWidgetItem(s.date))
            self.history_table.setItem(row, 1, QTableWidgetItem(bo_name))
            self.history_table.setItem(row, 2, QTableWidgetItem(_sec_to_mmss(s.duration_sec)))
            self.history_table.setItem(row, 3, QTableWidgetItem(_sec_to_mmss(s.feudal_time_sec)))
            self.history_table.setItem(row, 4, QTableWidgetItem(_sec_to_mmss(s.castle_time_sec)))
            self.history_table.setItem(row, 5, QTableWidgetItem(_pct(s.accuracy_pct)))
            self.history_table.setItem(row, 6, QTableWidgetItem(s.result))
            self.history_table.setItem(row, 7, QTableWidgetItem(s.notes[:60] if s.notes else ""))
            self.history_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, s.id)

    def _refresh_charts(self) -> None:
        if not _MPL_OK:
            self.lbl_feudal_chart.setText("Charts require matplotlib (already installed).")
            return

        bo_id = self.cb_chart_bo.currentData()
        feudal_trend = get_feudal_time_trend(bo_id, last_n=30)
        accuracy_trend = get_accuracy_trend(bo_id, last_n=30)
        chart_width = self.lbl_feudal_chart.width() or 700

        if not feudal_trend:
            self.lbl_feudal_chart.setText("No feudal time data yet.")
        else:
            x = list(range(len(feudal_trend)))
            y = [r["feudal_time_sec"] for r in feudal_trend]
            labels = [r["date"] for r in feudal_trend]

            fig, ax = _dark_fig(8, 3.0)
            ax.plot(x, y, color="#e67e22", linewidth=2, marker="o", markersize=5, zorder=3)
            ax.fill_between(x, y, alpha=0.15, color="#e67e22")
            ax.set_title("Feudal Time Trend (last 30 sessions)", color="#ecf0f1", pad=10)
            ax.set_ylabel("Seconds", color="#7f8c8d")
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda s, _: _sec_to_mmss(int(s))))
            ax.set_xticks(x[::max(1, len(x)//8)])
            ax.set_xticklabels([labels[i] for i in x[::max(1, len(x)//8)]], rotation=30, fontsize=8)
            ax.grid(axis="y", color="#2c2c2e", linestyle="--", alpha=0.5)
            fig.tight_layout(pad=1.5)

            pix = _render_chart(fig)
            plt.close(fig)
            self.lbl_feudal_chart.setPixmap(pix.scaledToWidth(
                chart_width, Qt.TransformationMode.SmoothTransformation
            ))

        if not accuracy_trend:
            self.lbl_accuracy_chart.setText("No accuracy data yet.")
        else:
            x = list(range(len(accuracy_trend)))
            y = [r["accuracy_pct"] for r in accuracy_trend]
            labels = [r["date"] for r in accuracy_trend]

            fig, ax = _dark_fig(8, 3.0)
            ax.plot(x, y, color="#1abc9c", linewidth=2, marker="o", markersize=5, zorder=3)
            ax.fill_between(x, y, alpha=0.15, color="#1abc9c")
            ax.set_title("Accuracy Trend (last 30 sessions)", color="#ecf0f1", pad=10)
            ax.set_ylabel("Accuracy %", color="#7f8c8d")
            ax.set_ylim(0, 100)
            ax.set_xticks(x[::max(1, len(x)//8)])
            ax.set_xticklabels([labels[i] for i in x[::max(1, len(x)//8)]], rotation=30, fontsize=8)
            ax.grid(axis="y", color="#2c2c2e", linestyle="--", alpha=0.5)
            fig.tight_layout(pad=1.5)

            pix = _render_chart(fig)
            plt.close(fig)
            self.lbl_accuracy_chart.setPixmap(pix.scaledToWidth(
                chart_width, Qt.TransformationMode.SmoothTransformation
            ))

    def _refresh_leaderboard(self) -> None:
        rows = get_most_practiced_builds(limit=20)
        self.leaderboard_table.setRowCount(0)
        for i, r in enumerate(rows):
            row = self.leaderboard_table.rowCount()
            self.leaderboard_table.insertRow(row)
            self.leaderboard_table.setItem(row, 0, QTableWidgetItem(r.get("name", "")))
            self.leaderboard_table.setItem(row, 1, QTableWidgetItem(r.get("civ", "")))
            self.leaderboard_table.setItem(row, 2, QTableWidgetItem(str(r.get("session_count", 0))))
            self.leaderboard_table.setItem(row, 3, QTableWidgetItem(_pct(r.get("avg_accuracy"))))
            self.leaderboard_table.setItem(row, 4, QTableWidgetItem(_sec_to_mmss(r.get("best_feudal"))))

    # ── Actions ───────────────────────────────────────────────────────────

    def _export(self, fmt: str) -> None:
        try:
            if fmt == "csv":
                path = export_sessions_csv()
            else:
                path = export_sessions_json()
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Exported", f"Data exported to:\n{path}")
        except Exception as exc:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Export Error", str(exc))

    def _on_delete_session(self) -> None:
        rows = self.history_table.selectedItems()
        if not rows:
            return
        row = self.history_table.currentRow()
        item = self.history_table.item(row, 0)
        session_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        if session_id is None:
            return
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Delete Session",
            "Delete this session permanently?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_session(session_id)
            self._refresh_history()

    def _on_ai_recommend(self) -> None:
        stats = get_summary_stats()
        self.ai_output.setPlainText("Asking AI Coach…")
        self._ai_thread = QThread(self)
        self._ai_worker = _AIWorker(stats, [])
        self._ai_worker.moveToThread(self._ai_thread)
        self._ai_thread.started.connect(self._ai_worker.run)
        self._ai_worker.finished.connect(self.ai_output.setPlainText)
        self._ai_worker.error.connect(lambda e: self.ai_output.setPlainText(f"Error: {e}"))
        self._ai_worker.finished.connect(self._ai_thread.quit)
        self._ai_worker.error.connect(self._ai_thread.quit)
        self._ai_thread.start()

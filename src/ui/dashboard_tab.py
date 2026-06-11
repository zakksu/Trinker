"""
TRINKER - Personal Dashboard
At-a-glance summary: last game, stats, coach tip, build comparison, Ask Coach chat.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..ai_coach.chat import ask_coach, build_summary_from_latest_replay, get_coach_messages
from ..analytics.compare import compare_to_build_order
from ..analytics.replay_store import get_latest_replay_analysis, get_replay_analyses
from ..analytics.session import get_sessions, get_summary_stats
from ..core.config import settings
from ..integrations.aoe2gg import get_stored_matches, import_recent_matches, profile_url_for
from .theme import apply_tab_panel, get_tokens

_STATUS_COLORS = {
    "green": "#2ecc71",
    "yellow": "#f1c40f",
    "red": "#e74c3c",
    "neutral": "#95a5a6",
}


def _fmt_sec(sec) -> str:
    """Format seconds (int or float from DB/JSON) as M:SS."""
    if sec is None:
        return "—"
    sec = int(round(float(sec)))
    return f"{sec // 60}:{sec % 60:02d}"


class _DashCard(QFrame):
    def __init__(self, title: str, value: str = "—", color: str = "#3498db", parent=None):
        super().__init__(parent)
        t = get_tokens()
        self.setStyleSheet(f"""
            QFrame {{
                background: {t.bg_elevated};
                border: 1px solid {t.border};
                border-radius: 10px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        self.lbl_val = QLabel(value)
        self.lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_val.setStyleSheet(
            f"color: {color}; font-size: 26px; font-weight: bold; font-family: monospace;"
        )
        self.lbl_title = QLabel(title)
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setStyleSheet(f"color: {t.text_dim}; font-size: 11px;")
        layout.addWidget(self.lbl_val)
        layout.addWidget(self.lbl_title)

    def set_value(self, value: str) -> None:
        self.lbl_val.setText(value)


class _CoachWorker(QObject):
    finished = Signal(str, str)  # reply, error

    def __init__(self, question: str):
        super().__init__()
        self.question = question

    def run(self) -> None:
        try:
            summary = build_summary_from_latest_replay()
            reply = ask_coach(self.question, summary)
            self.finished.emit(reply, "")
        except Exception as exc:
            self.finished.emit("", str(exc))


class DashboardTab(QWidget):
    """Personal dashboard — quick read on progress and last game."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._coach_thread: QThread | None = None
        self._setup_ui()
        self.apply_theme()

    def apply_theme(self, theme_name: str | None = None) -> None:
        apply_tab_panel(self)
        t = get_tokens(theme_name)
        self._title.setStyleSheet(
            f"font-size: 24px; font-weight: bold; color: {t.text_title};"
        )

    def _setup_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        self._title = QLabel("Dashboard")
        layout.addWidget(self._title)

        self.lbl_sub = QLabel("Your training snapshot — updates after each game.")
        self.lbl_sub.setWordWrap(True)
        layout.addWidget(self.lbl_sub)

        cards = QHBoxLayout()
        self.card_sessions = _DashCard("GAMES SAVED", "0", "#3498db")
        self.card_feudal = _DashCard("AVG FEUDAL", "—", "#e67e22")
        self.card_quality = _DashCard("LAST QUALITY", "—", "#2ecc71")
        for c in (self.card_sessions, self.card_feudal, self.card_quality):
            cards.addWidget(c)
        layout.addLayout(cards)

        last_group = QGroupBox("Last Game")
        last_layout = QVBoxLayout(last_group)
        self.lbl_last_game = QLabel("No games detected yet — play with the overlay on.")
        self.lbl_last_game.setWordWrap(True)
        last_layout.addWidget(self.lbl_last_game)
        layout.addWidget(last_group)

        compare_group = QGroupBox("Compare to Build Order")
        compare_layout = QVBoxLayout(compare_group)
        self.lbl_compare_summary = QLabel("—")
        self.lbl_compare_summary.setWordWrap(True)
        compare_layout.addWidget(self.lbl_compare_summary)
        self.compare_grid = QGridLayout()
        compare_layout.addLayout(self.compare_grid)
        self._compare_labels: list[QLabel] = []
        layout.addWidget(compare_group)

        coach_group = QGroupBox("Coach Tip for Next Game")
        coach_layout = QVBoxLayout(coach_group)
        self.lbl_coach = QLabel("—")
        self.lbl_coach.setWordWrap(True)
        coach_layout.addWidget(self.lbl_coach)
        layout.addWidget(coach_group)

        chat_group = QGroupBox("Ask Coach")
        chat_layout = QVBoxLayout(chat_group)
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setPlaceholderText("Ask about your last game, timings, or build order…")
        self.chat_history.setMaximumHeight(160)
        chat_layout.addWidget(self.chat_history)
        chat_row = QHBoxLayout()
        self.ed_question = QLineEdit()
        self.ed_question.setPlaceholderText("e.g. Why was my feudal late?")
        self.ed_question.returnPressed.connect(self._on_ask_coach)
        chat_row.addWidget(self.ed_question)
        self.btn_ask = QPushButton("Ask")
        self.btn_ask.clicked.connect(self._on_ask_coach)
        chat_row.addWidget(self.btn_ask)
        chat_layout.addLayout(chat_row)
        layout.addWidget(chat_group)

        online_group = QGroupBox("Online Matches (aoe2.gg)")
        online_layout = QVBoxLayout(online_group)
        self.lbl_online = QLabel("Set Steam ID in Settings, then import recent ladder games.")
        self.lbl_online.setWordWrap(True)
        online_layout.addWidget(self.lbl_online)
        online_btns = QHBoxLayout()
        self.btn_import = QPushButton("Import Recent Matches")
        self.btn_import.clicked.connect(self._on_import_matches)
        online_btns.addWidget(self.btn_import)
        self.btn_profile = QPushButton("Open aoe2.gg Profile")
        self.btn_profile.clicked.connect(self._on_open_profile)
        online_btns.addWidget(self.btn_profile)
        online_btns.addStretch()
        online_layout.addLayout(online_btns)
        layout.addWidget(online_group)

        recent_group = QGroupBox("Recent Games")
        recent_layout = QVBoxLayout(recent_group)
        self.lbl_recent = QLabel("—")
        self.lbl_recent.setWordWrap(True)
        recent_layout.addWidget(self.lbl_recent)
        layout.addWidget(recent_group)

        btn_row = QHBoxLayout()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh)
        btn_row.addWidget(btn_refresh)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()
        scroll.setWidget(container)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def _clear_compare_grid(self) -> None:
        while self.compare_grid.count():
            item = self.compare_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._compare_labels.clear()

    def _render_compare(self, feudal, castle, imperial) -> None:
        cmp = compare_to_build_order(
            feudal_sec=feudal,
            castle_sec=castle,
            imperial_sec=imperial,
        )
        self.lbl_compare_summary.setText(
            f"{cmp.build_name} ({cmp.civ}) — {cmp.summary}"
            if cmp.has_data()
            else cmp.summary
        )
        self._clear_compare_grid()
        for i, row in enumerate(cmp.rows):
            color = _STATUS_COLORS.get(row.status, "#95a5a6")
            lbl = QLabel(
                f"{row.label}:  {row.actual}  vs  {row.target}  —  {row.detail}"
            )
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color: {color}; font-family: monospace; font-size: 11px;")
            self.compare_grid.addWidget(lbl, i, 0)
            self._compare_labels.append(lbl)

    def _load_chat_history(self) -> None:
        msgs = get_coach_messages("dashboard")
        if not msgs:
            self.chat_history.clear()
            return
        lines = []
        for m in msgs[-12:]:
            prefix = "You" if m.role == "user" else "Coach"
            lines.append(f"{prefix}: {m.content}")
        self.chat_history.setPlainText("\n\n".join(lines))

    def _on_ask_coach(self) -> None:
        question = self.ed_question.text().strip()
        if not question:
            return
        self.ed_question.clear()
        self.btn_ask.setEnabled(False)
        self.chat_history.append(f"You: {question}")

        worker = _CoachWorker(question)
        thread = QThread()

        def _done(reply: str, error: str) -> None:
            self.btn_ask.setEnabled(True)
            if error:
                self.chat_history.append(f"Coach: Error — {error}")
            else:
                self.chat_history.append(f"Coach: {reply}")
            thread.quit()

        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(_done)
        worker.finished.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        self._coach_thread = thread
        thread.start()

    def _on_import_matches(self) -> None:
        if not settings.steam_id.strip():
            self.lbl_online.setText("Set your Steam ID in Settings first.")
            return
        self.btn_import.setEnabled(False)
        self.lbl_online.setText("Fetching recent matches…")
        try:
            result = import_recent_matches(settings.steam_id)
            if result.matches:
                self.lbl_online.setText(
                    f"Imported {len(result.matches)} match(es) via {result.source}."
                )
            else:
                self.lbl_online.setText(result.error or "No matches found.")
        except Exception as exc:
            self.lbl_online.setText(f"Import failed: {exc}")
        finally:
            self.btn_import.setEnabled(True)
        self._render_online_matches()

    def _on_open_profile(self) -> None:
        import webbrowser
        sid = settings.steam_id.strip()
        if sid:
            webbrowser.open(profile_url_for(sid))

    def _render_online_matches(self) -> None:
        matches = get_stored_matches(limit=5)
        if not matches:
            sid = settings.steam_id.strip()
            if sid:
                self.lbl_online.setText(
                    f"No imported matches yet. Profile: {profile_url_for(sid)}"
                )
            return
        lines = []
        for m in matches:
            res = m.result.upper() if m.result != "unknown" else "?"
            rating = f"  {m.rating}" if m.rating else ""
            lines.append(
                f"• {m.civ} on {m.map_name} — {res}{rating} vs {m.opponent}"
            )
        self.lbl_online.setText("\n".join(lines))

    def refresh(self) -> None:
        stats = get_summary_stats()
        self.card_sessions.set_value(str(stats.get("total_sessions", 0)))
        feudal = stats.get("avg_feudal_sec")
        self.card_feudal.set_value(_fmt_sec(feudal) if feudal else "—")

        latest = get_latest_replay_analysis()
        feudal_sec = castle_sec = imperial_sec = None
        if latest:
            self.card_quality.set_value(latest.data_quality or "—")
            try:
                data = json.loads(latest.profile_json)
            except Exception:
                data = {}
            feudal_sec = data.get("feudal_time_sec")
            castle_sec = data.get("castle_time_sec")
            imperial_sec = data.get("imperial_time_sec")
            feudal_s = _fmt_sec(feudal_sec)
            self.lbl_last_game.setText(
                f"{Path(latest.replay_path).name}\n"
                f"Civ: {latest.civ}  |  Map: {latest.map_name or '—'}  |  "
                f"Mode: {latest.game_mode.upper()}  |  Feudal: {feudal_s}\n"
                f"Quality: {latest.data_quality}"
            )
        else:
            self.card_quality.set_value("—")
            self.lbl_last_game.setText(
                "No games detected yet — pick a build on Start Here and play."
            )

        self._render_compare(feudal_sec, castle_sec, imperial_sec)

        if settings.overlay_coach_alert:
            self.lbl_coach.setText(settings.overlay_coach_alert)
        else:
            self.lbl_coach.setText("Play a game — coach tips appear here after auto-analysis.")

        recent = get_replay_analyses(5)
        if recent:
            lines = []
            for r in recent:
                name = Path(r.replay_path).name[:48]
                lines.append(f"• {r.civ} — {name} ({r.data_quality})")
            self.lbl_recent.setText("\n".join(lines))
        else:
            sessions = get_sessions(limit=5)
            if sessions:
                lines = [f"• {s.date[:10]} — session #{s.id}" for s in sessions]
                self.lbl_recent.setText("\n".join(lines))
            else:
                self.lbl_recent.setText("No saved games yet.")

        self._load_chat_history()
        self._render_online_matches()

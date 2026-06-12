"""
TRINKER - Personal Dashboard
At-a-glance summary with medieval strategy UI — stats, timeline, coach, compare.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QFrame,
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
from ..analytics.session import (
    get_activity_heatmap,
    get_practice_streak,
    get_sessions,
    get_summary_stats,
    get_training_badges,
)
from ..core.config import settings
from ..integrations.aoe2gg import get_stored_matches, import_recent_matches, profile_url_for
from .medieval.animations import stagger_fade_in
from .medieval.icons import Icon
from .medieval.palette import get_palette
from .medieval.widgets import (
    ActivityHeatmap,
    BadgeChip,
    CompareDiffTable,
    MedievalPanel,
    SectionHeader,
    StatCard,
    Timeline,
)
from .theme import apply_tab_panel, get_tokens

_STATUS_ACCENTS = {
    "green": "#6aab55",
    "yellow": "#d4a017",
    "red": "#b54a4a",
    "neutral": "#7a6f5c",
}


def _fmt_sec(sec) -> str:
    if sec is None:
        return "—"
    sec = int(round(float(sec)))
    return f"{sec // 60}:{sec % 60:02d}"


class _CoachWorker(QObject):
    finished = Signal(str, str)

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
    """Personal dashboard — command center for training progress."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._coach_thread: QThread | None = None
        self._stat_cards: list[StatCard] = []
        self._setup_ui()
        self.apply_theme()

    def apply_theme(self, theme_name: str | None = None) -> None:
        apply_tab_panel(self)
        t = get_tokens(theme_name)
        p = get_palette()
        if t.medieval:
            self._header.lbl_title.setStyleSheet(
                f"color: {p.gold_bright}; font-size: 26px; font-weight: bold;"
            )
            self._header.lbl_sub.setStyleSheet(f"color: {p.ink_dim}; font-size: 12px;")

    def _setup_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 20, 28, 24)
        layout.setSpacing(18)

        self._header = SectionHeader(
            "Command Center",
            "Your training snapshot — updates after each game.",
            Icon.DASHBOARD,
        )
        layout.addWidget(self._header)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        p = get_palette()
        self.card_sessions = StatCard(Icon.GAME, "Games Saved", "0", p.gold)
        self.card_feudal = StatCard(Icon.TIMER, "Avg Feudal", "—", p.feudal)
        self.card_quality = StatCard(Icon.QUALITY, "Last Quality", "—", p.success)
        self.card_winrate = StatCard(Icon.LADDER, "Win Rate", "—", p.gold_bright)
        self.card_streak = StatCard(Icon.REFRESH, "Day Streak", "0", p.success)
        self._stat_cards = [
            self.card_sessions,
            self.card_feudal,
            self.card_quality,
            self.card_winrate,
            self.card_streak,
        ]
        for c in self._stat_cards:
            cards.addWidget(c)
        layout.addLayout(cards)

        self._badges_row = QHBoxLayout()
        self._badges_row.setSpacing(8)
        badges_wrap = QWidget()
        badges_wrap.setLayout(self._badges_row)
        layout.addWidget(badges_wrap)

        heat_row = QHBoxLayout()
        heat_row.setSpacing(12)
        self.panel_activity = MedievalPanel("Training Activity", Icon.ANALYTICS)
        self.activity_heatmap = ActivityHeatmap()
        self.panel_activity.add_widget(self.activity_heatmap)
        heat_row.addWidget(self.panel_activity, 1)
        layout.addLayout(heat_row)

        self.panel_last = MedievalPanel("Last Game", Icon.GAME)
        self.lbl_last_game = QLabel("No games detected yet — play with the overlay on.")
        self.lbl_last_game.setWordWrap(True)
        p = get_palette()
        self.lbl_last_game.setStyleSheet(f"color: {p.ink}; font-size: 12px; line-height: 1.4;")
        self.panel_last.add_widget(self.lbl_last_game)
        layout.addWidget(self.panel_last)

        self.panel_compare = MedievalPanel("Compare to Build Order", Icon.COMPARE)
        self.lbl_compare_summary = QLabel("—")
        self.lbl_compare_summary.setWordWrap(True)
        self.lbl_compare_summary.setStyleSheet(f"color: {p.ink_dim}; font-size: 12px; font-weight: bold;")
        self.panel_compare.add_widget(self.lbl_compare_summary)
        self.compare_diff = CompareDiffTable()
        self.panel_compare.add_widget(self.compare_diff)
        self.compare_timeline = Timeline()
        self.panel_compare.add_widget(self.compare_timeline)
        layout.addWidget(self.panel_compare)

        self.panel_coach = MedievalPanel("Coach Tip — Next Game", Icon.COACH)
        self.lbl_coach = QLabel("—")
        self.lbl_coach.setWordWrap(True)
        self.lbl_coach.setStyleSheet(
            f"color: {p.gold_bright}; font-size: 13px; font-weight: bold; "
            f"background: rgba(201,162,39,0.08); border-radius: 8px; padding: 10px;"
        )
        self.panel_coach.add_widget(self.lbl_coach)
        layout.addWidget(self.panel_coach)

        self.panel_chat = MedievalPanel("Ask Coach", Icon.ASK)
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setPlaceholderText("Ask about your last game, timings, or build order…")
        self.chat_history.setMaximumHeight(150)
        self.panel_chat.add_widget(self.chat_history)
        chat_row = QHBoxLayout()
        self.ed_question = QLineEdit()
        self.ed_question.setPlaceholderText("e.g. Why was my feudal late?")
        self.ed_question.returnPressed.connect(self._on_ask_coach)
        chat_row.addWidget(self.ed_question)
        self.btn_ask = QPushButton(f"{Icon.ASK} Ask")
        self.btn_ask.clicked.connect(self._on_ask_coach)
        chat_row.addWidget(self.btn_ask)
        self.panel_chat.add_layout(chat_row)
        layout.addWidget(self.panel_chat)

        self.panel_online = MedievalPanel("Ladder — aoe2.gg", Icon.LADDER)
        self.lbl_online = QLabel("Set Steam ID in Settings, then import recent ladder games.")
        self.lbl_online.setWordWrap(True)
        self.lbl_online.setStyleSheet(f"color: {p.ink_dim}; font-size: 12px;")
        self.panel_online.add_widget(self.lbl_online)
        online_btns = QHBoxLayout()
        self.btn_import = QPushButton(f"{Icon.REFRESH} Import Matches")
        self.btn_import.clicked.connect(self._on_import_matches)
        online_btns.addWidget(self.btn_import)
        self.btn_profile = QPushButton("Open Profile")
        self.btn_profile.clicked.connect(self._on_open_profile)
        online_btns.addWidget(self.btn_profile)
        online_btns.addStretch()
        self.panel_online.add_layout(online_btns)
        layout.addWidget(self.panel_online)

        self.panel_recent = MedievalPanel("Recent Campaign", Icon.ANALYTICS)
        self.recent_timeline = Timeline()
        self.panel_recent.add_widget(self.recent_timeline)
        layout.addWidget(self.panel_recent)

        btn_row = QHBoxLayout()
        btn_refresh = QPushButton(f"{Icon.REFRESH} Refresh")
        btn_refresh.clicked.connect(self.refresh)
        btn_row.addWidget(btn_refresh)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()
        scroll.setWidget(container)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        stagger_fade_in(self._stat_cards, delay_ms=50)

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
        self.compare_diff.set_rows(cmp.rows)
        self.compare_timeline.clear()
        for row in cmp.rows:
            accent = _STATUS_ACCENTS.get(row.status, _STATUS_ACCENTS["neutral"])
            self.compare_timeline.add_item(
                Icon.status_glyph(row.status),
                f"{row.label}:  {row.actual}  vs  {row.target}",
                row.detail,
                accent=accent,
            )

    def _render_badges(self) -> None:
        while self._badges_row.count():
            item = self._badges_row.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        badges = get_training_badges()
        if not badges:
            self._badges_row.addWidget(
                BadgeChip("Play your first game to earn badges")
            )
        else:
            for name in badges:
                self._badges_row.addWidget(BadgeChip(f"🏅 {name}"))
        self._badges_row.addStretch()

    def _load_chat_history(self) -> None:
        msgs = get_coach_messages("dashboard")
        if not msgs:
            self.chat_history.clear()
            return
        lines = []
        for m in msgs[-12:]:
            prefix = "You" if m.role == "user" else f"{Icon.COACH} Coach"
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
                self.chat_history.append(f"{Icon.COACH} Coach: {reply}")
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
            return
        lines = []
        for m in matches:
            res = Icon.result_glyph(m.result)
            rating = f"  {m.rating}" if m.rating else ""
            lines.append(f"{res} {m.civ} on {m.map_name} — vs {m.opponent}{rating}")
        existing = self.lbl_online.text()
        if "Imported" in existing or "Profile" in existing:
            self.lbl_online.setText(existing + "\n\n" + "\n".join(lines))
        else:
            self.lbl_online.setText("\n".join(lines))

    def _render_recent_timeline(self) -> None:
        self.recent_timeline.clear()
        p = get_palette()
        recent = get_replay_analyses(5)
        if recent:
            for r in recent:
                name = Path(r.replay_path).name[:52]
                quality_color = p.success if r.data_quality == "high" else p.ink_dim
                self.recent_timeline.add_item(
                    Icon.GAME,
                    f"{r.civ} — {name}",
                    f"Quality: {r.data_quality}",
                    accent=quality_color,
                )
            return
        sessions = get_sessions(limit=5)
        for s in sessions:
            self.recent_timeline.add_item(
                Icon.TIMER,
                f"Session #{s.id}",
                s.date[:16],
                accent=p.gold_dim,
            )
        if not sessions:
            self.recent_timeline.add_item(
                Icon.DASHBOARD,
                "No saved games yet",
                "Play with overlay on to start tracking.",
                accent=p.ink_muted,
            )

    def refresh(self) -> None:
        stats = get_summary_stats()
        self.card_sessions.set_value(str(stats.get("total_sessions", 0)))
        feudal = stats.get("avg_feudal_sec")
        self.card_feudal.set_value(_fmt_sec(feudal) if feudal else "—")
        self.card_winrate.set_value(f"{stats.get('win_rate', 0):.1f}%")
        streak = get_practice_streak()
        self.card_streak.set_value(str(streak.get("current", 0)))
        self._render_badges()
        self.activity_heatmap.set_data(get_activity_heatmap())

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
                f"{Icon.GAME}  {Path(latest.replay_path).name}\n\n"
                f"{Icon.FEUDAL} Civ: {latest.civ}   ·   Map: {latest.map_name or '—'}\n"
                f"{Icon.TIMER} Mode: {latest.game_mode.upper()}   ·   Feudal: {feudal_s}\n"
                f"{Icon.QUALITY} Quality: {latest.data_quality}"
            )
        else:
            self.card_quality.set_value("—")
            self.lbl_last_game.setText(
                "No games detected yet — pick a build on Start Here and play."
            )

        self._render_compare(feudal_sec, castle_sec, imperial_sec)

        if settings.overlay_coach_alert:
            self.lbl_coach.setText(f"{Icon.COACH}  {settings.overlay_coach_alert}")
        else:
            self.lbl_coach.setText(
                "Play a game — coach tips appear here after auto-analysis."
            )

        self._render_recent_timeline()
        self._load_chat_history()
        self._render_online_matches()

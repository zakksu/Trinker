"""
TRINKER - Personal Dashboard
At-a-glance summary with medieval strategy UI — stats, timeline, coach, compare.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
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
from ..analytics.charts import (
    charts_available,
    render_accuracy_trend,
    render_feudal_trend,
    render_win_rate_bar,
)
from ..analytics.history import build_historical_summary, get_recurring_themes
from ..analytics.compare import compare_to_build_order
from ..analytics.session import (
    get_activity_heatmap,
    get_accuracy_trend,
    get_feudal_time_trend,
    get_practice_streak,
    get_sessions,
    get_summary_stats,
    get_training_badges,
)
from ..analytics.training_stats import format_win_rate_label, get_platform_stats
from ..analytics.replay_store import (
    get_latest_replay_analysis,
    get_replay_analyses,
    get_replay_feudal_trend,
)
from ..core.config import settings
from ..integrations.aoe2gg import get_stored_matches, import_recent_matches, profile_url_for
from ..training.drill_engine import pin_drill, suggest_drill
from .medieval.animations import stagger_fade_in
from .medieval.icons import Icon
from .medieval.palette import get_palette
from .medieval.styles import dialog_stylesheet
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

_KPI_OPTIONS: list[tuple[str, str]] = [
    ("sessions", "Games Saved"),
    ("feudal", "Avg Feudal"),
    ("quality", "Last Quality"),
    ("winrate", "Win Rate"),
    ("streak", "Day Streak"),
    ("accuracy", "Avg Accuracy"),
]


def _sanitize_coach_alert(alert: str) -> str:
    """Drop stale Ollama connection nags from pinned overlay alerts."""
    text = (alert or "").strip()
    if not text:
        return ""
    low = text.lower()
    if "ollama" in low and any(x in low for x in ("settings", "connection", "check trinker")):
        return ""
    return text


class _KpiCustomizeDialog(QDialog):
    """Pick which KPI stat cards appear on the Performance Hub."""

    def __init__(self, selected: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Customize KPI Cards")
        p = get_palette()
        self.setStyleSheet(dialog_stylesheet(p))
        self.setMinimumWidth(360)
        self._checks: dict[str, QCheckBox] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(10)
        title = QLabel("Choose stats for your Performance Hub banner:")
        title.setStyleSheet(f"color: {p.gold_bright}; font-weight: bold; font-size: 13px;")
        layout.addWidget(title)
        for key, label in _KPI_OPTIONS:
            cb = QCheckBox(label)
            cb.setChecked(key in selected)
            self._checks[key] = cb
            layout.addWidget(cb)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_keys(self) -> list[str]:
        return [k for k, cb in self._checks.items() if cb.isChecked()]


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
            "Performance Hub",
            "Your command center — KPIs, trends, patterns, and next-game focus.",
            Icon.DASHBOARD,
        )
        layout.addWidget(self._header)

        kpi_toolbar = QHBoxLayout()
        kpi_toolbar.addStretch()
        self.btn_customize_kpis = QPushButton(f"{Icon.SETTINGS} Customize KPIs")
        self.btn_customize_kpis.clicked.connect(self._customize_kpis)
        kpi_toolbar.addWidget(self.btn_customize_kpis)
        layout.addLayout(kpi_toolbar)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        p = get_palette()
        self.card_sessions = StatCard(Icon.GAME, "Games Saved", "0", p.gold)
        self.card_feudal = StatCard(Icon.TIMER, "Avg Feudal", "—", p.feudal)
        self.card_quality = StatCard(Icon.QUALITY, "Last Quality", "—", p.success)
        self.card_winrate = StatCard(Icon.LADDER, "Win Rate", "—", p.gold_bright)
        self.card_streak = StatCard(Icon.REFRESH, "Day Streak", "0", p.success)
        self.card_accuracy = StatCard(Icon.ANALYTICS, "Avg Accuracy", "—", p.gold_dim)
        self._kpi_cards: dict[str, StatCard] = {
            "sessions": self.card_sessions,
            "feudal": self.card_feudal,
            "quality": self.card_quality,
            "winrate": self.card_winrate,
            "streak": self.card_streak,
            "accuracy": self.card_accuracy,
        }
        self._stat_cards = list(self._kpi_cards.values())
        for c in self._stat_cards:
            cards.addWidget(c)
        layout.addLayout(cards)
        self._apply_kpi_visibility()

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

        if settings.dashboard_show_charts:
            self.panel_charts = MedievalPanel("Trend Charts", Icon.ANALYTICS)
            charts_row = QHBoxLayout()
            self.lbl_feudal_chart = QLabel("Play more games to see feudal trends.")
            self.lbl_feudal_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_accuracy_chart = QLabel("")
            self.lbl_accuracy_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_results_chart = QLabel("")
            self.lbl_results_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
            for lbl in (self.lbl_feudal_chart, self.lbl_accuracy_chart, self.lbl_results_chart):
                lbl.setMinimumHeight(120)
                lbl.setWordWrap(True)
            charts_row.addWidget(self.lbl_feudal_chart, 1)
            charts_row.addWidget(self.lbl_accuracy_chart, 1)
            charts_row.addWidget(self.lbl_results_chart, 1)
            self.panel_charts.add_layout(charts_row)
            if not charts_available():
                hint = QLabel("Install matplotlib for trend charts (pip install matplotlib).")
                hint.setWordWrap(True)
                hint.setStyleSheet(f"color: {p.ink_dim}; font-size: 11px;")
                self.panel_charts.add_widget(hint)
            layout.addWidget(self.panel_charts)
        else:
            self.panel_charts = None

        if settings.dashboard_show_patterns:
            self.panel_patterns = MedievalPanel("Historical Patterns", Icon.LIBRARY)
            self.lbl_themes = QLabel("—")
            self.lbl_themes.setWordWrap(True)
            self.lbl_themes.setStyleSheet(f"color: {p.gold_bright}; font-size: 12px; font-weight: bold;")
            self.panel_patterns.add_widget(self.lbl_themes)
            self.hist_output = QTextEdit()
            self.hist_output.setReadOnly(True)
            self.hist_output.setMaximumHeight(140)
            self.hist_output.setPlaceholderText("Historical analysis appears after a few saved sessions…")
            self.panel_patterns.add_widget(self.hist_output)
            layout.addWidget(self.panel_patterns)
        else:
            self.panel_patterns = None

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

        self.panel_drill = MedievalPanel("Next Drill", Icon.OVERLAY)
        self.lbl_drill = QLabel("—")
        self.lbl_drill.setWordWrap(True)
        self.panel_drill.add_widget(self.lbl_drill)
        drill_row = QHBoxLayout()
        self.btn_pin_drill = QPushButton(f"{Icon.OVERLAY} Pin Drill")
        self.btn_pin_drill.clicked.connect(self._pin_next_drill)
        drill_row.addWidget(self.btn_pin_drill)
        drill_row.addStretch()
        self.panel_drill.add_layout(drill_row)
        layout.addWidget(self.panel_drill)

        self.panel_chat = MedievalPanel("Ask Coach", Icon.ASK)
        self.lbl_coach_mode = QLabel("")
        self.lbl_coach_mode.setWordWrap(True)
        self.panel_chat.add_widget(self.lbl_coach_mode)
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

    def _apply_kpi_visibility(self) -> None:
        selected = settings.dashboard_kpis or [k for k, _ in _KPI_OPTIONS]
        for key, card in self._kpi_cards.items():
            card.setVisible(key in selected)

    def _customize_kpis(self) -> None:
        selected = settings.dashboard_kpis or [k for k, _ in _KPI_OPTIONS]
        dlg = _KpiCustomizeDialog(selected, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        picked = dlg.selected_keys()
        if not picked:
            picked = ["sessions", "feudal", "quality"]
        settings.dashboard_kpis = picked
        settings.save()
        self._apply_kpi_visibility()

    def _render_performance_charts(self, stats: dict) -> None:
        if not getattr(self, "panel_charts", None):
            return
        feudal_trend = get_feudal_time_trend(last_n=20)
        if not feudal_trend:
            feudal_trend = get_replay_feudal_trend(last_n=20)
        acc_trend = get_accuracy_trend(last_n=20)
        pix_f = render_feudal_trend(feudal_trend) if feudal_trend else None
        pix_a = render_accuracy_trend(acc_trend) if acc_trend else None
        breakdown: dict[str, int] = {}
        for key, label in (
            ("ranked_wins", "win"),
            ("ranked_losses", "loss"),
            ("ranked_draws", "draw"),
        ):
            val = stats.get(key) or 0
            if val:
                breakdown[label] = int(val)
        practice = int(stats.get("all_games") or 0) - sum(breakdown.values())
        if practice > 0:
            breakdown["practice"] = practice
        pix_r = render_win_rate_bar(breakdown) if breakdown else None

        def _set(lbl: QLabel, pix, empty: str) -> None:
            if pix and not pix.isNull():
                lbl.setPixmap(pix.scaledToWidth(280, Qt.TransformationMode.SmoothTransformation))
                lbl.setText("")
            else:
                lbl.setPixmap(QPixmap())
                lbl.setText(empty)

        _set(self.lbl_feudal_chart, pix_f, "Feudal trend — play more ranked/practice games.")
        _set(self.lbl_accuracy_chart, pix_a, "Accuracy trend — finish overlay sessions.")
        _set(self.lbl_results_chart, pix_r, "Results breakdown — wins tracked from replays.")

    def _render_patterns(self) -> None:
        if not getattr(self, "panel_patterns", None):
            return
        themes = get_recurring_themes()
        if themes:
            self.lbl_themes.setText(
                "  ·  ".join(f"{t} ({c})" for t, c in themes[:8])
            )
        else:
            self.lbl_themes.setText("No recurring themes yet — add notes when saving sessions.")
        bo_id = settings.last_practice_bo_id
        civ = "Any"
        if bo_id:
            from ..build_orders.manager import get_build_order

            bo = get_build_order(bo_id)
            if bo:
                civ = bo.civ
        self.hist_output.setPlainText(build_historical_summary(civ, bo_id))

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
        from ..training.drill_progress import get_completed_drill_badges

        drill_badges = get_completed_drill_badges()
        all_badges = [f"🏅 {b}" for b in badges] + drill_badges
        if not all_badges:
            self._badges_row.addWidget(
                BadgeChip("Play your first game to earn badges")
            )
        else:
            for name in all_badges:
                self._badges_row.addWidget(BadgeChip(name))
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

    def _render_drill(self, stats: dict) -> None:
        from ..core.config import settings as cfg
        from ..training.drill_progress import format_progress_label, get_drill

        wr = float(
            stats.get("ranked_win_rate") or stats.get("replay_win_rate") or stats.get("win_rate") or 0
        )
        drill = suggest_drill(
            feudal_sec=stats.get("avg_feudal_sec"),
            overlay_alert=cfg.overlay_coach_alert,
            win_rate=wr,
        )
        progress = ""
        if cfg.active_drill_id:
            progress = f" [{format_progress_label(cfg.active_drill_id)}]"
        self.lbl_drill.setText(f"{Icon.COACH} {drill.title}{progress}\n{drill.instructions}")
        if cfg.active_drill_id:
            active = get_drill(cfg.active_drill_id)
            if active and active.id != drill.id:
                self.lbl_drill.setText(
                    f"{Icon.OVERLAY} Active: {active.title}{progress}\n{active.instructions}"
                )

    def _pin_next_drill(self) -> None:
        stats = get_platform_stats()
        wr = float(
            stats.get("ranked_win_rate") or stats.get("replay_win_rate") or stats.get("win_rate") or 0
        )
        drill = suggest_drill(
            feudal_sec=stats.get("avg_feudal_sec"),
            overlay_alert=settings.overlay_coach_alert,
            win_rate=wr,
        )
        pin_drill(drill)
        self.lbl_drill.setText(f"{Icon.OVERLAY} Pinned: {drill.title}")

    def refresh(self) -> None:
        stats = get_platform_stats()
        self.card_sessions.set_value(str(stats.get("all_games") or stats.get("total_sessions", 0)))
        feudal = stats.get("avg_feudal_sec")
        self.card_feudal.set_value(_fmt_sec(feudal) if feudal else "—")
        self.card_winrate.set_value(format_win_rate_label(stats))
        acc = stats.get("avg_accuracy")
        self.card_accuracy.set_value(f"{acc:.1f}%" if acc is not None else "—")
        streak = get_practice_streak()
        self.card_streak.set_value(str(streak.get("current", 0)))
        self._render_badges()
        self.activity_heatmap.set_data(get_activity_heatmap())
        self._render_performance_charts(stats)
        self._render_patterns()

        stale = _sanitize_coach_alert(settings.overlay_coach_alert)
        if settings.overlay_coach_alert and not stale:
            settings.overlay_coach_alert = ""
            settings.overlay_coach_alert_bo_id = None
            settings.save()

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

        self._render_drill(stats)

        from ..ai_coach.coach import _is_ollama_available

        if _is_ollama_available():
            self.lbl_coach_mode.setText("")
        else:
            self.lbl_coach_mode.setText(
                "○ Offline mode — rule-based tips. Enable Ollama in Settings for AI replies."
            )
            self.lbl_coach_mode.setStyleSheet("color: #b8a88a; font-size: 11px;")

        if stale:
            self.lbl_coach.setText(f"{Icon.COACH}  {stale}")
        else:
            self.lbl_coach.setText(
                "Play a game — coach tips appear here after auto-analysis."
            )

        self._render_recent_timeline()
        self._load_chat_history()
        self._render_online_matches()

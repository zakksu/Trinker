"""
TRINKER - Build Order Library Tab
Browse, search, import, and manage all build orders.
Supports URL import from buildorderguide.com, JSON/TXT file import, and inline editing.
"""

from typing import Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..build_orders.importer import (
    import_from_json_file,
    import_from_txt_file,
    import_from_url,
)
from ..build_orders.manager import (
    delete_build_order,
    get_all_build_orders,
    import_and_save,
    save_build_order,
    toggle_favorite,
)
from ..build_orders.models import BuildOrder
from ..core.logger import logger

CIVS = [
    "Any",
    "Aztecs",
    "Bengalis",
    "Berbers",
    "Bohemians",
    "Britons",
    "Bulgarians",
    "Burgundians",
    "Burmese",
    "Byzantines",
    "Celts",
    "Chinese",
    "Cumans",
    "Dravidians",
    "Ethiopians",
    "Franks",
    "Goths",
    "Gurjaras",
    "Hindustanis",
    "Huns",
    "Incas",
    "Italians",
    "Japanese",
    "Khmer",
    "Koreans",
    "Lithuanians",
    "Magyars",
    "Malay",
    "Malians",
    "Mayans",
    "Mongols",
    "Persians",
    "Poles",
    "Portuguese",
    "Romans",
    "Saracens",
    "Sicilians",
    "Slavs",
    "Spanish",
    "Tatars",
    "Teutons",
    "Turks",
    "Vietnamese",
    "Vikings",
]

from .build_order_editor import BuildOrderEditorDialog as BuildOrderDialog
from .library_cards import BuildOrderCard
from .notifications import show_toast
from .theme import apply_tab_with_table

# ---------------------------------------------------------------------------


class _ImportWorker(QObject):
    """Worker that fetches a build order on a background thread."""

    finished = Signal(object)  # BuildOrder
    error = Signal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self) -> None:
        try:
            bo = import_from_url(self.url)
            self.finished.emit(bo)
        except Exception as exc:
            logger.error("Import failed: %s", exc, exc_info=True)
            self.error.emit(str(exc))


# Build order editor: see build_order_editor.py (imported as BuildOrderDialog above)


# ---------------------------------------------------------------------------
# URL import dialog
# ---------------------------------------------------------------------------


class UrlImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import from buildorderguide.com")
        self.setFixedWidth(520)
        apply_tab_with_table(self)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info = QLabel(
            "Paste a full build order URL from buildorderguide.com.\n"
            "Example: https://www.buildorderguide.com/builds/gvY357U7kHOBqI6QsDx8"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        layout.addWidget(info)

        self.ed_url = QLineEdit()
        self.ed_url.setPlaceholderText("https://www.buildorderguide.com/builds/…")
        layout.addWidget(self.ed_url)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #e74c3c; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def url(self) -> str:
        return self.ed_url.text().strip()


# ---------------------------------------------------------------------------
# Main Library Tab
# ---------------------------------------------------------------------------


class LibraryTab(QWidget):
    """
    Full build order library UI with search, filter, import, and edit.

    Signals:
        build_order_selected(BuildOrder): Emitted when user double-clicks a row
                                         or clicks "Load to Overlay".
    """

    build_order_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.apply_theme()
        self.refresh()

    def apply_theme(self, theme_name: str | None = None) -> None:
        apply_tab_with_table(self)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ── Toolbar ───────────────────────────────────────────────────────
        toolbar = QHBoxLayout()

        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText("Search build orders…")
        self.ed_search.textChanged.connect(self._on_filter_changed)

        self.cb_civ_filter = QComboBox()
        self.cb_civ_filter.addItem("All Civs")
        self.cb_civ_filter.addItems(CIVS[1:])  # skip "Any"
        self.cb_civ_filter.currentTextChanged.connect(self._on_filter_changed)

        self.chk_favs = QCheckBox("Favorites only")
        self.chk_favs.setStyleSheet("color: #ecf0f1;")
        self.chk_favs.toggled.connect(self._on_filter_changed)

        btn_url = QPushButton("🌐 Import URL")
        btn_url.clicked.connect(self._on_import_url)
        btn_file = QPushButton("📁 Import File")
        btn_file.clicked.connect(self._on_import_file)
        btn_new = QPushButton("+ New")
        btn_new.clicked.connect(self._on_new)
        btn_export = QPushButton("⬇ Export All")
        btn_export.clicked.connect(self._on_export)
        self.btn_view_table = QPushButton("☰ Table")
        self.btn_view_table.setCheckable(True)
        self.btn_view_table.setChecked(True)
        self.btn_view_cards = QPushButton("▦ Cards")
        self.btn_view_cards.setCheckable(True)
        self.btn_view_table.clicked.connect(lambda: self._set_view(0))
        self.btn_view_cards.clicked.connect(lambda: self._set_view(1))

        for w in [self.ed_search, self.cb_civ_filter, self.chk_favs]:
            toolbar.addWidget(w)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_view_table)
        toolbar.addWidget(self.btn_view_cards)
        for btn in [btn_url, btn_file, btn_new, btn_export]:
            toolbar.addWidget(btn)
        root.addLayout(toolbar)

        self._stack = QStackedWidget()
        # ── Table view ────────────────────────────────────────────────────
        table_page = QWidget()
        table_layout = QVBoxLayout(table_page)
        table_layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["⭐", "Name", "Civ", "Strategy", "Steps", "Difficulty", "Updated"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 32)
        self.table.setColumnWidth(4, 60)
        self.table.setColumnWidth(5, 80)
        self.table.doubleClicked.connect(self._on_row_double_click)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("QTableWidget::item:alternate { background: #1a1a20; }")
        table_layout.addWidget(self.table)
        self._stack.addWidget(table_page)

        # ── Card grid view ────────────────────────────────────────────────
        card_scroll = QScrollArea()
        card_scroll.setWidgetResizable(True)
        card_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        card_host = QWidget()
        self._card_grid = QGridLayout(card_host)
        self._card_grid.setSpacing(12)
        card_scroll.setWidget(card_host)
        self._stack.addWidget(card_scroll)

        root.addWidget(self._stack)

        # ── Action buttons ────────────────────────────────────────────────
        action_row = QHBoxLayout()
        btn_load = QPushButton("▶ Load to Overlay")
        btn_load.setStyleSheet(
            "QPushButton { background: #1c3a5c; color: #3498db; border: 1px solid #2c5a8c; border-radius: 6px; padding: 6px 14px; font-weight: bold; }"
        )
        btn_load.clicked.connect(self._on_load_overlay)
        btn_edit = QPushButton("✏ Edit")
        btn_edit.clicked.connect(self._on_edit)
        btn_fav = QPushButton("⭐ Toggle Favorite")
        btn_fav.clicked.connect(self._on_toggle_fav)
        btn_delete = QPushButton("🗑 Delete")
        btn_delete.setStyleSheet(
            "QPushButton { color: #e74c3c; } QPushButton:hover { border-color: #e74c3c; }"
        )
        btn_delete.clicked.connect(self._on_delete)
        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet("color: #7f8c8d; font-size: 11px;")

        action_row.addWidget(btn_load)
        action_row.addWidget(btn_edit)
        action_row.addWidget(btn_fav)
        action_row.addWidget(btn_delete)
        action_row.addStretch()
        action_row.addWidget(self.lbl_count)
        root.addLayout(action_row)

        self._all_build_orders: list[BuildOrder] = []
        self._filtered: list[BuildOrder] = []
        self._thread = None
        self._worker = None

    def _set_view(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        self.btn_view_table.setChecked(index == 0)
        self.btn_view_cards.setChecked(index == 1)

    # ── Data ──────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Reload build orders from DB and re-render the table."""
        self._all_build_orders = get_all_build_orders()
        self._apply_filters()

    def _apply_filters(self) -> None:
        search = self.ed_search.text().strip().lower()
        civ = self.cb_civ_filter.currentText()
        favs = self.chk_favs.isChecked()

        filtered = [
            bo
            for bo in self._all_build_orders
            if (
                not search
                or search in bo.name.lower()
                or search in bo.civ.lower()
                or search in bo.strategy.lower()
            )
            and (civ == "All Civs" or bo.civ in (civ, "Any"))
            and (not favs or bo.is_favorite)
        ]
        self._filtered = filtered
        self._populate_table(filtered)
        self._populate_cards(filtered)

    def _populate_cards(self, build_orders: list[BuildOrder]) -> None:
        while self._card_grid.count():
            item = self._card_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        cols = 3
        for i, bo in enumerate(build_orders):
            card = BuildOrderCard(bo)
            card.clicked.connect(self._on_card_clicked)
            card.load_requested.connect(self.build_order_selected.emit)
            self._card_grid.addWidget(card, i // cols, i % cols)

    def _on_card_clicked(self, bo: BuildOrder) -> None:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == bo.id:
                self.table.selectRow(row)
                break

    def _populate_table(self, build_orders: list[BuildOrder]) -> None:
        self.table.setRowCount(0)
        for bo in build_orders:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem("⭐" if bo.is_favorite else ""))
            self.table.setItem(row, 1, QTableWidgetItem(bo.name))
            self.table.setItem(row, 2, QTableWidgetItem(bo.civ))
            self.table.setItem(row, 3, QTableWidgetItem(bo.strategy))
            self.table.setItem(row, 4, QTableWidgetItem(str(bo.step_count)))
            self.table.setItem(row, 5, QTableWidgetItem(bo.difficulty))
            self.table.setItem(
                row, 6, QTableWidgetItem(bo.updated_at[:10] if bo.updated_at else "")
            )
            # Store bo.id in the first column item
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, bo.id)
        self.lbl_count.setText(f"{len(build_orders)} build orders")

    def _on_filter_changed(self) -> None:
        self._apply_filters()

    def _selected_bo_id(self) -> Optional[int]:
        rows = self.table.selectedItems()
        if not rows:
            return None
        row = self.table.currentRow()
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _selected_bo(self) -> Optional[BuildOrder]:
        bo_id = self._selected_bo_id()
        if bo_id is None:
            return None
        return next((bo for bo in self._all_build_orders if bo.id == bo_id), None)

    # ── Actions ───────────────────────────────────────────────────────────

    def _on_row_double_click(self) -> None:
        bo = self._selected_bo()
        if bo:
            self.build_order_selected.emit(bo)

    def _on_load_overlay(self) -> None:
        bo = self._selected_bo()
        if bo:
            self.build_order_selected.emit(bo)
        else:
            QMessageBox.information(self, "No selection", "Select a build order first.")

    def _on_import_url(self) -> None:
        dlg = UrlImportDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        url = dlg.url()
        if not url:
            return

        # Run import on background thread to avoid freezing UI
        self._thread = QThread(self)
        self._worker = _ImportWorker(url)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_import_success)
        self._worker.error.connect(self._on_import_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    def _on_import_success(self, bo: BuildOrder) -> None:
        saved = import_and_save(bo)
        self.refresh()
        QMessageBox.information(self, "Imported", f"'{saved.name}' imported successfully!")
        logger.info("URL import complete: '%s'", saved.name)

    def _on_import_error(self, msg: str) -> None:
        QMessageBox.warning(self, "Import Failed", f"Could not import build order:\n\n{msg}")
        show_toast("Build order import failed.", "error")

    def _on_import_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Build Order",
            "",
            "Build Order Files (*.json *.txt);;JSON (*.json);;Text (*.txt)",
        )
        if not path:
            return
        try:
            if path.lower().endswith(".txt"):
                bo = import_from_txt_file(path)
            else:
                bo = import_from_json_file(path)
            saved = import_and_save(bo)
            self.refresh()
            QMessageBox.information(self, "Imported", f"'{saved.name}' imported from file.")
        except Exception as exc:
            QMessageBox.warning(self, "Import Error", str(exc))

    def _on_new(self) -> None:
        dlg = BuildOrderDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            bo = dlg.result_build_order()
            if bo:
                save_build_order(bo)
                self.refresh()

    def _on_edit(self) -> None:
        bo = self._selected_bo()
        if not bo:
            QMessageBox.information(self, "No selection", "Select a build order to edit.")
            return
        dlg = BuildOrderDialog(bo=bo, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            edited = dlg.result_build_order()
            if edited:
                save_build_order(edited)
                self.refresh()

    def _on_toggle_fav(self) -> None:
        bo_id = self._selected_bo_id()
        if bo_id:
            toggle_favorite(bo_id)
            self.refresh()

    def _on_delete(self) -> None:
        bo = self._selected_bo()
        if not bo:
            return
        reply = QMessageBox.question(
            self,
            "Delete Build Order",
            f"Delete '{bo.name}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_build_order(bo.id)
            self.refresh()

    def _on_export(self) -> None:
        from ..build_orders.manager import export_all_to_json

        path = export_all_to_json()
        QMessageBox.information(self, "Exported", f"Build orders exported to:\n{path}")

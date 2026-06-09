"""
TRINKER - Build Order Library Tab
Browse, search, import, and manage all build orders.
Supports URL import from buildorderguide.com, JSON/TXT file import, and inline editing.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QDialog,
    QDialogButtonBox, QTextEdit, QFormLayout, QMessageBox, QFileDialog,
    QSplitter, QFrame, QCheckBox, QSpinBox, QGroupBox,
)

from ..build_orders.importer import (
    import_from_url, import_from_json_file, import_from_txt_file
)
from ..build_orders.manager import (
    get_all_build_orders, save_build_order, delete_build_order,
    toggle_favorite, import_and_save
)
from ..build_orders.models import BuildOrder, BuildStep
from ..core.logger import logger

CIVS = [
    "Any", "Aztecs", "Bengalis", "Berbers", "Bohemians", "Britons", "Bulgarians",
    "Burgundians", "Burmese", "Byzantines", "Celts", "Chinese", "Cumans",
    "Dravidians", "Ethiopians", "Franks", "Goths", "Gurjaras", "Hindustanis",
    "Huns", "Incas", "Italians", "Japanese", "Khmer", "Koreans", "Lithuanians",
    "Magyars", "Malay", "Malians", "Mayans", "Mongols", "Persians", "Poles",
    "Portuguese", "Romans", "Saracens", "Sicilians", "Slavs", "Spanish",
    "Tatars", "Teutons", "Turks", "Vietnamese", "Vikings",
]

STYLE = """
QWidget { background: #111113; color: #ecf0f1; }
QLineEdit, QComboBox, QTextEdit, QSpinBox {
    background: #1e1e22; border: 1px solid #2c2c2e;
    border-radius: 6px; padding: 5px 8px; color: #ecf0f1;
}
QTableWidget {
    background: #15151a; border: 1px solid #2c2c2e;
    gridline-color: #1e1e22; border-radius: 6px;
}
QTableWidget::item { padding: 6px 8px; }
QTableWidget::item:selected { background: #1c3a5c; }
QHeaderView::section {
    background: #1e1e22; color: #7f8c8d;
    border: none; padding: 6px 8px; font-size: 11px; letter-spacing: 1px;
}
QPushButton {
    background: #1e1e22; border: 1px solid #2c2c2e;
    border-radius: 6px; padding: 6px 14px; color: #ecf0f1;
}
QPushButton:hover { background: #25252c; border-color: #3498db; }
QPushButton:pressed { background: #1a1a25; }
QGroupBox { border: 1px solid #2c2c2e; border-radius: 6px; margin-top: 8px; padding-top: 6px; }
QGroupBox::title { color: #7f8c8d; padding: 0 6px; }
"""


# ---------------------------------------------------------------------------
# Background import worker (keeps UI responsive)
# ---------------------------------------------------------------------------

class _ImportWorker(QObject):
    """Worker that fetches a build order on a background thread."""
    finished  = Signal(object)   # BuildOrder
    error     = Signal(str)

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


# ---------------------------------------------------------------------------
# Build order detail / edit dialog
# ---------------------------------------------------------------------------

class BuildOrderDialog(QDialog):
    """Modal dialog for viewing and editing a build order's metadata and steps."""

    def __init__(self, bo: Optional[BuildOrder] = None, parent=None):
        super().__init__(parent)
        self.bo = bo or BuildOrder(name="New Build Order")
        self.setWindowTitle("Edit Build Order" if bo else "New Build Order")
        self.setMinimumSize(720, 580)
        self.setStyleSheet(STYLE)
        self._setup_ui()
        self._populate()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(8)

        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText("e.g. Spanish 18 pop Scout Rush")
        form.addRow("Name *", self.ed_name)

        self.cb_civ = QComboBox()
        self.cb_civ.addItems(CIVS)
        form.addRow("Civilization", self.cb_civ)

        self.ed_strategy = QLineEdit()
        self.ed_strategy.setPlaceholderText("e.g. Fast Castle, Scout Rush")
        form.addRow("Strategy", self.ed_strategy)

        self.cb_difficulty = QComboBox()
        self.cb_difficulty.addItems(["Easy", "Medium", "Hard"])
        form.addRow("Difficulty", self.cb_difficulty)

        self.ed_tags = QLineEdit()
        self.ed_tags.setPlaceholderText("Comma-separated, e.g. rush, knight, meta")
        form.addRow("Tags", self.ed_tags)

        self.ed_author = QLineEdit()
        form.addRow("Author", self.ed_author)

        self.ed_notes = QTextEdit()
        self.ed_notes.setMaximumHeight(80)
        self.ed_notes.setPlaceholderText("Overview, strategy notes…")
        form.addRow("Notes", self.ed_notes)

        root.addLayout(form)

        # Steps editor
        steps_label = QLabel("Steps")
        steps_label.setStyleSheet("color: #7f8c8d; font-size: 11px; letter-spacing: 1px; font-weight: bold;")
        root.addWidget(steps_label)

        self.steps_table = QTableWidget(0, 6)
        self.steps_table.setHorizontalHeaderLabels(["#", "Time", "Pop", "Description", "Age", "Notes"])
        self.steps_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.steps_table.setAlternatingRowColors(True)
        self.steps_table.setStyleSheet("QTableWidget::item:alternate { background: #1a1a20; }")
        root.addWidget(self.steps_table)

        # Steps buttons
        steps_btn_row = QHBoxLayout()
        btn_add = QPushButton("+ Add Step")
        btn_add.clicked.connect(self._add_step_row)
        btn_del = QPushButton("✕ Delete Selected")
        btn_del.clicked.connect(self._delete_step_row)
        steps_btn_row.addWidget(btn_add)
        steps_btn_row.addWidget(btn_del)
        steps_btn_row.addStretch()
        root.addLayout(steps_btn_row)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _populate(self) -> None:
        bo = self.bo
        self.ed_name.setText(bo.name)
        idx = self.cb_civ.findText(bo.civ)
        self.cb_civ.setCurrentIndex(max(0, idx))
        self.ed_strategy.setText(bo.strategy)
        diff_idx = self.cb_difficulty.findText(bo.difficulty)
        self.cb_difficulty.setCurrentIndex(max(0, diff_idx))
        self.ed_tags.setText(", ".join(bo.tags))
        self.ed_author.setText(bo.author)
        self.ed_notes.setPlainText(bo.notes)

        for step in bo.steps:
            self._add_step_row(step)

    def _add_step_row(self, step: Optional[BuildStep] = None) -> None:
        row = self.steps_table.rowCount()
        self.steps_table.insertRow(row)
        self.steps_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.steps_table.setItem(row, 1, QTableWidgetItem(step.time_str if step else ""))
        self.steps_table.setItem(row, 2, QTableWidgetItem(str(step.population) if step and step.population else ""))
        self.steps_table.setItem(row, 3, QTableWidgetItem(step.description if step else ""))
        self.steps_table.setItem(row, 4, QTableWidgetItem(step.age or "" if step else ""))
        self.steps_table.setItem(row, 5, QTableWidgetItem(step.notes if step else ""))

    def _delete_step_row(self) -> None:
        rows = {idx.row() for idx in self.steps_table.selectedIndexes()}
        for row in sorted(rows, reverse=True):
            self.steps_table.removeRow(row)

    def result_build_order(self) -> Optional[BuildOrder]:
        """Return edited BuildOrder, or None if name is empty."""
        name = self.ed_name.text().strip()
        if not name:
            return None
        steps = []
        for row in range(self.steps_table.rowCount()):
            def cell(col): return (self.steps_table.item(row, col) or QTableWidgetItem("")).text().strip()
            desc = cell(3)
            if not desc:
                continue
            from ..build_orders.importer import _mmss_to_sec
            time_str = cell(1)
            steps.append(BuildStep(
                index=row + 1,
                time_str=time_str,
                time_sec=_mmss_to_sec(time_str),
                population=int(cell(2)) if cell(2).isdigit() else 0,
                description=desc,
                age=cell(4) or None,
                notes=cell(5),
            ))
        self.bo.name = name
        self.bo.civ = self.cb_civ.currentText()
        self.bo.strategy = self.ed_strategy.text().strip()
        self.bo.difficulty = self.cb_difficulty.currentText()
        self.bo.tags = [t.strip() for t in self.ed_tags.text().split(",") if t.strip()]
        self.bo.author = self.ed_author.text().strip()
        self.bo.notes = self.ed_notes.toPlainText().strip()
        self.bo.steps = steps
        return self.bo


# ---------------------------------------------------------------------------
# URL import dialog
# ---------------------------------------------------------------------------

class UrlImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import from buildorderguide.com")
        self.setFixedWidth(520)
        self.setStyleSheet(STYLE)
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
        self.setStyleSheet(STYLE)
        self._setup_ui()
        self.refresh()

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
        self.cb_civ_filter.addItems(CIVS[1:])   # skip "Any"
        self.cb_civ_filter.currentTextChanged.connect(self._on_filter_changed)

        self.chk_favs = QCheckBox("Favorites only")
        self.chk_favs.setStyleSheet("color: #ecf0f1;")
        self.chk_favs.toggled.connect(self._on_filter_changed)

        btn_url    = QPushButton("🌐 Import URL")
        btn_url.clicked.connect(self._on_import_url)
        btn_file   = QPushButton("📁 Import File")
        btn_file.clicked.connect(self._on_import_file)
        btn_new    = QPushButton("+ New")
        btn_new.clicked.connect(self._on_new)
        btn_export = QPushButton("⬇ Export All")
        btn_export.clicked.connect(self._on_export)

        for w in [self.ed_search, self.cb_civ_filter, self.chk_favs]:
            toolbar.addWidget(w)
        toolbar.addStretch()
        for btn in [btn_url, btn_file, btn_new, btn_export]:
            toolbar.addWidget(btn)
        root.addLayout(toolbar)

        # ── Table ─────────────────────────────────────────────────────────
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["⭐", "Name", "Civ", "Strategy", "Steps", "Difficulty", "Updated"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 32)
        self.table.setColumnWidth(4, 60)
        self.table.setColumnWidth(5, 80)
        self.table.doubleClicked.connect(self._on_row_double_click)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("QTableWidget::item:alternate { background: #1a1a20; }")
        root.addWidget(self.table)

        # ── Action buttons ────────────────────────────────────────────────
        action_row = QHBoxLayout()
        btn_load   = QPushButton("▶ Load to Overlay")
        btn_load.setStyleSheet("QPushButton { background: #1c3a5c; color: #3498db; border: 1px solid #2c5a8c; border-radius: 6px; padding: 6px 14px; font-weight: bold; }")
        btn_load.clicked.connect(self._on_load_overlay)
        btn_edit   = QPushButton("✏ Edit")
        btn_edit.clicked.connect(self._on_edit)
        btn_fav    = QPushButton("⭐ Toggle Favorite")
        btn_fav.clicked.connect(self._on_toggle_fav)
        btn_delete = QPushButton("🗑 Delete")
        btn_delete.setStyleSheet("QPushButton { color: #e74c3c; } QPushButton:hover { border-color: #e74c3c; }")
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
        self._thread = None
        self._worker = None

    # ── Data ──────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Reload build orders from DB and re-render the table."""
        self._all_build_orders = get_all_build_orders()
        self._apply_filters()

    def _apply_filters(self) -> None:
        search = self.ed_search.text().strip().lower()
        civ    = self.cb_civ_filter.currentText()
        favs   = self.chk_favs.isChecked()

        filtered = [
            bo for bo in self._all_build_orders
            if (not search or search in bo.name.lower() or search in bo.civ.lower() or search in bo.strategy.lower())
            and (civ == "All Civs" or bo.civ in (civ, "Any"))
            and (not favs or bo.is_favorite)
        ]
        self._populate_table(filtered)

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
            self.table.setItem(row, 6, QTableWidgetItem(bo.updated_at[:10] if bo.updated_at else ""))
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

    def _on_import_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Build Order", "",
            "Build Order Files (*.json *.txt);;JSON (*.json);;Text (*.txt)"
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
            self, "Delete Build Order",
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

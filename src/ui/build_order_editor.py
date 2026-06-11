"""
TRINKER - Improved build order editor with drag-and-drop steps and resource fields.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from ..build_orders.importer import _mmss_to_sec
from ..build_orders.models import BuildOrder, BuildStep
from .theme import apply_tab_with_table

CIVS = [
    "Any", "Aztecs", "Bengalis", "Berbers", "Bohemians", "Britons", "Bulgarians",
    "Burgundians", "Burmese", "Byzantines", "Celts", "Chinese", "Cumans",
    "Dravidians", "Ethiopians", "Franks", "Goths", "Gurjaras", "Hindustanis",
    "Huns", "Incas", "Italians", "Japanese", "Khmer", "Koreans", "Lithuanians",
    "Magyars", "Malay", "Malians", "Mayans", "Mongols", "Persians", "Poles",
    "Portuguese", "Romans", "Saracens", "Sicilians", "Slavs", "Spanish",
    "Tatars", "Teutons", "Turks", "Vietnamese", "Vikings",
]

STEP_COLUMNS = ["#", "Time", "Pop", "F", "W", "G", "S", "Description", "Age", "Notes"]


class BuildOrderEditorDialog(QDialog):
    """Modal editor: metadata + draggable step table with resource targets."""

    def __init__(self, bo: Optional[BuildOrder] = None, parent=None):
        super().__init__(parent)
        self.bo = bo or BuildOrder(name="New Build Order")
        self.setWindowTitle("Edit Build Order" if bo else "New Build Order")
        self.setMinimumSize(900, 620)
        apply_tab_with_table(self)
        self._setup_ui()
        self._populate()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        form = QFormLayout()
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
        form.addRow("Tags", self.ed_tags)

        self.ed_author = QLineEdit()
        form.addRow("Author", self.ed_author)

        self.ed_notes = QTextEdit()
        self.ed_notes.setMaximumHeight(70)
        form.addRow("Notes", self.ed_notes)
        root.addLayout(form)

        hint = QLabel("Drag rows to reorder steps. F/W/G/S = food, wood, gold, stone targets.")
        hint.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        root.addWidget(hint)

        self.steps_table = QTableWidget(0, len(STEP_COLUMNS))
        self.steps_table.setHorizontalHeaderLabels(STEP_COLUMNS)
        self.steps_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        self.steps_table.setAlternatingRowColors(True)
        self.steps_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.steps_table.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.steps_table.setDragDropOverwriteMode(False)
        self.steps_table.model().rowsMoved.connect(self._renumber_steps)
        root.addWidget(self.steps_table)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("+ Add Step")
        btn_add.clicked.connect(lambda: self._add_step_row())
        btn_del = QPushButton("Delete Selected")
        btn_del.clicked.connect(self._delete_step_row)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()
        root.addLayout(btn_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
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
        values = [
            str(row + 1),
            step.time_str if step else "",
            str(step.population) if step and step.population else "",
            str(step.food) if step and step.food is not None else "",
            str(step.wood) if step and step.wood is not None else "",
            str(step.gold) if step and step.gold is not None else "",
            str(step.stone) if step and step.stone is not None else "",
            step.description if step else "",
            step.age or "" if step else "",
            step.notes if step else "",
        ]
        for col, val in enumerate(values):
            item = QTableWidgetItem(val)
            if col == 0:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.steps_table.setItem(row, col, item)

    def _delete_step_row(self) -> None:
        rows = sorted({idx.row() for idx in self.steps_table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.steps_table.removeRow(row)
        self._renumber_steps()

    def _renumber_steps(self, *_) -> None:
        for row in range(self.steps_table.rowCount()):
            item = self.steps_table.item(row, 0)
            if item:
                item.setText(str(row + 1))

    def _cell(self, row: int, col: int) -> str:
        item = self.steps_table.item(row, col)
        return item.text().strip() if item else ""

    def _optional_int(self, text: str) -> Optional[int]:
        return int(text) if text.isdigit() else None

    def _on_save(self) -> None:
        if not self.ed_name.text().strip():
            QMessageBox.warning(self, "Missing Name", "Build order name is required.")
            return
        self.accept()

    def result_build_order(self) -> Optional[BuildOrder]:
        name = self.ed_name.text().strip()
        if not name:
            return None
        steps: list[BuildStep] = []
        for row in range(self.steps_table.rowCount()):
            desc = self._cell(row, 7)
            if not desc:
                continue
            time_str = self._cell(row, 1)
            steps.append(BuildStep(
                index=len(steps) + 1,
                time_str=time_str,
                time_sec=_mmss_to_sec(time_str),
                population=int(self._cell(row, 2)) if self._cell(row, 2).isdigit() else 0,
                food=self._optional_int(self._cell(row, 3)),
                wood=self._optional_int(self._cell(row, 4)),
                gold=self._optional_int(self._cell(row, 5)),
                stone=self._optional_int(self._cell(row, 6)),
                description=desc,
                age=self._cell(row, 8) or None,
                notes=self._cell(row, 9),
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

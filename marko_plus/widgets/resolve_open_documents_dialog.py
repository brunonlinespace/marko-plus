# Plus-family shared implementation
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""Batch resolution dialog for closing several at-risk open documents."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ResolveOpenDocumentsDialog(QDialog):
    """Collect per-document close decisions before a multi-document transition."""

    def __init__(
        self,
        items: list[tuple[object, str, str, bool]],
        message: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Resolve Open Documents")
        self.setModal(True)
        self.setMinimumWidth(680)
        self._rows: list[tuple[object, QComboBox, bool]] = []

        layout = QVBoxLayout(self)
        label = QLabel(message, self)
        label.setWordWrap(True)
        layout.addWidget(label)

        self.tree = QTreeWidget(self)
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(("Document", "State", "Action"))
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        layout.addWidget(self.tree)

        for key, document_name, state_text, ordinary_dirty in items:
            row = QTreeWidgetItem((document_name, state_text, ""))
            self.tree.addTopLevelItem(row)
            chooser = QComboBox(self.tree)
            if ordinary_dirty:
                chooser.addItem("Save", "save")
                chooser.addItem("Discard", "discard")
            else:
                chooser.addItem("Resolve Individually…", "resolve")
            self.tree.setItemWidget(row, 2, chooser)
            self._rows.append((key, chooser, ordinary_dirty))

        self.tree.resizeColumnToContents(0)
        self.tree.resizeColumnToContents(1)

        hint = QLabel(
            "Save All and Discard All affect ordinary unsaved documents only. "
            "Missing or externally changed documents keep their protected individual workflow.",
            self,
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(self)
        save_all = buttons.addButton("Save All", QDialogButtonBox.ButtonRole.ActionRole)
        discard_all = buttons.addButton("Discard All", QDialogButtonBox.ButtonRole.ActionRole)
        continue_button = buttons.addButton("Continue", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_button = buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        save_all.clicked.connect(lambda: self._accept_with_ordinary_action("save"))
        discard_all.clicked.connect(lambda: self._accept_with_ordinary_action("discard"))
        continue_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(buttons)

    def _set_ordinary_action(self, action: str) -> None:
        for _key, chooser, ordinary_dirty in self._rows:
            if not ordinary_dirty:
                continue
            index = chooser.findData(action)
            if index >= 0:
                chooser.setCurrentIndex(index)

    def _accept_with_ordinary_action(self, action: str) -> None:
        self._set_ordinary_action(action)
        self.accept()

    def decisions(self) -> list[tuple[object, str]]:
        return [(key, str(chooser.currentData())) for key, chooser, _ordinary in self._rows]

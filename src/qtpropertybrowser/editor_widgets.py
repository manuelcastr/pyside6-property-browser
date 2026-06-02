# -*- coding: utf-8 -*-
#############################################################################
##
## Copyright (C) 2013 Digia Plc and/or its subsidiary(-ies).
## Contact: http://www.qt-project.org/legal
##
## Modifications Copyright (C) 2026 Manuel Alejandro Castro Fuentes
## Contact: <manuelcastr88@gmail.com>
## Adaptations for PySide6 migration, refactoring, and enhancements.
##
## This file is part of the Qt Solutions component.
##
## $QT_BEGIN_LICENSE:BSD$
## You may use this file under the terms of the BSD license as follows:
##
## "Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions are
## met:
##   * Redistributions of source code must retain the above copyright
##     notice, this list of conditions and the following disclaimer.
##   * Redistributions in binary form must reproduce the above copyright
##     notice, this list of conditions and the following disclaimer in
##     the documentation and/or other materials provided with the
##     distribution.
##   * Neither the name of Digia Plc and its Subsidiary(-ies) nor the names
##     of its contributors may be used to endorse or promote products derived
##     from this software without specific prior written permission.
##
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
## "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
## LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
## A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
## OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
## SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
## LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
## DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
## THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
## OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
##
## $QT_END_LICENSE$
##
############################################################################/
from PySide6.QtCore import Qt, Signal, QObject, QEvent
from PySide6.QtGui import (
    QBrush, QColor, QFont, QPainter, QPaintEvent, QKeyEvent,
    QMouseEvent, QKeySequence, QFocusEvent
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QCheckBox, QToolButton,
    QHBoxLayout, QSpacerItem, QStyleOption, QStyle, QSizePolicy,
    QColorDialog, QLineEdit, QFontDialog
)

from qtpropertybrowser.utils import (
    fontValuePixmap,
    fontValueText,
    brushValuePixmap,
    colorValueText
)


# Originally sourced from .\QtProperty\qtpropertybrowserutils.py
# noinspection PyPep8Naming
class QtBoolEdit(QWidget):
    """
    Custom widget for editing boolean values with a checkbox.

    This widget wraps a QCheckBox and provides additional functionality
    for controlling text visibility. When text is visible, the checkbox
    displays 'True' or 'False' labels. When hidden, only the checkbox
    indicator is shown.

    :ivar toggled: Signal emitted when the checkbox state changes
    """
    toggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the boolean edit widget.

        Creates a checkbox-based widget with configurable text visibility.
        The layout adapts to the application's layout direction for proper
        margin placement.

        :param parent: The parent QWidget
        """
        super().__init__(parent)
        self._check_box = QCheckBox(self)
        self._text_visible = True
        self._value_labels = {
            False: self.tr('False'),
            True: self.tr('True')
        }
        layout = QHBoxLayout()
        if QApplication.layoutDirection() == Qt.LayoutDirection.LeftToRight:
            layout.setContentsMargins(4, 0, 0, 0)
        else:
            layout.setContentsMargins(0, 0, 4, 0)
        layout.setAlignment(layout.alignment() | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._check_box)
        self.setLayout(layout)
        self._check_box.toggled.connect(self.onToggled)
        self.setFocusProxy(self._check_box)
        status = self._check_box.isChecked()
        self._check_box.setText(self._value_labels[status])

    def checkState(self) -> Qt.CheckState:
        """
        Return the current check state of the checkbox.

        :return: The current check state (Unchecked, Checked, or PartiallyChecked)
        """
        return self._check_box.checkState()

    def setCheckState(self, state: Qt.CheckState) -> None:
        """
        Set the check state of the checkbox.

        :param state: The new check state
        """
        self._check_box.setCheckState(state)

    def isChecked(self) -> bool:
        """
        Check if the checkbox is currently checked.

        :return: True if checked, False otherwise
        """
        return self._check_box.isChecked()

    def setChecked(self, checked: bool) -> None:
        """
        Set the checked state of the checkbox.

        Updates the checkbox text if text visibility is enabled.

        :param checked: The new checked state
        """
        self._check_box.setChecked(checked)
        if self._text_visible:
            self._check_box.setText(self._value_labels[checked])

    def textVisible(self) -> bool:
        """
        Check if text labels are visible on the checkbox.

        :return: True if text is visible, False otherwise
        """
        return self._text_visible

    def setTextVisible(self, text_visible: bool) -> None:
        """
        Set the text visibility for the checkbox.

        When enabled, displays 'True' or 'False' labels. When disabled,
        shows only the checkbox indicator without text.

        :param text_visible: True to show text, False to hide it
        """
        if self._text_visible == text_visible:
            return
        self._text_visible = text_visible
        if self._text_visible:
            status = self._check_box.isChecked()
            self._check_box.setText(self._value_labels[status])
        else:
            self._check_box.setText('')

    def onToggled(self, status: bool) -> None:
        """
        Handle checkbox toggle events.

        Updates the checkbox text based on the new state and text visibility
        setting, then emits the toggled signal.

        :param status: The new checked state
        """
        if self._text_visible:
            self._check_box.setText(self._value_labels[status])
        else:
            self._check_box.setText('')
        self.toggled.emit(status)

    def blockCheckBoxSignals(self, block: bool) -> bool:
        """
        Block or unblock checkbox signals.

        :param block: True to block signals, False to unblock
        :return: The previous block state
        """
        return self._check_box.blockSignals(block)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse press events.

        Captures left mouse button clicks and forwards them to the checkbox.
        Other mouse buttons are handled by the base class.

        :param event: The mouse press event
        """
        if event.buttons() == Qt.MouseButton.LeftButton:
            self._check_box.click()
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Handle paint events for the widget.

        Draws the widget using the current style to ensure consistent
        appearance with the application theme.

        :param event: The paint event
        """
        option = QStyleOption()
        option.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(
            QStyle.PrimitiveElement.PE_Widget,
            option,
            painter,
            self
        )


# Originally sourced from .\QtProperty\qteditorfactory.py
# noinspection PyPep8Naming
class QtColorEdit(QWidget):
    """
    Custom widget for editing color (QColor) values.

    This widget provides a color editor with a color preview pixmap, text
    representation of the color value, and a button to open a color dialog.
    The color dialog includes alpha channel support for transparency editing.

    :ivar valueChanged: Signal emitted when the color value changes
    """
    valueChanged = Signal(QColor)


    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the color edit widget.

        Creates a horizontal layout with a color preview pixmap, color value
        label, and a button ('...') to open the color dialog. The layout
        adapts to the application's layout direction for proper margin placement.

        :param parent: The parent QWidget
        """
        super().__init__(parent)
        self._color: QColor = QColor()
        self._pixmap_label: QLabel = QLabel()
        self._label: QLabel = QLabel()
        self._button: QToolButton = QToolButton()

        layout = QHBoxLayout(self)
        decoration_margin = 4
        if QApplication.layoutDirection() == Qt.LayoutDirection.LeftToRight:
            layout.setContentsMargins(decoration_margin, 0, 0, 0)
        else:
            layout.setContentsMargins(0, 0, decoration_margin, 0)
        layout.setAlignment(
            layout.alignment() | Qt.AlignmentFlag.AlignVCenter
        )
        layout.setSpacing(2)
        layout.addWidget(self._pixmap_label)
        layout.addWidget(self._label)

        policies = QSizePolicy.Policy
        layout.addItem(
            QSpacerItem(0, 0, policies.Expanding, policies.Ignored)
        )
        self._button.setSizePolicy(policies.Fixed, policies.Ignored)

        self._button.setFixedWidth(20)
        self._button.setText(self.tr("..."))
        self._button.installEventFilter(self)
        self._button.clicked.connect(self.buttonClicked)
        self.setFocusProxy(self._button)
        self.setFocusPolicy(self._button.focusPolicy())

        layout.addWidget(self._button)
        self._pixmap_label.setPixmap(brushValuePixmap(QBrush(self._color)))
        self._label.setText(colorValueText(self._color))

    def setValue(self, color: QColor) -> None:
        """
        Set the current color value.

        Updates the color preview pixmap and text representation. Does nothing
        if the new color is the same as the current color.

        :param color: The new color value
        """
        if self._color == color:
            return
        self._color = color
        self._pixmap_label.setPixmap(brushValuePixmap(QBrush(color)))
        self._label.setText(colorValueText(color))

    def buttonClicked(self) -> None:
        """
        Handle button click to open the color dialog.

        Opens a QColorDialog with alpha channel support. If the user selects
        a different color, updates the widget value and emits valueChanged.
        """
        old_rgba = self._color
        new_rgba = QColorDialog.getColor(
            old_rgba,
            self,
            '',
            QColorDialog.ColorDialogOption.ShowAlphaChannel
        )
        if new_rgba != old_rgba:
            self.setValue(new_rgba)
            self.valueChanged.emit(self._color)

    def eventFilter(self, obj : QObject, event: QEvent | QKeyEvent) -> bool:
        """
        Filter events for the tool button.

        Prevents the QToolButton from handling Enter/Escape keys that are
        meant to control the delegate editor. These keys are ignored to
        allow proper editor delegation behavior.

        :param obj: The object being filtered
        :param event: The event to filter
        :return: True if the event was handled, False otherwise
        """
        if (
            obj == self._button
            and isinstance(event, QKeyEvent)
            and event.type() in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease)
            and event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Enter, Qt.Key.Key_Return)
        ):
            event.ignore()
            return True
        return super().eventFilter(obj, event)


# Originally sourced from .\QtProperty\qteditorfactory.py
# noinspection PyPep8Naming
class QtCharEdit(QLineEdit):
    """
    Custom line edit widget for editing single-character strings.

    This widget extends QLineEdit with constraints to ensure only one
    printable character can be entered. Automatically selects all text
    on focus for easy replacement, and handles paste operations by
    extracting the last printable character.

    :ivar valueChanged: Signal emitted when the character value changes
    """
    valueChanged = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the character edit widget.

        Sets maximum length to 1 character and connects textChanged to
        the valueChanged signal for compatibility with the editor factory
        system.

        :param parent: The parent QWidget
        """
        super().__init__(parent)
        self.setMaxLength(1)  # Enforce max length visually and internally
        self.textChanged.connect(self.valueChanged)

    def value(self) -> str:
        """
        Return the current character value.

        Alias to the text() function for compatibility with the
        editor factory system.

        :return: The current single-character string
        """
        return self.text()

    def setValue(self, value: str) -> None:
        """
        Set the character value.

        Alias to the setText() function for compatibility with the editor
        factory system.

        :param value: The new single-character string
        """
        self.setText(value)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Handle key press events for single-character input.

        Replaces the current character with any new printable character
        instead of appending. Handles paste operations by extracting the
        last printable character from the clipboard. Backspace and Delete
        keys work normally to clear the field.

        :param event: The key press event
        """
        if (
            len(self.text()) >= 1
            and event.key() not in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete)
        ):
            # Replace with new character instead of ignoring
            self.setText(event.text())
            return
        if event.matches(QKeySequence.StandardKey.Paste):
            self.setText(QApplication.clipboard().text())
            return
        super().keyPressEvent(event)

    def setText(self, text: str | None) -> None:
        """
        Set the text, keeping only one printable character.

        Filters the input text to extract printable characters only.
        If any printable characters exist, keeps the last one. If no
        printable characters are found, the current text remains unchanged.

        :param text: The text to set (will be filtered to single character)
        """
        filtered  = ['', ]
        if text:
            filtered = [char for char in text if char.isprintable()]
        super().setText(filtered[-1] if filtered else self.text())

    def focusInEvent(self, event: QFocusEvent) -> None:
        """
        Handle focus in events.

        Automatically selects all text when the widget receives focus,
        allowing immediate replacement of the character with new input.

        :param event: The focus event
        """
        self.selectAll()
        super().focusInEvent(event)


# Originally sourced from .\QtProperty\qteditorfactory.py
# noinspection PyPep8Naming
class QtFontEdit(QWidget):
    """
    Custom widget for editing font (QFont) values.

    This widget provides a font editor with a font preview pixmap, text
    representation of the font (family and point size), and a button to
    open a font dialog. The font dialog allows selection of all font
    attributes while preserving unchanged properties.

    :ivar valueChanged: Signal emitted when the font value changes
    """
    valueChanged = Signal(QFont)

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the font edit widget.

        Creates a horizontal layout with a font preview pixmap, font value
        label, and a button ('...') to open the font dialog. The layout
        adapts to the application's layout direction for proper margin placement.

        :param parent: The parent QWidget
        """
        super().__init__(parent)
        self._font: QFont = QFont()
        self._label: QLabel = QLabel()
        self._pixmap_label: QLabel = QLabel()

        layout = QHBoxLayout(self)
        decoration_margin = 4
        if QApplication.layoutDirection() == Qt.LayoutDirection.LeftToRight:
            layout.setContentsMargins(decoration_margin, 0, 0, 0)
        else:
            layout.setContentsMargins(0, 0, decoration_margin, 0)

        policies = QSizePolicy.Policy
        layout.setSpacing(1)
        layout.addWidget(self._pixmap_label)
        layout.addWidget(self._label)
        layout.addItem(
            QSpacerItem(0, 0, policies.Expanding, policies.Ignored)
        )

        self._button: QToolButton = QToolButton()
        self._button.setSizePolicy(policies.Fixed, policies.Ignored)
        self._button.setFixedWidth(20)
        self.setFocusProxy(self._button)
        self.setFocusPolicy(self._button.focusPolicy())
        self._button.setText(self.tr("..."))
        self._button.installEventFilter(self)
        self._button.clicked.connect(self.buttonClicked)
        layout.addWidget(self._button)
        self._pixmap_label.setPixmap(fontValuePixmap(self._font))
        self._label.setText(fontValueText(self._font))

    def value(self) -> QFont:
        """
        Return the current font value.

        :return: The current font
        """
        return self._font

    def setValue(self, font: QFont) -> None:
        """
        Set the current font value.

        Updates the font preview pixmap and text representation.
        Does nothing if the new font is the same as the current font.

        :param font: The new font value
        """
        if self._font == font:
            return
        self._font = font
        self._pixmap_label.setPixmap(fontValuePixmap(font))
        self._label.setText(fontValueText(font))

    def buttonClicked(self) -> None :
        """
        Handle button click to open the font dialog.

        Opens a QFontDialog for font selection. When a new font is selected,
        only updates attributes that have actually changed to prevent unintended
        mask changes. This preserves attributes that the user didn't modify
        in the dialog. Emits valueChanged if the font changes.
        """
        ok, new_font = QFontDialog.getFont(self._font, self, self.tr("Select Font"))
        if ok and new_font != self._font:
            font = QFont(self._font)
            # Prevent mask for unchanged attributes,
            # don't change other attributes
            if self._font.family() != new_font.family():
                font.setFamily(new_font.family())
            if self._font.pointSize() != new_font.pointSize():
                font.setPointSize(new_font.pointSize())
            if self._font.bold() != new_font.bold():
                font.setBold(new_font.bold())
            if self._font.italic() != new_font.italic():
                font.setItalic(new_font.italic())
            if self._font.underline() != new_font.underline():
                font.setUnderline(new_font.underline())
            if self._font.strikeOut() != new_font.strikeOut():
                font.setStrikeOut(new_font.strikeOut())
            if self._font.weight() != new_font.weight():
                font.setWeight(new_font.weight())
            self.setValue(font)
            self.valueChanged.emit(font)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """
        Filter events for the tool button.

        Prevents the QToolButton from handling Enter/Escape keys that are
        meant to control the delegate editor. These keys are ignored to
        allow proper editor delegation behavior.

        :param obj: The object being filtered
        :param event: The event to filter
        :return: True if the event was handled, False otherwise
        """
        if obj == self._button:
            if (
                isinstance(event, QKeyEvent)
                and event.type() in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease)
            ):
                if event.key() in (
                        Qt.Key.Key_Escape,
                        Qt.Key.Key_Enter,
                        Qt.Key.Key_Return
                ):
                    event.ignore()
                    return True
        return super().eventFilter(obj, event)

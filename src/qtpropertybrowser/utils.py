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
import re

from PySide6.QtCore import QObject, Qt, QRect, QRectF
from PySide6.QtGui import QIcon, QCursor, QPixmap, QPainter, QBrush, QImage, QColor, QFont, QTextOption
from PySide6.QtWidgets import QStyleOptionButton, QStyle, QApplication

import qtpropertybrowser.qtpropertybrowser_rc  # noqa


# Originally sourced from .\QtProperty\qtpropertymanager.py
def draw_check_box(state: bool) -> QIcon:
    """
    Draw a checkbox icon for the given state.

    Creates a styled checkbox icon using the application's current style.
    The icon is sized appropriately for list view items to prevent scaling.

    :param state: The checkbox state (True for checked, False for unchecked)
    :return: The checkbox icon
    """
    option = QStyleOptionButton()
    if state:
        option.state |= QStyle.StateFlag.State_On
    else:
        option.state |= QStyle.StateFlag.State_Off
    option.state |= QStyle.StateFlag.State_Enabled
    style = QApplication.style()
    # Figure out size of an indicator and make sure it is not scaled down in a list
    # view item by making the pixmap as big as a list view icon and centering the
    # indicator in it.(if it is smaller, it can't be helped)
    indicator_width = style.pixelMetric(QStyle.PixelMetric.PM_IndicatorWidth, option)
    indicator_height = style.pixelMetric(QStyle.PixelMetric.PM_IndicatorHeight, option)
    list_view_icon_size = indicator_width
    pixmap_width = indicator_width
    pixmap_height = max(indicator_height, list_view_icon_size)

    option.rect = QRect(0, 0, indicator_width, indicator_height)
    option.palette = QApplication.palette()
    pixmap = QPixmap(pixmap_width, pixmap_height)
    pixmap.fill(Qt.GlobalColor.transparent)
    # Center?
    if pixmap_width > indicator_width:
        x_offset = (pixmap_width - indicator_width) / 2
    else:
        x_offset = 0
    if pixmap_height > indicator_height:
        y_offset = (pixmap_height - indicator_height) / 2
    else:
        y_offset = 0
    painter = QPainter(pixmap)
    painter.translate(x_offset, y_offset)
    style.drawPrimitive(QStyle.PrimitiveElement.PE_IndicatorCheckBox, option, painter)
    painter.end()
    return QIcon(pixmap)


# noinspection PyPep8Naming
def brushValuePixmap(brush: QBrush) -> QPixmap:
    """
    Generate a pixmap representation of a brush.

    Creates a 14x14 pixmap with the brush fill. For semi-transparent
    colors, adds an inset rectangle to indicate alpha presence.

    :param brush: The brush to render
    :return: The generated pixmap
    """
    image = QImage(14, 14, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
    painter.fillRect(0, 0, image.width(), image.height(), brush)
    color = brush.color()
    if color.alpha() != 255:  # indicate alpha by an inset
        color.setAlpha(255)
        brush.setColor(color)
        w, h = image.width(), image.height()
        inset = QRect(w // 4, h // 4, w // 2, h// 2,)
        painter.fillRect(inset, brush)
    painter.end()
    return QPixmap.fromImage(image)


# noinspection PyPep8Naming
def brushValueIcon(brush: QBrush) -> QIcon:
    """
    Generate an icon representation of a brush.

    :param brush: The brush to render
    :return: The generated icon
    """
    return QIcon(brushValuePixmap(brush))


# noinspection PyPep8Naming
def colorValueText(color: QColor) -> str:
    """
    Return the text representation of a color.

    Format: '[R, G, B] (A)' where values are in range [0, 255].

    :param color: The color to format
    :return: The string representation of the color
    """
    rgb_values: list[int] = color.getRgb()  # type: ignore
    r, g, b, alpha = rgb_values
    text = f"[{r}, {g}, {b}] ({alpha})"
    if instance := QApplication.instance():
        return instance.tr(text)
    return text


# noinspection PyPep8Naming
def formatMultiWordName(text: str) -> str:
    """
    Format a compound name by inserting spaces before capital letters.

    Converts camelCase or PascalCase strings into space-separated words.
    For example, 'CentralAfricanRepublic' becomes 'Central African Republic'.

    :param text: The compound locale name to format
    :return: The formatted string with spaces between words
    """
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', text)


# noinspection PyPep8Naming
def fontValuePixmap(font: QFont) -> QPixmap:
    """
    Generate a pixmap preview of a font.

    Creates a 16x16 pixmap with the letter 'A' rendered in the
    specified font for visual representation.

    :param font: The font to render
    :return: The generated pixmap
    """
    font = QFont(font)
    img = QImage(16, 16, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    font.setPointSize(13)
    painter.setFont(font)
    text_opt = QTextOption(Qt.AlignmentFlag.AlignCenter)
    painter.drawText(QRectF(0, 0, 16, 16), 'A', text_opt)
    painter.end()
    return QPixmap.fromImage(img)


# noinspection PyPep8Naming
def fontValueText(font: QFont) -> str:
    """
    Return the text representation of a font.

    Format: '[Family, PointSize]'

    :param font: The font to format
    :return: The string representation of the font
    """
    return f'[{font.family()}, {font.pointSize()}]'


# Originally sourced from .\QtProperty\qtpropertybrowserutils.py
# noinspection PyPep8Naming
class _QtCursorDatabase(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._cursor_names: list[str] = list()
        self._cursor_icons: dict[int, QIcon] = dict()
        self._index_to_cursor_shape: dict[int, Qt.CursorShape] = dict()
        self._cursor_shape_to_index: dict[Qt.CursorShape, int] = dict()
        self._is_initialized = False

    def isInitialized(self) -> bool:
        return self._is_initialized

    def init(self):
        self.appendCursor(Qt.CursorShape.ArrowCursor, self.tr("Arrow"),
                     QIcon(":/qt-project.org/qtpropertybrowser/images/cursor-arrow.png"))
        self.appendCursor(Qt.CursorShape.UpArrowCursor, self.tr("Up Arrow"),
                     QIcon(":/qt-project.org/qtpropertybrowser/images/cursor-uparrow.png"))
        self.appendCursor(Qt.CursorShape.CrossCursor, self.tr("Cross"),
                     QIcon(":/qt-project.org/qtpropertybrowser/images/cursor-cross.png"))
        self.appendCursor(Qt.CursorShape.WaitCursor, self.tr("Wait"),
                     QIcon(":/qt-project.org/qtpropertybrowser/images/cursor-wait.png"))
        self.appendCursor(Qt.CursorShape.IBeamCursor, self.tr("IBeam"),
                     QIcon(":/qt-project.org/qtpropertybrowser/images/cursor-ibeam.png"))
        self.appendCursor(Qt.CursorShape.SizeVerCursor, self.tr("Size Vertical"),
                     QIcon(":/qt-project.org/qtpropertybrowser/images/cursor-sizev.png"))
        self.appendCursor(Qt.CursorShape.SizeHorCursor, self.tr("Size Horizontal"),
                     QIcon(":/qt-project.org/qtpropertybrowser/images/cursor-sizeh.png"))
        self.appendCursor(Qt.CursorShape.SizeFDiagCursor, self.tr("Size Backslash"),
                     QIcon(":/qt-project.org/qtpropertybrowser/images/cursor-sizef.png"))
        self.appendCursor(Qt.CursorShape.SizeBDiagCursor, self.tr("Size Slash"),
                     QIcon(":/qt-project.org/qtpropertybrowser/images/cursor-sizeb.png"))
        self.appendCursor(Qt.CursorShape.SizeAllCursor, self.tr("Size All"),
                     QIcon(":/qt-project.org/qtpropertybrowser/images/cursor-sizeall.png"))
        self.appendCursor(Qt.CursorShape.BlankCursor, self.tr("Blank"),
                     QIcon())
        self.appendCursor(Qt.CursorShape.SplitVCursor, self.tr("Split Vertical"),
                     QIcon(":/qt-project.org/qtpropertybrowser/images/cursor-vsplit.png"))
        self.appendCursor(Qt.CursorShape.SplitHCursor, self.tr("Split Horizontal"),
                     QIcon(":/qt-project.org/qtpropertybrowser/images/cursor-hsplit.png"))
        self.appendCursor(Qt.CursorShape.PointingHandCursor, self.tr("Pointing Hand"),
                     QIcon(":/qt-project.org/qtpropertybrowser/images/cursor-hand.png"))
        self.appendCursor(Qt.CursorShape.ForbiddenCursor, self.tr("Forbidden"),
                     QIcon(":/qt-project.org/qtpropertybrowser/images/cursor-forbidden.png"))
        self.appendCursor(Qt.CursorShape.OpenHandCursor, self.tr("Open Hand"),
                     QIcon(":/qt-project.org/qtpropertybrowser/images/cursor-openhand.png"))
        self.appendCursor(Qt.CursorShape.ClosedHandCursor, self.tr("Closed Hand"),
                     QIcon(":/qt-project.org/qtpropertybrowser/images/cursor-closedhand.png"))
        self.appendCursor(Qt.CursorShape.WhatsThisCursor, self.tr("What's This"),
                     QIcon(":/qt-project.org/qtpropertybrowser/images/cursor-whatsthis.png"))
        self.appendCursor(Qt.CursorShape.BusyCursor, self.tr("Busy"),
                     QIcon(":/qt-project.org/qtpropertybrowser/images/cursor-busy.png"))
        self._is_initialized = True

    def clear(self) -> None:
        self._cursor_names.clear()
        self._cursor_icons.clear()
        self._index_to_cursor_shape.clear()
        self._cursor_shape_to_index.clear()
        self._is_initialized = False

    def appendCursor(self, shape: Qt.CursorShape, name: str, icon: QIcon) -> None:
        if self._cursor_shape_to_index.get(shape, None):
            return
        value = len(self._cursor_names)
        self._cursor_names.append(name)
        self._cursor_icons[value] = icon
        self._index_to_cursor_shape[value] = shape
        self._cursor_shape_to_index[shape] = value

    def cursorShapeNames(self) -> list[str]:
        return self._cursor_names

    def cursorShapeIcons(self) -> dict[int, QIcon]:
        return self._cursor_icons

    def cursorToShapeName(self, cursor: QCursor) -> str:
        index = self.cursorToIndex(cursor)
        if index >= 0:
            return self._cursor_names[index]
        return ''

    def cursorToShapeIcon(self, cursor: QCursor) -> QIcon:
        val = self.cursorToIndex(cursor)
        return self._cursor_icons.get(val, QIcon())

    def cursorToIndex(self, cursor: QCursor) -> int:
        shape = cursor.shape()
        return self._cursor_shape_to_index.get(shape, -1)

    def indexToCursor(self, value: int) -> QCursor:
        if value in self._index_to_cursor_shape:
            return QCursor(self._index_to_cursor_shape[value])
        return QCursor()


CURSOR_DATABASE = _QtCursorDatabase()

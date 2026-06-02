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
#############################################################################
from typing import override, Any

from PySide6.QtCore import (
    Qt, QRect, QSize, QEvent, Signal, QModelIndex, QAbstractItemModel, QObject, QSignalBlocker, QPersistentModelIndex
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView, QApplication, QStyle,
    QTreeWidget,
    QStyleOptionViewItem,
    QTreeWidgetItem,
    QStyleOption,
    QAbstractItemView,
    QWidget, QStyledItemDelegate
)
from PySide6.QtGui import (
    QIcon, QPainter, QPalette, QFontMetrics, QColor, QPixmap,
    QKeyEvent, QMouseEvent, QFocusEvent, QBrush
)

from qtpropertybrowser.property_managers import QtProperty
from qtpropertybrowser.property_browser_base import QtAbstractPropertyBrowser, QtBrowserItem


class QtPropertyEditorView(QTreeWidget):
    def __init__(self, browser: QtTreePropertyBrowser) -> None:
        super().__init__(parent=browser)
        self._parent_browser: QtTreePropertyBrowser = browser
        self.header().sectionDoubleClicked.connect(self.resizeColumnToContents)

    def drawRow(self, painter: QPainter, options: QStyleOptionViewItem, index: QModelIndex | QPersistentModelIndex) -> None:
        option = QStyleOptionViewItem(options)

        bg_color = QColor()
        prop = self._parent_browser.indexToProperty(index)
        if self._parent_browser.markPropertiesWithoutValue() and not (prop and prop.hasValue()):
            bg_color = option.palette.color(QPalette.ColorRole.Dark)
        else:
            item = self._parent_browser.indexToBrowserItem(index)
            if item:
                bg_color = self._parent_browser.calculatedBackgroundColor(item)

        if bg_color.isValid():
            option.palette.setColor(QPalette.ColorRole.Base, bg_color)
            option.palette.setColor(QPalette.ColorRole.AlternateBase, bg_color.lighter(112))

        super().drawRow(painter, option, index)

        grid_rgb = QApplication.style().styleHint(
            QStyle.StyleHint.SH_Table_GridLineColor, option
        )
        painter.save()
        painter.setPen(QColor.fromRgb(grid_rgb & 0xFFFFFFFF))
        painter.drawLine(
            option.rect.left(),
            option.rect.bottom(),
            option.rect.right(),
            option.rect.bottom()
        )
        painter.restore()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        browser = self._parent_browser
        # The key triggers an edit
        if browser and not browser.editedItem():
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
                if (
                    (item := self.currentItem())
                    and (item.flags() & Qt.ItemFlag.ItemIsEnabled)
                    and (item.flags() & Qt.ItemFlag.ItemIsEditable)
                    and browser.hasEditor(browser.getBrowserItem(item))
                ):
                    event.accept()
                    self.editItem(item, 1)
                    return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)
        item: QTreeWidgetItem = self.itemAt(event.pos())  # type: ignore
        browser = self._parent_browser
        if item:
            if (
                item != browser.editedItem()
                and event.button() == Qt.MouseButton.LeftButton
                and self.header().logicalIndexAt(event.pos().x()) == 1
                and (item.flags() & Qt.ItemFlag.ItemIsEnabled)
                and (item.flags() & Qt.ItemFlag.ItemIsEditable)
                and browser.hasEditor(browser.getBrowserItem(item))
            ):
                self.editItem(item, 1)
            elif (
                not browser.hasValue(item)
                and browser.markPropertiesWithoutValue()
                and not self.rootIsDecorated()
            ):
                indicator_margin = self.style().pixelMetric(QStyle.PixelMetric.PM_IndicatorWidth) + 8
                if event.pos().x() < indicator_margin:
                    item.setExpanded(not item.isExpanded())


# noinspection PyPep8Naming
class QtPropertyEditorDelegate(QStyledItemDelegate):
    def __init__(self, browser: QtTreePropertyBrowser) -> None:
        super().__init__(browser)
        self._property_browser: QtTreePropertyBrowser = browser
        self._editor_to_property: dict[QWidget, QtProperty[Any]] = dict()
        self._edited_item: QTreeWidgetItem | None = None
        self._edited_widget: QWidget | None = None

    def parentTree(self) -> QTreeWidget:
        return self._property_browser.treeWidget()

    def setModelData(self, editor: QWidget, model: QAbstractItemModel, index: QModelIndex | QPersistentModelIndex) -> None:
        # This function must remain reimplemented to an empty function
        # for this custom delegate to work properly
        pass

    def setEditorData(self, editor: QWidget, index: QModelIndex | QPersistentModelIndex) -> None:
        # This function must remain reimplemented to an empty function
        # for this custom delegate to work properly
        pass

    def editedItem(self) -> QTreeWidgetItem | None:
        return self._edited_item

    def indentation(self, index: QModelIndex | QPersistentModelIndex) -> int:
        if not self._property_browser:
            return 0
        item = self.parentTree().itemFromIndex(index)
        indent = 0
        while item.parent():
            item = item.parent()
            indent += 1
        if self.parentTree().rootIsDecorated():
            indent += 1
        return indent * self.parentTree().indentation()

    def updateEditorGeometry(self, editor: QWidget, option: QStyleOptionViewItem, index: QModelIndex | QPersistentModelIndex) -> None:
        editor.setGeometry(option.rect.adjusted(0, 0, 0, -1))

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex | QPersistentModelIndex) -> QSize:
        return super(QtPropertyEditorDelegate, self).sizeHint(option, index) + QSize(3, 4)

    def eventFilter(self, obj: QObject, event: QEvent | QFocusEvent) -> bool:
        if (
            isinstance(event, QFocusEvent)
            and event.type() == QEvent.Type.FocusOut
            and event.reason() == Qt.FocusReason.ActiveWindowFocusReason
        ):
            return False
        if event.type() == QEvent.Type.KeyPress:
            return super().eventFilter(obj, event)
        return super().eventFilter(obj, event)

    def closePropertyEditor(self, property_: QtProperty[Any]) -> None:
        for editor, prop in self._editor_to_property.items():
            if prop is property_:
                editor.close()

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex | QPersistentModelIndex) -> QWidget:
        tree_item = self.parentTree().itemFromIndex(index)
        # The tree widget will only enter edit mode if an editor exists, so
        # the property should be there to be edited, and the widget should be able
        # to be created without issues
        property_: QtProperty[Any] = self._property_browser.indexToProperty(index)  # type: ignore
        editor: QWidget = self._property_browser.createEditor(property_, parent)    # type: ignore
        editor.installEventFilter(self)
        editor.setAutoFillBackground(True)
        self._editor_to_property[editor] = property_
        self._edited_item = tree_item
        self._edited_widget = editor
        return editor

    def destroyEditor(self, editor: QWidget, index: QModelIndex | QPersistentModelIndex) -> None:
        if editor is self._edited_widget:
            self._edited_widget = None
            self._edited_item = None
        self._editor_to_property.pop(editor, None)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex | QPersistentModelIndex) -> None:
        option = QStyleOptionViewItem(option)
        self.initStyleOption(option, index)

        has_value = False
        property_: QtProperty[Any] | None = None
        if self._property_browser:
            property_ = self._property_browser.indexToProperty(index)
            has_value = property_ is not None and property_.hasValue()

        if property_ and property_.isModified() and (not has_value or index.column() == 0):
            option.font.setBold(True)
            option.fontMetrics = QFontMetrics(option.font)

        custom_bg = QColor()
        # Explicit and safe bg/text color by theme
        if self._property_browser:
            if self._property_browser.markPropertiesWithoutValue() and not has_value:
                # Solid bg color (no alpha) to avoid color "washing"
                base_light = option.palette.color(QPalette.ColorRole.Base).lightness()
                bg = QColor(192, 192, 192) if base_light > 128 else QColor(92, 92, 92)
                fg = QColor(80, 80, 80) if base_light > 128 else QColor(208, 208, 208)
                painter.save()
                painter.fillRect(option.rect, bg)
                option.palette.setColor(QPalette.ColorRole.Text, fg)
                painter.restore()
            else:
                item = self._property_browser.indexToBrowserItem(index)
                if item:
                    custom_bg = self._property_browser.calculatedBackgroundColor(item)
                if custom_bg.isValid() and (option.features & QStyleOptionViewItem.ViewItemFeature.Alternate):
                    custom_bg = custom_bg.lighter(112)
                    option.backgroundBrush = QBrush(custom_bg)

        is_selected = option.state & QStyle.StateFlag.State_Selected
        if custom_bg.isValid() and not is_selected:
            custom_bg.setAlpha(64)
            option.palette.setColor(QPalette.ColorRole.Base, custom_bg)
            option.palette.setColor(QPalette.ColorRole.AlternateBase, custom_bg)

        option.state &= ~QStyle.StateFlag.State_HasFocus

        super().paint(painter, option, index)

        grid_rgb = QApplication.style().styleHint(
            QStyle.StyleHint.SH_Table_GridLineColor,
            option
        )
        painter.save()
        painter.setPen(QColor.fromRgb(grid_rgb & 0xFFFFFFFF))

        if (
            not self._property_browser
            or (not self._property_browser.isLastColumn(index.column()) and has_value)
        ):
            right = option.rect.left()
            if option.direction == Qt.LayoutDirection.LeftToRight:
                right = option.rect.right()
            painter.drawLine(right, option.rect.y(), right, option.rect.bottom())

        painter.restore()


# noinspection PyPep8Naming
class QtTreePropertyBrowser(QtAbstractPropertyBrowser[QTreeWidgetItem]):
    expanded = Signal(QtBrowserItem)
    collapsed = Signal(QtBrowserItem)
    currentItemChanged = Signal(QtBrowserItem)

    def __init__(self, parent: QWidget | None=None) -> None:
        super().__init__(parent)

        self._header_visible: bool = True
        self._mark_properties_without_value: bool = False
        self._resize_mode: QHeaderView.ResizeMode = QHeaderView.ResizeMode.Stretch
        self._expand_icon: QIcon = self.draw_indicator_icon(
            self.palette(),
            self.style()
        )

        self._edit_delegate = QtPropertyEditorDelegate(self)

        self._tree_widget: QtPropertyEditorView = QtPropertyEditorView(self)
        self._tree_widget.setItemDelegate(self._edit_delegate)
        self._tree_widget.setIconSize(QSize(18, 18))
        self._tree_widget.setColumnCount(2)
        self._tree_widget.setHeaderLabels([self.tr('Property'), self.tr('Value')])
        self._tree_widget.setAlternatingRowColors(True)
        self._tree_widget.setEditTriggers(QAbstractItemView.EditTrigger.EditKeyPressed)
        self._tree_widget.header().setSectionsMovable(False)
        self._tree_widget.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tree_widget.collapsed.connect(self.onCollapsed)
        self._tree_widget.expanded.connect(self.onExpanded)
        self._tree_widget.currentItemChanged.connect(self.onCurrentTreeItemChanged)
        self.setFocusProxy(self._tree_widget)

        palette = self._tree_widget.palette()
        c = palette.color(QPalette.ColorRole.Base)
        alt_c = c.darker(112) if c.lightness() > 128 else c.lighter(112)
        palette.setColor(QPalette.ColorRole.AlternateBase, alt_c)
        self._tree_widget.setPalette(palette)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tree_widget)

        self._current_item: QtBrowserItem | None = None
        self.currentItemChanged.connect(self.onCurrentBrowserItemChanged)

        self._browser_item_to_bg_color: dict[QtBrowserItem, QColor] = dict()
        self._block_browser_changes: bool = False

    @staticmethod
    def draw_indicator_icon(palette: QPalette, style: QStyle) -> QIcon:
        """
        Draw an icon indicating opened/closing branches
        """
        # This is a QApplication instance, the inference is wrong here
        dpr = QApplication.instance().devicePixelRatio()  # type: ignore
        base_size = 14
        size = int(base_size * dpr)
        icon = QIcon()

        def _make_pixmap(state: QStyle.StateFlag) -> QPixmap:
            pixmap = QPixmap(size, size)
            pixmap.setDevicePixelRatio(dpr)
            pixmap.fill(Qt.GlobalColor.transparent)

            painter = QPainter(pixmap)
            opt = QStyleOption()
            # Logic coordinates (Qt scales internally)
            opt.rect = QRect(2, 2, 9, 9)
            opt.palette = palette
            opt.state = QStyle.StateFlag.State_Children | state  # noqa

            style.drawPrimitive(
                QStyle.PrimitiveElement.PE_IndicatorBranch,
                opt,
                painter
            )
            painter.end()
            return pixmap

        # Closed (Off)
        closed = _make_pixmap(QStyle.StateFlag(0))
        icon.addPixmap(closed, QIcon.Mode.Normal, QIcon.State.Off)
        icon.addPixmap(closed, QIcon.Mode.Selected, QIcon.State.Off)
        # Open (On)
        opened = _make_pixmap(QStyle.StateFlag.State_Open)
        icon.addPixmap(opened, QIcon.Mode.Normal, QIcon.State.On)
        icon.addPixmap(opened, QIcon.Mode.Selected, QIcon.State.On)

        return icon

    def currentItem(self) -> QtBrowserItem | None:
        return self._current_item

    def setCurrentItem(self, item: QtBrowserItem | None) -> None:
        if self._current_item is item:
            return
        self._current_item = item
        self.currentItemChanged.emit(item if item else QtBrowserItem(self))

    def indexToProperty(self, index: QModelIndex | QPersistentModelIndex) -> QtProperty[Any] | None:
        browser_item = self.getBrowserItem(self._tree_widget.itemFromIndex(index))
        if browser_item:
            return browser_item.itemProperty()
        return None

    def indexToBrowserItem(self, index: QModelIndex | QPersistentModelIndex) -> QtBrowserItem | None:
        return self.getBrowserItem(self._tree_widget.itemFromIndex(index))

    def isLastColumn(self, column: int) -> bool:
        return self._tree_widget.header().visualIndex(column) == self._tree_widget.columnCount() - 1

    def disableItem(self, item: QTreeWidgetItem) -> None:
        if not (item.flags() & Qt.ItemFlag.ItemIsEnabled):
            return
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)

        if self._edit_delegate.editedItem() is item:
            browser_item = self.getBrowserItem(item)
            if browser_item and (prop := browser_item.itemProperty()):
                self._edit_delegate.closePropertyEditor(prop)

        for i in range(item.childCount()):
            self.disableItem(item.child(i))

    def enableItem(self, item: QTreeWidgetItem) -> None:
        browser_item = self.getBrowserItem(item)
        if (
            not browser_item
            or not (prop := browser_item.itemProperty())
            or prop.isEnabled()
        ):
            return
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled)
        for i in range(item.childCount()):
            self.enableItem(item.child(i))

    def hasValue(self, item: QTreeWidgetItem) -> bool:
        browser_item = self.getBrowserItem(item)
        if browser_item and (prop := browser_item.itemProperty()):
            return prop.hasValue()
        return False

    def treeWidget(self) -> QtPropertyEditorView:
        return self._tree_widget

    def markPropertiesWithoutValue(self) -> bool:
        return self._mark_properties_without_value

    def setPropertiesWithoutValueMarked(self, mark: bool) -> None:
        if self._mark_properties_without_value == mark:
            return
        self._mark_properties_without_value = mark
        for item in self.browserItems():
            property_ = item.itemProperty()
            if property_ and not property_.hasValue():
                self.updateItem(item)
        self._tree_widget.viewport().update()

    @override
    def itemInserted(self, item: QtBrowserItem, after: QtBrowserItem | None) -> None:
        after_tree_item: QTreeWidgetItem | None = None
        parent_tree_item: QTreeWidgetItem | None = None
        if after:
            after_tree_item = self.getWidgetItem(after)
        if parent_item := item.parent():
            parent_tree_item = self.getWidgetItem(parent_item)

        parent = parent_tree_item if parent_tree_item else self._tree_widget
        tree_item = QTreeWidgetItem(parent, after_tree_item)  # type: ignore
        tree_item.setFlags(tree_item.flags() | Qt.ItemFlag.ItemIsEditable)
        tree_item.setExpanded(True)
        self.setWidgetItem(item, tree_item)

        self.updateItem(item)

    @override
    def itemRemoved(self, item: QtBrowserItem) -> None:
        tree_item = self.getWidgetItem(item)
        if not tree_item:
            return
        if self._tree_widget.currentItem() is tree_item:
            with QSignalBlocker(self._tree_widget):
                self._tree_widget.setCurrentItem(None)  # type: ignore

        parent = tree_item.parent()
        if parent:
            parent.removeChild(tree_item)
        elif (idx := self._tree_widget.indexOfTopLevelItem(tree_item)) >= 0:
            self._tree_widget.takeTopLevelItem(idx)

        self.unsetWidgetItem(item, tree_item)
        self._browser_item_to_bg_color.pop(item, None)

    @override
    def updateItem(self, browser_item: QtBrowserItem) -> None:
        if not browser_item:
            return
        if not (property_ := browser_item.itemProperty()):
            return
        if not (tree_item := self.getWidgetItem(browser_item)):
            return

        tree_item.setText(0, property_.name())
        tree_item.setToolTip(0, property_.name())
        tree_item.setStatusTip(0, property_.statusTip())
        tree_item.setWhatsThis(0, property_.whatsThis())

        has_value = property_.hasValue()
        if has_value:
            tree_item.setText(1, property_.displayText() or property_.valueText())
            tree_item.setIcon(1, property_.valueIcon())
            tree_item.setToolTip(1, property_.toolTip() or property_.displayText())
        else:
            tree_item.setText(1, '')
            tree_item.setIcon(1, QIcon())
            tree_item.setToolTip(1, '')

        if not has_value and self.markPropertiesWithoutValue() and not self.rootIsDecorated():
            tree_item.setIcon(0, self._expand_icon)
        else:
            tree_item.setIcon(0, QIcon())

        if tree_item.isFirstColumnSpanned() != (not has_value):
            tree_item.setFirstColumnSpanned(not has_value)

        is_enabled = property_.isEnabled()
        if is_enabled and (parent := tree_item.parent()):
            is_enabled = bool(parent.flags() & Qt.ItemFlag.ItemIsEnabled)
        was_enabled = bool(tree_item.flags() & Qt.ItemFlag.ItemIsEnabled)
        if was_enabled != is_enabled:
            if is_enabled:
                self.enableItem(tree_item)
            else:
                self.disableItem(tree_item)

    def calculatedBackgroundColor(self, item: QtBrowserItem) -> QColor:
        browser_item: QtBrowserItem | None = item
        while browser_item:
            bg_color = self._browser_item_to_bg_color.get(browser_item, None)
            if bg_color:
                return bg_color
            browser_item = browser_item.parent()
        return QColor()

    def onCollapsed(self, index: QModelIndex | QPersistentModelIndex) -> None:
        tree_item = self._tree_widget.itemFromIndex(index)
        if not tree_item:
            return
        browser_item = self.getBrowserItem(tree_item)
        if not browser_item:
            browser_item = QtBrowserItem(self)
        self.collapsed.emit(browser_item)

    def onExpanded(self, index: QModelIndex | QPersistentModelIndex) -> None:
        tree_item = self._tree_widget.itemFromIndex(index)
        if not tree_item:
            return
        browser_item = self.getBrowserItem(tree_item)
        self.expanded.emit(browser_item)

    def onCurrentBrowserItemChanged(self, item: QtBrowserItem) -> None:
        tree_item = self.getWidgetItem(item)
        if tree_item is not self._tree_widget.currentItem():
            with QSignalBlocker(self._tree_widget):
                self._tree_widget.setCurrentItem(tree_item)  # type: ignore

    def onCurrentTreeItemChanged(self, item: QTreeWidgetItem) -> None:
        browser_item = self.getBrowserItem(item)
        if browser_item is not self._current_item:
            self.setCurrentItem(browser_item)

    def editedItem(self) -> QTreeWidgetItem | None:
        return self._edit_delegate.editedItem()

    def editItem(self, item: QtBrowserItem) -> None:
        tree_item = self.getWidgetItem(item)
        if tree_item:
            self._tree_widget.setCurrentItem(tree_item, 1)
            self._tree_widget.editItem(tree_item, 1)

    def indentation(self) -> int:
        return self._tree_widget.indentation()

    def setIndentation(self, indent: int) -> None:
        self._tree_widget.setIndentation(indent)

    def rootIsDecorated(self) -> bool:
        return self._tree_widget.rootIsDecorated()

    def setRootIsDecorated(self, show: bool) -> None:
        self._tree_widget.setRootIsDecorated(show)
        for item in self.browserItems():
            property_ = item.itemProperty()
            if property_ and not property_.hasValue():
                self.updateItem(item)

    def alternatingRowColors(self) -> bool:
        return self._tree_widget.alternatingRowColors()

    def setAlternatingRowColors(self, enable: bool) -> None:
        self._tree_widget.setAlternatingRowColors(enable)

    def isHeaderVisible(self) -> bool:
        return self._header_visible

    def setHeaderVisible(self, visible: bool) -> None:
        if self._header_visible == visible:
            return
        self._header_visible = visible
        self._tree_widget.header().setVisible(visible)

    def resizeMode(self) -> QHeaderView.ResizeMode:
        return self._resize_mode

    def setResizeMode(self, mode: QHeaderView.ResizeMode) -> None:
        if self._resize_mode == mode:
            return
        self._resize_mode = mode
        header = self._tree_widget.header()
        header.setSectionResizeMode(mode)
        if mode == QHeaderView.ResizeMode.Stretch:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

    def scrollPosition(self) -> tuple[int, int]:
        h_bar = self._tree_widget.horizontalScrollBar()
        v_bar = self._tree_widget.verticalScrollBar()
        return h_bar.value(), v_bar.value()

    def setScrollPosition(self, dx: int, dy: int) -> None:
        h_bar = self._tree_widget.horizontalScrollBar()
        v_bar = self._tree_widget.verticalScrollBar()
        with QSignalBlocker(h_bar), QSignalBlocker(v_bar):
            h_bar.setValue(dx)
            v_bar.setValue(dy)
        
    def splitterPosition(self) -> int:
        return self._tree_widget.header().sectionSize(0)

    def setSplitterPosition(self, position: int) -> None:
        header = self._tree_widget.header()
        with QSignalBlocker(header):
            header.resizeSection(0, position)
        self._tree_widget.viewport().update()

    def setExpanded(self, item: QtBrowserItem, expanded: bool) -> None:
        tree_item = self.getWidgetItem(item)
        if tree_item:
            tree_item.setExpanded(expanded)

    def isExpanded(self, item: QtBrowserItem) -> bool:
        tree_item = self.getWidgetItem(item)
        if tree_item:
            return tree_item.isExpanded()
        return False

    def isItemVisible(self, item: QtBrowserItem) -> bool:
        tree_item = self.getWidgetItem(item)
        if tree_item:
            return not tree_item.isHidden()
        return False

    def setItemVisible(self, item: QtBrowserItem, visible: bool) -> None:
        tree_item = self.getWidgetItem(item)
        if tree_item:
            tree_item.setHidden(not visible)

    def backgroundColor(self, item: QtBrowserItem) -> QColor:
        return self._browser_item_to_bg_color.get(item, QColor())

    def setBackgroundColor(self, item: QtBrowserItem, color: QColor) -> None:
        if not item in self.browserItems():
            return
        if color.isValid():
            self._browser_item_to_bg_color[item] = color
        else:
            self._browser_item_to_bg_color.pop(item, None)
        self._tree_widget.viewport().update()

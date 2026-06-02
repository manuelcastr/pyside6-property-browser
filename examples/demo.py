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
## "Redistribution and use in source and binary formsith or without
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
## LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES LOSS OF USE,
## DATA, OR PROFITS OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
## THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
## OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
##
## $QT_END_LICENSE$
##
############################################################################/
import pathlib
import sys

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QScrollArea,
    QGridLayout,
    QWidget,
    QFrame, QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit, QSlider, QScrollBar
)
from PySide6.QtCore import Qt

from qtpropertybrowser.editor_widgets import QtFontEdit, QtBoolEdit
from qtpropertybrowser.property_managers import QtGroupPropertyManager, QtBoolPropertyManager, QtIntPropertyManager, \
    QtStringPropertyManager, QtSizePropertyManager, QtEnumPropertyManager, QtSizePolicyPropertyManager, \
    QtRectPropertyManager, QtCursorPropertyManager, QtFontPropertyManager, QtPointFPropertyManager
from qtpropertybrowser.editor_factories import QtSpinBoxFactory, QtCheckBoxFactory, QtEnumEditorFactory, \
    QtLineEditFactory, QtSliderFactory, QtScrollBarFactory, QtCursorEditorFactory, QtFontEditorFactory, \
    QtDoubleSpinBoxFactory

from qtpropertybrowser.tree_property_browser import QtTreePropertyBrowser
from qtpropertybrowser.groupbox_property_browser import QtGroupBoxPropertyBrowser
from qtpropertybrowser.qtbuttonpropertybrowser import QtButtonPropertyBrowser

from PySide6.QtGui import QIcon
import demo_rc  # noqa

import os
os.environ['QT_LOGGING_RULES'] = '*.debug=true'
os.environ['QT_DEBUG_PLUGINS'] = '1'

log_path = pathlib.Path('./debug.log')
log_path.unlink(missing_ok=True)

from debug_utils import logger  # noqa

if __name__ == '__main__':
    args = sys.argv + ['-platform', 'windows:darkmode=0']
    app = QApplication(args)

    app.setStyle('Fusion')

    w = QWidget()

    boolManager = QtBoolPropertyManager('QtBoolPropertyManager')
    intManager = QtIntPropertyManager('QtIntPropertyManager')
    stringManager = QtStringPropertyManager('QtStringPropertyManager')
    sizeManager = QtSizePropertyManager('QtSizePropertyManager')
    rectManager = QtRectPropertyManager('QtRectPropertyManager')
    sizePolicyManager = QtSizePolicyPropertyManager('QtSizePolicyPropertyManager')
    enumManager = QtEnumPropertyManager('QtEnumPropertyManager')
    groupManager = QtGroupPropertyManager('QtGroupPropertyManager')

    item0 = groupManager.addProperty("QObject")
    item00 = groupManager.addProperty('Empty Group')
    item0.addSubProperty(item00)

    item1 = stringManager.addProperty("objectName")
    item0.addSubProperty(item1)

    item2 = boolManager.addProperty("enabled")
    item0.addSubProperty(item2)

    item3 = rectManager.addProperty("geometry")
    item0.addSubProperty(item3)

    item4 = sizePolicyManager.addProperty("sizePolicy")
    item0.addSubProperty(item4)

    item5 = sizeManager.addProperty("sizeIncrement")
    item0.addSubProperty(item5)

    item7 = boolManager.addProperty("mouseTracking")
    item0.addSubProperty(item7)

    item8 = enumManager.addProperty("direction")
    enumNames = list()
    enumNames.append("Up")
    enumNames.append("Right")
    enumNames.append("Down")
    enumNames.append("Left")

    enumManager.setEnumNames(item8, enumNames)
    enumIcons = dict()
    enumIcons[0] = QIcon(":/demo/images/up.png")
    enumIcons[1] = QIcon(":/demo/images/right.png")
    enumIcons[2] = QIcon(":/demo/images/down.png")
    enumIcons[3] = QIcon(":/demo/images/left.png")
    enumManager.setEnumIcons(item8, enumIcons)
    item0.addSubProperty(item8)

    item8a = stringManager.addProperty("Sub direction")
    item8a.setValue('Some text')
    item8.addSubProperty(item8a)
    def f8(p, value: int):
        item8a.setValue(enumManager.enumNames(item8)[value])
    item8.valueChanged.connect(f8)

    item9 = intManager.addProperty("value")
    intManager.setRange(item9, -100, 100)
    item0.addSubProperty(item9)

    # from qtpropertybrowser.qt_cursor_manager_and_factory import QtCursorPropertyManager
    cursor_manager = QtCursorPropertyManager('QtCursorPropertyManager')
    item10 = cursor_manager.addProperty('Cursors')
    item0.addSubProperty(item10)

    font_manager = QtFontPropertyManager('QtFontPropertyManager')
    item11 = font_manager.addProperty('A font')
    item0.addSubProperty(item11)

    point_f_manager = QtPointFPropertyManager('QtPointFPropertyManager')
    item12 = point_f_manager.addProperty('PointF')
    point_f_manager.setDecimals(item12, 2)
    item0.addSubProperty(item12)

    checkBoxFactory = QtCheckBoxFactory(QtBoolEdit)
    spinBoxFactory = QtSpinBoxFactory(QSpinBox)
    sliderFactory = QtSliderFactory(QSlider)
    scrollBarFactory = QtScrollBarFactory(QScrollBar)
    lineEditFactory = QtLineEditFactory(QLineEdit)
    comboBoxFactory = QtEnumEditorFactory(QComboBox)
    cursor_factory = QtCursorEditorFactory(QComboBox)
    font_factory = QtFontEditorFactory(QtFontEdit)
    float_factory = QtDoubleSpinBoxFactory(QDoubleSpinBox)

    editor1 = QtTreePropertyBrowser()
    editor1.setFactoryForManager(boolManager, checkBoxFactory)
    editor1.setFactoryForManager(intManager, spinBoxFactory)
    editor1.setFactoryForManager(stringManager, lineEditFactory)
    editor1.setFactoryForManager(sizeManager.subPropertyManager(), spinBoxFactory)
    editor1.setFactoryForManager(rectManager.subIntPropertyManager(), spinBoxFactory)
    editor1.setFactoryForManager(sizePolicyManager.subIntPropertyManager(), spinBoxFactory)
    editor1.setFactoryForManager(sizePolicyManager.subEnumPropertyManager(), comboBoxFactory)
    editor1.setFactoryForManager(enumManager, comboBoxFactory)
    editor1.setFactoryForManager(cursor_manager, cursor_factory)

    editor1.setFactoryForManager(font_manager, font_factory)
    editor1.setFactoryForManager(font_manager.subBoolPropertyManager(), checkBoxFactory)
    editor1.setFactoryForManager(font_manager.subIntPropertyManager(), spinBoxFactory)
    editor1.setFactoryForManager(font_manager.subEnumPropertyManager(), comboBoxFactory)
    editor1.setFactoryForManager(point_f_manager.subPropertyManager(), float_factory)

    editor1.addProperty(item0)

    editor2 = QtTreePropertyBrowser()
    editor2.addProperty(item0)

    editor3 = QtGroupBoxPropertyBrowser()
    editor3.setFactoryForManager(boolManager, checkBoxFactory)
    editor3.setFactoryForManager(intManager, spinBoxFactory)
    editor3.setFactoryForManager(stringManager, lineEditFactory)
    editor3.setFactoryForManager(sizeManager.subPropertyManager(), spinBoxFactory)
    editor3.setFactoryForManager(rectManager.subIntPropertyManager(), spinBoxFactory)
    editor3.setFactoryForManager(sizePolicyManager.subIntPropertyManager(), spinBoxFactory)
    editor3.setFactoryForManager(sizePolicyManager.subEnumPropertyManager(), comboBoxFactory)
    editor3.setFactoryForManager(enumManager, comboBoxFactory)
    editor3.setFactoryForManager(cursor_manager, cursor_factory)

    editor3.setFactoryForManager(font_manager, font_factory)
    editor3.setFactoryForManager(font_manager.subBoolPropertyManager(), checkBoxFactory)
    editor3.setFactoryForManager(font_manager.subIntPropertyManager(), scrollBarFactory)
    editor3.setFactoryForManager(font_manager.subEnumPropertyManager(), comboBoxFactory)
    editor3.setFactoryForManager(point_f_manager.subPropertyManager(), float_factory)

    editor3.addProperty(item0)

    scroll3 = QScrollArea()
    scroll3.setWidgetResizable(True)
    scroll3.setWidget(editor3)

    editor4 = QtGroupBoxPropertyBrowser()
    editor4.setFactoryForManager(boolManager, checkBoxFactory)
    editor4.setFactoryForManager(intManager, scrollBarFactory)
    editor4.setFactoryForManager(stringManager, lineEditFactory)
    editor4.setFactoryForManager(sizeManager.subPropertyManager(), spinBoxFactory)
    editor4.setFactoryForManager(rectManager.subIntPropertyManager(), spinBoxFactory)
    editor4.setFactoryForManager(sizePolicyManager.subIntPropertyManager(), sliderFactory)
    editor4.setFactoryForManager(sizePolicyManager.subEnumPropertyManager(), comboBoxFactory)
    editor4.setFactoryForManager(enumManager, comboBoxFactory)
    editor4.setFactoryForManager(cursor_manager, cursor_factory)
    editor4.setFactoryForManager(point_f_manager.subPropertyManager(), float_factory)

    editor4.addProperty(item0)

    scroll4 = QScrollArea()
    scroll4.setWidgetResizable(True)
    scroll4.setWidget(editor4)

    editor5 = QtButtonPropertyBrowser()
    editor5.setFactoryForManager(boolManager, checkBoxFactory)
    editor5.setFactoryForManager(intManager, scrollBarFactory)
    editor5.setFactoryForManager(stringManager, lineEditFactory)
    editor5.setFactoryForManager(sizeManager.subPropertyManager(), spinBoxFactory)
    editor5.setFactoryForManager(rectManager.subIntPropertyManager(), spinBoxFactory)
    editor5.setFactoryForManager(sizePolicyManager.subIntPropertyManager(), sliderFactory)
    editor5.setFactoryForManager(sizePolicyManager.subEnumPropertyManager(), comboBoxFactory)
    editor5.setFactoryForManager(enumManager, comboBoxFactory)
    editor5.setFactoryForManager(cursor_manager, cursor_factory)

    editor5.setFactoryForManager(point_f_manager.subPropertyManager(), float_factory)

    editor5.addProperty(item0)

    scroll5 = QScrollArea()
    scroll5.setWidgetResizable(True)
    scroll5.setWidget(editor5)

    layout = QGridLayout(w)
    label1 = QLabel("Editable Tree Property Browser")
    label2 = QLabel("Read Only Tree Property Browser, editor factories are not set")
    label3 = QLabel("Group Box Property Browser")
    label4 = QLabel("Group Box Property Browser with different editor factories")
    label5 = QLabel("Button Property Browser")
    label1.setWordWrap(True)
    label2.setWordWrap(True)
    label3.setWordWrap(True)
    label4.setWordWrap(True)
    label5.setWordWrap(True)
    label1.setFrameShadow(QFrame.Shadow.Sunken)
    label2.setFrameShadow(QFrame.Shadow.Sunken)
    label3.setFrameShadow(QFrame.Shadow.Sunken)
    label4.setFrameShadow(QFrame.Shadow.Sunken)
    label5.setFrameShadow(QFrame.Shadow.Sunken)
    label1.setFrameShape(QFrame.Shape.Panel)
    label2.setFrameShape(QFrame.Shape.Panel)
    label3.setFrameShape(QFrame.Shape.Panel)
    label4.setFrameShape(QFrame.Shape.Panel)
    label5.setFrameShape(QFrame.Shape.Panel)
    label1.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label2.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label3.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label4.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label5.setAlignment(Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(label1, 0, 0)
    layout.addWidget(label2, 0, 1)
    layout.addWidget(label3, 0, 2)
    layout.addWidget(label4, 0, 3)
    layout.addWidget(label5, 0, 4)
    layout.addWidget(editor1, 1, 0)
    layout.addWidget(editor2, 1, 1)
    layout.addWidget(scroll3, 1, 2)
    layout.addWidget(scroll4, 1, 3)
    layout.addWidget(scroll5, 1, 4)
    # w.showMaximized()
    w.show()

    sys.exit(app.exec())

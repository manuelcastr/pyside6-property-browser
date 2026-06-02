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
import contextlib
from functools import partial
from typing import Generic, Any, override, TypeVar, Protocol, runtime_checkable, Callable
from weakref import WeakKeyDictionary, WeakValueDictionary

from PySide6.QtCore import (
    Qt, QDate, QTime, QDateTime, QRegularExpression, SignalInstance, QSignalBlocker
)
from PySide6.QtGui import (
    QIcon, QCursor, QKeySequence,
    QRegularExpressionValidator
)
from PySide6.QtWidgets import (
    QWidget, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit,
    QTimeEdit, QDateTimeEdit, QLineEdit, QSlider, QScrollBar,
    QKeySequenceEdit
)

from qtpropertybrowser.property_managers import (
    QtProperty,
    QtAbstractPropertyManager,
    QtEnumPropertyManager
)
from qtpropertybrowser.editor_widgets import (
    QtBoolEdit,
    QtColorEdit,
    QtCharEdit,
    QtFontEdit
)
from qtpropertybrowser.utils import CURSOR_DATABASE


WidgetType = TypeVar("WidgetType", bound=QWidget)

# noinspection PyPep8Naming
class QtAbstractEditorFactory(Generic[WidgetType]):
    """
    Abstract base class for property editor factories.

    This class provides the foundation for creating editor widgets that
    allow users to modify property values. It manages the relationship
    between property managers and their corresponding editor widgets,
    handling synchronization of values between them.

    Subclasses must implement connectPropertyManager() and
    disconnectPropertyManager() to handle manager-specific signals.
    """
    def __init__(self, editor_class: type[WidgetType]) -> None:
        """
        Initialize the editor factory.

        :param editor_class: The class to instantiate to create the editor widgets
        """
        self._editor_class: type[WidgetType] = editor_class
        self._managers: set[QtAbstractPropertyManager[Any]] = set()
        # _created_editors: dict[property_, WeakValueDict[parent_widget, editor]]
        self._created_editors: dict[
            QtProperty[Any],
            WeakValueDictionary[QWidget | None, WidgetType]
        ] = dict()
        # _editor_to_property: WeakKeyDict[editor, tuple[property_, parent_widget]]
        self._editor_to_property: WeakKeyDictionary[
            WidgetType,
            tuple[QtProperty[Any], QWidget | None]
        ] = WeakKeyDictionary()
        self._updating_properties: bool = False

    def get_property_editors(self, property_: QtProperty[Any]) -> list[WidgetType]:
        return list(
            self._created_editors.get(property_, WeakValueDictionary()).values()
        )

    def managers(self) -> list[QtAbstractPropertyManager[Any]]:
        """
        Return a list of all managed property managers.

        :return: List of property managers associated with this factory
        """
        return list(self._managers)

    def propertyManager(self, property_: QtProperty[Any]) -> QtAbstractPropertyManager[Any] | None:
        """
        Return the property manager for a property if it is managed by this factory.

        :param property_: The property to check
        :return: The property manager, or None if not managed
        """
        if property_ and property_.manager() in self._managers:
            return property_.manager()
        return None

    def addPropertyManager(self, manager: QtAbstractPropertyManager[Any]) -> None:
        """
        Add a property manager to this factory.

        Connects the manager's valueChanged and managerDestroyed signals, and calls
        connectPropertyManager() for subclass-specific signal connections.

        :param manager: The property manager to add
        """
        if manager in self._managers:
            return
        self._managers.add(manager)
        self.connectPropertyManager(manager)
        manager.valueChanged.connect(self.onPropertyValueChanged)

    def removePropertyManager(self, manager: QtAbstractPropertyManager[Any]) -> None:
        """
        Remove a property manager from this factory.

        Disconnects all signals and calls disconnectPropertyManager() for
        subclass-specific cleanup.

        :param manager: The property manager to remove
        """
        if not manager in self._managers:
            return
        # In PySide6, trying to wrongly disconnect a signal can raise RuntimeError
        with contextlib.suppress(RuntimeError):
            manager.valueChanged.disconnect(self.onPropertyValueChanged)
            self.disconnectPropertyManager(manager)
        self._managers.discard(manager)

    def connectPropertyManager(self, manager: QtAbstractPropertyManager[Any]) -> None:
        """
        Connect manager-specific signals for property synchronization.

        Subclasses should override this method to connect additional signals
        beyond valueChanged() and managerDestroyed() that are automatically connected
        when adding a property manager.

        :param manager: The property manager to connect
        """
        pass

    def disconnectPropertyManager(self, manager: QtAbstractPropertyManager[Any]) -> None:
        """
        Disconnect manager-specific signals.

        Subclasses should override this method to disconnect additional signals
        beyond valueChanged() and managerDestroyed() that are automatically disconnected
        when removing a property manager.

        Since trying to wrongly disconnect a signal can raise a RuntimeError in PySide6,
        this function is inside a try/except block in the body of removePropertyManager().
        Subclasses shouldn't need to catch their possible exceptions.

        :param manager: The property manager to disconnect
        """
        pass

    def findEditor(self, property_: QtProperty[Any], parent: QWidget | None) -> WidgetType | None:
        """
        Find or create an editor widget for a property.

        Returns an existing editor if one exists for the given property and
        parent widget, otherwise creates a new editor.

        :param property_: The property to create/find an editor for
        :param parent: The parent widget for the editor.
        :return: The editor widget, or None if creation fails
        """
        manager = property_.manager()
        if manager is None or manager not in self._managers:
            return None
        parents_to_editors = self._created_editors.get(
            property_,
            WeakValueDictionary()
        )
        existing_editor = parents_to_editors.get(parent,None)
        if existing_editor is not None:
            return existing_editor
        return self.createEditor(property_, parent)

    def createEditor(
        self,
        property_: QtProperty[Any],
        parent: QWidget | None = None
    ) -> WidgetType | None:
        """
        Create a new editor widget for a property.

        Instantiates the registered widget type for this factory, initializes
        it with the property value via the adapter function `setEditorValue()`,
        and connects its signal for tracking changes in value with the property's
        manager via the `getEditorValueChangedSignal()` adapter function.

        Subclasses must handle value initialization and signal connections
        for widgets with different functionality.

        :param property_: The property to create an editor for
        :param parent: The parent widget for the editor
        :return: The created editor widget, or None if creation fails
        """
        if not self._editor_class:
            return None
        editor = self._editor_class(parent)
        self.setEditorValue(editor, property_.value())
        value_changed_signal = self.getEditorValueChangedSignal(editor)
        if value_changed_signal is not None:
            value_changed_signal.connect(partial(self.onEditorValueChanged, editor))
        parents_to_editors = self._created_editors.setdefault(
            property_,
            WeakValueDictionary()
        )
        parents_to_editors[parent] = editor
        self._editor_to_property[editor] = (property_, parent)
        return editor

    @staticmethod
    def setEditorValue(editor: WidgetType, value: Any) -> None:
        """
        Adapter function to set the value on an editor widget.

        By default, attempt to set the value using the `setValue()` function,
        but each subclass must override this method to fit the behavior of
        its created editor widgets.

        :param editor: The editor widget to set
        :param value: The new value to set on the editor
        """
        if hasattr(editor, 'setValue'):
            editor.setValue(value)

    @staticmethod
    def getEditorValueChangedSignal(editor: WidgetType) -> SignalInstance | None:
        """
        Adapter function to get the signal that emits when the value on the editor
        widget changes.

        By default, returns the `valueChanged` signal if the editor widget has that
        attribute, otherwise returns `None`. Subclasses should override this function
        to return the proper signal that triggers an update of the value of the
        property linked to the editor widget.

        :param editor: The editor widget to get the signal from
        :return: The signal that emits when the value on the editor widget changes
        """
        if hasattr(editor, 'valueChanged'):
            return editor.valueChanged
        return None

    def update_editors_attribute(
        self,
        property_: QtProperty[Any],
        action: Callable[[Any], Any],
        check_updating: bool = True
    ) -> None:
        """

        :param property_:
        :param action:
        :param check_updating:
        """
        if check_updating and self._updating_properties:
            return
        for editor in self.get_property_editors(property_):
            with QSignalBlocker(editor):
                action(editor)

    def onPropertyValueChanged(self, property_: QtProperty[Any], value: Any) -> None:
        """
        Handle property value changes from the manager.

        Updates all editor widgets associated with the property to reflect
        the new value. Subclasses should override this method if their
        widgets use a method other than setValue() to update values.

        :param property_: The property that changed
        :param value: The new property value
        """
        if self._updating_properties:
            return
        for editor in self.get_property_editors(property_):
            with QSignalBlocker(editor):
                self.setEditorValue(editor, value)

    def onEditorValueChanged(self, editor: WidgetType, value: Any) -> None:
        """
        Handle editor value changes from the widget.

        Propagates the new value from the editor to the property manager.
        Prevents infinite recursion by blocking propagation for properties
        with sub-properties that may be handled separately.

        :param editor: The editor widget that changed values
        :param value: The new value from the editor
        """
        property_, parent_widget = self._editor_to_property.get(
            editor,
            (None, None)
        )
        if property_ is None:
            return
        manager = self.propertyManager(property_)
        if manager and property_:
            # Only block propagation for properties with subproperties
            # that may be handled in their own way. Blocking propagation
            # for all, prevents properties from updating multiple editors
            # they may have
            self._updating_properties = bool(property_.subProperties())
            manager.setValue(property_, value)
            self._updating_properties = False


# -------- Editor factories that only need the code from the base class --------

class QtCharEditorFactory(QtAbstractEditorFactory[QtCharEdit]):
    """
    Editor factory for character (single-character string) properties.

    This factory creates QtCharEdit widgets for editing single-character
    string properties. The widget provides a specialized input field for
    character entry.

    Registered widget: QtCharEdit
    """
    pass


class QtColorEditorFactory(QtAbstractEditorFactory[QtColorEdit]):
    """
    Editor factory for color (QColor) properties.

    This factory creates QtColorEdit widgets for editing color
    properties. The widget provides a color picker interface with preview.

    Registered widget: QtColorEdit
    """
    pass


class QtFontEditorFactory(QtAbstractEditorFactory[QtFontEdit]):
    """
    Editor factory for font (QFont) properties.

    This factory creates QtFontEdit widgets for editing font
    properties. The widget provides a font selector interface with preview.

    Registered widget: QtFontEdit
    """
    pass

# -------- ------------------------------------------------------------ --------

class QtKeySequenceEditorFactory(QtAbstractEditorFactory[QKeySequenceEdit]):
    """
    Editor factory for key sequence (QKeySequence) properties.

    This factory creates QKeySequenceEdit widgets for editing keyboard
    shortcut properties. The widget provides an input field that captures
    key combinations from the user.

    Registered widget: QKeySequenceEdit
    """

    @override
    @staticmethod
    def setEditorValue(editor: QKeySequenceEdit, value: QKeySequence) -> None:
        editor.setKeySequence(value)

    @override
    @staticmethod
    def getEditorValueChangedSignal(editor: QKeySequenceEdit) -> SignalInstance | None:
        return editor.keySequenceChanged


# noinspection PyPep8Naming
@runtime_checkable
class ManagedBool(Protocol):
    @property
    def textVisibleChanged(self) -> SignalInstance: ...

    def textVisible(self, prop: QtProperty[bool]) -> bool: ...


# noinspection PyPep8Naming
class QtCheckBoxFactory(QtAbstractEditorFactory[QtBoolEdit]):
    """
    Editor factory for boolean (bool) properties.

    This factory creates QtBoolEdit widgets (checkbox-based) for editing
    boolean properties. Supports text visibility configuration from the
    property manager, allowing checkboxes to display 'True'/'False' labels.

    Registered widget: QtBoolEdit
    """

    @override
    @staticmethod
    def setEditorValue(editor: QtBoolEdit, value: bool) -> None:
        editor.setChecked(value)

    @override
    @staticmethod
    def getEditorValueChangedSignal(editor: QtBoolEdit) -> SignalInstance | None:
        return editor.toggled

    @override
    def createEditor(
        self,
        property_: QtProperty[bool],
        parent: QWidget | None = None
    ) -> QtBoolEdit | None:
        editor: QtBoolEdit | None = super().createEditor(property_, parent)
        if editor is None:
            return None
        manager = property_.manager()
        if isinstance(manager, ManagedBool):
            editor.setTextVisible(manager.textVisible(property_))
        return editor

    @override
    def connectPropertyManager(self, manager: QtAbstractPropertyManager[bool]) -> None:
        """
        Connect manager-specific signals for boolean properties.

        Connects the textVisibleChanged signal to synchronize text visibility
        settings across all editors for a property.

        :param manager: The boolean property manager to connect
        """
        if isinstance(manager, ManagedBool):
            manager.textVisibleChanged.connect(self.onTextVisibleChanged)

    @override
    def disconnectPropertyManager(self, manager: QtAbstractPropertyManager[bool]) -> None:
        """
        Disconnect manager-specific signals for boolean properties.

        Disconnects the textVisibleChanged signal when removing a manager.

        :param manager: The boolean property manager to disconnect
        """
        if isinstance(manager, ManagedBool):
            manager.textVisibleChanged.disconnect(self.onTextVisibleChanged)

    def onTextVisibleChanged(self, property_: QtProperty[bool], text_visible: bool) -> None:
        """
        Handle text visibility changes from the property manager.

        Updates all checkbox editors associated with the property to reflect
        the new text visibility setting. Prevents infinite recursion by
        checking the updating_properties flag.

        :param property_: The property whose text visibility changed
        :param text_visible: The new text visibility state
        """
        self.update_editors_attribute(
            property_,
            partial(QtBoolEdit.setTextVisible, text_visible)  # type: ignore
        )


# noinspection PyPep8Naming
@runtime_checkable
class ManagedRangedInteger(Protocol):
    @property
    def rangeChanged(self) -> SignalInstance: ...
    @property
    def singleStepChanged(self) -> SignalInstance: ...
    @property
    def readOnlyChanged(self) -> SignalInstance: ...

    def minimum(self, prop: QtProperty[Any]) -> Any: ...
    def maximum(self, prop: QtProperty[Any]) -> Any: ...
    def singleStep(self, prop: QtProperty[Any]) -> Any: ...
    def isReadOnly(self, prop: QtProperty[Any]) -> bool: ...


# noinspection PyPep8Naming
class QtSpinBoxFactory(QtAbstractEditorFactory[QSpinBox]):
    """
    Editor factory for integer (int) properties.

    This factory creates QSpinBox widgets for editing integer properties.
    Synchronizes range constraints, single step increment, and read-only
    state between the property manager and editor widgets.

    Registered widget: QSpinBox
    """

    @override
    def createEditor(
        self,
        property_: QtProperty[int],
        parent: QWidget | None = None
    ) -> QSpinBox | None:
        editor: QSpinBox | None = super().createEditor(property_, parent)
        if editor is None:
            return None
        manager = property_.manager()
        if not manager:
            return editor
        with QSignalBlocker(editor):
            if isinstance(manager, ManagedRangedInteger):
                editor.setSingleStep(manager.singleStep(property_))
                editor.setRange(
                    manager.minimum(property_),
                    manager.maximum(property_)
                )
                editor.setReadOnly(manager.isReadOnly(property_))
            # Set the value again because previously it was bounded to
            # the default QSpinBox range
            editor.setValue(property_.value())
            editor.setKeyboardTracking(False)
        return editor

    @override
    def connectPropertyManager(self, manager: QtAbstractPropertyManager[int]) -> None:
        """
        Connect manager-specific signals for integer properties.

        Connects rangeChanged, singleStepChanged, and readOnlyChanged signals
        to synchronize these attributes across all editors for a property.

        :param manager: The integer property manager to connect
        """
        if isinstance(manager, ManagedRangedInteger):
            manager.rangeChanged.connect(self.onRangeChanged)
            manager.singleStepChanged.connect(self.onSingleStepChanged)
            manager.readOnlyChanged.connect(self.onReadOnlyChanged)

    @override
    def disconnectPropertyManager(self, manager: QtAbstractPropertyManager[int]) -> None:
        """
        Disconnect manager-specific signals for integer properties.

        Disconnects rangeChanged, singleStepChanged, and readOnlyChanged
        signals when removing a manager.

        :param manager: The integer property manager to disconnect
        """
        if isinstance(manager, ManagedRangedInteger):
            manager.rangeChanged.disconnect(self.onRangeChanged)
            manager.singleStepChanged.disconnect(self.onSingleStepChanged)
            manager.readOnlyChanged.disconnect(self.onReadOnlyChanged)

    def onRangeChanged(
        self,
        property_: QtProperty[int],
        minimum: int,
        maximum: int
    ) -> None:
        """
        Handle range changes from the property manager.

        Updates all spin box editors associated with the property to reflect
        the new minimum and maximum values. Also updates the current value
        to ensure it stays within the new range.

        :param property_: The property whose range changed
        :param minimum: The new minimum value
        :param maximum: The new maximum value
        """
        if self._updating_properties:
            return
        for editor in self.get_property_editors(property_):
            with QSignalBlocker(editor):
                editor.setRange(minimum, maximum)
                editor.setValue(property_.value())

    def onSingleStepChanged(self, property_: QtProperty[int], step: int) -> None:
        """
        Handle single step changes from the property manager.

        Updates all spin box editors associated with the property to reflect
        the new step increment value.

        :param property_: The property whose single step changed
        :param step: The new single step value
        """
        self.update_editors_attribute(
            property_,
            partial(QSpinBox.setSingleStep, step)  # type: ignore
        )

    def onReadOnlyChanged(self, property_: QtProperty[int], read_only: bool) -> None:
        """
        Handle read-only state changes from the property manager.

        Updates all spin box editors associated with the property to reflect
        the new read-only state.

        :param property_: The property whose read-only state changed
        :param read_only: The new read-only state
        """
        self.update_editors_attribute(
            property_,
            partial(QSpinBox.setReadOnly, read_only)  # type: ignore
        )


# noinspection PyPep8Naming
@runtime_checkable
class ManagedRangedFloating(Protocol):
    @property
    def rangeChanged(self) -> SignalInstance: ...
    @property
    def singleStepChanged(self) -> SignalInstance: ...
    @property
    def readOnlyChanged(self) -> SignalInstance: ...
    @property
    def decimalsChanged(self) -> SignalInstance: ...

    def minimum(self, prop: QtProperty[Any]) -> Any: ...
    def maximum(self, prop: QtProperty[Any]) -> Any: ...
    def singleStep(self, prop: QtProperty[Any]) -> Any: ...
    def isReadOnly(self, prop: QtProperty[Any]) -> bool: ...
    def decimals(self, prop: QtProperty[Any]) -> Any: ...


# noinspection PyPep8Naming
class QtDoubleSpinBoxFactory(QtAbstractEditorFactory[QDoubleSpinBox]):
    """
    Editor factory for floating-point (float) properties.

    This factory creates QDoubleSpinBox widgets for editing floating-point
    properties. Synchronizes range constraints, single step increment, decimal
    precision, and read-only state between the property manager and editor
    widgets.

    Registered widget: QDoubleSpinBox
    """

    @override
    def createEditor(
        self,
        property_: QtProperty[float],
        parent: QWidget | None = None
    ) -> QDoubleSpinBox | None:
        editor: QDoubleSpinBox | None = super().createEditor(property_, parent)
        if editor is None:
            return None
        manager = property_.manager()
        if not manager:
            return editor
        with QSignalBlocker(editor):
            if isinstance(manager, ManagedRangedFloating):
                editor.setSingleStep(manager.singleStep(property_))
                editor.setDecimals(manager.decimals(property_))
                editor.setRange(
                    manager.minimum(property_),
                    manager.maximum(property_)
                )
                editor.setReadOnly(manager.isReadOnly(property_))
            # Set the value again because previously it was rounded to the default
            # QDoubleSpinBox decimals and bound to the default range
            editor.setValue(property_.value())
            editor.setKeyboardTracking(False)
        return editor

    @override
    def connectPropertyManager(self, manager: QtAbstractPropertyManager[float]) -> None:
        """
        Connect manager-specific signals for floating-point properties.

        Connects rangeChanged, singleStepChanged, readOnlyChanged, and
        decimalsChanged signals to synchronize these attributes across
        all editors for a property.

        :param manager: The floating-point property manager to connect
        """
        if isinstance(manager, ManagedRangedFloating):
            manager.rangeChanged.connect(self.onRangeChanged)
            manager.singleStepChanged.connect(self.onSingleStepChanged)
            manager.readOnlyChanged.connect(self.onReadOnlyChanged)
            manager.decimalsChanged.connect(self.onDecimalsChanged)

    @override
    def disconnectPropertyManager(self, manager: QtAbstractPropertyManager[float]) -> None:
        """
        Disconnect manager-specific signals for floating-point properties.

        Disconnects rangeChanged, singleStepChanged, readOnlyChanged, and
        decimalsChanged signals when removing a manager.

        :param manager: The floating-point property manager to disconnect
        """
        if isinstance(manager, ManagedRangedFloating):
            manager.rangeChanged.disconnect(self.onRangeChanged)
            manager.singleStepChanged.disconnect(self.onSingleStepChanged)
            manager.readOnlyChanged.disconnect(self.onReadOnlyChanged)
            manager.decimalsChanged.disconnect(self.onDecimalsChanged)

    def onRangeChanged(
        self,
        property_: QtProperty[float],
        minimum: float,
        maximum: float
    ) -> None:
        """
        Handle range changes from the property manager.

        Updates all double spin box editors associated with the property
        to reflect the new minimum and maximum values. Also updates the
        current value to ensure it stays within the new range.

        :param property_: The property whose range changed
        :param minimum: The new minimum value
        :param maximum: The new maximum value
        """
        if self._updating_properties:
            return
        for editor in self.get_property_editors(property_):
            with QSignalBlocker(editor):
                editor.setRange(minimum, maximum)
                editor.setValue(property_.value())

    def onSingleStepChanged(self, property_: QtProperty[float], step: float) -> None:
        """
        Handle single step changes from the property manager.

        Updates all double spin box editors associated with the property
        to reflect the new step increment value.

        :param property_: The property whose single step changed
        :param step: The new single step value
        """
        self.update_editors_attribute(
            property_,
            partial(QDoubleSpinBox.setSingleStep, step)  # type: ignore
        )

    def onReadOnlyChanged(self, property_: QtProperty[float], read_only: bool) -> None:
        """
        Handle read-only state changes from the property manager.

        Updates all double spin box editors associated with the property
        to reflect the new read-only state.

        :param property_: The property whose read-only state changed
        :param read_only: The new read-only state
        """
        self.update_editors_attribute(
            property_,
            partial(QDoubleSpinBox.setReadOnly, read_only)  # type: ignore
        )

    def onDecimalsChanged(self, property_: QtProperty[float], decimals: int) -> None:
        """
        Handle decimal precision changes from the property manager.

        Updates all double spin box editors associated with the property
        to reflect the new decimal precision setting.

        :param property_: The property whose decimal precision changed
        :param decimals: The new decimal precision value
        """
        self.update_editors_attribute(
            property_,
            partial(QDoubleSpinBox.setDecimals, decimals)  # type: ignore
        )


# noinspection PyPep8Naming
@runtime_checkable
class ManagedEnum(Protocol):
    @property
    def enumNamesChanged(self) -> SignalInstance: ...
    @property
    def enumIconsChanged(self) -> SignalInstance: ...

    def enumNames(self, prop: QtProperty[Any]) -> Any: ...
    def enumIcons(self, prop: QtProperty[Any]) -> Any: ...


# Originally sourced from .\QtProperty\qteditorfactory.py
# noinspection PyPep8Naming
class QtEnumEditorFactory(QtAbstractEditorFactory[QComboBox]):
    """
    Editor factory for enum (integer index) properties.

    This factory creates QComboBox widgets for editing enum properties.
    Synchronizes enum names and icons between the property manager and
    editor widgets. The combo box displays enum names with optional icons
    for each option.

    Registered widget: QComboBox
    """

    @override
    @staticmethod
    def setEditorValue(editor: QComboBox, value: int) -> None:
        editor.setCurrentIndex(value)

    @override
    @staticmethod
    def getEditorValueChangedSignal(editor: QComboBox) -> SignalInstance | None:
        return editor.currentIndexChanged

    @override
    def createEditor(
        self,
        property_: QtProperty[int],
        parent: QWidget | None = None
    ) -> QComboBox | None:
        editor: QComboBox | None = super().createEditor(property_, parent)
        # Here can't use [if not editor] because an empty QComboBox will return False
        if editor is None:
            return None
        manager = property_.manager()
        if not manager:
            return editor
        with QSignalBlocker(editor):
            editor.setSizeAdjustPolicy(
                QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )
            editor.setMinimumContentsLength(1)
            editor.view().setTextElideMode(Qt.TextElideMode.ElideRight)
            if isinstance(manager, ManagedEnum):
                enum_names = manager.enumNames(property_)
                editor.addItems(enum_names)
                enum_icons = manager.enumIcons(property_)
                for i in range(len(enum_names)):
                    editor.setItemIcon(i, enum_icons.get(i, QIcon()))
            # Setting the value again since the items of the QComboBox changed
            editor.setCurrentIndex(property_.value())
        return editor

    @override
    def connectPropertyManager(self, manager: QtAbstractPropertyManager[int]) -> None:
        """
        Connect manager-specific signals for enum properties.

        Connects enumNamesChanged and enumIconsChanged signals to synchronize
        these attributes across all editors for a property.

        :param manager: The enum property manager to connect
        """
        if isinstance(manager, ManagedEnum):
            manager.enumNamesChanged.connect(self.onEnumNamesChanged)
            manager.enumIconsChanged.connect(self.onEnumIconsChanged)

    @override
    def disconnectPropertyManager(self, manager: QtAbstractPropertyManager[int]) -> None:
        """
        Disconnect manager-specific signals for enum properties.

        Disconnects enumNamesChanged and enumIconsChanged signals when
        removing a manager.

        :param manager: The enum property manager to disconnect
        """
        if isinstance(manager, ManagedEnum):
            manager.enumNamesChanged.disconnect(self.onEnumNamesChanged)
            manager.enumIconsChanged.disconnect(self.onEnumIconsChanged)

    def onEnumNamesChanged(self, property_: QtProperty[int], enum_names: list[str]) -> None:
        """
        Handle enum names changes from the property manager.

        Updates all combo box editors associated with the property by
        clearing and repopulating the item list with new names and icons.
        Preserves the current selection index when possible.

        :param property_: The property whose enum names changed
        :param enum_names: The new list of enum names
        """
        if self._updating_properties:
            return
        for editor in self.get_property_editors(property_):
            with QSignalBlocker(editor):
                editor.clear()
                editor.addItems(enum_names)
                manager = self.propertyManager(property_)
                if isinstance(manager, ManagedEnum):
                    enum_icons = manager.enumIcons(property_)
                    for i in range(len(enum_names)):
                        editor.setItemIcon(i, enum_icons.get(i, QIcon()))
                editor.setCurrentIndex(property_.value())

    def onEnumIconsChanged(self, property_: QtProperty[int], enum_icons: dict[int, QIcon]) -> None:
        """
        Handle enum icons changes from the property manager.

        Updates all combo box editors associated with the property by
        refreshing the icons for each item while preserving the item names
        and current selection.

        :param property_: The property whose enum icons changed
        :param enum_icons: The new dictionary of enum icons
        """
        if self._updating_properties:
            return
        for editor in self.get_property_editors(property_):
            with QSignalBlocker(editor):
                manager = self.propertyManager(property_)
                if isinstance(manager, ManagedEnum):
                    enum_names = manager.enumNames(property_)
                    for i in range(len(enum_names)):
                        editor.setItemIcon(i, enum_icons.get(i, QIcon()))
                editor.setCurrentIndex(property_.value())


# noinspection PyPep8Naming
@runtime_checkable
class ManagedRangedDate(Protocol):
    @property
    def rangeChanged(self) -> SignalInstance: ...

    def minimum(self, prop: QtProperty[Any]) -> Any: ...
    def maximum(self, prop: QtProperty[Any]) -> Any: ...


# Originally sourced from .\QtProperty\qteditorfactory.py
# noinspection PyPep8Naming
class QtDateEditFactory(QtAbstractEditorFactory[QDateEdit]):
    """
    Editor factory for date (QDate) properties.

    This factory creates QDateEdit widgets for editing date properties.
    Synchronizes date range constraints between the property manager and
    editor widgets. The editor includes a calendar popup for date selection.

    Registered widget: QDateEdit
    """

    @override
    @staticmethod
    def setEditorValue(editor: QDateEdit, value: QDate) -> None:
        editor.setDate(value)

    @override
    @staticmethod
    def getEditorValueChangedSignal(editor: QDateEdit) -> SignalInstance | None:
        return editor.dateChanged

    @override
    def createEditor(
        self,
        property_: QtProperty[QDate],
        parent: QWidget | None = None
    ) -> QDateEdit | None:
        editor: QDateEdit | None = super().createEditor(property_, parent)
        if editor is None:
            return None
        manager = property_.manager()
        if not manager:
            return editor
        with QSignalBlocker(editor):
            editor.setCalendarPopup(True)
            if isinstance(manager, ManagedRangedDate):
                editor.setDateRange(
                    manager.minimum(property_),
                    manager.maximum(property_)
                )
            # Set the date again after the range adjustment
            editor.setDate(property_.value())
        return editor

    @override
    def connectPropertyManager(self, manager: QtAbstractPropertyManager[QDate]) -> None:
        """
        Connect manager-specific signals for date properties.

        Connects the rangeChanged signal to synchronize date range constraints
        across all editors for a property.

        :param manager: The date property manager to connect
        """
        if isinstance(manager, ManagedRangedDate):
            manager.rangeChanged.connect(self.onRangeChanged)

    @override
    def disconnectPropertyManager(self, manager: QtAbstractPropertyManager[QDate]) -> None:
        """
        Disconnect manager-specific signals for date properties.

        Disconnects the rangeChanged signal when removing a manager.

        :param manager: The date property manager to disconnect
        """
        if isinstance(manager, ManagedRangedDate):
            manager.rangeChanged.disconnect(self.onRangeChanged)

    def onRangeChanged(
        self,
        property_: QtProperty[QDate],
        minimum: QDate,
        maximum: QDate
    ) -> None:
        """
        Handle date range changes from the property manager.

        Updates all date editors associated with the property to reflect
        the new minimum and maximum dates. Also updates the current date
        to ensure it stays within the new range.

        :param property_: The property whose date range changed
        :param minimum: The new minimum date
        :param maximum: The new maximum date
        """
        if self._updating_properties:
            return
        for editor in self.get_property_editors(property_):
            with QSignalBlocker(editor):
                editor.setDateRange(minimum, maximum)
                editor.setDate(property_.value())


# Originally sourced from .\QtProperty\qteditorfactory.py
# noinspection PyPep8Naming
class QtTimeEditFactory(QtAbstractEditorFactory[QTimeEdit]):
    """
    Editor factory for time (QTime) properties.

    This factory creates QTimeEdit widgets for editing time properties.
    Provides basic value synchronization between the property manager
    and editor widgets without additional attribute synchronization.

    Registered widget: QTimeEdit
    """

    @override
    @staticmethod
    def setEditorValue(editor: QTimeEdit, value: QTime) -> None:
        editor.setTime(value)

    @override
    @staticmethod
    def getEditorValueChangedSignal(editor: QTimeEdit) -> SignalInstance | None:
        return editor.timeChanged


# Originally sourced from .\QtProperty\qteditorfactory.py
# noinspection PyPep8Naming
class QtDateTimeEditFactory(QtAbstractEditorFactory[QDateTimeEdit]):
    """
    Editor factory for datetime (QDateTime) properties.

    This factory creates QDateTimeEdit widgets for editing datetime properties.
    Provides basic value synchronization between the property manager and
    editor widgets. The editor includes a calendar popup for date selection.

    Registered widget: QDateTimeEdit
    """

    @override
    @staticmethod
    def setEditorValue(editor: QDateTimeEdit, value: QDateTime) -> None:
        editor.setDateTime(value)

    @override
    @staticmethod
    def getEditorValueChangedSignal(editor: QDateTimeEdit) -> SignalInstance | None:
        return editor.dateTimeChanged

    @override
    def createEditor(
        self,
        property_: QtProperty[QDateTime],
        parent: QWidget | None = None
    ) -> QDateTimeEdit | None:
        editor: QDateTimeEdit | None = super().createEditor(property_, parent)
        if editor is None:
            return None
        editor.setCalendarPopup(True)
        return editor


# noinspection PyPep8Naming
@runtime_checkable
class ManagedString(Protocol):
    @property
    def echoModeChanged(self) -> SignalInstance: ...
    @property
    def readOnlyChanged(self) -> SignalInstance: ...
    @property
    def regularExpressionChanged(self) -> SignalInstance: ...

    def echoMode(self, prop: QtProperty[Any]) -> Any: ...
    def isReadOnly(self, prop: QtProperty[Any]) -> bool: ...
    def regularExpression(self, prop: QtProperty[Any]) -> Any: ...


# Originally sourced from .\QtProperty\qteditorfactory.py
# noinspection PyPep8Naming
class QtLineEditFactory(QtAbstractEditorFactory[QLineEdit]):
    """
    Editor factory for string (str) properties.

    This factory creates QLineEdit widgets for editing string properties.
    Synchronizes echo mode, read-only state, and regular expression validation
    between the property manager and editor widgets. Supports password fields
    and input validation through regular expressions.

    Registered widget: QLineEdit
    """

    @override
    @staticmethod
    def setEditorValue(editor: QLineEdit, value: str) -> None:
        editor.setText(value)

    @override
    @staticmethod
    def getEditorValueChangedSignal(editor: QLineEdit) -> SignalInstance | None:
        return editor.textChanged

    @override
    def createEditor(
        self,
        property_: QtProperty[str],
        parent: QWidget | None = None
    ) -> QLineEdit | None:
        editor: QLineEdit | None = super().createEditor(property_, parent)
        if editor is None:
            return None
        manager = property_.manager()
        if not manager:
            return editor
        if isinstance(manager, ManagedString):
            editor.setEchoMode(manager.echoMode(property_))
            editor.setReadOnly(manager.isReadOnly(property_))
            reg_exp = manager.regularExpression(property_)
            if reg_exp.isValid():
                validator = QRegularExpressionValidator(reg_exp, editor)
                editor.setValidator(validator)
        return editor

    @override
    def connectPropertyManager(self, manager: QtAbstractPropertyManager[str]) -> None:
        """
        Connect manager-specific signals for string properties.

        Connects regularExpressionChanged, echoModeChanged, and readOnlyChanged
        signals to synchronize these attributes across all editors for a property.

        :param manager: The string property manager to connect
        """
        if isinstance(manager, ManagedString):
            manager.regularExpressionChanged.connect(self.onRegularExpressionChanged)
            manager.echoModeChanged.connect(self.onEchoModeChanged)
            manager.readOnlyChanged.connect(self.onReadOnlyChanged)

    @override
    def disconnectPropertyManager(self, manager: QtAbstractPropertyManager[str]) -> None:
        """
        Disconnect manager-specific signals for string properties.

        Disconnects regularExpressionChanged, echoModeChanged, and readOnlyChanged
        signals when removing a manager.

        :param manager: The string property manager to disconnect
        """
        if isinstance(manager, ManagedString):
            manager.regularExpressionChanged.disconnect(self.onRegularExpressionChanged)
            manager.echoModeChanged.disconnect(self.onEchoModeChanged)
            manager.readOnlyChanged.disconnect(self.onReadOnlyChanged)

    def onEchoModeChanged(
        self,
        property_: QtProperty[str],
        echo_mode: QLineEdit.EchoMode
    ) -> None:
        """
        Handle echo mode changes from the property manager.

        Updates all line edit editors associated with the property to reflect
        the new echo mode (e.g., Normal, Password, NoEcho).

        :param property_: The property whose echo mode changed
        :param echo_mode: The new echo mode value
        """
        self.update_editors_attribute(
            property_,
            partial(QLineEdit.setEchoMode, echo_mode),  # type: ignore
            check_updating=False
        )

    def onReadOnlyChanged(self, property_: QtProperty[str], read_only: bool) -> None:
        """
        Handle read-only state changes from the property manager.

        Updates all line edit editors associated with the property to reflect
        the new read-only state.

        :param property_: The property whose read-only state changed
        :param read_only: The new read-only state
        """
        self.update_editors_attribute(
            property_,
            partial(QLineEdit.setReadOnly, read_only),  # type: ignore
            check_updating=False
        )

    def onRegularExpressionChanged(
        self,
        property_: QtProperty[str],
        reg_exp: QRegularExpression
    ) -> None:
        """
        Handle regular expression changes from the property manager.

        Updates all line edit editors associated with the property by setting
        a new validator if the regular expression is valid, or removing the
        validator if the expression is invalid.

        :param property_: The property whose regular expression changed
        :param reg_exp: The new regular expression for validation
        """
        for editor in self.get_property_editors(property_):
            with QSignalBlocker(editor):
                new_validator = None
                if reg_exp.isValid():
                    new_validator = QRegularExpressionValidator(reg_exp, editor)
                editor.setValidator(new_validator)  # type: ignore


# Originally sourced from .\QtProperty\qteditorfactory.py
# noinspection PyPep8Naming
class QtSliderFactory(QtAbstractEditorFactory[QSlider]):
    """
    Editor factory for integer (int) properties with slider widgets.

    This factory creates QSlider widgets for editing integer properties.
    Synchronizes range constraints and single step increment between the
    property manager and editor widgets. Sliders are configured with
    horizontal orientation.

    Registered widget: QSlider
    """
    @override
    def createEditor(
        self,
        property_: QtProperty[int],
        parent: QWidget | None = None
    ) -> QSlider | None:
        editor: QSlider | None = super().createEditor(property_, parent)
        if editor is None:
            return None
        editor.setOrientation(Qt.Orientation.Horizontal)
        manager = property_.manager()
        if not manager:
            return editor
        with QSignalBlocker(editor):
            if isinstance(manager, ManagedRangedInteger):
                editor.setSingleStep(manager.singleStep(property_))
                editor.setRange(manager.minimum(property_), manager.maximum(property_))
            # Set the value again because previously it was bounded to the default range
            editor.setValue(property_.value())
        return editor

    @override
    def connectPropertyManager(self, manager: QtAbstractPropertyManager[int]) -> None:
        """
        Connect manager-specific signals for integer slider properties.

        Connects rangeChanged and singleStepChanged signals to synchronize
        these attributes across all editors for a property.

        :param manager: The integer property manager to connect
        """
        if isinstance(manager, ManagedRangedInteger):
            manager.rangeChanged.connect(self.onRangeChanged)
            manager.singleStepChanged.connect(self.onSingleStepChanged)

    @override
    def disconnectPropertyManager(self, manager: QtAbstractPropertyManager[int]) -> None:
        """
        Disconnect manager-specific signals for integer slider properties.

        Disconnects rangeChanged and singleStepChanged signals when
        removing a manager.

        :param manager: The integer property manager to disconnect
        """
        if isinstance(manager, ManagedRangedInteger):
            manager.rangeChanged.disconnect(self.onRangeChanged)
            manager.singleStepChanged.disconnect(self.onSingleStepChanged)

    def onRangeChanged(self, property_: QtProperty[int], minimum: int, maximum: int) -> None:
        """
        Handle range changes from the property manager.

        Updates all slider editors associated with the property to reflect
        the new minimum and maximum values. Also updates the current value
        to ensure it stays within the new range.

        :param property_: The property whose range changed
        :param minimum: The new minimum value
        :param maximum: The new maximum value
        """
        if self._updating_properties:
            return
        for editor in self.get_property_editors(property_):
            with QSignalBlocker(editor):
                editor.setRange(minimum, maximum)
                editor.setValue(property_.value())

    def onSingleStepChanged(self, property_: QtProperty[int], step: int) -> None:
        """
        Handle single step changes from the property manager.

        Updates all slider editors associated with the property to reflect
        the new step increment value.

        :param property_: The property whose single step changed
        :param step: The new single step value
        """
        self.update_editors_attribute(
            property_,
            partial(QSlider.setSingleStep, step)  # type: ignore
        )


# Originally sourced from .\QtProperty\qteditorfactory.py
# noinspection PyPep8Naming
class QtScrollBarFactory(QtAbstractEditorFactory[QScrollBar]):
    """
    Editor factory for integer (int) properties with scroll bar widgets.

    This factory creates QScrollBar widgets for editing integer properties.
    Synchronizes range constraints and single step increment between the
    property manager and editor widgets. Scroll bars are configured with
    horizontal orientation.

    Registered widget: QScrollBar
    """
    @override
    def createEditor(
        self,
        property_: QtProperty[int],
        parent: QWidget | None = None
    ) -> QScrollBar | None:
        editor: QScrollBar | None = super().createEditor(property_, parent)
        if editor is None:
            return None
        editor.setOrientation(Qt.Orientation.Horizontal)
        manager = property_.manager()
        if not manager:
            return editor
        with QSignalBlocker(editor):
            if isinstance(manager, ManagedRangedInteger):
                editor.setSingleStep(manager.singleStep(property_))
                editor.setRange(manager.minimum(property_), manager.maximum(property_))
            # Set the value again because previously it was bounded to the default range
            editor.setValue(property_.value())
        return editor

    @override
    def connectPropertyManager(self, manager: QtAbstractPropertyManager[int]) -> None:
        """
        Connect manager-specific signals for integer scroll bar properties.

        Connects rangeChanged and singleStepChanged signals to synchronize
        these attributes across all editors for a property.

        :param manager: The integer property manager to connect
        """
        if isinstance(manager, ManagedRangedInteger):
            manager.rangeChanged.connect(self.onRangeChanged)
            manager.singleStepChanged.connect(self.onSingleStepChanged)

    @override
    def disconnectPropertyManager(self, manager: QtAbstractPropertyManager[int]) -> None:
        """
        Disconnect manager-specific signals for integer scroll bar properties.

        Disconnects rangeChanged and singleStepChanged signals when
        removing a manager.

        :param manager: The integer property manager to disconnect
        """
        if isinstance(manager, ManagedRangedInteger):
            manager.rangeChanged.disconnect(self.onRangeChanged)
            manager.singleStepChanged.disconnect(self.onSingleStepChanged)

    def onRangeChanged(self, property_: QtProperty[int], minimum: int, maximum: int) -> None:
        """
        Handle range changes from the property manager.

        Updates all scroll bar editors associated with the property to reflect
        the new minimum and maximum values. Also updates the current value
        to ensure it stays within the new range.

        :param property_: The property whose range changed
        :param minimum: The new minimum value
        :param maximum: The new maximum value
        """
        if self._updating_properties:
            return
        for editor in self.get_property_editors(property_):
            with QSignalBlocker(editor):
                editor.setRange(minimum, maximum)
                editor.setValue(property_.value())

    def onSingleStepChanged(self, property_: QtProperty[int], step: int) -> None:
        """
        Handle single step changes from the property manager.

        Updates all scroll bar editors associated with the property to reflect
        the new step increment value.

        :param property_: The property whose single step changed
        :param step: The new single step value
        """
        self.update_editors_attribute(
            property_,
            partial(QScrollBar.setSingleStep, step)  # type: ignore
        )


# Originally sourced from .\QtProperty\qteditorfactory.py
# noinspection PyPep8Naming
class QtCursorEditorFactory(QtAbstractEditorFactory[QComboBox]):
    """
    Editor factory for cursor (QCursor) properties.

    This factory creates QComboBox widgets for editing cursor properties
    through an internal enum property manager. Uses a cursor database to
    provide cursor shape names and icons for selection. Unlike other factories,
    this class does not require external registration as it manages its own
    internal enum factory.

    :ivar _property_to_enum_prop: Mapping from cursor properties to internal enum properties
    :ivar _enum_prop_to_property: Mapping from internal enum properties to cursor properties
    :ivar _enum_sub_manager: Internal enum property manager for cursor shapes
    :ivar _enum_factory: Internal enum editor factory for the combo box widget
    """

    def __init__(self, editor_class: type[QComboBox]) -> None:
        super().__init__(editor_class)
        self._property_to_enum_prop: dict[
            QtProperty[QCursor],
            QtProperty[int]
        ] = dict()
        self._enum_prop_to_property: dict[
            QtProperty[int],
            QtProperty[QCursor]
        ] = dict()
        self._enum_sub_manager = QtEnumPropertyManager()
        self._enum_sub_manager.valueChanged.connect(self.onEnumChanged)
        self._enum_factory = QtEnumEditorFactory(QComboBox)
        self._enum_factory.addPropertyManager(self._enum_sub_manager)

    def close(self):
        """
        Cleanup internal managers and break reference cycles.
        """
        with contextlib.suppress(RuntimeError):
            self._enum_sub_manager.valueChanged.disconnect(self.onEnumChanged)
        with contextlib.suppress(RuntimeError):
            self._enum_factory.removePropertyManager(self._enum_sub_manager)
        self._property_to_enum_prop.clear()
        self._enum_prop_to_property.clear()
        self._created_editors.clear()
        self._editor_to_property.clear()

    @override
    def createEditor(
        self,
        property_: QtProperty[QCursor],
        parent: QWidget | None = None
    ) -> QComboBox | None:
        """
        Create a combo box editor widget for a cursor property.

        Creates or reuses an internal enum property for the cursor, populates
        it with cursor shape names and icons from the cursor database, and
        returns the corresponding combo box editor from the internal enum factory.

        :param property_: The property to create an editor for
        :param parent: The parent widget for the editor
        :return: The created QComboBox widget, or None if creation fails
        """
        if property_ in self._property_to_enum_prop:
            enum_prop = self._property_to_enum_prop[property_]
        else:
            if not CURSOR_DATABASE.isInitialized():
                CURSOR_DATABASE.init()
            enum_prop = self._enum_sub_manager.addProperty(property_.name())
            self._enum_sub_manager.setEnumNames(
                enum_prop,
                CURSOR_DATABASE.cursorShapeNames()
            )
            self._enum_sub_manager.setEnumIcons(
                enum_prop,
                CURSOR_DATABASE.cursorShapeIcons()
            )
            self._enum_sub_manager.setValue(
                enum_prop,
                CURSOR_DATABASE.cursorToIndex(property_.value())
            )
            self._property_to_enum_prop[property_] = enum_prop
            self._enum_prop_to_property[enum_prop] = property_
        editor = self._enum_factory.findEditor(enum_prop, parent)
        if editor is None:
            return None
        parents_to_editors = self._created_editors.setdefault(
            property_,
            WeakValueDictionary()
        )
        parents_to_editors[parent] = editor
        self._editor_to_property[editor] = (property_, parent)
        return editor

    @override
    def onPropertyValueChanged(self, property_: QtProperty[QCursor], value: QCursor) -> None:
        """
        Handle cursor value changes from the property manager.

        Updates all combo box editors associated with the property to reflect
        the new cursor shape by setting the corresponding enum index.

        :param property_: The property whose cursor value changed
        :param value: The new cursor value
        """
        if self._updating_properties:
            return
        for editor in self.get_property_editors(property_):
            with QSignalBlocker(editor):
                editor.setCurrentIndex(CURSOR_DATABASE.cursorToIndex(value))

    @override
    def onEditorValueChanged(self, editor: QComboBox, value: QCursor) -> None:
        """
        Handle editor value changes (overridden to do nothing).

        Value changes from the editor are handled internally by the enum
        property manager and onEnumChanged handler, so this method is
        intentionally left empty.
        """
        pass

    def onEnumChanged(self, property_: QtProperty[int], value: int) -> None:
        """
        Handle enum value changes from the internal enum property manager.

        Converts the enum index back to a QCursor and updates the corresponding
        cursor property. This is the main synchronization path for editor-to-property
        value changes in this factory.

        :param property_: The internal enum property that changed
        :param value: The new enum index value
        """
        if self._updating_properties:
            return
        # Update cursor property
        cursor_prop = self._enum_prop_to_property.get(property_, None)
        if cursor_prop is None:
            return
        cursor_prop.setValue(QCursor(CURSOR_DATABASE.indexToCursor(value)))

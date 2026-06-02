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
import itertools
from enum import StrEnum, auto, IntFlag
from typing import override, TypeVar, Generic, Any

from PySide6.QtCore import (
    Qt, Signal, QRect, QDate, QLocale, QTime, QDateTime, QRegularExpression,
    QObject, QPoint, QPointF, QSize, QSizeF, QRectF, QTimer, SignalInstance
)
from PySide6.QtGui import (
    QIcon, QKeySequence, QColor, QBrush, QCursor, QFont, QFontDatabase
)
from PySide6.QtWidgets import (
    QApplication, QLineEdit, QSizePolicy
)

from qtpropertybrowser.utils import (
    CURSOR_DATABASE,
    draw_check_box,
    brushValueIcon,
    formatMultiWordName,
    fontValueText,
    fontValuePixmap
)


class _BaseSignalEmitter(QObject):
    """
    Isolated internal QObject to manage Qt signals without corrupting the MRO
    of the QtProperty class and managers.

     :ivar propertyChanged: Signal emitted when any attribute changes
     :ivar valueChanged: Signal emitted when the value changes
     :ivar propertyInserted: Signal emitted when a sub-property is inserted
     :ivar propertyRemoved: Signal emitted when a sub-property is removed
     :ivar propertyDestroyed: Signal emitted when the property is being destroyed
    """

    propertyChanged = Signal(object, str, object)
    """ propertyChanged(property, attribute, value) """
    valueChanged = Signal(object, object)
    """ valueChanged(property, value) """
    propertyInserted = Signal(object, object, object)
    """ propertyInserted(property, parent_property, after_property) """
    propertyRemoved = Signal(object, object)
    """ propertyRemoved(property, parent_property) """
    propertyDestroyed = Signal(object)
    """ propertyDestroyed(property) """


ValueType = TypeVar('ValueType')

# noinspection PyPep8Naming
class QtProperty(Generic[ValueType]):
    """
     Represents a property with metadata and hierarchical relationships.

     This class provides a generic property implementation with support for
     attributes, value changes, and parent-child relationships. Properties
     can be organized in a tree structure and emit signals when their
     state changes.

     Signals emitting is handled internally by a SignalEmitter object
     """

    class Attributes(StrEnum):
        """
        Enum for the default QtProperty attributes to be accessed or set via its
        metadata accessor functions.

        The value of each enum member is a lowercase version of its name.
        """
        NAME = auto()
        VALUE = auto()
        ENABLED = auto()
        TOOLTIP = auto()
        STATUS_TIP = auto()
        WHATS_THIS = auto()
        MODIFIED = auto()
        NAME_COLOR = auto()
        VALUE_COLOR = auto()


    def __init__(
        self,
        name: str,
        value: ValueType,
        manager: QtAbstractPropertyManager[ValueType] | None = None,
    ) -> None:
        """
        Initialize a QtProperty instance.

        :param name: The name of the property
        :param value: Initial value of the property
        :param manager: The manager responsible for this property
        """
        self._emitter: _BaseSignalEmitter = _BaseSignalEmitter()

        self._manager: QtAbstractPropertyManager[ValueType] | None = manager
        self._parent_properties: set[QtProperty[Any]] = set()
        self._sub_properties: list[QtProperty[Any]] = list()
        self._attributes: dict[str, Any] = dict()

        self._value: ValueType = value
        self._enabled: bool = True
        self._modified: bool = False
        self._name: str = name
        self._tooltip: str = ''
        self._status_tip: str = ''
        self._whats_this: str = ''
        self._name_color: QColor = QColor()
        self._value_color: QColor = QColor()

    def __del__(self) -> None:
        self.destroy()

    # ----- Signals -----

    @property
    def propertyChanged(self) -> SignalInstance:
        """ Signal emitted when any attribute of the property changes. """
        return self._emitter.propertyChanged

    @property
    def valueChanged(self) -> SignalInstance:
        """ Signal emitted when the value of the property changes """
        return self._emitter.valueChanged

    @property
    def propertyInserted(self) -> SignalInstance:
        """ Signal emitted when a sub-property is inserted as a child """
        return self._emitter.propertyInserted

    @property
    def propertyRemoved(self) -> SignalInstance:
        """ Signal emitted when a child sub-property is removed """
        return self._emitter.propertyRemoved

    @property
    def propertyDestroyed(self) -> SignalInstance:
        """ Signal emitted when the property is being destroyed """
        return self._emitter.propertyDestroyed

    # ----- For attributes/metadata -----

    def attributes(self) -> dict[str, Any]:
        """
        Return the dictionary of custom attributes.

        .. note::
            Modification of the dictionary outside the object will not
            automatically register as a property change.

        :return: The attributes dictionary
        """
        return self._attributes

    def hasAttribute(self, key: str) -> bool:
        """
        Check if an attribute exists.

        .. note::
            Modifications of the returned value in-place (i.e. modifying a
            returned list) will not automatically register as a property change.

        :param key: The attribute key to check
        :return: True if the attribute exists, False otherwise
        """
        return key in self._attributes

    def getAttributeValue(self, key: str, default: Any | None = None) -> Any:
        """
        Get the value of an attribute.

        :param key: The attribute key
        :param default: Default value if the attribute does not exist
        :return: The attribute value or default
        """
        return self._attributes.get(key, default)

    def setAttributeValue(self, key: str, value: Any) -> bool:
        """
        Set the value of an attribute. If the attribute changes value, it will
        trigger the propertyChanged() signal.

        :param key: The attribute key
        :param value: The value to set
        :return: True if the attribute changed, False otherwise
        """
        changed = False
        if key not in self._attributes or self._attributes[key] != value:
            changed = True
        self._attributes[key] = value
        if changed:
            self.propertyChanged.emit(self, key, value)
        return changed

    # ----- Getters y Setters -----

    def manager(self) -> QtAbstractPropertyManager[ValueType] | None:
        """
        Return the property manager this property belongs to.

        :return: The property manager
        """
        return self._manager

    def subProperties(self) -> list[QtProperty]:
        """
         Return the list of sub-properties of this property.

         .. note::
             Returns a copy so the list can't be modified by accident from outside.

         :return: List of sub-properties
         """
        return self._sub_properties[:]

    def parentProperties(self) -> list[QtProperty]:
        """
        Return a list of parent properties that have this property as one of
        their children.

        .. note::
            Returns a copy so the set of parents can't be modified by accident
            from outside.

        :return: List of parent properties
        """
        return list(self._parent_properties)

    def name(self) -> str:
        """
        Return the property name.

        :return: The property name
        """
        return self._name

    def setName(self, name: str) -> None:
        """
        Set the property name.

        :param name: The new property name
        """
        if self._name == name:
            return
        self._name = name
        self.propertyChanged.emit(self, QtProperty.Attributes.NAME, name)

    def hasValue(self) -> bool:
        """
        Check if the property has a value (i.e: the value if not None).

        :return: True if the property has a value, False otherwise
        """
        return self._value is not None

    def value(self) -> ValueType:
        """
        Return the property value.

        :return: The property value
        :raises AttributeError: If the property has no value (i.e: value is None)
        """
        return self._value

    def setValue(self, value: ValueType) -> bool:
        """
        Set the property value. If the value changes, it will trigger the
        valueChanged() signal.

        :param value: The new value
        :return: True if the value changed, False otherwise
        """
        if value == self._value:
            return False
        self._value = value
        self.valueChanged.emit(self, value)
        self.propertyChanged.emit(self, QtProperty.Attributes.VALUE, value)
        return True

    def isEnabled(self) -> bool:
        """
        Check if the property is enabled.

        This attribute is to be used mainly within property browsers.

        :return: True if enabled, False otherwise
        """
        return self._enabled

    def setEnabled(self, enabled: bool) -> None:
        """
        Set the enabled state of the property.

        :param enabled: The enabled state
        """
        if self._enabled == enabled:
            return
        self._enabled = enabled
        self.propertyChanged.emit(self, QtProperty.Attributes.ENABLED, enabled)

    def toolTip(self) -> str:
        """
        Return the tooltip text.

        :return: The tooltip text
        """
        return self._tooltip

    def setToolTip(self, text: str) -> None:
        """
        Set the tooltip text.

        :param text: The tooltip text
        """
        if self._tooltip == text:
            return
        self._tooltip = text
        self.propertyChanged.emit(self, QtProperty.Attributes.TOOLTIP, text)

    def statusTip(self) -> str:
        """
        Return the status tip text.

        :return: The status tip text
        """
        return self._status_tip

    def setStatusTip(self, text: str) -> None:
        """
        Set the status tip text.

        :param text: The status tip text
        """
        if self._status_tip == text:
            return
        self._status_tip = text
        self.propertyChanged.emit(self, QtProperty.Attributes.STATUS_TIP, text)

    def whatsThis(self) -> str:
        """
        Return the 'What's This' help text.

        :return: The 'What's This' text
        """
        return self._whats_this

    def setWhatsThis(self, text: str) -> None:
        """
        Set the 'What's This' help text.

        :param text: The 'What's This' text
        """
        if self._whats_this == text:
            return
        self._whats_this = text
        self.propertyChanged.emit(self, QtProperty.Attributes.WHATS_THIS, text)

    def isModified(self) -> bool:
        """
        Check if the property has been modified.

        :return: True if modified, False otherwise
        """
        return self._modified

    def setModified(self, modified: bool) -> None:
        """
        Set the modified state of the property.

        :param modified: The modified state
        """
        if self._modified == modified:
            return
        self._modified = modified
        self.propertyChanged.emit(self, QtProperty.Attributes.MODIFIED, modified)

    def nameColor(self) -> QColor:
        """
        Return the display color of the property name.

        :return: The name color
        """
        return self._name_color

    def setNameColor(self, color: QColor) -> None:
        """
        Set the display color of the property name.

        :param color: The new name color
        """
        if self._name_color == color:
            return
        self._name_color = color
        self.propertyChanged.emit(self, QtProperty.Attributes.NAME_COLOR, color)

    def valueColor(self) -> QColor:
        """
        Return the display color of the property value.

        :return: The value color
        """
        return self._value_color

    def setValueColor(self, color: QColor) -> None:
        """
        Set the display color of the property value.

        :param color: The new value color
        """
        if self._value_color == color:
            return
        self._value_color = color
        self.propertyChanged.emit(self, QtProperty.Attributes.VALUE_COLOR, color)

    # ----- Determined by the manager -----

    def valueIcon(self) -> QIcon:
        """
        Return the manager assigned icon for this property's value.

        :return: The value icon, or empty QIcon if the property has no manager
        """
        if self._manager:
            return self._manager.valueIcon(self)
        return QIcon()

    def valueText(self) -> str:
        """
        Return the manager assigned text for this property's value.

        :return: The value text, or empty string if the property has no manager
        """
        if self._manager:
            return self._manager.valueText(self)
        return ""

    def displayText(self) -> str:
        """
        Return the display text from the manager for this property.

        :return: The display text, or empty string if the property has no manager
        """
        if self._manager:
            return self._manager.displayText(self)
        return ""

    # ----- Hierarchical structure -----

    def addSubProperty(self, property_: QtProperty[Any]) -> None:
        """
        Add a sub-property at the end of the list of this property's children.

        If the property to be inserted is already a child, it does nothing.

        :param property_: The sub-property to add
        """
        if not property_:
            return
        self.insertSubProperty(property_, None)

    def insertSubProperty(self, property_: QtProperty[Any], after: QtProperty[Any] | None) -> None:
        """
        Insert a sub-property at a specific position in the list of this property's children.

        If the property to be inserted is already a child, it does nothing.

        :param property_: The sub-property to insert
        :param after: The sub-property to insert after, or None for end of list
        """
        if not property_ or property_ == self:
            return
        # Traverse all the children of this item. If the new property item
        # is a child of this item, then it cannot be added.
        pending = self._sub_properties[:]
        visited = set()
        while pending:
            sub_items = itertools.chain.from_iterable(
                item.subProperties() for item in pending
            )
            children = list()
            for child in sub_items:
                if child == property_:
                    return
                if id(child) not in visited:
                    visited.add(id(child))
                    children.append(child)
            pending = children[:]
        position: int = len(self._sub_properties)
        after_property = None if position == 0 else self._sub_properties[-1]
        if after is not None and after in self._sub_properties:
            after_property = after
            position = self._sub_properties.index(after) + 1
        self._sub_properties.insert(position, property_)
        property_._parent_properties.add(self)
        self.propertyInserted.emit(property_, self, after_property)

    def removeSubProperty(self, property_: QtProperty[Any]) -> None:
        """
        Remove a sub-property.

        If the property to be removed is not a child of this property, it does nothing.

        :param property_: The sub-property to remove
        """
        if not property_ or property_ not in self._sub_properties:
            return
        self._sub_properties.remove(property_)
        property_._parent_properties.discard(self)
        self.propertyRemoved.emit(property_, self)

    # ----- Cleanup -----

    def clearSubProperties(self) -> None:
        """
        Remove all sub-properties.
        """
        for sub_prop in list(self._sub_properties):
            self.removeSubProperty(sub_prop)
        self._sub_properties.clear()

    def destroy(self) -> None:
        """
        Destroy the property and clean up all relationships.

        This method clears all sub-properties, removes this property from
        all parent properties, and schedules the object for deletion.
        """
        self.clearSubProperties()
        for parent in list(self._parent_properties):
            parent.removeSubProperty(self)
        self.propertyDestroyed.emit(self)


# noinspection PyPep8Naming
class QtAbstractPropertyManager(Generic[ValueType]):
    """
    Abstract base class for property managers.

    This class provides the foundation for managing properties of a specific type.
    It handles property creation, value management, and signal emission when
    properties change. Subclasses should override methods to implement type-specific
    behavior.

    Signals emitting is handled internally by a SignalEmitter object

    :cvar DEFAULT_VALUE: Default value for properties managed by this manager. Each
      subclass must define its own default value.
    """

    DEFAULT_VALUE: ValueType

    def __init__(self, name: str='') -> None:
        """
        Initialize the property manager.

        :param name: The name of the manager
        """
        self._name: str = name
        self._managed_properties: set[QtProperty[ValueType]] = set()
        self._emitter: _BaseSignalEmitter = _BaseSignalEmitter()

    def __del__(self) -> None:
        self.destroy()

    # ----- Signals -----

    @property
    def propertyChanged(self) -> SignalInstance:
        """ Signal emitted when any attribute of a property changes """
        return self._emitter.propertyChanged

    @property
    def valueChanged(self) -> SignalInstance:
        """ Signal emitted when the value of a property changes """
        return self._emitter.valueChanged

    @property
    def propertyInserted(self) -> SignalInstance:
        """ Signal emitted when a sub-property is inserted as a child of an existing property """
        return self._emitter.propertyInserted

    @property
    def propertyRemoved(self) -> SignalInstance:
        """ Signal emitted when a child sub-property is removed from an existing property """
        return self._emitter.propertyRemoved

    @property
    def propertyDestroyed(self) -> SignalInstance:
        """ Signal emitted when a property is being destroyed """
        return self._emitter.propertyDestroyed

    def name(self) -> str:
        """
        Return the manager name.

        :return: The manager name
        """
        return self._name

    def properties(self) -> list[QtProperty[ValueType]]:
        """
        Return a list of all managed properties.

        :return: List of managed properties
        """
        return list(self._managed_properties)

    def value(self, property_: QtProperty[ValueType]) -> ValueType:
        """
        Return the value of a property.

        :param property_: The property to get the value from
        :return: The property value, or DEFAULT_VALUE if not managed
        """
        if property_ not in self._managed_properties:
            return self.DEFAULT_VALUE
        return property_.value()

    def setValue(self, property_: QtProperty[ValueType], value: ValueType) -> bool:
        """
        Set the value of a property.

        :param property_: The property to set the value on
        :param value: The new value
        :return: True if the value was changed, False otherwise
        """
        if property_ not in self._managed_properties:
            return False
        return property_.setValue(value)

    def hasValue(self, property_: QtProperty[ValueType]) -> bool:
        """
        Check if a property has a value.

        :param property_: The property to check
        :return: True if the property has a value, False otherwise or if not managed
        """
        if property_ not in self._managed_properties:
            return False
        return property_.hasValue()

    def valueIcon(self, property_: QtProperty[ValueType]) -> QIcon:
        """
        Return the icon for a property value.

        :param property_: The property to get the icon for
        :return: The value icon, or empty QIcon by default
        """
        return QIcon()

    def valueText(self, property_: QtProperty[ValueType]) -> str:
        """
        Return the text representation of a property value.

        :param property_: The property to get the text for
        :return: The value text, or empty string by default
        """
        return ''

    def displayText(self, property_: QtProperty[ValueType]) -> str:
        """
        Return the display text for a property value.

        :param property_: The property to get the display text for
        :return: The display text, or empty string by default
        """
        return ''

    def addProperty(self, name: str='', value: ValueType | None = None) -> QtProperty[ValueType]:
        """
        Create and add a new property.

        This is the preferred method to create new properties. Subclasses should
        override createProperty() to implement type-specific property creation.

        :param name: The name of the new property
        :param value: The initial value of the property
        :return: The created property, or None if creation failed
        """
        if value is None:
           value = self.DEFAULT_VALUE
        property_ = self.createProperty(name, value)
        if property_:
            self._managed_properties.add(property_)
            property_.propertyChanged.connect(self.propertyChanged)
            property_.valueChanged.connect(self.valueChanged)
            property_.propertyInserted.connect(self.propertyInserted)
            property_.propertyRemoved.connect(self.propertyRemoved)
            property_.propertyDestroyed.connect(self.onPropertyDestroyed)
        return property_

    def createProperty(
        self,
        name: str,
        value: ValueType,
    ) -> QtProperty[ValueType]:
        """
        Create a new property instance.

        Subclasses should override this method to manage type-specific attributes
        in addition to the value itself.

        :param name: The name of the property
        :param value: The initial value of the property
        :return: The created property
        """
        return QtProperty[ValueType](name, value, manager=self)

    def removeProperty(self, property_: QtProperty[ValueType]) -> None:
        """
        Remove a property from management.

        Disconnects all signal connections and emits the propertyRemoved signal.

        :param property_: The property to remove
        """
        if property_ in self._managed_properties:
            self._managed_properties.remove(property_)
            with contextlib.suppress(RuntimeError):
                property_.propertyChanged.disconnect(self.propertyChanged)
                property_.valueChanged.disconnect(self.valueChanged)
                property_.propertyInserted.disconnect(self.propertyInserted)
                property_.propertyRemoved.disconnect(self.propertyRemoved)
                property_.propertyDestroyed.disconnect(self.onPropertyDestroyed)
            self.propertyRemoved.emit(property_, None)

    def onPropertyDestroyed(self, property_: QtProperty[ValueType]):
        """
        Handle property destruction.

        Emits the propertyDestroyed signal and removes the property from management.

        :param property_: The property that was destroyed
        """
        if property_ in self._managed_properties:
            self.propertyDestroyed.emit(property_)
            self._managed_properties.remove(property_)

    def clear(self) -> None:
        """
        Remove all managed properties.

        Destroys all properties currently managed by this manager.
        """
        while self._managed_properties:
            prop = self._managed_properties.pop()
            self.propertyRemoved.emit(prop, None)
            prop.destroy()

    def destroy(self) -> None:
        """
        Destroy the manager and clean up all resources.

        Clears all managed properties and schedules the manager for deletion.
        """
        self.clear()


# noinspection PyPep8Naming
class QtGroupPropertyManager(QtAbstractPropertyManager[None]):
    """
    The QtGroupPropertyManager provides and manages group properties.
    This class is intended to provide a grouping element without any value.
    """
    DEFAULT_VALUE = None


class _BoolManagerSignalEmitter(_BaseSignalEmitter):
    """
    Internal emitter for the QtBoolPropertyManager

    :ivar textVisibleChanged: Signal emitted when text visibility changes
    """

    textVisibleChanged = Signal(object, bool)
    """ textVisibleChanged(property, status) """


# noinspection PyPep8Naming
class QtBoolPropertyManager(QtAbstractPropertyManager[bool]):
    """
    Property manager for boolean properties.

    This class manages boolean properties with support for text visibility
    and checkbox icon representation. Properties can display their value as
    text ('True'/'False') and/or as a checkbox icon.

    :cvar DEFAULT_VALUE: Default value for boolean properties
    """
    DEFAULT_VALUE: bool = False


    class BoolAttributes(StrEnum):
        """
        Enum for boolean-specific property attributes.

        These attributes extend the default QtProperty attributes with
        options specific to boolean property types.
        """
        TEXT_VISIBLE = auto()


    def __init__(self, name: str = '') -> None:
        super().__init__(name)
        self._emitter: _BoolManagerSignalEmitter = _BoolManagerSignalEmitter()

    @property
    def textVisibleChanged(self) -> SignalInstance:
        """ Signal emitted when the bool text visibility of a property changes """
        return self._emitter.textVisibleChanged

    @override
    def createProperty(
        self,
        name: str='',
        value: bool=DEFAULT_VALUE,
    ) -> QtProperty[bool]:
        """
        Create a new boolean property instance.

        Sets the default text visibility attribute to True for new properties.

        :param name: The name of the property
        :param value: The initial boolean value
        :return: The created property
        """
        property_ = super().createProperty(name, value)
        property_.setAttributeValue(self.BoolAttributes.TEXT_VISIBLE, True)
        return property_

    def textVisible(self, property_: QtProperty[bool]) -> bool:
        """
        Check if text representation is visible for a property.

        :param property_: The property to check
        :return: True if text is visible, False otherwise
        """
        if property_ not in self._managed_properties:
            return False
        return property_.getAttributeValue(self.BoolAttributes.TEXT_VISIBLE, False)

    def setTextVisible(self, property_: QtProperty[bool], text_visible: bool) -> None:
        """
        Set the text visibility for a property.

        Emits textVisibleChanged if the value changes.

        :param property_: The property to modify
        :param text_visible: Whether to show text representation
        """
        if property_ not in self._managed_properties:
            return
        if property_.setAttributeValue(self.BoolAttributes.TEXT_VISIBLE, text_visible):
            self.textVisibleChanged.emit(property_, text_visible)

    @override
    def valueText(self, property_: QtProperty[bool]) -> str:
        """
        Return the text representation of a boolean value.

        Returns 'True' or 'False' if text visibility is enabled, otherwise
        returns an empty string.

        :param property_: The property to get the text for
        :return: The text representation or empty string
        """
        if property_ not in self._managed_properties:
            return ''
        labels = {True: 'True', False: 'False'}
        text = labels[property_.value()] if self.textVisible(property_) else ''
        if (instance := QApplication.instance()) is not None:
            return instance.tr(text)
        else:
            return text

    @override
    def valueIcon(self, property_: QtProperty[bool]) -> QIcon:
        """
        Return the checkbox icon for a boolean property.

        :param property_: The property to get the icon for
        :return: The checkbox icon representing the boolean value
        """
        if property_ not in self._managed_properties:
            return QIcon()
        return draw_check_box(property_.value())


class _IntManagerSignalEmitter(_BaseSignalEmitter):
    """
    Internal emitter for the QtIntPropertyManager

    :ivar rangeChanged: Signal emitted when the range changes
    :ivar singleStepChanged: Signal emitted when the single step changes
    :ivar readOnlyChanged: Signal emitted when read-only state changes
    """

    rangeChanged = Signal(QtProperty, int, int)
    """ rangeChanged(property, minimum, maximum) """
    singleStepChanged = Signal(QtProperty, int)
    """ singleStepChanged(property, step) """
    readOnlyChanged = Signal(QtProperty, bool)
    """ readOnlyChanged(property, status) """


# noinspection PyPep8Naming
class QtIntPropertyManager(QtAbstractPropertyManager[int]):
    """
    Property manager for integer properties.

    This class manages integer properties with support for range constraints,
    single step increments, and read-only state. Properties can be configured
    with minimum and maximum values, and the manager ensures values stay within
    the defined range.

    :cvar MAXIMUM_INT: Maximum allowed integer value
    :cvar MINIMUM_INT: Minimum allowed integer value
    :cvar DEFAULT_VALUE: Default value for integer properties
    """
    MAXIMUM_INT: int = 2 ** 31 - 1
    MINIMUM_INT: int = -MAXIMUM_INT
    DEFAULT_VALUE: int = 0


    class IntAttributes(StrEnum):
        """
        Enum for integer-specific property attributes.

        These attributes extend the default QtProperty attributes with
        options specific to integer property types.
        """
        RANGE = auto()
        READONLY = auto()
        SINGLE_STEP = auto()


    def __init__(self, name: str = '') -> None:
        super().__init__(name)
        self._emitter: _IntManagerSignalEmitter = _IntManagerSignalEmitter()

    @property
    def rangeChanged(self) -> SignalInstance:
        """ Signal emitted when the range of values for a property changes """
        return self._emitter.rangeChanged

    @property
    def singleStepChanged(self) -> SignalInstance:
        """ Emitted when the increment step of the value for a property changes """
        return self._emitter.singleStepChanged

    @property
    def readOnlyChanged(self) -> SignalInstance:
        """ Signal emitted when the read-only status of a property changes """
        return self._emitter.rangeChanged

    @override
    def createProperty(
        self,
        name: str,
        value: int,
    ) -> QtProperty[int]:
        """
        Create a new integer property instance.

        Sets default attributes including range (MINIMUM_INT to MAXIMUM_INT),
        single step of 1, and read-only state of False.

        :param name: The name of the property
        :param value: The initial integer value
        :return: The created property
        """
        property_ = super().createProperty(name, value)
        range_min, range_max = (self.MINIMUM_INT, self.MAXIMUM_INT)
        property_.setAttributeValue(self.IntAttributes.RANGE, (range_min, range_max))
        property_.setAttributeValue(self.IntAttributes.SINGLE_STEP, 1)
        property_.setAttributeValue(self.IntAttributes.READONLY, False)
        return property_

    @override
    def setValue(self, property_: QtProperty[int], value: int) -> bool:
        """
        Set the value of an integer property.

        The value is clamped to the property's defined range before being set.

        :param property_: The property to set the value on
        :param value: The new integer value
        :return: True if the value changed, False otherwise
        """
        if property_ not in self._managed_properties:
            return False
        range_min, range_max = property_.getAttributeValue(
            self.IntAttributes.RANGE,
            (0, 0)
        )
        value = max(range_min, min(value, range_max))
        return property_.setValue(value)

    def minimum(self, property_: QtProperty[int]) -> int:
        """
        Return the minimum value of a property's range.

        :param property_: The property to get the minimum from
        :return: The minimum value
        """
        if property_ not in self._managed_properties:
            return 0
        minimum, _ = property_.getAttributeValue(
            self.IntAttributes.RANGE,
            (0, 0)
        )
        return minimum

    def setMinimum(self, property_: QtProperty[int], minimum: int) -> None:
        """
        Set the minimum value of a property's range.

        Emits rangeChanged if the range changes. The property value
        is clamped to the new range if necessary.

        :param property_: The property to modify
        :param minimum: The new minimum value
        """
        if property_ not in self._managed_properties:
            return
        range_min, range_max = property_.getAttributeValue(
            self.IntAttributes.RANGE,
            (0, 0)
        )
        range_min, range_max = minimum, max(minimum, range_max)
        if property_.setAttributeValue(
            self.IntAttributes.RANGE,
            (range_min, range_max)
        ):
            self.rangeChanged.emit(property_, range_min, range_max)
            value = max(range_min, min(property_.value(), range_max))
            property_.setValue(value)

    def maximum(self, property_: QtProperty[int]) -> int:
        """
        Return the maximum value of a property's range.

        :param property_: The property to get the maximum from
        :return: The maximum value
        """
        if property_ not in self._managed_properties:
            return 0
        _, maximum = property_.getAttributeValue(
            self.IntAttributes.RANGE,
            (0, 0)
        )
        return maximum

    def setMaximum(self, property_: QtProperty[int], maximum: int) -> None:
        """
        Set the maximum value of a property's range.

        Emits rangeChanged if the range changes. The property value
        is clamped to the new range if necessary.

        :param property_: The property to modify
        :param maximum: The new maximum value
        """
        if property_ not in self._managed_properties:
            return
        range_min, range_max = property_.getAttributeValue(
            self.IntAttributes.RANGE,
            (0, 0)
        )
        range_min, range_max = min(range_min, maximum), maximum
        if property_.setAttributeValue(
            self.IntAttributes.RANGE,
            (range_min, range_max)
        ):
            self.rangeChanged.emit(property_, range_min, range_max)
            value = max(range_min, min(property_.value(), range_max))
            property_.setValue(value)

    def setRange(self, property_: QtProperty[int], minimum: int, maximum: int) -> None:
        """
        Set both minimum and maximum values of a property's range.

        Emits rangeChanged if the range changes. The property value
        is clamped to the new range if necessary.

        :param property_: The property to modify
        :param minimum: The new minimum value
        :param maximum: The new maximum value
        """
        if property_ not in self._managed_properties:
            return
        range_min, range_max = min(minimum, maximum), max(minimum, maximum)
        if property_.setAttributeValue(
            self.IntAttributes.RANGE,
            (range_min, range_max)
        ):
            self.rangeChanged.emit(property_, range_min, range_max)
            value = max(range_min, min(property_.value(), range_max))
            property_.setValue(value)

    def singleStep(self, property_: QtProperty[int]) -> int:
        """
        Return the single step increment for a property.

        :param property_: The property to get the step from
        :return: The single step value
        """
        if property_ not in self._managed_properties:
            return 0
        return property_.getAttributeValue(self.IntAttributes.SINGLE_STEP, 0)

    def setSingleStep(self, property_: QtProperty[int], step: int) -> None:
        """
        Set the single step increment for a property.

        Emits singleStepChanged if the step changes.

        :param property_: The property to modify
        :param step: The new single step value
        """
        if property_ not in self._managed_properties:
            return
        if property_.setAttributeValue(self.IntAttributes.SINGLE_STEP, step):
            self.singleStepChanged.emit(property_, step)

    def isReadOnly(self, property_: QtProperty[int]) -> bool:
        """
        Check if a property is read-only.

        :param property_: The property to check
        :return: True if read-only, False otherwise
        """
        if property_ not in self._managed_properties:
            return False
        return property_.getAttributeValue(self.IntAttributes.READONLY, False)

    def setReadOnly(self, property_: QtProperty[int], read_only: bool) -> None:
        """
        Set the read-only state of a property.

        Emits readOnlyChanged if the state changes.

        :param property_: The property to modify
        :param read_only: The new read-only state
        """
        if property_ not in self._managed_properties:
            return
        if property_.setAttributeValue(self.IntAttributes.READONLY, read_only):
            self.readOnlyChanged.emit(property_, read_only)

    @override
    def valueText(self, property_: QtProperty[int]) -> str:
        """
        Return the text representation of an integer value.

        :param property_: The property to get the text for
        :return: The string representation of the integer value
        """
        if property_ not in self._managed_properties:
            return ''
        text = str(property_.value())
        if (instance := QApplication.instance()) is not None:
            return instance.tr(text)
        else:
            return text


class _DoubleManagerSignalEmitter(_BaseSignalEmitter):
    """
    Internal emitter for the QtDoublePropertyManager

    :ivar rangeChanged: Signal emitted when the range changes
    :ivar singleStepChanged: Signal emitted when the single step changes
    :ivar readOnlyChanged: Signal emitted when read-only state changes
    :ivar decimalsChanged: Signal emitted when decimal precision changes
    """

    rangeChanged = Signal(QtProperty, float, float)
    """ rangeChanged(property, minimum, maximum) """
    singleStepChanged = Signal(QtProperty, float)
    """ singleStepChanged(property, step) """
    readOnlyChanged = Signal(QtProperty, bool)
    """ readOnlyChanged(property, status) """
    decimalsChanged = Signal(QtProperty, int)
    """ decimalsChanged(property, precision) """


# Originally sourced from .\QtProperty\qtpropertymanager.py
# noinspection PyPep8Naming
class QtDoublePropertyManager(QtAbstractPropertyManager[float]):
    """
    Property manager for floating-point properties.

    This class manages double/float properties with support for range constraints,
    decimal precision, single step increments, and read-only state. Properties can
    be configured with minimum and maximum values, and the manager ensures values
    stay within the defined range.

    :cvar MAXIMUM_FLOAT: Maximum allowed float value
    :cvar MINIMUM_FLOAT: Minimum allowed float value
    :cvar DEFAULT_VALUE: Default value for float properties
    """
    MAXIMUM_FLOAT: float = 2.0 ** 31 - 1
    MINIMUM_FLOAT: float = -MAXIMUM_FLOAT
    DEFAULT_VALUE: float = .0


    class DoubleAttributes(StrEnum):
        """
        Enum for float-specific property attributes.

        These attributes extend the default QtProperty attributes with
        options specific to floating-point property types.
        """
        RANGE = auto()
        DECIMALS = auto()
        READONLY = auto()
        SINGLE_STEP = auto()


    def __init__(self, name: str = '') -> None:
        super().__init__(name)
        self._emitter: _DoubleManagerSignalEmitter = _DoubleManagerSignalEmitter()

    @property
    def rangeChanged(self) -> SignalInstance:
        """ Signal emitted when the range of values for a property changes """
        return self._emitter.rangeChanged

    @property
    def singleStepChanged(self) -> SignalInstance:
        """ Emitted when the increment step of the value for a property changes """
        return self._emitter.singleStepChanged

    @property
    def readOnlyChanged(self) -> SignalInstance:
        """ Signal emitted when the read-only status of a property changes """
        return self._emitter.readOnlyChanged

    @property
    def decimalsChanged(self) -> SignalInstance:
        """ Signal emitted when the precision of a property changes """
        return self._emitter.decimalsChanged

    @override
    def createProperty(
        self,
        name: str,
        value: float,
    ) -> QtProperty[float]:
        """
        Create a new float property instance.

        Sets default attributes including range, single step of 0.1,
        read-only state of False, and decimal precision of 8.

        :param name: The name of the property
        :param value: The initial float value
        :return: The created property
        """
        property_ = super().createProperty(name, value)
        range_min, range_max = (self.MINIMUM_FLOAT, self.MAXIMUM_FLOAT)
        property_.setAttributeValue(self.DoubleAttributes.RANGE, (range_min, range_max))
        property_.setAttributeValue(self.DoubleAttributes.SINGLE_STEP, .1)
        property_.setAttributeValue(self.DoubleAttributes.READONLY, False)
        property_.setAttributeValue(self.DoubleAttributes.DECIMALS, 8)
        return property_

    @override
    def setValue(self, property_: QtProperty[float], value: float) -> bool:
        """
        Set the value of a float property.

        The value is clamped to the property's defined range before being set.

        :param property_: The property to set the value on
        :param value: The new float value
        :return: True if the value changed, False otherwise
        """
        if property_ not in self._managed_properties:
            return False
        range_min, range_max = property_.getAttributeValue(self.DoubleAttributes.RANGE, (.0, .0))
        value = max(range_min, min(value, range_max))
        return property_.setValue(value)

    def minimum(self, property_: QtProperty[float]) -> float:
        """
        Return the minimum value of a property's range.

        :param property_: The property to get the minimum from
        :return: The minimum value
        """
        if property_ not in self._managed_properties:
            return .0
        minimum, _ = property_.getAttributeValue(self.DoubleAttributes.RANGE, (.0, .0))
        return minimum

    def setMinimum(self, property_: QtProperty[float], minimum: float) -> None:
        """
        Set the minimum value of a property's range.

        Emits rangeChanged if the range changes. The property value
        is clamped to the new range if necessary.

        :param property_: The property to modify
        :param minimum: The new minimum value
        """
        if property_ not in self._managed_properties:
            return
        range_min, range_max = property_.getAttributeValue(
            self.DoubleAttributes.RANGE, (.0, .0)
        )
        range_min, range_max = minimum, max(minimum, range_max)
        if property_.setAttributeValue(self.DoubleAttributes.RANGE, (range_min, range_max)):
            self.rangeChanged.emit(property_, range_min, range_max)
            value = max(range_min, min(property_.value(), range_max))
            property_.setValue(value)

    def maximum(self, property_: QtProperty[float]) -> float:
        """
        Return the maximum value of a property's range.

        :param property_: The property to get the maximum from
        :return: The maximum value
        """
        if property_ not in self._managed_properties:
            return .0
        _, maximum = property_.getAttributeValue(self.DoubleAttributes.RANGE, (.0, .0))
        return maximum

    def setMaximum(self, property_: QtProperty[float], maximum: float) -> None:
        """
        Set the maximum value of a property's range.

        Emits rangeChanged if the range changes. The property value
        is clamped to the new range if necessary.

        :param property_: The property to modify
        :param maximum: The new maximum value
        """
        if property_ not in self._managed_properties:
            return
        range_min, range_max = property_.getAttributeValue(
            self.DoubleAttributes.RANGE, (.0, .0)
        )
        range_min, range_max = min(range_min, maximum), maximum
        if property_.setAttributeValue(self.DoubleAttributes.RANGE, (range_min, range_max)):
            self.rangeChanged.emit(property_, range_min, range_max)
            value = max(range_min, min(property_.value(), range_max))
            property_.setValue(value)

    def setRange(self, property_: QtProperty[float], minimum: float, maximum: float) -> None:
        """
        Set both minimum and maximum values of a property's range.

        Emits rangeChanged if the range changes. The property value
        is clamped to the new range if necessary.

        :param property_: The property to modify
        :param minimum: The new minimum value
        :param maximum: The new maximum value
        """
        if property_ not in self._managed_properties:
            return
        range_min, range_max = min(minimum, maximum), max(minimum, maximum)
        if property_.setAttributeValue(self.DoubleAttributes.RANGE, (range_min, range_max)):
            self.rangeChanged.emit(property_, range_min, range_max)
            value = max(range_min, min(property_.value(), range_max))
            property_.setValue(value)

    def singleStep(self, property_: QtProperty[float]) -> int:
        """
        Return the single step increment for a property.

        :param property_: The property to get the step from
        :return: The single step value
        """
        if property_ not in self._managed_properties:
            return 0
        step = property_.getAttributeValue(self.DoubleAttributes.SINGLE_STEP, 0)
        return step

    def setSingleStep(self, property_: QtProperty[float], step: float) -> None:
        """
        Set the single step increment for a property.

        Emits singleStepChanged if the step changes.

        :param property_: The property to modify
        :param step: The new single step value
        """
        if property_ not in self._managed_properties:
            return
        if property_.setAttributeValue(self.DoubleAttributes.SINGLE_STEP, step):
            self.singleStepChanged.emit(property_, step)

    def decimals(self, property_: QtProperty[float]) -> int:
        """
        Return the decimal precision for a property.

        :param property_: The property to get the decimals from
        :return: The number of decimal places
        """
        if property_ not in self._managed_properties:
            return 0
        return property_.getAttributeValue(self.DoubleAttributes.DECIMALS, 0)

    def setDecimals(self, property_: QtProperty[float], decimals: int) -> None:
        """
        Set the decimal precision for a property.

        Emits decimalsChanged if the precision changes.

        :param property_: The property to modify
        :param decimals: The new decimal precision (minimum 0)
        """
        decimals = max(0, decimals)
        if property_ not in self._managed_properties:
            return
        if property_.setAttributeValue(self.DoubleAttributes.DECIMALS, decimals):
            self.decimalsChanged.emit(property_, decimals)

    def isReadOnly(self, property_: QtProperty[float]) -> bool:
        """
        Check if a property is read-only.

        :param property_: The property to check
        :return: True if read-only, False otherwise
        """
        if property_ not in self._managed_properties:
            return False
        return property_.getAttributeValue(self.DoubleAttributes.READONLY, False)

    def setReadOnly(self, property_: QtProperty[float], read_only: bool) -> None:
        """
        Set the read-only state of a property.

        Emits readOnlyChanged if the state changes.

        :param property_: The property to modify
        :param read_only: The new read-only state
        """
        if property_ not in self._managed_properties:
            return
        if property_.setAttributeValue(self.DoubleAttributes.READONLY, read_only):
            self.readOnlyChanged.emit(property_, read_only)

    @override
    def valueText(self, property_: QtProperty[float]) -> str:
        """
        Return the text representation of a float value.

        The value is formatted according to the property's decimal precision.

        :param property_: The property to get the text for
        :return: The string representation of the float value
        """
        if property_ not in self._managed_properties:
            return ''
        d = property_.getAttributeValue(self.DoubleAttributes.DECIMALS, 0)
        text = f'{property_.value():.{d}f}'
        if (instance := QApplication.instance()) is not None:
            return instance.tr(text)
        else:
            return text


class _DateManagerSignalEmitter(_BaseSignalEmitter):
    """
    Internal emitter for the QtDatePropertyManager

    :ivar rangeChanged: Signal emitted when the dates range changes
    """

    rangeChanged = Signal(QtProperty, QDate, QDate)
    """ rangeChanged(property, minimum, maximum) """


# Originally sourced from .\QtProperty\qtpropertymanager.py
# noinspection PyPep8Naming
class QtDatePropertyManager(QtAbstractPropertyManager[QDate]):
    """
    Property manager for date properties.

    This class manages QDate properties with support for range constraints.
    Properties can be configured with minimum and maximum dates, and the
    manager ensures values stay within the defined range.

    :cvar MINIMUM_DATE: Minimum allowed date value
    :cvar MAXIMUM_DATE: Maximum allowed date value
    :cvar DATE_FORMAT: Format for date values
    :cvar DEFAULT_VALUE: Default value (current date) for date properties
    """
    MINIMUM_DATE: QDate = QDate(1752, 9, 14)
    MAXIMUM_DATE: QDate = QDate(7999, 12, 31)
    DATE_FORMAT = QLocale.FormatType.ShortFormat
    DEFAULT_VALUE: QDate = QDate.currentDate()


    class DateAttributes(StrEnum):
        """
        Enum for date-specific property attributes.

        These attributes extend the default QtProperty attributes with
        options specific to date property types.
        """
        RANGE = auto()


    def __init__(self, name: str = '') -> None:
        super().__init__(name)
        self._emitter: _DateManagerSignalEmitter = _DateManagerSignalEmitter()

    @property
    def rangeChanged(self) -> SignalInstance:
        """ Signal emitted when the range of values for a property changes """
        return self._emitter.rangeChanged

    @override
    def createProperty(
        self,
        name: str,
        value: QDate,
    ) -> QtProperty[QDate]:
        """
        Create a new date property instance.

        Sets default attributes including range (MINIMUM_DATE to MAXIMUM_DATE).

        :param name: The name of the property
        :param value: The initial date value
        :return: The created property
        """
        property_ = super().createProperty(name, value)
        range_min, range_max = (self.MINIMUM_DATE, self.MAXIMUM_DATE)
        property_.setAttributeValue(
            self.DateAttributes.RANGE, (range_min, range_max)
        )
        return property_

    @override
    def setValue(self, property_: QtProperty[QDate], value: QDate) -> bool:
        """
        Set the value of a date property.

        The value is clamped to the property's defined range before being set.

        :param property_: The property to set the value on
        :param value: The new date value
        :return: True if the value changed, False otherwise
        """
        if property_ not in self._managed_properties:
            return False
        range_min, range_max = property_.getAttributeValue(
            self.DateAttributes.RANGE, (QDate(), QDate())
        )
        value = max(range_min, min(value, range_max))
        return property_.setValue(value)

    def minimum(self, property_: QtProperty[QDate]) -> QDate:
        """
        Return the minimum date of a property's range.

        :param property_: The property to get the minimum from
        :return: The minimum date
        """
        if property_ not in self._managed_properties:
            return QDate()
        minimum, _ = property_.getAttributeValue(
            self.DateAttributes.RANGE,
            (QDate(), QDate())
        )
        return minimum

    def setMinimum(self, property_: QtProperty[QDate], minimum: QDate) -> None:
        """
        Set the minimum date of a property's range.

        Emits rangeChanged if the range changes. The property value
        is clamped to the new range if necessary.

        :param property_: The property to modify
        :param minimum: The new minimum date
        """
        if property_ not in self._managed_properties:
            return
        range_min, range_max = property_.getAttributeValue(
            self.DateAttributes.RANGE, (QDate(), QDate())
        )
        range_min, range_max = minimum, max(minimum, range_max)
        if property_.setAttributeValue(
            self.DateAttributes.RANGE,
            (range_min, range_max)
        ):
            self.rangeChanged.emit(property_, range_min, range_max)
            value = max(range_min, min(property_.value(), range_max))
            property_.setValue(value)

    def maximum(self, property_: QtProperty[QDate]) -> QDate:
        """
        Return the maximum date of a property's range.

        :param property_: The property to get the maximum from
        :return: The maximum date
        """
        if property_ not in self._managed_properties:
            return QDate()
        _, maximum = property_.getAttributeValue(
            self.DateAttributes.RANGE,
            (QDate(), QDate())
        )
        return maximum

    def setMaximum(self, property_: QtProperty[QDate], maximum: QDate) -> None:
        """
        Set the maximum date of a property's range.

        Emits rangeChanged if the range changes. The property value
        is clamped to the new range if necessary.

        :param property_: The property to modify
        :param maximum: The new maximum date
        """
        if property_ not in self._managed_properties:
            return
        range_min, range_max = property_.getAttributeValue(
            self.DateAttributes.RANGE, (QDate(), QDate())
        )
        range_min, range_max = min(range_min, maximum), maximum

        if property_.setAttributeValue(
            self.DateAttributes.RANGE,
            (range_min, range_max)
        ):
            self.rangeChanged.emit(property_, range_min, range_max)
            value = max(range_min, min(property_.value(), range_max))
            property_.setValue(value)

    def setRange(self, property_: QtProperty[QDate], minimum: QDate, maximum: QDate) -> None:
        """
        Set both minimum and maximum dates of a property's range.

        Emits rangeChanged if the range changes. The property value
        is clamped to the new range if necessary.

        :param property_: The property to modify
        :param minimum: The new minimum date
        :param maximum: The new maximum date
        """
        if property_ not in self._managed_properties:
            return
        range_min, range_max = min(minimum, maximum), max(minimum, maximum)
        if property_.setAttributeValue(
            self.DateAttributes.RANGE,
            (range_min, range_max)
        ):
            self.rangeChanged.emit(property_, range_min, range_max)
            value = max(range_min, min(property_.value(), range_max))
            property_.setValue(value)

    @override
    def valueText(self, property_: QtProperty[QDate]) -> str:
        """
        Return the text representation of a date value.

        The date is formatted using the system locale's short date format.

        :param property_: The property to get the text for
        :return: The string representation of the date
        """
        if property_ not in self._managed_properties:
            return ''
        value = property_.value()
        return value.toString(QLocale().dateFormat(self.DATE_FORMAT))


# Originally sourced from .\QtProperty\qtpropertymanager.py
# noinspection PyPep8Naming
class QtTimePropertyManager(QtAbstractPropertyManager[QTime]):
    """
    Property manager for time properties.

    This class manages QTime properties. Time values are formatted using
    the system locale's short time format for text representation.

    :cvar TIME_FORMAT: Format for time values
    :cvar DEFAULT_VALUE: Default value (current time) for time properties
    """
    TIME_FORMAT = QLocale.FormatType.ShortFormat
    DEFAULT_VALUE: QTime = QTime.currentTime()

    @override
    def valueText(self, property_: QtProperty[QTime]) -> str:
        if property_ not in self._managed_properties:
            return ''
        value = property_.value()
        return value.toString(QLocale().timeFormat(self.TIME_FORMAT))


# Originally sourced from .\QtProperty\qtpropertymanager.py
# noinspection PyPep8Naming
class QtDateTimePropertyManager(QtAbstractPropertyManager[QDateTime]):
    """
    Property manager for datetime properties.

    This class manages QDateTime properties. Datetime values are formatted
    using the system locale's short date and time formats for text representation.

    :cvar DATE_FORMAT: Date format type for text representation
    :cvar TIME_FORMAT: Time format type for text representation
    :cvar DEFAULT_VALUE: Default value (current datetime) for datetime properties
    """
    DATE_FORMAT = QLocale.FormatType.ShortFormat
    TIME_FORMAT = QLocale.FormatType.ShortFormat
    DEFAULT_VALUE: QDateTime = QDateTime.currentDateTime()

    @override
    def valueText(self, property_: QtProperty[QDateTime]) -> str:
        """
        Return the text representation of a datetime value.

        The datetime is formatted using the system locale's short date and
        time formats, combined into a single string.

        :param property_: The property to get the text for
        :return: The string representation of the datetime
        """
        if property_ not in self._managed_properties:
            return ''
        date_format = QLocale().dateFormat(self.DATE_FORMAT)
        time_format = QLocale().timeFormat(self.TIME_FORMAT)
        value = property_.value()
        return value.toString(f'{date_format} {time_format}')


class _StringManagerSignalEmitter(_BaseSignalEmitter):
    """
    Internal emitter for the QtStringPropertyManager

    :ivar regularExpressionChanged: Signal emitted when the regular expression changes
    :ivar echoModeChanged: Signal emitted when the echo mode changes
    :ivar readOnlyChanged: Signal emitted when read-only state changes
    """

    regularExpressionChanged = Signal(QtProperty, QRegularExpression)
    """ rangeChanged(property, regular_expression) """
    echoModeChanged = Signal(QtProperty, int)
    """ rangeChanged(property, echo_mode) """
    readOnlyChanged = Signal(QtProperty, bool)
    """ rangeChanged(property, status) """


# Originally sourced from .\QtProperty\qtpropertymanager.py
# noinspection PyPep8Naming
class QtStringPropertyManager(QtAbstractPropertyManager[str]):
    """
    Property manager for string properties.

    This class manages string properties with support for regular expression
    validation, echo mode (for password fields), and read-only state. Properties
    can be configured with validation patterns and display modes.

    :cvar DEFAULT_VALUE: Default value for string properties
    """
    DEFAULT_VALUE: str = ''


    class StringAttributes(StrEnum):
        """
        Enum for string-specific property attributes.

        These attributes extend the default QtProperty attributes with
        options specific to string property types.
        """
        REGULAR_EXPRESSION = auto()
        ECHO_MODE = auto()
        READONLY = auto()

    def __init__(self, name: str = '') -> None:
        super().__init__(name)
        self._emitter: _StringManagerSignalEmitter = _StringManagerSignalEmitter()

    @property
    def regularExpressionChanged(self) -> SignalInstance:
        """ Emitted when the validation regular expression of a property changes """
        return self._emitter.regularExpressionChanged

    @property
    def echoModeChanged(self) -> SignalInstance:
        """ Signal emitted when the echo mode of a property changes """
        return self._emitter.echoModeChanged

    @property
    def readOnlyChanged(self) -> SignalInstance:
        """ Emitted when the read-only status of a property changes """
        return self._emitter.readOnlyChanged

    @override
    def createProperty(
        self,
        name: str,
        value: str,
    ) -> QtProperty[str]:
        """
        Create a new string property instance.

        Sets default attributes including empty regular expression (no validation),
        normal echo mode, and read-only state of False.

        :param name: The name of the property
        :param value: The initial string value
        :return: The created property
        """
        property_ = super().createProperty(name, value)
        property_.setAttributeValue(
            self.StringAttributes.REGULAR_EXPRESSION,
            QRegularExpression()
        )
        property_.setAttributeValue(
            self.StringAttributes.ECHO_MODE,
            QLineEdit.EchoMode.Normal
        )
        property_.setAttributeValue(self.StringAttributes.READONLY, False)
        return property_

    @override
    def setValue(self, property_: QtProperty[str], value: str) -> bool:
        """
        Set the value of a string property.

        If a regular expression is set, the value is validated against it
        before being accepted.

        :param property_: The property to set the value on
        :param value: The new string value
        :return: True if the value changed, False if validation fails
        """
        if property_ not in self._managed_properties:
            return False
        regular_expression: QRegularExpression = property_.getAttributeValue(
            self.StringAttributes.REGULAR_EXPRESSION,
            QRegularExpression()
        )
        if (regular_expression.isValid()
            and not regular_expression.match(value).hasMatch()):
            return False
        return property_.setValue(value)

    def regularExpression(self, property_: QtProperty[str]) -> QRegularExpression:
        """
        Return the regular expression used for validation.

        :param property_: The property to get the regular expression from
        :return: The validation regular expression
        """
        if property_ not in self._managed_properties:
            return QRegularExpression()
        return property_.getAttributeValue(
            self.StringAttributes.REGULAR_EXPRESSION,
            QRegularExpression()
        )

    def setRegularExpression(
        self,
        property_: QtProperty[str],
        regular_expression: QRegularExpression
    ) -> None:
        """
        Set the regular expression for validation.

        Emits regularExpressionChanged if the expression changes.

        :param property_: The property to modify
        :param regular_expression: The new validation regular expression
        """
        if property_ not in self._managed_properties:
            return
        if property_.setAttributeValue(
            self.StringAttributes.REGULAR_EXPRESSION,
            regular_expression
        ):
            self.regularExpressionChanged.emit(property_, regular_expression)

    def echoMode(self, property_: QtProperty[str]) -> QLineEdit.EchoMode:
        """
        Return the echo mode for a property.

        :param property_: The property to get the echo mode from
        :return: The echo mode (e.g., Normal, Password, NoEcho)
        """
        if property_ not in self._managed_properties:
            return QLineEdit.EchoMode.Normal
        return property_.getAttributeValue(
            self.StringAttributes.ECHO_MODE,
            QLineEdit.EchoMode.Normal
        )

    def setEchoMode(self, property_: QtProperty[str], echo_mode: QLineEdit.EchoMode) -> None:
        """
        Set the echo mode for a property.

        Emits echoModeChanged if the mode changes. Useful for
        password fields or hidden input.

        :param property_: The property to modify
        :param echo_mode: The new echo mode
        """
        if property_ not in self._managed_properties:
            return
        if property_.setAttributeValue(self.StringAttributes.ECHO_MODE, echo_mode):
            self.echoModeChanged.emit(property_, echo_mode)

    def isReadOnly(self, property_: QtProperty[str]) -> bool:
        """
        Check if a property is read-only.

        :param property_: The property to check
        :return: True if read-only, False otherwise
        """
        if property_ not in self._managed_properties:
            return False
        return property_.getAttributeValue(self.StringAttributes.READONLY, False)

    def setReadOnly(self, property_: QtProperty[str], read_only: bool) -> None:
        """
        Set the read-only state of a property.

        Emits readOnlyChanged if the state changes.

        :param property_: The property to modify
        :param read_only: The new read-only state
        """
        if property_ not in self._managed_properties:
            return
        if property_.setAttributeValue(self.StringAttributes.READONLY, read_only):
            self.readOnlyChanged.emit(property_, read_only)

    @override
    def valueText(self, property_: QtProperty[str]) -> str:
        """
        Return the text representation of a string value.

        :param property_: The property to get the text for
        :return: The string value
        """
        if property_ not in self._managed_properties:
            return ''
        return property_.value()

    @override
    def displayText(self, property_: QtProperty[str]) -> str:
        """
        Return the display text for a string value.

        The text is formatted according to the property's echo mode,
        which may mask characters for password fields.

        :param property_: The property to get the display text for
        :return: The formatted display text
        """
        if property_ not in self._managed_properties:
            return ''
        line_edit = QLineEdit()
        line_edit.setEchoMode(property_.getAttributeValue(
            self.StringAttributes.ECHO_MODE,
            QLineEdit.EchoMode.Normal)
        )
        line_edit.setText(property_.value())
        return line_edit.displayText()


# Originally sourced from .\QtProperty\qtpropertymanager.py
# noinspection PyPep8Naming
class QtKeySequencePropertyManager(QtAbstractPropertyManager[QKeySequence]):
    """
    Property manager for key sequence properties.

    This class manages QKeySequence properties for keyboard shortcuts.
    Key sequences are formatted using native text representation for
    text display.

    :cvar SEQUENCE_FORMAT: The formatting of the key sequence text representation
    :cvar DEFAULT_VALUE: Default value (empty key sequence) for key sequence properties
    """
    SEQUENCE_FORMAT = QKeySequence.SequenceFormat.NativeText
    DEFAULT_VALUE: QKeySequence = QKeySequence()


    @override
    def valueText(self, property_: QtProperty[QKeySequence]) -> str:
        """
        Return the text representation of a key sequence.

        The key sequence is formatted using native text representation
        (e.g., 'Ctrl+S' on Windows/Linux, 'Cmd+S' on macOS).

        :param property_: The property to get the text for
        :return: The string representation of the key sequence
        """
        if property_ not in self._managed_properties:
            return ''
        key_sequence: QKeySequence = property_.value()
        return key_sequence.toString(self.SEQUENCE_FORMAT)


# Originally sourced from .\QtProperty\qtpropertymanager.py
# noinspection PyPep8Naming
class QtPointPropertyManager(QtAbstractPropertyManager[QPoint]):
    """
    Property manager for point (QPoint) properties.

    This class manages QPoint properties with X and Y coordinates as sub-properties.
    Changes to the point or its coordinates are synchronized between the parent
    property and its sub-properties.

    :cvar DEFAULT_VALUE: Default value (0, 0) for point properties
    """
    DEFAULT_VALUE: QPoint = QPoint(0, 0)


    def __init__(self, name: str='') -> None:
        """
        Initialize the point property manager.

        Creates an internal integer property manager for handling X and Y
        coordinate sub-properties.

        :param name: The name of the manager
        """
        super().__init__(name)
        self._int_sub_manager = QtIntPropertyManager()
        self._int_sub_manager.valueChanged.connect(self.subPropertyChanged)
        self._property_to_xy: dict[
            QtProperty[QPoint],
            tuple[QtProperty[int], QtProperty[int]]
        ] = dict()
        self._sub_property_to_parent: dict[
            QtProperty[int],
            tuple[QtProperty[QPoint], int]
        ] = dict()
        self._updating_sub_properties: bool = False

    @override
    def createProperty(
        self,
        name: str,
        value: QPoint,
    ) -> QtProperty[QPoint]:
        """
        Create a new point property instance.

        Creates X and Y integer sub-properties for the point coordinates
        and establishes the relationship between parent and sub-properties.

        :param name: The name of the property
        :param value: The initial point value
        :return: The created property
        """
        x_tag, y_tag = 'X', 'Y'
        app: QApplication = QApplication.instance()  # type: ignore
        if app is not None:
            x_tag = app.tr(x_tag)
            y_tag = app.tr(y_tag)
        property_ = super().createProperty(name, value)
        x_property = self._int_sub_manager.addProperty(x_tag, value.x())
        property_.addSubProperty(x_property)
        y_property = self._int_sub_manager.addProperty(y_tag, value.y())
        property_.addSubProperty(y_property)
        self._property_to_xy[property_] = (x_property, y_property)
        self._sub_property_to_parent[x_property] = (property_, 0)
        self._sub_property_to_parent[y_property] = (property_, 1)
        return property_

    def subIntPropertyManager(self) -> QtIntPropertyManager:
        """
        Return the internal integer property manager.

        This manager handles the X and Y coordinate sub-properties.

        :return: The integer sub-property manager
        """
        return self._int_sub_manager

    @override
    def setValue(self, property_: QtProperty[QPoint], value: QPoint) -> bool:
        """
        Set the value of a point property.

        Updates both the parent property and its X/Y sub-properties.
        Prevents infinite recursion during sub-property updates.

        :param property_: The property to set the value on
        :param value: The new point value
        :return: True if the value is changed, False otherwise
        """
        if property_ not in self._managed_properties:
            return False
        changed = property_.setValue(value)
        if changed:
            x_property, y_property = self._property_to_xy.get(
                property_,
                (None, None)
            )
            if x_property is not None and y_property is not None:
                self._updating_sub_properties = True
                x_property.setValue(value.x())
                y_property.setValue(value.y())
                self._updating_sub_properties = False
        return changed

    @override
    def valueText(self, property_: QtProperty[QPoint]) -> str:
        """
        Return the text representation of a point value.

        Format: '(x, y)'

        :param property_: The property to get the text for
        :return: The string representation of the point
        """
        if property_ not in self._managed_properties:
            return ''
        point: QPoint = property_.value()
        text = f"({point.x()}, {point.y()})"
        app: QApplication = QApplication.instance()  # type: ignore
        if app is not None:
            return app.tr(text)
        return text

    def subPropertyChanged(self, property_: QtProperty[int], value: int) -> None:
        """
        Handle changes to X or Y coordinate sub-properties.

        Updates the parent point property when a coordinate changes.
        Only processes changes if not already updating sub-properties.

        :param property_: The coordinate sub-property that changed
        :param value: The new coordinate value
        """
        if not self._updating_sub_properties and property_ in self._sub_property_to_parent:
            parent_prop, coord = self._sub_property_to_parent[property_]
            if parent_prop is not None:
                p: QPoint = parent_prop.value()
                point_xy = [p.x(), p.y()]
                point_xy[coord] = value
                parent_prop.setValue(QPoint(*point_xy))


class _PointFManagerSignalEmitter(_BaseSignalEmitter):
    """
    Internal emitter for the QtPointFPropertyManager

    :ivar decimalsChanged: Signal emitted when decimal precision changes
    """

    decimalsChanged = Signal(QtProperty, int)
    """ decimalsChanged(property, precision) """


# Originally sourced from .\QtProperty\qtpropertymanager.py
# noinspection PyPep8Naming
class QtPointFPropertyManager(QtAbstractPropertyManager[QPointF]):
    """
    Property manager for floating-point point (QPointF) properties.

    This class manages QPointF properties with X and Y coordinates as sub-properties.
    Changes to the point or its coordinates are synchronized between the parent
    property and its sub-properties. Supports decimal precision configuration.

    :cvar DEFAULT_VALUE: Default value (0.0, 0.0) for floating-point point properties
    """
    DEFAULT_VALUE: QPointF = QPointF(.0, .0)


    class PointFAttributes(StrEnum):
        """
        Enum for floating-point point-specific property attributes.

        These attributes extend the default QtProperty attributes with
        options specific to floating-point point property types.
        """
        DECIMALS = auto()


    def __init__(self, name: str='') -> None:
        """
        Initialize the floating-point point property manager.

        Creates an internal double property manager for handling X and Y
        coordinate sub-properties.

        :param name: The name of the manager
        """
        super().__init__(name)
        self._emitter: _PointFManagerSignalEmitter = _PointFManagerSignalEmitter()
        self._double_sub_manager = QtDoublePropertyManager()
        self._double_sub_manager.valueChanged.connect(self.subPropertyChanged)
        self._property_to_xy: dict[
            QtProperty[QPointF],
            tuple[QtProperty[float], QtProperty[float]]
        ] = dict()
        self._sub_property_to_parent: dict[
            QtProperty[float],
            tuple[QtProperty[QPointF], int]
        ] = dict()
        self._updating_sub_properties: bool = False

    @property
    def decimalsChanged(self) -> SignalInstance:
        """ Signal emitted when the precision of a property changes """
        return self._emitter.decimalsChanged

    @override
    def createProperty(
        self,
        name: str,
        value: QPointF,
    ) -> QtProperty[QPointF]:
        """
        Create a new floating-point point property instance.

        Creates X and Y double sub-properties for the point coordinates
        and establishes the relationship between parent and sub-properties.
        Sets default decimal precision to 2.

        :param name: The name of the property
        :param value: The initial point value
        :return: The created property
        """
        property_ = super().createProperty(name, value)
        property_.setAttributeValue(self.PointFAttributes.DECIMALS, 2)
        x_tag, y_tag = 'X', 'Y'
        app: QApplication = QApplication.instance()  # type: ignore
        if app is not None:
            x_tag = app.tr(x_tag)
            y_tag = app.tr(y_tag)
        x_property = self._double_sub_manager.addProperty(x_tag, value.x())
        self._double_sub_manager.setDecimals(x_property, 2)
        property_.addSubProperty(x_property)
        y_property = self._double_sub_manager.addProperty(y_tag, value.y())
        self._double_sub_manager.setDecimals(y_property, 2)
        property_.addSubProperty(y_property)
        self._property_to_xy[property_] = (x_property, y_property)
        self._sub_property_to_parent[x_property] = (property_, 0)
        self._sub_property_to_parent[y_property] = (property_, 1)
        return property_

    def subPropertyManager(self) -> QtDoublePropertyManager:
        """
        Return the internal double property manager.

        This manager handles the X and Y coordinate sub-properties.

        :return: The double sub-property manager
        """
        return self._double_sub_manager

    @override
    def setValue(self, property_: QtProperty[QPointF], value: QPointF) -> bool:
        """
        Set the value of a floating-point point property.

        Updates both the parent property and its X/Y sub-properties.
        Prevents infinite recursion during sub-property updates.

        :param property_: The property to set the value on
        :param value: The new point value
        :return: True if the value changed, False otherwise
        """
        if property_ not in self._managed_properties:
            return False
        changed = property_.setValue(value)
        if changed:
            x_property, y_property = self._property_to_xy.get(
                property_,
                (None, None)
            )
            if x_property is not None and y_property is not None:
                self._updating_sub_properties = True
                x_property.setValue(value.x())
                y_property.setValue(value.y())
                self._updating_sub_properties = False
        return changed

    @override
    def valueText(self, property_: QtProperty[QPointF]) -> str:
        """
        Return the text representation of a floating-point point value.

        Format: '(x, y)' with configurable decimal precision.

        :param property_: The property to get the text for
        :return: The string representation of the point
        """
        if property_ not in self._managed_properties:
            return ''
        point: QPointF = property_.value()
        d = property_.getAttributeValue(self.PointFAttributes.DECIMALS, 0)
        text = f"({point.x():.{d}f}, {point.y():.{d}f})"
        app: QApplication = QApplication.instance()  # type: ignore
        if app is not None:
            return app.tr(text)
        return text

    def decimals(self, property_: QtProperty[QPointF]) -> int:
        """
        Return the decimal precision for a property.

        :param property_: The property to get the decimals from
        :return: The number of decimal places
        """
        if property_ not in self._managed_properties:
            return 0
        return property_.getAttributeValue(self.PointFAttributes.DECIMALS, 0)

    def setDecimals(self, property_: QtProperty[QPointF], decimals: int) -> None:
        """
        Set the decimal precision for a property.

        Updates both X and Y sub-properties with the new precision.
        Emits decimalsChanged if the precision changes.

        :param property_: The property to modify
        :param decimals: The new decimal precision (minimum 0)
        """
        decimals = max(0, decimals)
        if property_ not in self._managed_properties:
            return
        if property_.setAttributeValue(self.PointFAttributes.DECIMALS, decimals):
            x_prop, y_prop = self._property_to_xy[property_]
            self._double_sub_manager.setDecimals(x_prop, decimals)
            self._double_sub_manager.setDecimals(y_prop, decimals)
            self.decimalsChanged.emit(property_, decimals)

    def subPropertyChanged(self, property_: QtProperty[float], value: float) -> None:
        """
        Handle changes to X or Y coordinate sub-properties.

        Updates the parent point property when a coordinate changes.
        Only processes changes if not already updating sub-properties.

        :param property_: The coordinate sub-property that changed
        :param value: The new coordinate value
        """
        if not self._updating_sub_properties and property_ in self._sub_property_to_parent:
            parent_prop, coord = self._sub_property_to_parent[property_]
            if parent_prop is not None:
                p: QPointF = parent_prop.value()
                point_xy = [p.x(), p.y()]
                point_xy[coord] = value
                parent_prop.setValue(QPointF(*point_xy))


class _SizeManagerSignalEmitter(_BaseSignalEmitter):
    """
    Internal emitter for the QtSizePropertyManager

    :ivar rangeChanged: Signal emitted when the size range changes
    """

    rangeChanged = Signal(QtProperty, QSize, QSize)
    """ rangeChanged(property, minimum, maximum) """


# Originally sourced from .\QtProperty\qtpropertymanager.py
# noinspection PyPep8Naming
class QtSizePropertyManager(QtAbstractPropertyManager[QSize]):
    """
    Property manager for size (QSize) properties.

    This class manages QSize properties with width and height as sub-properties.
    Changes to the size or its dimensions are synchronized between the parent
    property and its sub-properties. Supports range constraints for minimum
    and maximum size values.

    :cvar MAXIMUM_VALUE: Maximum allowed dimension value
    :cvar DEFAULT_VALUE: Default value (0, 0) for size properties
    """
    MAXIMUM_VALUE: int = 2 ** 31 - 1
    DEFAULT_VALUE: QSize = QSize(0, 0)


    class SizeAttributes(StrEnum):
        """
        Enum for size-specific property attributes.

        These attributes extend the default QtProperty attributes with
        options specific to size property types.
        """
        RANGE = auto()


    def __init__(self, name: str='') -> None:
        """
        Initialize the size property manager.

        Creates an internal integer property manager for handling width and
        height sub-properties.

        :param name: The name of the manager
        """
        super().__init__(name)
        self._emitter: _SizeManagerSignalEmitter = _SizeManagerSignalEmitter()
        self._int_sub_manager = QtIntPropertyManager()
        self._int_sub_manager.valueChanged.connect(self.subPropertyChanged)
        self._property_to_wh: dict[
            QtProperty[QSize],
            tuple[QtProperty[int], QtProperty[int]]
        ] = dict()
        self._sub_property_to_parent: dict[
            QtProperty[int],
            tuple[QtProperty[QSize], int]
        ] = dict()
        self._updating_sub_properties: bool = False

    @property
    def rangeChanged(self) -> SignalInstance:
        """ Signal emitted when the range of values for a property changes """
        return self._emitter.rangeChanged

    @override
    def createProperty(
        self,
        name: str,
        value: QSize,
    ) -> QtProperty[QSize]:
        """
        Create a new size property instance.

        Creates width and height integer sub-properties for the size dimensions
        and establishes the relationship between parent and sub-properties.
        Sets default range from (0, 0) to (MAXIMUM_VALUE, MAXIMUM_VALUE).

        :param name: The name of the property
        :param value: The initial size value
        :return: The created property
        """
        property_ = super().createProperty(name, value)
        property_.setAttributeValue(
            self.SizeAttributes.RANGE,
            (QSize(0, 0), QSize(self.MAXIMUM_VALUE, self.MAXIMUM_VALUE))
        )
        width_tag, height_tag = 'Width', 'Height'
        app: QApplication = QApplication.instance()  # type: ignore
        if app is not None:
            width_tag = app.tr(width_tag)
            height_tag = app.tr(height_tag)
        w_property = self._int_sub_manager.addProperty(width_tag, value.width())
        self._int_sub_manager.setRange(w_property, 0, self.MAXIMUM_VALUE)
        property_.addSubProperty(w_property)
        h_property = self._int_sub_manager.addProperty(height_tag, value.height())
        self._int_sub_manager.setRange(h_property, 0, self.MAXIMUM_VALUE)
        property_.addSubProperty(h_property)
        self._property_to_wh[property_] = (w_property, h_property)
        self._sub_property_to_parent[w_property] = (property_, 0)
        self._sub_property_to_parent[h_property] = (property_, 1)
        return property_

    def subPropertyManager(self) -> QtIntPropertyManager:
        """
        Return the internal integer property manager.

        This manager handles the width and height sub-properties.

        :return: The integer sub-property manager
        """
        return self._int_sub_manager

    @override
    def setValue(self, property_: QtProperty[QSize], value: QSize) -> bool:
        """
        Set the value of a size property.

        The value is clamped to the property's defined range before being set.
        Updates both the parent property and its width/height sub-properties.
        Prevents infinite recursion during sub-property updates.

        :param property_: The property to set the value on
        :param value: The new size value
        :return: True if the value changed, False otherwise
        """
        if property_ not in self._managed_properties:
            return False
        size_range: tuple[QSize, QSize] = property_.getAttributeValue(
            self.SizeAttributes.RANGE,
            (QSize(0, 0), QSize(self.MAXIMUM_VALUE, self.MAXIMUM_VALUE))
        )
        s_min, s_max = size_range
        actual_value = QSize(
            max(s_min.width(), min(value.width(), s_max.width())),
            max(s_min.height(), min(value.height(), s_max.height()))
        )
        changed = property_.setValue(actual_value)
        if changed:
            w_property, h_property = self._property_to_wh.get(
                property_,
                (None, None)
            )
            if w_property is not None and h_property is not None:
                self._updating_sub_properties = True
                self._int_sub_manager.setValue(w_property, actual_value.width())
                self._int_sub_manager.setValue(h_property, actual_value.height())
                self._updating_sub_properties = False
        return changed

    @override
    def valueText(self, property_: QtProperty[QSize]) -> str:
        """
        Return the text representation of a size value.

        Format: 'width x height'

        :param property_: The property to get the text for
        :return: The string representation of the size
        """
        if property_ not in self._managed_properties:
            return ''
        size: QSize = property_.value()
        text = f"{size.width()} x {size.height()}"
        app: QApplication = QApplication.instance()  # type: ignore
        if app is not None:
            return app.tr(text)
        return text

    def minimum(self, property_: QtProperty[QSize]) -> QSize:
        """
        Return the minimum size of a property's range.

        :param property_: The property to get the minimum from
        :return: The minimum size
        """
        if property_ not in self._managed_properties:
            return QSize(0, 0)
        minimum, _ = property_.getAttributeValue(
            self.SizeAttributes.RANGE,
            (QSize(0, 0), QSize(0, 0))
        )
        return minimum

    def setMinimum(self, property_: QtProperty[QSize], minimum: QSize) -> None:
        """
        Set the minimum size of a property's range.

        Emits rangeChanged if the range changes. Updates sub-property
        ranges and clamps the current value if necessary.

        :param property_: The property to modify
        :param minimum: The new minimum size
        """
        if property_ not in self._managed_properties:
            return
        size_range: tuple[QSize, QSize] = property_.getAttributeValue(
            self.SizeAttributes.RANGE,
            (QSize(0, 0), QSize(0, 0))
        )
        range_min, range_max = size_range
        w1, h1 = range_max.width(), range_max.height()
        range_min = QSize(min(w1, minimum.width()), min(h1, minimum.height()))
        range_max = QSize(max(w1, minimum.width()), max(h1, minimum.height()))
        if property_.setAttributeValue(
            self.SizeAttributes.RANGE,
            (range_min, range_max)
        ):
            self.rangeChanged.emit(property_, range_min, range_max)
            value: QSize = property_.value()
            actual_value = QSize(
                max(range_min.width(), min(value.width(), range_max.width())),
                max(range_min.height(), min(value.height(), range_max.height()))
            )
            property_.setValue(actual_value)
            self._updating_sub_properties = True
            w_property, h_property = self._property_to_wh.get(property_, (None, None))
            if w_property is not None and h_property is not None:
                self._int_sub_manager.setRange(w_property, range_min.width(), range_max.width())
                self._int_sub_manager.setRange(h_property, range_min.height(), range_max.height())
            self._updating_sub_properties = False

    def maximum(self, property_: QtProperty[QSize]) -> QSize:
        """
        Return the maximum size of a property's range.

        :param property_: The property to get the maximum from
        :return: The maximum size
        """
        if property_ not in self._managed_properties:
            return QSize(0, 0)
        _, maximum = property_.getAttributeValue(
            self.SizeAttributes.RANGE,
            (QSize(0, 0), QSize(0, 0))
        )
        return maximum

    def setMaximum(self, property_: QtProperty[QSize], maximum: QSize) -> None:
        """
        Set the maximum size of a property's range.

        Emits rangeChanged if the range changes. Updates sub-property
        ranges and clamps the current value if necessary.

        :param property_: The property to modify
        :param maximum: The new maximum size
        """
        if property_ not in self._managed_properties:
            return
        size_range: tuple[QSize, QSize] = property_.getAttributeValue(
            self.SizeAttributes.RANGE,
            (QSize(0, 0), QSize(0, 0))
        )
        range_min, range_max = size_range
        w0, h0 = range_min.width(), range_min.height()
        range_min = QSize(min(w0, maximum.width()), min(h0, maximum.height()))
        range_max = QSize(max(w0, maximum.width()), max(h0, maximum.height()))
        if property_.setAttributeValue(
            self.SizeAttributes.RANGE,
            (range_min, range_max)
        ):
            self.rangeChanged.emit(property_, range_min, range_max)
            value: QSize = property_.value()
            actual_value = QSize(
                max(range_min.width(), min(value.width(), range_max.width())),
                max(range_min.height(), min(value.height(), range_max.height()))
            )
            property_.setValue(actual_value)
            self._updating_sub_properties = True
            w_property, h_property = self._property_to_wh.get(
                property_,
                (None, None)
            )
            if w_property is not None and h_property is not None:
                self._int_sub_manager.setRange(w_property, range_min.width(), range_max.width())
                self._int_sub_manager.setRange(h_property, range_min.height(), range_max.height())
            self._updating_sub_properties = False

    def setRange(self, property_: QtProperty[QSize], minimum: QSize, maximum: QSize) -> None:
        """
        Set both minimum and maximum sizes of a property's range.

        Emits rangeChanged if the range changes. Updates sub-property
        ranges and clamps the current value if necessary.

        :param property_: The property to modify
        :param minimum: The new minimum size
        :param maximum: The new maximum size
        """
        if property_ not in self._managed_properties:
            return
        w0, h0 = minimum.width(), minimum.height()
        w1, h1 = maximum.width(), maximum.height()
        range_min = QSize(min(w0, w1), min(h0, h1))
        range_max = QSize(max(w0, w1), max(h0, h1))
        if property_.setAttributeValue(
            self.SizeAttributes.RANGE,
            (range_min, range_max)
        ):
            self.rangeChanged.emit(property_, range_min, range_max)
            value: QSize = property_.value()
            actual_value = QSize(
                max(w0, min(value.width(), w1)),
                max(h0, min(value.height(), h1))
            )
            property_.setValue(actual_value)
            self._updating_sub_properties = True
            w_property, h_property = self._property_to_wh.get(
                property_,
                (None, None)
            )
            if w_property is not None and h_property is not None:
                self._int_sub_manager.setRange(w_property, range_min.width(), range_max.width())
                self._int_sub_manager.setRange(h_property, range_min.height(), range_max.height())
            self._updating_sub_properties = False

    def subPropertyChanged(self, property_: QtProperty[int], value: int) -> None:
        """
        Handle changes to width or height sub-properties.

        Updates the parent size property when a dimension changes.
        Only processes changes if not already updating sub-properties.

        :param property_: The dimension sub-property that changed
        :param value: The new dimension value
        """
        if not self._updating_sub_properties and property_ in self._sub_property_to_parent:
            parent_prop, idx = self._sub_property_to_parent[property_]
            s = parent_prop.value()
            size_wh = [s.width(), s.height()]
            size_wh[idx] = value
            parent_prop.setValue(QSize(*size_wh))


class _SizeFManagerSignalEmitter(_BaseSignalEmitter):
    """
    Internal emitter for the QtSizeFPropertyManager

    :ivar rangeChanged: Signal emitted when the size range changes
    :ivar decimalsChanged: Signal emitted when decimal precision changes
    """

    rangeChanged = Signal(QtProperty, QSizeF, QSizeF)
    """ rangeChanged(property, minimum, maximum) """
    decimalsChanged = Signal(QtProperty, int)
    """ decimalsChanged(property, precision) """


# Originally sourced from .\QtProperty\qtpropertymanager.py
# noinspection PyPep8Naming
class QtSizeFPropertyManager(QtAbstractPropertyManager[QSizeF]):
    """
    Property manager for floating-point size (QSizeF) properties.

    This class manages QSizeF properties with width and height as sub-properties.
    Changes to the size or its dimensions are synchronized between the parent
    property and its sub-properties. Supports range constraints and decimal
    precision configuration.

    :cvar MAXIMUM_VALUE: Maximum allowed dimension value
    :cvar DEFAULT_VALUE: Default value (0.0, 0.0) for floating-point size properties
    """
    MAXIMUM_VALUE: float = 2.0 ** 31 - 1
    DEFAULT_VALUE: QSizeF = QSizeF(0, 0)


    class SizeFAttributes(StrEnum):
        """
        Enum for floating-point size-specific property attributes.

        These attributes extend the default QtProperty attributes with
        options specific to floating-point size property types.
        """
        RANGE = auto()
        DECIMALS = auto()


    def __init__(self, name: str='') -> None:
        """
        Initialize the floating-point size property manager.

        Creates an internal double property manager for handling width and
        height sub-properties.

        :param name: The name of the manager
        """
        super().__init__(name)
        self._emitter: _SizeFManagerSignalEmitter = _SizeFManagerSignalEmitter()
        self._double_sub_manager = QtDoublePropertyManager()
        self._double_sub_manager.valueChanged.connect(self.subPropertyChanged)
        self._property_to_wh: dict[
            QtProperty[QSizeF],
            tuple[QtProperty[float], QtProperty[float]]
        ] = dict()
        self._sub_property_to_parent: dict[
            QtProperty[float],
            tuple[QtProperty[QSizeF], int]
        ] = dict()
        self._updating_sub_properties: bool = False

    @property
    def rangeChanged(self) -> SignalInstance:
        """ Signal emitted when the range of values for a property changes """
        return self._emitter.rangeChanged

    @property
    def decimalsChanged(self) -> SignalInstance:
        """ Signal emitted when the precision of a property changes """
        return self._emitter.decimalsChanged

    @override
    def createProperty(
        self,
        name: str,
        value: QSizeF,
    ) -> QtProperty[QSizeF]:
        """
        Create a new floating-point size property instance.

        Creates width and height double sub-properties for the size dimensions
        and establishes the relationship between parent and sub-properties.
        Sets default range and decimal precision (4 digits).

        :param name: The name of the property
        :param value: The initial size value
        :return: The created property
        """
        property_ = super().createProperty(name, value)
        property_.setAttributeValue(
            self.SizeFAttributes.RANGE,
            (QSizeF(.0, .0), QSizeF(self.MAXIMUM_VALUE, self.MAXIMUM_VALUE))
        )
        property_.setAttributeValue(self.SizeFAttributes.DECIMALS, 4)
        width_tag, height_tag = 'Width', 'Height'
        app: QApplication = QApplication.instance()  # type: ignore
        if app is not None:
            width_tag, height_tag = app.tr(width_tag), app.tr(height_tag)
        w_property = self._double_sub_manager.addProperty(width_tag, value.width())
        self._double_sub_manager.setRange(w_property, .0, self.MAXIMUM_VALUE)
        self._double_sub_manager.setDecimals(w_property, 4)
        property_.addSubProperty(w_property)
        h_property = self._double_sub_manager.addProperty(height_tag, value.height())
        self._double_sub_manager.setRange(h_property, .0, self.MAXIMUM_VALUE)
        self._double_sub_manager.setDecimals(h_property, 4)
        property_.addSubProperty(h_property)
        self._property_to_wh[property_] = (w_property, h_property)
        self._sub_property_to_parent[w_property] = (property_, 0)
        self._sub_property_to_parent[h_property] = (property_, 1)
        return property_

    def subPropertyManager(self) -> QtDoublePropertyManager:
        """
        Return the internal double property manager.

        This manager handles the width and height sub-properties.

        :return: The double sub-property manager
        """
        return self._double_sub_manager

    @override
    def setValue(self, property_: QtProperty[QSizeF], value: QSizeF) -> bool:
        """
        Set the value of a floating-point size property.

        The value is clamped to the property's defined range before being set.
        Updates both the parent property and its width/height sub-properties.
        Prevents infinite recursion during sub-property updates.

        :param property_: The property to set the value on
        :param value: The new size value
        :return: True if the value changed, False otherwise
        """
        if property_ not in self._managed_properties:
            return False
        size_range: tuple[QSizeF, QSizeF] = property_.getAttributeValue(
            self.SizeFAttributes.RANGE,
            (QSizeF(0, 0), QSizeF(self.MAXIMUM_VALUE, self.MAXIMUM_VALUE))
        )
        s_min, s_max = size_range
        actual_value = QSizeF(
            max(s_min.width(), min(value.width(), s_max.width())),
            max(s_min.height(), min(value.height(), s_max.height()))
        )
        changed = property_.setValue(actual_value)
        if changed:
            w_property, h_property = self._property_to_wh.get(property_, (None, None))
            if w_property is not None and h_property is not None:
                self._updating_sub_properties = True
                self._double_sub_manager.setValue(w_property, actual_value.width())
                self._double_sub_manager.setValue(h_property, actual_value.height())
                self._updating_sub_properties = False
        return changed

    @override
    def valueText(self, property_: QtProperty[QSizeF]) -> str:
        """
        Return the text representation of a floating-point size value.

        Format: 'width x height' with configurable decimal precision.

        :param property_: The property to get the text for
        :return: The string representation of the size
        """
        if property_ not in self._managed_properties:
            return ''
        size: QSizeF = property_.value()
        d = property_.getAttributeValue(self.SizeFAttributes.DECIMALS, 2)
        text = f"{size.width():.{d}f} x {size.height():.{d}f}"
        app: QApplication = QApplication.instance()  # type: ignore
        if app is not None:
            return app.tr(text)
        return text

    def decimals(self, property_: QtProperty[QSizeF]) -> int:
        """
        Return the decimal precision for a property.

        :param property_: The property to get the decimals from
        :return: The number of decimal places
        """
        if property_ not in self._managed_properties:
            return 0
        return property_.getAttributeValue(self.SizeFAttributes.DECIMALS, 0)

    def setDecimals(self, property_: QtProperty[QSizeF], decimals: int) -> None:
        """
        Set the decimal precision for a property.

        Updates both width and height sub-properties with the new precision.
        Emits decimalsChanged if the precision changes.

        :param property_: The property to modify
        :param decimals: The new decimal precision (minimum 0)
        """
        decimals = max(0, decimals)
        if property_ not in self._managed_properties:
            return
        if property_.setAttributeValue(self.SizeFAttributes.DECIMALS, decimals):
            x_prop, y_prop = self._property_to_wh[property_]
            self._double_sub_manager.setDecimals(x_prop, decimals)
            self._double_sub_manager.setDecimals(y_prop, decimals)
            self.decimalsChanged.emit(property_, decimals)

    def minimum(self, property_: QtProperty[QSizeF]) -> QSizeF:
        """
        Return the minimum size of a property's range.

        :param property_: The property to get the minimum from
        :return: The minimum size
        """
        if property_ not in self._managed_properties:
            return QSizeF(.0, .0)
        minimum, _ = property_.getAttributeValue(
            self.SizeFAttributes.RANGE,
            (QSizeF(0, 0), QSizeF(0, 0))
        )
        return minimum

    def setMinimum(self, property_: QtProperty[QSizeF], minimum: QSizeF) -> None:
        """
        Set the minimum size of a property's range.

        Emits rangeChanged if the range changes. Updates sub-property
        ranges accordingly.

        :param property_: The property to modify
        :param minimum: The new minimum size
        """
        if property_ not in self._managed_properties:
            return
        size_range: tuple[QSizeF, QSizeF] = property_.getAttributeValue(
            self.SizeFAttributes.RANGE,
            (QSizeF(.0, .0), QSizeF(.0, .0))
        )
        range_min, range_max = size_range
        w1, h1 = range_max.width(), range_max.height()
        range_min = QSizeF(min(w1, minimum.width()), min(h1, minimum.height()))
        range_max = QSizeF(max(w1, minimum.width()), max(h1, minimum.height()))
        if property_.setAttributeValue(
            self.SizeFAttributes.RANGE,
            (range_min, range_max)
        ):
            self.rangeChanged.emit(property_, range_min, range_max)
            self._updating_sub_properties = True
            w_property, h_property = self._property_to_wh.get(
                property_,
                (None, None)
            )
            if w_property and h_property:
                self._double_sub_manager.setRange(
                    w_property, range_min.width(), range_max.width()
                )
                self._double_sub_manager.setRange(
                    h_property, range_min.height(), range_max.height()
                )
            self._updating_sub_properties = False

    def maximum(self, property_: QtProperty[QSizeF]) -> QSizeF:
        """
        Return the maximum size of a property's range.

        :param property_: The property to get the maximum from
        :return: The maximum size
        """
        if property_ not in self._managed_properties:
            return QSizeF(0, 0)
        _, maximum = property_.getAttributeValue(
            self.SizeFAttributes.RANGE,
            (QSizeF(0, 0), QSizeF(0, 0))
        )
        return maximum

    def setMaximum(self, property_: QtProperty[QSizeF], maximum: QSizeF) -> None:
        """
        Set the maximum size of a property's range.

        Emits rangeChanged if the range changes. Updates sub-property
        ranges and clamps the current value if necessary.

        :param property_: The property to modify
        :param maximum: The new maximum size
        """
        if property_ not in self._managed_properties:
            return
        size_range: tuple[QSizeF, QSizeF] = property_.getAttributeValue(
            self.SizeFAttributes.RANGE,
            (QSizeF(0, 0), QSizeF(0, 0))
        )
        range_min, range_max = size_range
        w0, h0 = range_min.width(), range_min.height()
        range_min = QSizeF(min(w0, maximum.width()), min(h0, maximum.height()))
        range_max = QSizeF(max(w0, maximum.width()), max(h0, maximum.height()))
        if property_.setAttributeValue(
            self.SizeFAttributes.RANGE,
            (range_min, range_max)
        ):
            self.rangeChanged.emit(property_, range_min, range_max)
            value: QSizeF = property_.value()
            actual_value = QSizeF(
                max(range_min.width(), min(value.width(), range_max.width())),
                max(range_min.height(), min(value.height(), range_max.height()))
            )
            property_.setValue(actual_value)
            self._updating_sub_properties = True
            w_property, h_property = self._property_to_wh.get(
                property_,
                (None, None)
            )
            if w_property and h_property:
                self._double_sub_manager.setRange(
                    w_property, range_min.width(), range_max.width()
                )
                self._double_sub_manager.setRange(
                    h_property, range_min.height(), range_max.height()
                )
            self._updating_sub_properties = False

    def setRange(self, property_: QtProperty[QSizeF], minimum: QSizeF, maximum: QSizeF) -> None:
        """
        Set both minimum and maximum sizes of a property's range.

        Emits rangeChanged if the range changes. Updates sub-property
        ranges and clamps the current value if necessary.

        :param property_: The property to modify
        :param minimum: The new minimum size
        :param maximum: The new maximum size
        """
        if property_ not in self._managed_properties:
            return
        w0, h0 = minimum.width(), minimum.height()
        w1, h1 = maximum.width(), maximum.height()
        range_min = QSizeF(min(w0, w1), min(h0, h1))
        range_max = QSizeF(max(w0, w1), max(h0, h1))
        if property_.setAttributeValue(
            self.SizeFAttributes.RANGE,
            (range_min, range_max)
        ):
            self.rangeChanged.emit(property_, range_min, range_max)
            value: QSizeF = property_.value()
            actual_value = QSizeF(
                max(w0, min(value.width(), w1)),
                max(h0, min(value.height(), h1))
            )
            property_.setValue(actual_value)
            self._updating_sub_properties = True
            w_property, h_property = self._property_to_wh.get(
                property_,
                (None, None)
            )
            if w_property and h_property:
                self._double_sub_manager.setRange(
                    w_property, minimum.width(), maximum.width()
                )
                self._double_sub_manager.setRange(
                    h_property, minimum.height(), maximum.height()
                )
            self._updating_sub_properties = False

    def subPropertyChanged(self, property_: QtProperty[float], value: float) -> None:
        """
        Handle changes to width or height sub-properties.

        Updates the parent size property when a dimension changes.
        Only processes changes if not already updating sub-properties.

        :param property_: The dimension sub-property that changed
        :param value: The new dimension value
        """
        if not self._updating_sub_properties and property_ in self._sub_property_to_parent:
            parent_prop, idx = self._sub_property_to_parent[property_]
            s: QSizeF = parent_prop.value()
            size_wh = [s.width(), s.height()]
            size_wh[idx] = value
            parent_prop.setValue(QSizeF(*size_wh))


# Originally sourced from .\QtProperty\qtpropertymanager.py
# noinspection PyPep8Naming
class QtColorPropertyManager(QtAbstractPropertyManager[QColor]):
    """
    Property manager for color (QColor) properties.

    This class manages QColor properties with RGBA channels as sub-properties.
    Changes to the color or its channels are synchronized between the parent
    property and its sub-properties. Provides visual representation via icons
    and text formatting.

    :cvar DEFAULT_VALUE: Default value (transparent black) for color properties
    """
    DEFAULT_VALUE: QColor = QColor()


    def __init__(self, name: str='') -> None:
        """
        Initialize the color property manager.

        Creates an internal integer property manager for handling RGBA channel
        sub-properties.

        :param name: The name of the manager
        """
        super().__init__(name)
        self._int_sub_manager = QtIntPropertyManager()
        self._int_sub_manager.valueChanged.connect(self.subPropertyChanged)
        self._property_to_channel: dict[
            QtProperty[QColor],
            tuple[QtProperty[int], ...]
        ] = dict()
        self._channel_property_to_parent: dict[
            QtProperty[int],
            tuple[QtProperty[QColor], int]
        ] = dict()
        self._updating_sub_properties: bool = False

    @override
    def createProperty(
        self,
        name: str,
        value: QColor,
    ) -> QtProperty[QColor]:
        """
        Create a new color property instance.

        Creates Red, Green, Blue, and Alpha integer sub-properties for the
        color channels and establishes the relationship between parent and
        sub-properties. Each channel is constrained to the range [0, 255].

        :param name: The name of the property
        :param value: The initial color value
        :return: The created property
        """
        property_ = super().createProperty(name, value)
        rgb_color: list[int] = value.getRgb()  # type: ignore
        red, green, blue, alpha = rgb_color

        r_tag, g_tag, b_tag, a_tag = 'Red', 'Green', 'Blue', 'Alpha'
        app: QApplication = QApplication.instance()  # type: ignore
        if app is not None:
            r_tag, g_tag, b_tag, a_tag = map(app.tr, [r_tag, g_tag, b_tag, a_tag])

        red_channel = self._int_sub_manager.addProperty(r_tag, red)
        self._int_sub_manager.setRange(red_channel, 0, 255)
        property_.addSubProperty(red_channel)
        self._channel_property_to_parent[red_channel] = (property_, 0)

        green_channel = self._int_sub_manager.addProperty(g_tag, green)
        self._int_sub_manager.setRange(green_channel, 0, 255)
        property_.addSubProperty(green_channel)
        self._channel_property_to_parent[green_channel] = (property_, 1)

        blue_channel = self._int_sub_manager.addProperty(b_tag, blue)
        self._int_sub_manager.setRange(blue_channel, 0, 255)
        property_.addSubProperty(blue_channel)
        self._channel_property_to_parent[blue_channel] = (property_, 2)

        alpha_channel = self._int_sub_manager.addProperty(a_tag, alpha)
        self._int_sub_manager.setRange(alpha_channel, 0, 255)
        property_.addSubProperty(alpha_channel)
        self._channel_property_to_parent[alpha_channel] = (property_, 3)

        self._property_to_channel[property_] = (
            red_channel, green_channel, blue_channel, alpha_channel
        )
        return property_

    def subPropertyManager(self) -> QtIntPropertyManager:
        """
        Return the internal integer property manager.

        This manager handles the RGBA channel sub-properties.

        :return: The integer sub-property manager
        """
        return self._int_sub_manager

    @override
    def setValue(self, property_: QtProperty[QColor], value: QColor) -> bool:
        """
        Set the value of a color property.

        Updates both the parent property and its RGBA channel sub-properties.
        Prevents infinite recursion during sub-property updates.

        :param property_: The property to set the value on
        :param value: The new color value
        :return: True if the value changed, False otherwise
        """
        if property_ not in self._managed_properties:
            return False
        if property_.setValue(value):
            rgb_values: list[int] = value.getRgb()  # type: ignore
            r, g, b, a = rgb_values
            red, green, blue, alpha = self._property_to_channel[property_]
            self._updating_sub_properties = True
            red.setValue(r)
            green.setValue(g)
            blue.setValue(b)
            alpha.setValue(a)
            self._updating_sub_properties = False
            return True
        return False

    @override
    def valueText(self, property_: QtProperty[QColor]) -> str:
        """
        Return the text representation of a color value.

        Format: '[R, G, B] (A)' where values are in range [0, 255].

        :param property_: The property to get the text for
        :return: The string representation of the color
        """
        if property_ not in self._managed_properties:
            return ''
        rgb_values: list[int] = property_.value().getRgb()  # type: ignore
        r, g, b, alpha = rgb_values
        text = f"[{r}, {g}, {b}] ({alpha})"
        app: QApplication = QApplication.instance()  # type: ignore
        if app is not None:
            return app.tr(text)
        return text

    @override
    def valueIcon(self, property_: QtProperty[QColor]) -> QIcon:
        """
        Return the icon representation of a color value.

        :param property_: The property to get the icon for
        :return: The icon representing the color
        """
        if property_ not in self._managed_properties:
            return QIcon()
        return brushValueIcon(QBrush(property_.value()))

    def subPropertyChanged(self, property_: QtProperty[int], value: int) -> None:
        """
        Handle changes to RGBA channel sub-properties.

        Updates the parent color property when a channel changes.
        Only processes changes if not already updating sub-properties.

        :param property_: The channel sub-property that changed
        :param value: The new channel value (0-255)
        """
        if self._updating_sub_properties or property_ not in self._channel_property_to_parent:
            return
        color_property, idx = self._channel_property_to_parent[property_]
        color = color_property.value()
        channels = [color.red(), color.green(), color.blue(), color.alpha()]
        channels[idx] = value
        color_property.setValue(QColor(*channels))


class _FlagManagerSignalEmitter(_BaseSignalEmitter):
    """
    Internal emitter for the QtFlagPropertyManager

    :ivar flagNamesChanged: Signal emitted when the flag names list changes
    """

    flagNamesChanged = Signal(QtProperty, list)
    """ flagNamesChanged(property, flag_names) """


# Originally sourced from .\QtProperty\qtpropertymanager.py
# noinspection PyPep8Naming
class QtFlagPropertyManager(QtAbstractPropertyManager[int]):
    """
    Property manager for flag (bitmask integer) properties.

    This class manages integer properties where each bit represents a boolean
    flag. Flags are exposed as individual boolean sub-properties for easy
    manipulation.

    The manager handles synchronization between the integer value and
    its flag components. To ensure this synchronization, values should be set
    with the manager's setValue() function.

    :cvar DEFAULT_VALUE: Default value for flag properties
    """
    DEFAULT_VALUE: int = -1  # No flags


    class FlagAttributes(StrEnum):
        """
        Enum for flag-specific property attributes.

        These attributes extend the default QtProperty attributes with
        options specific to flag property types.
        """
        FLAG_NAMES = auto()


    def __init__(self, name: str='') -> None:
        """
        Initialize the flag property manager.

        Creates an internal boolean property manager for handling individual
        flag sub-properties.

        :param name: The name of the manager
        """
        super().__init__(name)
        self._emitter: _FlagManagerSignalEmitter = _FlagManagerSignalEmitter()
        self._bool_sub_manager = QtBoolPropertyManager()
        self._bool_sub_manager.valueChanged.connect(self.subPropertyChanged)
        self._property_to_flag_props: dict[
            QtProperty[int],
            list[QtProperty[bool]]
        ] = dict()
        self._flag_prop_to_parent: dict[
            QtProperty[bool],
            tuple[QtProperty[int], int]
        ] = dict()
        self._updating_sub_properties: bool = False

    @property
    def flagNamesChanged(self) -> SignalInstance:
        """ Emitted when the list of flag names of a property changes """
        return self._emitter.flagNamesChanged

    @override
    def createProperty(
        self,
        name: str,
        value: int,
    ) -> QtProperty[int]:
        """
        Create a new flag property instance.

        Initializes the property with an empty flag names list. Flag names
        must be set separately using setFlagNames() to define the available flags.

        :param name: The name of the property
        :param value: The initial flag value
        :return: The created property
        """
        property_ = super().createProperty(name, value)
        property_.setAttributeValue(self.FlagAttributes.FLAG_NAMES, list())
        return property_

    def subPropertyManager(self) -> QtBoolPropertyManager:
        """
        Return the internal boolean property manager.

        This manager handles the individual flag sub-properties.

        :return: The boolean sub-property manager
        """
        return self._bool_sub_manager

    @override
    def setValue(self, property_: QtProperty[int], value: int) -> bool:
        """
        Set the value of a flag property.

        The value is clamped to the valid range based on the number of defined
        flags. Updates all flag sub-properties to reflect the new value.
        Prevents infinite recursion during sub-property updates.

        :param property_: The property to set the value on
        :param value: The new flag value
        :return: True if the value changed, False otherwise
        """
        if property_ not in self._managed_properties:
            return False
        flag_names: list[str] = property_.getAttributeValue(
            self.FlagAttributes.FLAG_NAMES,
            list()
        )
        value = max(0, min(value, (1 << len(flag_names)) - 1))
        if property_.setValue(value):
            sub_props = self._property_to_flag_props.get(property_, list())
            self._updating_sub_properties = True
            # Helpers making use of the standard flag classes
            flags = IntFlag('Flags', flag_names)  # type: ignore
            flags_item = flags(value)
            for i, prop in enumerate(sub_props):
                prop.setValue(flags(1 << i) in flags_item)
            self._updating_sub_properties = False
            return True
        return False

    def flagNames(self, property_: QtProperty[int]) -> list[str]:
        """
        Return the list of flag names for a property.

        :param property_: The property to get the flag names from
        :return: The list of flag names
        """
        if property_ not in self._managed_properties:
            return list()
        return property_.getAttributeValue(
            self.FlagAttributes.FLAG_NAMES,
            list()
        )

    def setFlagNames(self, property_: QtProperty[int], flag_names: list[str]) -> None:
        """
        Set the list of flag names for a property.

        Creates or removes boolean sub-properties to match the new flag names.
        Resets the property value to 0 and emits flagNamesChanged.

        :param property_: The property to modify
        :param flag_names: The new list of flag names
        """
        if property_ not in self._managed_properties:
            return
        if not property_.setAttributeValue(
            self.FlagAttributes.FLAG_NAMES,
            flag_names
        ):
            return
        while self._property_to_flag_props.get(property_, list()):
            flag_prop = self._property_to_flag_props[property_].pop()
            self._flag_prop_to_parent.pop(flag_prop)
            property_.removeSubProperty(flag_prop)
            flag_prop.destroy()
        new_props = list()
        for i, name in enumerate(flag_names):
            prop = self._bool_sub_manager.addProperty(name, False)
            self._flag_prop_to_parent[prop] = (property_, i)
            new_props.append(prop)
            property_.addSubProperty(prop)
        self._property_to_flag_props[property_] = new_props
        property_.setValue(0)
        self.flagNamesChanged.emit(property_, flag_names)

    @override
    def valueText(self, property_: QtProperty[int]) -> str:
        """
        Return the text representation of a flag value.

        Returns the symbolic name of the flag combination (e.g., 'FlagA|FlagC')
        or the integer value if no symbolic name exists.

        :param property_: The property to get the text for
        :return: The string representation of the flag value
        """
        if property_ not in self._managed_properties:
            return ''
        flag_names: list[str] = property_.getAttributeValue(
            self.FlagAttributes.FLAG_NAMES,
            list()
        )
        value = property_.value()
        flags = IntFlag('Flags', flag_names)  # type: ignore
        flags_item = flags(value)
        item_name = flags_item.name
        return item_name if item_name else ''

    def subPropertyChanged(self, property_: QtProperty[bool], value: bool) -> None:
        """
        Handle changes to individual flag sub-properties.

        Updates the parent integer property when a flag changes.
        Only processes changes if not already updating sub-properties.

        :param property_: The flag sub-property that changed
        :param value: The new boolean value of the flag
        """
        if self._updating_sub_properties or property_ not in self._flag_prop_to_parent:
            return
        parent_prop, i = self._flag_prop_to_parent.get(
            property_,
            (None, 0)
        )
        if parent_prop is None:
            return
        flag_value: int = parent_prop.value()
        if value:
            flag_value |= (1 << i)
        else:
            flag_value &= ~(1 << i)
        parent_prop.setValue(flag_value)


class _EnumManagerSignalEmitter(_BaseSignalEmitter):
    """
    Internal emitter for the QtEnumPropertyManager

    :ivar enumNamesChanged: Signal emitted when the enum names list changes
    :ivar enumIconsChanged: Signal emitted when the enum icons dictionary changes
    """

    enumNamesChanged = Signal(QtProperty, list)
    """ enumNamesChanged(property, enum_names) """
    # The signature here is enumIconsChanged(QtProperty, dict), but PySide6 complains
    # with the following:
    # Shiboken::Conversions::_pythonToCppCopy: Cannot copy-convert 000002D2BE71F400 (dict) to C++.
    enumIconsChanged = Signal(QtProperty, object)
    """ enumNamesChanged(property, icons_map) """


# Originally sourced from .\QtProperty\qtpropertymanager.py
# noinspection PyPep8Naming
class QtEnumPropertyManager(QtAbstractPropertyManager[int]):
    """
    Property manager for enum (integer index) properties.

    This class manages integer properties that represent enum values by index.
    Supports configurable enum names and optional icons for each enum value.
    The manager handles validation to ensure values stay within the defined
    enum range.

    :cvar DEFAULT_VALUE: Default value for enum properties
    """
    DEFAULT_VALUE: int = -1


    class EnumAttributes(StrEnum):
        """
        Enum for enum-specific property attributes.

        These attributes extend the default QtProperty attributes with
        options specific to enum property types.
        """
        ENUM_NAMES = auto()
        ENUM_ICONS = auto()


    def __init__(self, name: str='') -> None:
        """
        Initialize the enum property manager.

        :param name: The name of the manager
        """
        super().__init__(name)
        self._emitter: _EnumManagerSignalEmitter = _EnumManagerSignalEmitter()

    @property
    def enumNamesChanged(self) -> SignalInstance:
        """ Emitted when the list of enum names of a property changes """
        return self._emitter.enumNamesChanged

    @property
    def enumIconsChanged(self) -> SignalInstance:
        """ Emitted when the mapping of enum values to icons of a property changes """
        return self._emitter.enumIconsChanged

    @override
    def createProperty(
        self,
        name: str,
        value: int,
    ) -> QtProperty[int]:
        """
        Create a new enum property instance.

        Initializes the property with empty enum names and icons dictionaries.
        These must be set separately using setEnumNames() and setEnumIcons().

        :param name: The name of the property
        :param value: The initial enum index value
        :return: The created property
        """
        property_ = super().createProperty(name, value)
        property_.setAttributeValue(self.EnumAttributes.ENUM_NAMES, list())
        property_.setAttributeValue(self.EnumAttributes.ENUM_ICONS, dict())
        return property_

    @override
    def setValue(self, property_: QtProperty[int], value: int) -> bool:
        """
        Set the value of an enum property.

        Validates that the value is within the bounds of the defined enum names.
        If no enum is defined, only accepts -1 as a valid value.

        :param property_: The property to set the value on
        :param value: The new enum index value
        :return: True if the value changed, False otherwise or if validation fails
        """
        if property_ not in self._managed_properties:
            return False
        enum_names = property_.getAttributeValue(
            self.EnumAttributes.ENUM_NAMES,
            list()
        )
        # If there's an Enum defined and the value is inside the bounds
        if enum_names and (0 <= value < len(enum_names)):
            return property_.setValue(value)
        # If there's no Enum defined and the value is negative, make it always -1
        if not enum_names and value < 0:
            return property_.setValue(-1)
        return False

    def enumNames(self, property_: QtProperty[int]) -> list[str]:
        """
        Return the list of enum names for a property.

        :param property_: The property to get the enum names from
        :return: The list of enum names
        """
        if property_ not in self._managed_properties:
            return list()
        return property_.getAttributeValue(
            self.EnumAttributes.ENUM_NAMES,
            list()
        )

    def setEnumNames(self, property_: QtProperty[int], enum_names: list[str]) -> None:
        """
        Set the list of enum names for a property.

        Emits enumNamesChanged if the list changes. Resets the property
        value to 0 if names exist, or -1 if the list is empty.

        :param property_: The property to modify
        :param enum_names: The new list of enum names
        """
        if property_ not in self._managed_properties:
            return
        if property_.setAttributeValue(
            self.EnumAttributes.ENUM_NAMES,
            enum_names
        ):
            self.enumNamesChanged.emit(property_, enum_names)
            property_.setValue(0 if enum_names else -1)

    def enumIcons(self, property_: QtProperty[int]) -> dict[int, QIcon]:
        """
        Return the dictionary of icons for enum values.

        :param property_: The property to get the icons from
        :return: Dictionary mapping enum indices to icons
        """
        if property_ not in self._managed_properties:
            return dict()
        return property_.getAttributeValue(
            self.EnumAttributes.ENUM_ICONS,
            dict()
        )

    def setEnumIcons(self, property_: QtProperty[int], enum_icons: dict[int, QIcon]) -> None:
        """
        Set the dictionary of icons for enum values.

        Emits enumIconsChanged if the dictionary changes.

        :param property_: The property to modify
        :param enum_icons: Dictionary mapping enum indices to icons
        """
        if property_ not in self._managed_properties:
            return
        if property_.setAttributeValue(
            self.EnumAttributes.ENUM_ICONS,
            enum_icons
        ):
            self.enumIconsChanged.emit(property_, enum_icons)

    @override
    def valueText(self, property_: QtProperty[int]) -> str:
        """
        Return the text representation of an enum value.

        Returns the name of the enum at the current index, or an empty
        string if the index is out of bounds.

        :param property_: The property to get the text for
        :return: The enum name or empty string
        """
        if property_ not in self._managed_properties:
            return ''
        idx: int = property_.value()
        enum_names: list[str] = property_.getAttributeValue(
            self.EnumAttributes.ENUM_NAMES,
            list()
        )
        if 0 <= idx < len(enum_names):
            return enum_names[idx]
        return ''

    @override
    def valueIcon(self, property_: QtProperty[int]) -> QIcon:
        """
        Return the icon representation of an enum value.

        Returns the icon for the current enum index, or an empty QIcon
        if no icon is defined for that index.

        :param property_: The property to get the icon for
        :return: The enum icon or empty QIcon
        """
        if property_ not in self._managed_properties:
            return QIcon()
        idx: int = property_.value()
        enum_icons: dict[int, QIcon] = property_.getAttributeValue(
            self.EnumAttributes.ENUM_ICONS,
            dict()
        )
        return enum_icons.get(idx, QIcon())


# Originally sourced from .\QtProperty\qtpropertymanager.py
# noinspection PyPep8Naming
class QtSizePolicyPropertyManager(QtAbstractPropertyManager[QSizePolicy]):
    """
    Property manager for size policy (QSizePolicy) properties.

    This class manages QSizePolicy properties with sub-properties for
    horizontal policy, vertical policy, horizontal stretch, and vertical
    stretch. Changes to the size policy or its components are synchronized
    between the parent property and its sub-properties.

    :cvar DEFAULT_VALUE: Default value for size policy properties
    """
    DEFAULT_VALUE: QSizePolicy = QSizePolicy()


    class SizePolicyComponents(StrEnum):
        """
        Enum for identifying size policy sub-properties.

        These values are used to identify which sub-property changed
        when synchronizing values between the parent and sub-properties.
        """
        HORIZONTAL_POLICY  = auto()
        VERTICAL_POLICY    = auto()
        HORIZONTAL_STRETCH = auto()
        VERTICAL_STRETCH   = auto()


    def __init__(self,  name: str='') -> None:
        """
        Initialize the size policy property manager.

        Creates internal integer and enum property managers for handling
        policy and stretch sub-properties.

        :param name: The name of the manager
        """
        super().__init__(name)
        self._int_sub_manager = QtIntPropertyManager()
        self._int_sub_manager.valueChanged.connect(self.subPropertyChanged)
        self._enum_sub_manager = QtEnumPropertyManager()
        self._enum_sub_manager.valueChanged.connect(self.subPropertyChanged)

        # property_ -> (Horizontal_Policy, Vertical_Policy, Horizontal_Stretch, Vertical_Stretch)
        self._property_to_sub_props: dict[
            QtProperty[QSizePolicy],
            tuple[QtProperty[int], ...]
        ] = dict()
        self._sub_property_to_parent: dict[
            QtProperty[int],
            tuple[QtProperty[QSizePolicy], str]
        ] = dict()
        self._updating_sub_properties: bool = False

        self._size_policies = [pol for pol in QSizePolicy.Policy]

    @override
    def createProperty(
        self,
        name: str,
        value: QSizePolicy,
    ) -> QtProperty[QSizePolicy]:
        """
        Create a new size policy property instance.

        Creates sub-properties for horizontal policy, vertical policy,
        horizontal stretch, and vertical stretch. Policy sub-properties
        use enum values from QSizePolicy.Policy, while stretch sub-properties
        are integers in the range [0, 255].

        :param name: The name of the property
        :param value: The initial size policy value
        :return: The created property
        """
        property_ = super().createProperty(name, value)

        policy_names = [pol.name for pol in self._size_policies]
        h_idx = self._size_policies.index(value.horizontalPolicy())
        v_idx = self._size_policies.index(value.verticalPolicy())

        h_pol_tag, v_pol_tag = "Horizontal Policy", "Vertical Policy"
        h_stretch_tag, v_stretch_tag = "Horizontal Stretch", "Vertical Stretch"
        app: QApplication = QApplication.instance()  # type: ignore
        if app is not None:
            h_pol_tag = app.tr(h_pol_tag)
            v_pol_tag = app.tr(v_pol_tag)
            h_stretch_tag = app.tr(h_stretch_tag)
            v_stretch_tag = app.tr(v_stretch_tag)

        h_policy_prop = self._enum_sub_manager.addProperty(h_pol_tag, h_idx)
        keys = self.SizePolicyComponents
        self._enum_sub_manager.setEnumNames(h_policy_prop, policy_names)
        # Setting the names also changes the value, resetting it to zero. Assign again
        h_policy_prop.setValue(h_idx)
        self._sub_property_to_parent[h_policy_prop] = (property_, keys.HORIZONTAL_POLICY)
        property_.addSubProperty(h_policy_prop)

        v_policy_prop = self._enum_sub_manager.addProperty(v_pol_tag, v_idx)
        self._enum_sub_manager.setEnumNames(v_policy_prop, policy_names)
        # Setting the names also changes the value, resetting it to zero. Assign again
        v_policy_prop.setValue(v_idx)
        self._sub_property_to_parent[v_policy_prop] = (property_, keys.VERTICAL_POLICY)
        property_.addSubProperty(v_policy_prop)

        h_stretch_prop = self._int_sub_manager.addProperty(
            h_stretch_tag,
            value.horizontalStretch()
        )
        self._int_sub_manager.setRange(h_stretch_prop, 0, 255)
        self._sub_property_to_parent[h_stretch_prop] = (property_, keys.HORIZONTAL_STRETCH)
        property_.addSubProperty(h_stretch_prop)

        v_stretch_prop = self._int_sub_manager.addProperty(
            v_stretch_tag,
            value.verticalStretch()
        )
        self._int_sub_manager.setRange(v_stretch_prop, 0, 255)
        self._sub_property_to_parent[v_stretch_prop] = (property_, keys.VERTICAL_STRETCH)
        property_.addSubProperty(v_stretch_prop)

        self._property_to_sub_props[property_] = (
            h_policy_prop, v_policy_prop, h_stretch_prop, v_stretch_prop
        )
        return property_

    def subIntPropertyManager(self) -> QtIntPropertyManager:
        """
        Return the internal integer property manager.

        This manager handles the horizontal and vertical stretch sub-properties.

        :return: The integer sub-property manager
        """
        return self._int_sub_manager

    def subEnumPropertyManager(self) -> QtEnumPropertyManager:
        """
        Return the internal enum property manager.

        This manager handles the horizontal and vertical policy sub-properties.

        :return: The enum sub-property manager
        """
        return self._enum_sub_manager

    @override
    def setValue(self, property_: QtProperty[QSizePolicy], value: QSizePolicy) -> bool:
        """
        Set the value of a size policy property.

        Updates both the parent property and its sub-properties (policies
        and stretches). Prevents infinite recursion during sub-property updates.

        :param property_: The property to set the value on
        :param value: The new size policy value
        :return: True if the value changed, False otherwise
        """
        if property_ not in self._managed_properties:
            return False
        if property_.setValue(value):
            h_idx = self._size_policies.index(value.horizontalPolicy())
            v_idx = self._size_policies.index(value.verticalPolicy())

            h_policy, v_policy, h_stretch, v_stretch = self._property_to_sub_props[property_]
            self._updating_sub_properties = True
            h_policy.setValue(h_idx)
            v_policy.setValue(v_idx)
            h_stretch.setValue(value.horizontalStretch())
            v_stretch.setValue(value.verticalStretch())
            self._updating_sub_properties = False
            return True
        return False

    @override
    def valueText(self, property_: QtProperty[QSizePolicy]) -> str:
        """
        Return the text representation of a size policy value.

        Format: '[HorizontalPolicy, VerticalPolicy, HorizontalStretch, VerticalStretch]'

        :param property_: The property to get the text for
        :return: The string representation of the size policy
        """
        if property_ not in self._managed_properties:
            return ''
        size_policy: QSizePolicy = property_.value()
        h_policy = size_policy.horizontalPolicy()
        v_policy = size_policy.verticalPolicy()
        h_stretch = size_policy.horizontalStretch()
        v_stretch = size_policy.verticalStretch()

        text = f'[{h_policy.name}, {v_policy.name}, {h_stretch},{v_stretch}]'
        app: QApplication = QApplication.instance()  # type: ignore
        if app is not None:
            return app.tr(text)
        return text


    def subPropertyChanged(self, property_: QtProperty[int], value: int) -> None:
        """
        Handle changes to size policy sub-properties.

        Updates the parent size policy property when a component changes.
        Only processes changes if not already updating sub-properties.

        :param property_: The sub-property that changed
        :param value: The new value of the sub-property
        """
        if self._updating_sub_properties or property_ not in self._sub_property_to_parent:
            return
        parent_prop, key = self._sub_property_to_parent[property_]
        size_policy = QSizePolicy(parent_prop.value())

        if key == self.SizePolicyComponents.HORIZONTAL_POLICY:
            size_policy.setHorizontalPolicy(self._size_policies[value])
        if key == self.SizePolicyComponents.VERTICAL_POLICY:
            size_policy.setVerticalPolicy(self._size_policies[value])
        if key == self.SizePolicyComponents.HORIZONTAL_STRETCH:
            size_policy.setHorizontalStretch(value)
        if key == self.SizePolicyComponents.VERTICAL_STRETCH:
            size_policy.setVerticalStretch(value)
        parent_prop.setValue(size_policy)


class _RectManagerSignalEmitter(_BaseSignalEmitter):
    """
    Internal emitter for the QtRectPropertyManager

    :ivar constraintChanged: Signal emitted when the constraint rectangle changes
    """

    constraintChanged = Signal(QtProperty, QRect)
    """ constraintChanged(property, constraint) """


# Originally sourced from .\QtProperty\qtpropertymanager.py
# noinspection PyPep8Naming
class QtRectPropertyManager(QtAbstractPropertyManager[QRect]):
    """
    Property manager for rectangle (QRect) properties.

    This class manages QRect properties with sub-properties for X coordinate,
    Y coordinate, width, and height. Changes to the rectangle or its components
    are synchronized between the parent property and its sub-properties.
    Supports constraint rectangles to limit the valid bounds.

    :cvar MAXIMUM_INT: Maximum allowed coordinate value
    :cvar MINIMUM_INT: Minimum allowed coordinate value
    :cvar DEFAULT_VALUE: Default value for rectangle properties
    """

    MAXIMUM_INT: int = 2 ** 31 - 1
    MINIMUM_INT: int = -MAXIMUM_INT
    DEFAULT_VALUE: QRect = QRect()


    class RectAttributes(StrEnum):
        """
        Enum for rectangle-specific property attributes.

        These attributes extend the default QtProperty attributes with
        options specific to rectangle property types.
        """
        CONSTRAINT = auto()


    class RectComponents(StrEnum):
        """
        Enum for identifying rectangle sub-property components.

        These values are used to identify which sub-property changed
        when synchronizing values between the parent and sub-properties.
        """
        X_COORD = auto()
        Y_COORD = auto()
        WIDTH = auto()
        HEIGHT = auto()


    def __init__(self, name: str='') -> None:
        """
        Initialize the rectangle property manager.

        Creates an internal integer property manager for handling coordinate
        and dimension sub-properties.

        :param name: The name of the manager
        """
        super().__init__(name)
        self._emitter: _RectManagerSignalEmitter = _RectManagerSignalEmitter()
        self._int_sub_manager = QtIntPropertyManager()
        self._int_sub_manager.valueChanged.connect(self.subPropertyChanged)
        self._property_to_sub_props: dict[
            QtProperty[QRect],
            tuple[QtProperty[int], ...]
        ] = dict()
        self._sub_property_to_parent: dict[
            QtProperty[int],
            tuple[QtProperty[QRect], str]
        ] = dict()
        self._updating_sub_properties: bool = False

    @property
    def constraintChanged(self) -> SignalInstance:
        """ Signal emitted when the constraint rectangle of a property changes """
        return self._emitter.constraintChanged

    @override
    def createProperty(
        self,
        name: str,
        value: QRect,
    ) -> QtProperty[QRect]:
        """
        Create a new rectangle property instance.

        Creates sub-properties for X, Y, Width, and Height. Width and Height
        are constrained to the range [0, MAXIMUM_INT]. Sets default constraint
        to an invalid QRect (no constraint).

        :param name: The name of the property
        :param value: The initial rectangle value
        :return: The created property
        """
        property_ = super().createProperty(name, value)
        property_.setAttributeValue(self.RectAttributes.CONSTRAINT, QRect())

        x_tag, y_tag, w_tag, h_tag = 'X', 'Y', 'Width', 'Height'
        app: QApplication = QApplication.instance()  # type: ignore
        if app is not None:
            x_tag, y_tag, = app.tr(x_tag), app.tr(y_tag)
            w_tag, h_tag = app.tr(w_tag), app.tr(h_tag)

        keys = self.RectComponents
        x_property = self._int_sub_manager.addProperty(x_tag, value.x())
        self._sub_property_to_parent[x_property] = (property_, keys.X_COORD)
        property_.addSubProperty(x_property)

        y_property = self._int_sub_manager.addProperty(y_tag, value.y())
        self._sub_property_to_parent[y_property] = (property_, keys.Y_COORD)
        property_.addSubProperty(y_property)

        w_property = self._int_sub_manager.addProperty(w_tag, value.width())
        self._int_sub_manager.setRange(w_property, 0, self.MAXIMUM_INT)
        self._sub_property_to_parent[w_property] = (property_, keys.WIDTH)
        property_.addSubProperty(w_property)

        h_property = self._int_sub_manager.addProperty(h_tag, value.height())
        self._int_sub_manager.setRange(h_property, 0, self.MAXIMUM_INT)
        self._sub_property_to_parent[h_property] = (property_, keys.HEIGHT)
        property_.addSubProperty(h_property)

        self._property_to_sub_props[property_] = (
            x_property, y_property, w_property, h_property
        )
        return property_

    def subIntPropertyManager(self) -> QtIntPropertyManager:
        """
        Return the internal integer property manager.

        This manager handles the X, Y, Width, and Height sub-properties.

        :return: The integer sub-property manager
        """
        return self._int_sub_manager

    @override
    def setValue(self, property_: QtProperty[QRect], value: QRect) -> bool:
        """
        Set the value of a rectangle property.

        The value is normalized and clamped to the constraint rectangle, if one
        is defined. Updates all sub-properties to reflect the new value.
        Prevents infinite recursion during sub-property updates.

        :param property_: The property to set the value on
        :param value: The new rectangle value
        :return: True if successful, False otherwise
        """
        if property_ not in self._managed_properties:
            return False
        value = value.normalized()
        bounds: QRect = property_.getAttributeValue(
            self.RectAttributes.CONSTRAINT,
            QRect()
        )
        if bounds.isValid():
            value.setLeft(max(bounds.left(), value.left()))
            value.setRight(min(bounds.right(), value.right()))
            value.setTop(max(bounds.top(), value.top()))
            value.setBottom(min(bounds.bottom(), value.bottom()))
            if not value.isValid():
                return False
        if property_.setValue(value):
            x_prop, y_prop, w_prop, h_prop = self._property_to_sub_props[property_]
            self._updating_sub_properties = True
            x_prop.setValue(value.x())
            y_prop.setValue(value.y())
            w_prop.setValue(value.width())
            h_prop.setValue(value.height())
            self._updating_sub_properties = False
            return True
        return False

    @override
    def valueText(self, property_: QtProperty[QRect]) -> str:
        """
        Return the text representation of a rectangle value.

        Format: '[(x, y), width x height]'

        :param property_: The property to get the text for
        :return: The string representation of the rectangle
        """
        if property_ not in self._managed_properties:
            return ''
        rect: QRect = property_.value()
        text = f"[({rect.x()}, {rect.y()}), {rect.width()} x {rect.height()}]"
        app: QApplication = QApplication.instance()  # type: ignore
        if app is not None:
            return app.tr(text)
        return text

    def constraint(self, property_: QtProperty[QRect]) -> QRect:
        """
        Return the constraint rectangle for a property.

        :param property_: The property to get the constraint from
        :return: The constraint rectangle, or invalid QRect if none set
        """
        if property_ not in self._managed_properties:
            return QRect()
        return property_.getAttributeValue(
            self.RectAttributes.CONSTRAINT,
            QRect()
        )

    def setConstraint(self, property_: QtProperty[QRect], constraint: QRect) -> None:
        """
        Set the constraint rectangle for a property.

        The constraint limits the valid bounds for the rectangle. When set,
        the rectangle's position and dimensions are clamped to stay within
        the constraint. Updates sub-property ranges accordingly.

        :param property_: The property to modify
        :param constraint: The new constraint rectangle
        """
        if property_ not in self._managed_properties:
            return
        constraint = constraint.normalized()
        if not property_.setAttributeValue(
            self.RectAttributes.CONSTRAINT,
            constraint
        ):
            return
        self.constraintChanged.emit(property_, constraint)
        current_value: QRect = property_.value()
        if constraint.isValid():
            width = min(constraint.width(), current_value.width())
            max_w = constraint.width()
            height = min(constraint.height(), current_value.height())
            max_h = constraint.height()
            min_x = constraint.left()
            max_x = constraint.right() - width + 1
            min_y = constraint.top()
            max_y = constraint.bottom() - height + 1

            x = max(min_x, min(current_value.x(), max_x))
            y = max(min_y, min(current_value.y(), max_y))
            current_value = QRect(x, y, width, height)
        else:
            width, height = current_value.width(), current_value.height()
            min_x = min_y = self.MINIMUM_INT
            max_x = max_y = max_w = max_h = self.MAXIMUM_INT
        property_.setValue(current_value)

        x_prop, y_prop, w_prop, h_prop = self._property_to_sub_props[property_]

        self._updating_sub_properties = True
        self._int_sub_manager.setRange(x_prop, min_x, max_x)
        x_prop.setValue(current_value.x())
        self._int_sub_manager.setRange(y_prop, min_y, max_y)
        y_prop.setValue(current_value.y())
        self._int_sub_manager.setRange(w_prop, 0, max_w)
        w_prop.setValue(width)
        self._int_sub_manager.setRange(h_prop, 0, max_h)
        h_prop.setValue(height)
        self._updating_sub_properties = False

    def subPropertyChanged(self, property_: QtProperty[int], value: int) -> None:
        """
        Handle changes to rectangle sub-properties.

        Updates the parent rectangle property when a component changes.
        Handles constraint validation when width or height changes.
        Only processes changes if not already updating sub-properties.

        :param property_: The sub-property that changed
        :param value: The new value of the sub-property
        """
        if self._updating_sub_properties or property_ not in self._sub_property_to_parent:
            return
        parent_prop, key = self._sub_property_to_parent[property_]
        rect = QRect(parent_prop.value())
        constraint = parent_prop.getAttributeValue(
            self.RectAttributes.CONSTRAINT,
            QRect()
        )
        x_prop, y_prop, _, _ = self._property_to_sub_props[parent_prop]
        if key == self.RectComponents.X_COORD:
            rect.moveLeft(value)
        if key == self.RectComponents.Y_COORD:
            rect.moveTop(value)
        if key == self.RectComponents.WIDTH:
            rect.setWidth(value)
            if (constraint.isValid()
                and (constraint.x() + constraint.width()) < (rect.x() + value)):
                rect.moveLeft(constraint.left() + constraint.width() - value)
                self._updating_sub_properties = True
                x_prop.setValue(rect.x())
                self._updating_sub_properties = False
        if key == self.RectComponents.HEIGHT:
            rect.setHeight(value)
            if (constraint.isValid()
                and (constraint.y() + constraint.height()) < (rect.y() + value)):
                rect.moveTop(constraint.top() + constraint.height() - value)
                self._updating_sub_properties = True
                y_prop.setValue(rect.y())
                self._updating_sub_properties = False
        parent_prop.setValue(rect)


class _RectFManagerSignalEmitter(_BaseSignalEmitter):
    """
    Internal emitter for the QtRectFPropertyManager

    :ivar constraintChanged: Signal emitted when the constraint rectangle changes
    """

    constraintChanged = Signal(QtProperty, QRectF)
    """ constraintChanged(property, constraint) """
    decimalsChanged = Signal(QtProperty, int)
    """ decimalsChanged(property, precision) """


# Originally sourced from .\QtProperty\qtpropertymanager.py
# noinspection PyPep8Naming
class QtRectFPropertyManager(QtAbstractPropertyManager[QRectF]):
    """
    Property manager for floating-point rectangle (QRectF) properties.

    This class manages QRectF properties with sub-properties for X coordinate,
    Y coordinate, width, and height. Changes to the rectangle or its components
    are synchronized between the parent property and its sub-properties.
    Supports constraint rectangles and configurable decimal precision.

    :cvar MAXIMUM_DOUBLE: Maximum allowed coordinate value
    :cvar MINIMUM_DOUBLE: Minimum allowed coordinate value
    :cvar DEFAULT_VALUE: Default value for floating-point rectangle properties
    """
    MAXIMUM_DOUBLE: float = 2.0 ** 31 - 1
    MINIMUM_DOUBLE: float = -MAXIMUM_DOUBLE
    DEFAULT_VALUE: QRectF = QRectF()


    class RectFAttributes(StrEnum):
        """
        Enum for floating-point rectangle-specific property attributes.

        These attributes extend the default QtProperty attributes with
        options specific to floating-point rectangle property types.
        """
        CONSTRAINT = auto()
        DECIMALS = auto()


    class RectFComponents(StrEnum):
        """
        Enum for identifying floating-point rectangle sub-property components.

        These values are used to identify which sub-property changed
        when synchronizing values between the parent and sub-properties.
        """
        X_COORD = auto()
        Y_COORD = auto()
        WIDTH = auto()
        HEIGHT = auto()


    def __init__(self, name: str='') -> None:
        """
        Initialize the floating-point rectangle property manager.

        Creates an internal double property manager for handling coordinate
        and dimension sub-properties.

        :param name: The name of the manager
        """
        super().__init__(name)
        self._emitter: _RectFManagerSignalEmitter = _RectFManagerSignalEmitter()
        self._double_sub_manager = QtDoublePropertyManager()
        self._double_sub_manager.valueChanged.connect(self.subPropertyChanged)
        self._property_to_sub_props: dict[
            QtProperty[QRectF],
            tuple[QtProperty[float], ...]
        ] = dict()
        self._sub_property_to_parent: dict[
            QtProperty[float],
            tuple[QtProperty[QRectF], str]
        ] = dict()
        self._updating_sub_properties: bool = False

    @property
    def constraintChanged(self) -> SignalInstance:
        """ Signal emitted when the constraint rectangle of a property changes """
        return self._emitter.constraintChanged

    @property
    def decimalsChanged(self) -> SignalInstance:
        """ Signal emitted when the precision of a property changes """
        return self._emitter.decimalsChanged

    @override
    def createProperty(
        self,
        name: str,
        value: QRectF,
    ) -> QtProperty[QRectF]:
        """
        Create a new floating-point rectangle property instance.

        Creates sub-properties for X, Y, Width, and Height. Width and Height
        are constrained to the range [0, MAXIMUM_DOUBLE]. Sets default constraint
        to an invalid QRectF (no constraint) and decimal precision to 2.

        :param name: The name of the property
        :param value: The initial rectangle value
        :return: The created property
        """
        property_ = super().createProperty(name, value)
        property_.setAttributeValue(self.RectFAttributes.CONSTRAINT, QRectF())
        precision: int = 2
        property_.setAttributeValue(self.RectFAttributes.DECIMALS, precision)

        x_tag, y_tag, w_tag, h_tag = 'X', 'Y', 'Width', 'Height'
        app: QApplication = QApplication.instance()  # type: ignore
        if app is not None:
            x_tag, y_tag, = app.tr(x_tag), app.tr(y_tag)
            w_tag, h_tag = app.tr(w_tag), app.tr(h_tag)

        keys = self.RectFComponents
        x_property = self._double_sub_manager.addProperty(x_tag, value.x())
        self._double_sub_manager.setDecimals(x_property, precision)
        self._sub_property_to_parent[x_property] = (property_, keys.X_COORD)
        property_.addSubProperty(x_property)

        y_property = self._double_sub_manager.addProperty(y_tag, value.y())
        self._double_sub_manager.setDecimals(y_property, precision)
        self._sub_property_to_parent[y_property] = (property_, keys.Y_COORD)
        property_.addSubProperty(y_property)

        w_property = self._double_sub_manager.addProperty(w_tag, value.width())
        self._double_sub_manager.setDecimals(w_property, precision)
        self._double_sub_manager.setRange(w_property, .0, self.MAXIMUM_DOUBLE)
        self._sub_property_to_parent[w_property] = (property_, keys.WIDTH)
        property_.addSubProperty(w_property)

        h_property = self._double_sub_manager.addProperty(h_tag, value.height())
        self._double_sub_manager.setDecimals(h_property, precision)
        self._double_sub_manager.setRange(h_property, .0, self.MAXIMUM_DOUBLE)
        self._sub_property_to_parent[h_property] = (property_, keys.HEIGHT)
        property_.addSubProperty(h_property)

        self._property_to_sub_props[property_] = (
            x_property, y_property, w_property, h_property
        )
        return property_

    def subDoublePropertyManager(self) -> QtDoublePropertyManager:
        """
        Return the internal double property manager.

        This manager handles the X, Y, Width, and Height sub-properties.

        :return: The double sub-property manager
        """
        return self._double_sub_manager

    @override
    def setValue(self, property_: QtProperty[QRectF], value: QRectF) -> bool:
        """
        Set the value of a floating-point rectangle property.

        The value is normalized and clamped to the constraint rectangle if one
        is defined. Updates all sub-properties to reflect the new value.
        Prevents infinite recursion during sub-property updates.

        :param property_: The property to set the value on
        :param value: The new rectangle value
        :return: True if the value changed, False otherwise
        """
        if property_ not in self._managed_properties:
            return False
        value = value.normalized()
        bounds: QRectF = property_.getAttributeValue(
            self.RectFAttributes.CONSTRAINT,
            QRectF()
        )
        if bounds.isValid():
            value.setLeft(max(bounds.left(), value.left()))
            value.setRight(min(bounds.right(), value.right()))
            value.setTop(max(bounds.top(), value.top()))
            value.setBottom(min(bounds.bottom(), value.bottom()))
            if not value.isValid():
                return False
        if property_.setValue(value):
            x_prop, y_prop, w_prop, h_prop = self._property_to_sub_props[property_]
            self._updating_sub_properties = True
            x_prop.setValue(value.x())
            y_prop.setValue(value.y())
            w_prop.setValue(value.width())
            h_prop.setValue(value.height())
            self._updating_sub_properties = False
            return True
        return False

    @override
    def valueText(self, property_: QtProperty[QRectF]) -> str:
        """
        Return the text representation of a floating-point rectangle value.

        Format: '[(x, y), width x height]' with configurable decimal precision.

        :param property_: The property to get the text for
        :return: The string representation of the rectangle
        """
        if property_ not in self._managed_properties:
            return ''
        rect: QRectF = property_.value()
        d: int = property_.getAttributeValue(self.RectFAttributes.DECIMALS, 2)
        text = (
            f"[({rect.x():.{d}f}, {rect.y():.{d}f}), "
            f"{rect.width():.{d}f} x {rect.height():.{d}f}]"
        )
        app: QApplication = QApplication.instance()  # type: ignore
        if app is not None:
            return app.tr(text)
        return text

    def constraint(self, property_: QtProperty[QRectF]) -> QRectF:
        """
        Return the constraint rectangle for a property.

        :param property_: The property to get the constraint from
        :return: The constraint rectangle, or invalid QRectF if none set
        """
        if property_ not in self._managed_properties:
            return QRectF()
        return property_.getAttributeValue(
            self.RectFAttributes.CONSTRAINT,
            QRectF()
        )

    def setConstraint(self, property_: QtProperty[QRectF], constraint: QRectF) -> None:
        """
        Set the constraint rectangle for a property.

        The constraint limits the valid bounds for the rectangle. When set,
        the rectangle's position and dimensions are clamped to stay within
        the constraint. Updates sub-property ranges accordingly.

        :param property_: The property to modify
        :param constraint: The new constraint rectangle
        """
        if property_ not in self._managed_properties:
            return
        constraint = constraint.normalized()
        if not property_.setAttributeValue(
            self.RectFAttributes.CONSTRAINT,
            constraint
        ):
            return
        self.constraintChanged.emit(property_, constraint)
        current_value: QRectF = property_.value()
        if constraint.isValid():
            width = min(constraint.width(), current_value.width())
            max_w = constraint.width()
            height = min(constraint.height(), current_value.height())
            max_h = constraint.height()
            min_x = constraint.left()
            max_x = constraint.right() - width + 1
            min_y = constraint.top()
            max_y = constraint.bottom() - height + 1

            x = max(min_x, min(current_value.x(), max_x))
            y = max(min_y, min(current_value.y(), max_y))
            current_value = QRectF(x, y, width, height)
        else:
            width, height = current_value.width(), current_value.height()
            min_x = min_y = self.MINIMUM_DOUBLE
            max_x = max_y = max_w = max_h = self.MAXIMUM_DOUBLE
        property_.setValue(current_value)

        x_prop, y_prop, w_prop, h_prop = self._property_to_sub_props[property_]

        self._updating_sub_properties = True
        self._double_sub_manager.setRange(x_prop, min_x, max_x)
        x_prop.setValue(current_value.x())
        self._double_sub_manager.setRange(y_prop, min_y, max_y)
        y_prop.setValue(current_value.y())
        self._double_sub_manager.setRange(w_prop, .0, max_w)
        w_prop.setValue(width)
        self._double_sub_manager.setRange(h_prop, .0, max_h)
        h_prop.setValue(height)
        self._updating_sub_properties = False

    def decimals(self, property_: QtProperty[QRectF]) -> int:
        """
        Return the decimal precision for a property.

        :param property_: The property to get the decimals from
        :return: The number of decimal places
        """
        if property_ not in self._managed_properties:
            return 0
        return property_.getAttributeValue(self.RectFAttributes.DECIMALS, 0)

    def setDecimals(self, property_: QtProperty[QRectF], decimals: int) -> None:
        """
        Set the decimal precision for a property.

        Updates all sub-properties (X, Y, Width, Height) with the new precision.
        Emits decimalsChanged if the precision changes.

        :param property_: The property to modify
        :param decimals: The new decimal precision (minimum 0)
        """
        decimals = max(0, decimals)
        if property_ not in self._managed_properties:
            return
        if property_.setAttributeValue(self.RectFAttributes.DECIMALS, decimals):
            x_prop, y_prop, w_prop, h_prop = self._property_to_sub_props[property_]
            self._double_sub_manager.setDecimals(x_prop, decimals)
            self._double_sub_manager.setDecimals(y_prop, decimals)
            self._double_sub_manager.setDecimals(w_prop, decimals)
            self._double_sub_manager.setDecimals(h_prop, decimals)
            self.decimalsChanged.emit(property_, decimals)

    def subPropertyChanged(self, property_: QtProperty[float], value: float) -> None:
        """
        Handle changes to rectangle sub-properties.

        Updates the parent rectangle property when a component changes.
        Handles constraint validation when width or height changes.
        Only processes changes if not already updating sub-properties.

        :param property_: The sub-property that changed
        :param value: The new value of the sub-property
        """
        if self._updating_sub_properties or property_ not in self._sub_property_to_parent:
            return
        parent_prop, key = self._sub_property_to_parent[property_]
        rect = QRectF(parent_prop.value())
        constraint = parent_prop.getAttributeValue(
            self.RectFAttributes.CONSTRAINT,
            QRectF()
        )
        x_prop, y_prop, _, _ = self._property_to_sub_props[parent_prop]
        if key == self.RectFComponents.X_COORD:
            rect.moveLeft(value)
        if key == self.RectFComponents.Y_COORD:
            rect.moveTop(value)
        if key == self.RectFComponents.WIDTH:
            rect.setWidth(value)
            if (constraint.isValid()
                and (constraint.x() + constraint.width()) < (rect.x() + value)):
                rect.moveLeft(constraint.left() + constraint.width() - value)
                self._updating_sub_properties = True
                x_prop.setValue(rect.x())
                self._updating_sub_properties = False
        if key == self.RectFComponents.HEIGHT:
            rect.setHeight(value)
            if (constraint.isValid()
                and (constraint.y() + constraint.height()) < (rect.y() + value)):
                rect.moveTop(constraint.top() + constraint.height() - value)
                self._updating_sub_properties = True
                y_prop.setValue(rect.y())
                self._updating_sub_properties = False
        parent_prop.setValue(rect)


# Originally sourced from .\QtProperty\qtpropertymanager.py
# noinspection PyPep8Naming
class QtCursorPropertyManager(QtAbstractPropertyManager[QCursor]):
    """
    Property manager for cursor (QCursor) properties.

    This class manages QCursor properties with support for cursor shape
    identification. Uses a cursor database to provide text names and icon
    representations for different cursor shapes.

    :cvar DEFAULT_VALUE: Default value for cursor properties
    """
    DEFAULT_VALUE: QCursor = QCursor()

    def __init__(self, name: str='') -> None:
        """
        Initialize the cursor property manager.

        Ensures the cursor database is initialized before use and reassigns the
        default value to try to get a valid cursor from the QApplication instance
        that should be already created.

        :param name: The name of the manager
        """
        super().__init__(name)
        if not CURSOR_DATABASE.isInitialized():
            CURSOR_DATABASE.init()
        self.DEFAULT_VALUE = QCursor()

    @override
    def setValue(self, property_: QtProperty[QCursor], value: QCursor) -> bool:
        """
        Set the value of a cursor property.

        Avoids setting the value if the cursor shape is identical, unless
        it is a bitmap cursor (which may have different pixmap data despite
        having the same shape).

        :param property_: The property to set the value on
        :param value: The new cursor value
        :return: True if successful, False otherwise
        """
        if property_ not in self._managed_properties:
            return False
        if (
            property_.value().shape() == value.shape()
            and value.shape() != Qt.CursorShape.BitmapCursor
        ):
            return False
        return property_.setValue(value)

    @override
    def valueText(self, property_: QtProperty[QCursor]) -> str:
        """
        Return the text representation of a cursor value.

        Returns the cursor shape name from the cursor database.

        :param property_: The property to get the text for
        :return: The cursor shape name or empty string
        """
        if property_ not in self._managed_properties:
            return ''
        return CURSOR_DATABASE.cursorToShapeName(property_.value())

    @override
    def valueIcon(self, property_: QtProperty[QCursor]) -> QIcon:
        """
        Return the icon representation of a cursor value.

        Returns the cursor shape icon from the cursor database.

        :param property_: The property to get the icon for
        :return: The cursor icon or empty QIcon
        """
        if property_ not in self._managed_properties:
            return QIcon()
        return CURSOR_DATABASE.cursorToShapeIcon(property_.value())


# Originally sourced from .\QtProperty\qtpropertymanager.py
# noinspection PyPep8Naming
class QtLocalePropertyManager(QtAbstractPropertyManager[QLocale]):
    """
    Property manager for locale (QLocale) properties.

    This class manages QLocale properties with sub-properties for language
    and country selection. The country options are dynamically filtered based
    on the selected language. Changes to the locale or its components are
    synchronized between the parent property and its sub-properties.

    :cvar DEFAULT_VALUE: Default value for locale properties
    """
    DEFAULT_VALUE: QLocale = QLocale()

    class LocaleComponents(StrEnum):
        """
        Enum for identifying locale (QLocale) sub-property components.

        These values are used to identify which sub-property changed
        when synchronizing values between the parent and sub-properties.
        """
        LANGUAGE = auto()
        COUNTRY  = auto()


    def __init__(self, name: str='') -> None:
        """
        Initialize the locale property manager.

        Creates an internal enum property manager for handling language and
        country sub-properties. Builds a list of available languages that have
        associated countries.

        :param name: The name of the manager
        """
        super().__init__(name)
        self.DEFAULT_VALUE = QLocale.system()
        self._enum_sub_manager = QtEnumPropertyManager()
        self._enum_sub_manager.valueChanged.connect(self.subPropertyChanged)
        self._property_to_sub_props: dict[
            QtProperty[QLocale],
            tuple[QtProperty[int], QtProperty[int]]
        ] = dict()
        self._sub_property_to_parent: dict[
            QtProperty[int],
            tuple[QtProperty[QLocale], str]
        ] = dict()
        self._updating_sub_properties: bool = False

        self._available_languages = [
            lang for lang in QLocale.Language if QLocale.countriesForLanguage(lang)
        ]
        self._available_languages.remove(QLocale.Language.AnyLanguage)
        self._available_languages.remove(QLocale.Language.C)

    def locale_to_indices(self, locale: QLocale) -> tuple[int, int]:
        """
        Convert a locale to its language and country indices.

        :param locale: The locale to convert
        :return: Tuple of (language_index, country_index)
        """
        languages = self._available_languages
        countries = [loc.country() for loc in locale.matchingLocales(
            locale.language(), locale.Script.AnyScript, locale.Country.AnyCountry
        )]
        language_idx = languages.index(locale.language())
        country_idx = countries.index(locale.country())
        return language_idx, country_idx

    @override
    def createProperty(
        self,
        name: str,
        value: QLocale=QLocale.system(),
    ) -> QtProperty[QLocale]:
        """
        Create a new locale property instance.

        Creates language and country enum sub-properties. The language list
        includes all available languages with countries. The country list is
        initialized based on the selected language.

        :param name: The name of the property
        :param value: The initial locale value
        :return: The created property
        """
        property_ = super().createProperty(name, value)
        language_idx, country_idx = self.locale_to_indices(value)

        language_tag, country_tag = 'Language', 'Country'
        language_names = [formatMultiWordName(lang.name) for lang in self._available_languages]

        app: QApplication = QApplication.instance()  # type: ignore
        if app is not None:
            language_tag = app.tr(language_tag)
            country_tag = app.tr(country_tag)
            language_names = [app.tr(lang) for lang in language_names]

        language_prop = self._enum_sub_manager.addProperty(language_tag)
        self._enum_sub_manager.setEnumNames(
            language_prop,
            language_names
        )
        language_prop.setValue(language_idx)

        keys = self.LocaleComponents
        self._sub_property_to_parent[language_prop] = (property_, keys.LANGUAGE)
        property_.addSubProperty(language_prop)

        country_prop = self._enum_sub_manager.addProperty(country_tag)
        countries = QLocale.countriesForLanguage(value.language())
        country_names = [formatMultiWordName(c.name) for c in countries]
        if app is not None:
            country_names = [app.tr(country) for country in country_names]
        self._enum_sub_manager.setEnumNames(
            country_prop,
            country_names
        )
        country_prop.setValue(country_idx)
        self._sub_property_to_parent[country_prop] = (property_, keys.COUNTRY)
        property_.addSubProperty(country_prop)
        self._property_to_sub_props[property_] = (language_prop, country_prop)
        return property_

    def subPropertyManager(self) -> QtEnumPropertyManager:
        """
        Return the internal enum property manager.

        This manager handles the language and country sub-properties.

        :return: The enum sub-property manager
        """
        return self._enum_sub_manager

    @override
    def setValue(self, property_: QtProperty[QLocale], value: QLocale) -> bool:
        """
        Set the value of a locale property.

        Updates both the parent property and its language/country sub-properties.
        When the language changes, the country list is updated to match.
        Prevents infinite recursion during sub-property updates.

        :param property_: The property to set the value on
        :param value: The new locale value
        :return: True if successful, False otherwise
        """
        if property_ not in self._managed_properties:
            return False
        if property_.setValue(value):
            self._updating_sub_properties = True
            language_idx, country_idx = self.locale_to_indices(value)
            language_prop, country_prop = self._property_to_sub_props[property_]
            countries = QLocale.countriesForLanguage(value.language())
            country_names = [formatMultiWordName(c.name) for c in countries]
            app: QApplication = QApplication.instance()  # type: ignore
            if app is not None:
                country_names = [app.tr(country) for country in country_names]
            if language_prop.setValue(language_idx):
                self._enum_sub_manager.setEnumNames(country_prop, country_names)
                country_prop.setValue(country_idx)
            self._updating_sub_properties = False
            return True
        return False

    @override
    def valueText(self, property_: QtProperty[QLocale]) -> str:
        """
        Return the text representation of a locale value.

        Format: 'Language, Country'

        :param property_: The property to get the text for
        :return: The string representation of the locale
        """
        if property_ not in self._managed_properties:
            return ''
        locale = property_.value()
        language = formatMultiWordName(locale.language().name)
        country = formatMultiWordName(locale.country().name)
        text = f"{language}, {country}"
        app: QApplication = QApplication.instance()  # type: ignore
        if app is not None:
            return app.tr(text)
        return text

    def subPropertyChanged(self, property_: QtProperty[int], value: int) -> None:
        """
        Handle changes to language or country sub-properties.

        Updates the parent locale property when a component changes.
        When the language changes, the country list is dynamically updated
        to show only countries available for that language.
        Only processes changes if not already updating sub-properties.

        :param property_: The sub-property that changed
        :param value: The new value of the sub-property
        """
        if self._updating_sub_properties or property_ not in self._sub_property_to_parent:
            return
        locale_prop, key = self._sub_property_to_parent[property_]
        language_prop, country_prop = self._property_to_sub_props[locale_prop]
        new_locale = QLocale(locale_prop.value())
        if key == self.LocaleComponents.LANGUAGE:
            new_language = self._available_languages[value]
            countries = QLocale.countriesForLanguage(new_language)
            new_locale = QLocale(new_language, countries[0])
            self._updating_sub_properties = True
            country_names = [formatMultiWordName(c.name) for c in countries]
            app: QApplication = QApplication.instance()  # type: ignore
            if app is not None:
                country_names = [app.tr(country) for country in country_names]
            # Setting the names also changes the value, resetting it to zero.
            self._enum_sub_manager.setEnumNames(country_prop, country_names)
            self._updating_sub_properties = False
        if key == self.LocaleComponents.COUNTRY:
            same_language = self._available_languages[language_prop.value()]
            countries = QLocale.countriesForLanguage(same_language)
            new_locale = QLocale(same_language, countries[value])
        locale_prop.setValue(new_locale)


# Originally sourced from .\QtProperty\qtpropertymanager.py
# noinspection PyPep8Naming
class QtFontPropertyManager(QtAbstractPropertyManager[QFont]):
    """
    Property manager for font (QFont) properties.

    This class manages QFont properties with sub-properties for family,
    point size, bold, italic, underline, strikeout, kerning, and weight.
    Changes to the font or its components are synchronized between the
    parent property and its sub-properties. Monitors font database changes
    to update available font families dynamically.

    :cvar DEFAULT_VALUE: Default value for font properties
    """
    DEFAULT_VALUE: QFont = QFont()


    class FontComponents(StrEnum):
        """
        Enum for identifying font sub-property components.

        These values are used to identify which sub-property changed
        when synchronizing values between the parent and sub-properties.
        """
        FAMILY = auto()
        POINT_SIZE = auto()
        BOLD = auto()
        ITALIC = auto()
        UNDERLINE = auto()
        STRIKEOUT = auto()
        WEIGHT = auto()


    def __init__(self, name: str='') -> None:
        """
        Initialize the font property manager.

        Creates internal property managers for handling font component
        sub-properties (int, enum, and bool). Sets up monitoring for
        font database changes to keep available families updated.

        :param name: The name of the manager
        """
        super().__init__(name)
        self.DEFAULT_VALUE = QFont()  # A font after the QApplication has been initialized
        self._int_sub_manager = QtIntPropertyManager()
        self._int_sub_manager.valueChanged.connect(self.subIntPropertyChanged)
        self._enum_sub_manager = QtEnumPropertyManager()
        self._enum_sub_manager.valueChanged.connect(self.subEnumPropertyChanged)
        self._bool_sub_manager = QtBoolPropertyManager()
        self._bool_sub_manager.valueChanged.connect(self.subBoolPropertyChanged)
        self._updating_sub_properties: bool = False

        self._family_names: list[str] = QFontDatabase.families()
        self._property_to_sub_props: dict[
            QtProperty[QFont],
            dict[
                QtFontPropertyManager.FontComponents,
                QtProperty[int] | QtProperty[bool]
            ]
        ] = dict()
        self._sub_property_to_parent: dict[
            QtProperty[int] | QtProperty[bool],
            tuple[QtProperty[QFont], QtFontPropertyManager.FontComponents]
        ] = dict()

        self._database_change_timer: QTimer = QTimer()
        self._database_change_timer.setInterval(0)
        self._database_change_timer.setSingleShot(True)
        self._database_change_timer.timeout.connect(self.onFontDatabaseDelayedChange)
        app_instance: QApplication = QApplication.instance()  # type: ignore
        if app_instance is not None:
            app_instance.fontDatabaseChanged.connect(self.onFontDatabaseChanged)

    @override
    def createProperty(
        self,
        name: str,
        value: QFont,
    ) -> QtProperty[QFont]:
        """
        Create a new font property instance.

        Creates sub-properties for all font components: Family, Point Size,
        Bold, Italic, Underline, Strikeout, Kerning, and Weight. Family and
        Weight use enum sub-properties, Point Size uses int, and the rest
        use boolean sub-properties.

        :param name: The name of the property
        :param value: The initial font value
        :return: The created property
        """
        property_ = super().createProperty(name, value)

        family_tag = 'Family'
        size_tag, bold_tag, italic_tag = 'Point Size', 'Bold', 'Italic'
        underline_tag, strikeout_tag = 'Underline', 'Strikeout'
        weight_tag = 'Weight'
        app: QApplication = QApplication.instance()  # type: ignore
        if app is not None:
            family_tag = app.tr(family_tag)
            size_tag = app.tr(size_tag)
            bold_tag = app.tr(bold_tag)
            italic_tag = app.tr(italic_tag)
            underline_tag = app.tr(underline_tag)
            strikeout_tag = app.tr(strikeout_tag)
            weight_tag = app.tr(weight_tag)

        keys = self.FontComponents
        family_idx = 0
        if value.family() in self._family_names:
            family_idx = self._family_names.index(value.family())
        family_prop = self._enum_sub_manager.addProperty(family_tag, 0)
        # Changing the names sets the value to zero, so change the names first
        # and set the value after
        self._enum_sub_manager.setEnumNames(family_prop, self._family_names)
        family_prop.setValue(family_idx)
        self._sub_property_to_parent[family_prop] = (property_, keys.FAMILY)
        property_.addSubProperty(family_prop)

        psize_prop = self._int_sub_manager.addProperty(size_tag, value.pointSize())
        self._int_sub_manager.setRange(psize_prop, 1, 1000)
        self._sub_property_to_parent[psize_prop] = (property_, keys.POINT_SIZE)
        property_.addSubProperty(psize_prop)

        bold_prop = self._bool_sub_manager.addProperty(bold_tag, value.bold())
        self._sub_property_to_parent[bold_prop] = (property_, keys.BOLD)
        property_.addSubProperty(bold_prop)

        italic_prop = self._bool_sub_manager.addProperty(italic_tag, value.italic())
        self._sub_property_to_parent[italic_prop] = (property_, keys.ITALIC)
        property_.addSubProperty(italic_prop)

        underline_prop = self._bool_sub_manager.addProperty(underline_tag, value.underline())
        self._sub_property_to_parent[underline_prop] = (property_, keys.UNDERLINE)
        property_.addSubProperty(underline_prop)

        strikeout_prop = self._bool_sub_manager.addProperty(strikeout_tag, value.strikeOut())
        self._sub_property_to_parent[strikeout_prop] = (property_, keys.STRIKEOUT)
        property_.addSubProperty(strikeout_prop)

        weight_prop = self._enum_sub_manager.addProperty(weight_tag, 0)
        # Changing the names sets the value to zero, so change the names first
        # and set the value after
        weights = [w for w in value.Weight]
        weight_names = [formatMultiWordName(w.name) for w in value.Weight]
        self._enum_sub_manager.setEnumNames(weight_prop, weight_names)
        weight_prop.setValue(weights.index(value.weight()))
        self._sub_property_to_parent[weight_prop] = (property_, keys.WEIGHT)
        property_.addSubProperty(weight_prop)

        self._property_to_sub_props[property_] = {
            keys.FAMILY:     family_prop,
            keys.POINT_SIZE: psize_prop,
            keys.BOLD:       bold_prop,
            keys.ITALIC:     italic_prop,
            keys.UNDERLINE:  underline_prop,
            keys.STRIKEOUT:  strikeout_prop,
            keys.WEIGHT:     weight_prop,
        }
        return property_

    def subBoolPropertyManager(self) -> QtBoolPropertyManager:
        """
        Return the internal boolean property manager.

        This manager handles the Bold, Italic, Underline, Strikeout,
        and Kerning sub-properties.

        :return: The boolean sub-property manager
        """
        return self._bool_sub_manager

    def subEnumPropertyManager(self) -> QtEnumPropertyManager:
        """
        Return the internal enum property manager.

        This manager handles the Family and Weight sub-properties.

        :return: The enum sub-property manager
        """
        return self._enum_sub_manager

    def subIntPropertyManager(self) -> QtIntPropertyManager:
        """
        Return the internal integer property manager.

        This manager handles the Point Size sub-property.

        :return: The integer sub-property manager
        """
        return self._int_sub_manager

    @override
    def setValue(self, property_: QtProperty[QFont], value: QFont) -> bool:
        """
        Set the value of a font property.

        Updates all sub-properties to reflect the new font value.
        Prevents infinite recursion during sub-property updates.

        :param property_: The property to set the value on
        :param value: The new font value
        :return: True if the value changed, False if value unchanged
        """
        if property_ not in self._managed_properties:
            return False
        if value == property_.value():
            return False
        idx = 0
        if value.family() in self._family_names:
            idx = self._family_names.index(value.family())
        keys = self.FontComponents
        self._updating_sub_properties = True
        family_prop = (
            self._property_to_sub_props[property_][keys.FAMILY]
        )
        family_prop.setValue(idx)  # type: ignore
        point_size_prop = (
            self._property_to_sub_props[property_][keys.POINT_SIZE]
        )
        point_size_prop.setValue(value.pointSize())  # type: ignore
        bold_prop = (
            self._property_to_sub_props[property_][keys.BOLD]
        )
        bold_prop.setValue(value.bold())
        italic_prop = (
            self._property_to_sub_props[property_][keys.ITALIC]
        )
        italic_prop.setValue(value.italic())
        underline_prop = (
            self._property_to_sub_props[property_][keys.UNDERLINE]
        )
        underline_prop.setValue(value.underline())
        strikeout_prop = (
            self._property_to_sub_props[property_][keys.STRIKEOUT]
        )
        strikeout_prop.setValue(value.strikeOut())
        weight_prop = (
            self._property_to_sub_props[property_][keys.WEIGHT]
        )
        weights = [w for w in value.Weight]
        weight_prop.setValue(weights.index(value.weight()))  # type: ignore
        property_.setValue(value)
        self._updating_sub_properties = False
        return True

    @override
    def valueText(self, property_: QtProperty[QFont]) -> str:
        """
        Return the text representation of a font value.

        :param property_: The property to get the text for
        :return: The string representation of the font
        """
        if property_ not in self._managed_properties:
            return ''
        return fontValueText(property_.value())

    @override
    def valueIcon(self, property_: QtProperty[QFont]) -> QIcon:
        """
        Return the icon representation of a font value.

        Returns a preview icon with the letter 'A' rendered in the font.

        :param property_: The property to get the icon for
        :return: The font preview icon
        """
        if property_ not in self._managed_properties:
            return QIcon()
        return QIcon(fontValuePixmap(property_.value()))

    def subIntPropertyChanged(self, property_: QtProperty[int], value: int) -> None:
        """
        Handle changes to the point size sub-property.

        Updates the parent font property when point size changes.
        Only processes changes if not already updating sub-properties.

        :param property_: The point size sub-property that changed
        :param value: The new point size value
        """
        if self._updating_sub_properties or property_ not in self._sub_property_to_parent:
            return
        parent_prop, _ = self._sub_property_to_parent[property_]
        font = QFont(parent_prop.value())
        font.setPointSize(value)
        parent_prop.setValue(font)

    def subEnumPropertyChanged(self, property_: QtProperty[int], value: int) -> None:
        """
        Handle changes to family or weight sub-properties.

        Updates the parent font property when family or weight changes.
        When family changes, updates the weight enum names to match
        the available weights for that font family.
        Only processes changes if not already updating sub-properties.

        :param property_: The sub-property that changed
        :param value: The new value of the sub-property
        """
        if self._updating_sub_properties or property_ not in self._sub_property_to_parent:
            return
        parent_prop, key = self._sub_property_to_parent[property_]
        font = QFont(parent_prop.value())
        keys = self.FontComponents
        if key == keys.FAMILY:
            # Make sure it's in range
            value = max(0, min(value, len(self._family_names) - 1))
            font.setFamily(self._family_names[value])
            self._updating_sub_properties = True
            weights = [w for w in font.Weight]
            weight_names = [formatMultiWordName(w.name) for w in font.Weight]
            weight_prop: QtProperty[int] = self._property_to_sub_props[parent_prop][keys.WEIGHT]  # type: ignore
            self._enum_sub_manager.setEnumNames(weight_prop, weight_names)
            weight_prop.setValue(weights.index(font.weight()))
            self._updating_sub_properties = False
        if key == keys.WEIGHT:
            weights = [w for w in font.Weight]
            font.setWeight(weights[value])
            self._updating_sub_properties = True
            bold_prop = self._property_to_sub_props[parent_prop][keys.BOLD]
            bold_prop.setValue(font.bold())
            self._updating_sub_properties = False
        parent_prop.setValue(font)

    def subBoolPropertyChanged(self, property_: QtProperty[bool], value: bool) -> None:
        """
        Handle changes to boolean font sub-properties.

        Updates the parent font property when bold, italic, underline,
        strikeout, or kerning changes. When bold changes, also updates
        the weight enum to stay synchronized.
        Only processes changes if not already updating sub-properties.

        :param property_: The sub-property that changed
        :param value: The new boolean value
        """
        if self._updating_sub_properties or property_ not in self._sub_property_to_parent:
            return
        parent_prop, key = self._sub_property_to_parent[property_]
        font = QFont(parent_prop.value())
        keys = self.FontComponents
        if key == keys.BOLD:
            font.setBold(value)
            self._updating_sub_properties = True
            weights = [w for w in font.Weight]
            weight_prop: QtProperty[int] = self._property_to_sub_props[parent_prop][keys.WEIGHT]  # type: ignore
            weight_prop.setValue(weights.index(font.weight()))
            self._updating_sub_properties = False
        if key == keys.ITALIC:
            font.setItalic(value)
        if key == keys.UNDERLINE:
            font.setUnderline(value)
        if key == keys.STRIKEOUT:
            font.setStrikeOut(value)
        parent_prop.setValue(font)

    def onFontDatabaseChanged(self):
        """
        Handle font database change notifications.

        Starts a delayed timer to update available font families.
        Uses a timer to debounce rapid consecutive changes.
        """
        if not self._database_change_timer.isActive():
            self._database_change_timer.start()

    def onFontDatabaseDelayedChange(self):
        """
        Update available font families after a database change.

        Rescans the font database and updates all managed properties
        with the new family list. Preserves the current family selection
        when possible.
        """
        old_families = self._family_names
        self._family_names = QFontDatabase.families()
        keys = self.FontComponents
        for property_ in self._managed_properties:
            family_prop = self._property_to_sub_props[property_][keys.FAMILY]
            old_family = old_families[family_prop.value()]
            new_idx = 0
            if old_family in self._family_names:
                new_idx = self._family_names.index(old_family)
            # Changing the names sets the value to zero, so change
            # the names first and set the value after
            self._enum_sub_manager.setEnumNames(family_prop, self._family_names)
            family_prop.setValue(new_idx)

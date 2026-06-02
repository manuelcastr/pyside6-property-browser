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
## LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES LOSS OF USE,
## DATA, OR PROFITS OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
## THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
## OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
##
## $QT_END_LICENSE$
##
#############################################################################
from typing import Any, TypeVar, Generic, Union

from PySide6.QtWidgets import QWidget, QTreeWidgetItem

from qtpropertybrowser.editor_factories import QtAbstractEditorFactory
from qtpropertybrowser.property_managers import (
    QtProperty,
    QtAbstractPropertyManager
)


class _BrowserConnectionsRegistry:
    """
    Internal registry for tracking connections between browsers, managers,
    and factories.

    This class maintains the mapping of which property manager uses which
    editor factory within each property browser instance. It ensures that
    each manager has at most one factory per browser and handles
    connection/disconnection logic.
    """
    def __init__(self) -> None:
        """
        Initialize the connection registry.
        """
        self._browser_to_manager_to_factory: dict[
            QtAbstractPropertyBrowser,
            dict[
                QtAbstractPropertyManager[Any],
                QtAbstractEditorFactory[Any]
            ]
        ] = dict()

    def has_connections_in_browser(
        self,
        manager: QtAbstractPropertyManager[Any],
        browser: QtAbstractPropertyBrowser
    ) -> bool:
        """
        Check if a manager has any factory connection in a browser.

        :param manager: The property manager to check
        :param browser: The property browser to check in
        :return: True if the manager has a connection in the browser
        """
        browser_managers = self._browser_to_manager_to_factory.get(
            browser,
            dict()
        )
        return manager in browser_managers

    def has_factory_in_browser(
        self,
        manager: QtAbstractPropertyManager[Any],
        browser: QtAbstractPropertyBrowser,
        factory: QtAbstractEditorFactory[Any]
    ) -> bool:
        """
        Check if a specific factory is linked to a manager in a browser.

        :param manager: The property manager to check
        :param browser: The property browser to check in
        :param factory: The editor factory to check
        :return: True if the factory is linked to the manager in the browser
        """
        browser_managers = self._browser_to_manager_to_factory.get(
            browser,
            dict()
        )
        return browser_managers.get(manager, None) == factory

    def get_factory_for_browser(
        self,
        manager: QtAbstractPropertyManager[Any],
        browser: QtAbstractPropertyBrowser,
    ) -> QtAbstractEditorFactory[Any] | None:
        """
        Get the factory associated with a manager in a browser.

        :param manager: The property manager
        :param browser: The property browser
        :return: The associated factory, or None if not connected
        """
        return self._browser_to_manager_to_factory.get(
            browser,
            dict()
        ).get(manager, None)

    def set_factory_for_browser(
        self,
        manager: QtAbstractPropertyManager[Any],
        factory: QtAbstractEditorFactory[Any],
        browser: QtAbstractPropertyBrowser
    ) -> None:
        """
        Set the factory for a manager in a browser.

        :param manager: The property manager
        :param factory: The editor factory to associate
        :param browser: The property browser
        """
        manager_factories = self._browser_to_manager_to_factory.setdefault(
            browser,
            dict()
        )
        manager_factories[manager] = factory

    def pop_manager_factory_from_browser(
        self,
        manager: QtAbstractPropertyManager[Any],
        browser: QtAbstractPropertyBrowser
    ) -> QtAbstractEditorFactory[Any] | None:
        """
        Remove and return the factory for a manager in a browser.

        Cleans up empty browser entries to prevent memory leaks.

        :param manager: The property manager
        :param browser: The property browser
        :return: The removed factory, or None if not connected
        """
        factory = self._browser_to_manager_to_factory.get(
            browser,
            dict()
        ).pop(manager, None)
        if not self._browser_to_manager_to_factory.get(browser, dict()):
            self._browser_to_manager_to_factory.pop(browser, None)
        return factory


BROWSERS_CONNECTIONS_REGISTRY = _BrowserConnectionsRegistry()
"""
Global registry instance for tracking browser-manager-factory connections.
"""

# Originally sourced from .\QtProperty\qtpropertybrowser.py
# noinspection PyPep8Naming
class QtBrowserItem:
    """
    Represents an item in a property browser.

    This class wraps a property and provides hierarchical structure within
    a property browser. Each item has a reference to its property, parent
    item, browser, and child items. Multiple items can represent the same
    property if it appears in multiple browsers or locations.
    """
    def __init__(
        self,
        browser: QtAbstractPropertyBrowser[Any],
        property_: QtProperty[Any] | None = None,
        parent: QtBrowserItem | None = None
    ) -> None:
        """
        Initialize a browser item.

        :param browser: The property browser containing this item
        :param property_: The property this item represents
        :param parent: The parent browser item, or None for top-level items
        """
        self._browser: QtAbstractPropertyBrowser[Any] = browser
        self._property: QtProperty[Any] | None = property_
        self._parent: QtBrowserItem | None = parent
        self._children: list[QtBrowserItem] = list()

    def browser(self) -> QtAbstractPropertyBrowser:
        """
        Return the property browser containing this item.

        :return: The property browser
        """
        return self._browser

    def itemProperty(self) -> QtProperty[Any] | None:
        """
        Return the property this item represents.

        :return: The property
        """
        return self._property

    def parent(self) -> QtBrowserItem | None:
        """
        Return the parent browser item.

        :return: The parent item, or None if this is a top-level item
        """
        return self._parent

    def children(self) -> list[QtBrowserItem]:
        """
        Return a list of child browser items.

        :return: List of child items
        """
        return list(self._children)

    def addChild(self, browser_item: QtBrowserItem, after: QtBrowserItem | None) -> None:
        """
        Add a child browser item.

        Inserts the child at the specified position. If 'after' is provided,
        inserts the child after that item. Otherwise, appends to the end.

        :param browser_item: The child item to add
        :param after: The sibling item to insert after, or None to append
        """
        if browser_item in self._children:
            return
        idx = len(self._children)
        if after and after in self._children:
            idx = self._children.index(after) + 1
        self._children.insert(idx, browser_item)

    def removeChild(self, browser_item: QtBrowserItem) -> None:
        """
        Remove a child browser item.

        :param browser_item: The child item to remove
        """
        if browser_item in self._children:
            self._children.remove(browser_item)


WidgetType = TypeVar("WidgetType", bound=Union[QTreeWidgetItem, QWidget])
"""
Type variable for the widget item type used in property browsers.

Bound to support both QWidget-based browsers (like QtGroupBoxPropertyBrowser) 
and QTreeWidgetItem-based browsers (like QtTreePropertyBrowser), Both types are
specified since QTreeWidgetItem inherits from QObject instead. This allows the 
abstract browser class to be generic over the specific widget item type used by
each subclass implementation.
"""


# Originally sourced from .\QtProperty\qtpropertybrowser.py
# noinspection PyPep8Naming
class QtAbstractPropertyBrowser(QWidget, Generic[WidgetType]):
    """
    Abstract base class for property browser widgets.

    This class provides the core functionality for displaying and editing
    properties in a browser widget. It manages the relationship between
    properties, browser items, and editor widgets. Subclasses must implement
    specific UI layouts (tree view, group box, etc.).

    The browser handles property insertion, removal, and updates, and
    coordinates with editor factories to create appropriate widgets for
    each property type.

    This class is generic over type WidgetType (bound to QObject), which represents
    the widget item type used by the specific browser implementation. For
    example, QtTreePropertyBrowser uses QTreeWidgetItem, while other browsers
    may use QWidget or custom widget types.
    """
    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the property browser.

        :param parent: The parent QWidget
        """
        super().__init__(parent)
        self._sub_properties: list[QtProperty[Any]] = list()
        self._properties_to_browser_items: dict[
            QtProperty[Any],
            list[QtBrowserItem]
        ] = dict()
        self._top_level_property_to_browser_item: dict[
            QtProperty[Any],
            QtBrowserItem
        ] = dict()
        self._top_level_items: list[QtBrowserItem] = list()
        self._manager_to_properties: dict[
            QtAbstractPropertyManager[Any],
            list[QtProperty[Any]]
        ] = dict()
        self._property_to_parents: dict[QtProperty[Any], list[QtProperty[Any] | None]] = dict()

        self._browser_item_to_widget_item: dict[QtBrowserItem, WidgetType] = dict()
        self._widget_item_to_browser_item: dict[WidgetType, QtBrowserItem] = dict()

    # <editor-fold desc="--- Accessing the class attributes ---">

    def properties(self) -> list[QtProperty[Any]]:
        """
        Return a list of all properties in the browser.

        :return: List of top-level properties
        """
        return self._sub_properties

    def items(self, property_: QtProperty[Any]) -> list[QtBrowserItem]:
        """
        Return all browser items representing a property.

        A property may have multiple items if it appears in multiple
        locations or browsers.

        :param property_: The property to get items for
        :return: List of browser items for the property
        """
        return self._properties_to_browser_items.get(property_, list())

    def topLevelItem(self, property_: QtProperty[Any]) -> QtBrowserItem | None:
        """
        Return the top-level browser item for a property.

        :param property_: The property to get the item for
        :return: The top-level item, or None if not found
        """
        return self._top_level_property_to_browser_item.get(property_, None)

    def topLevelItems(self) -> list[QtBrowserItem]:
        """
        Return all top-level browser items.

        :return: List of top-level items
        """
        return self._top_level_items

    def browserItems(self) -> list[QtBrowserItem]:
        """
        Return all browser items that have associated widget items.

        :return: List of browser items with widget items
        """
        return list(self._browser_item_to_widget_item.keys())

    def getBrowserItem(self, widget_item: WidgetType) -> QtBrowserItem | None:
        """
        Get the browser item associated with a widget item.

        :param widget_item: The widget item (QTreeWidgetItem, QWidget, etc.)
        :return: The associated browser item, or None if not found
        """
        return self._widget_item_to_browser_item.get(widget_item, None)

    def getWidgetItem(self, browser_item: QtBrowserItem) -> WidgetType | None:
        """
        Get the widget item associated with a browser item.

        :param browser_item: The browser item
        :return: The associated widget item, or None if not found
        """
        return self._browser_item_to_widget_item.get(browser_item, None)

    def setWidgetItem(self, browser_item: QtBrowserItem, widget_item: WidgetType) -> None:
        """
        Associate a widget item with a browser item.

        Creates a bidirectional mapping between the browser item and
        widget item for efficient lookups in both directions.

        :param browser_item: The browser item
        :param widget_item: The widget item to associate
        """
        self._browser_item_to_widget_item[browser_item] = widget_item
        self._widget_item_to_browser_item[widget_item] = browser_item

    def unsetWidgetItem(self, browser_item: QtBrowserItem, widget_item: WidgetType) -> None:
        """
        Remove the association between a browser item and widget item.

        Cleans up both directions of the mapping.

        :param browser_item: The browser item
        :param widget_item: The widget item to disassociate
        """
        self._browser_item_to_widget_item.pop(browser_item, None)
        self._widget_item_to_browser_item.pop(widget_item, None)

    # </editor-fold>

    # <editor-fold desc="--- Handling insertion and deletion of properties ---">

    def itemInserted(self, item: QtBrowserItem, after: QtBrowserItem | None) -> None:
        """
        Called when a browser item is inserted.

        Subclasses should override this method to update the UI when
        new items are added.

        :param item: The inserted browser item
        :param after: The sibling item after which this was inserted
        """
        pass

    def itemRemoved(self, item: QtBrowserItem) -> None:
        """
        Called when a browser item is removed.

        Subclasses should override this method to update the UI when
        items are removed.

        :param item: The removed browser item
        """
        pass

    def addProperty(self, property_: QtProperty[Any]) -> QtBrowserItem:
        """
        Add a property to the browser.

        Appends the property to the end of the property list.

        :param property_: The property to add
        :return: The created browser item
        """
        after_property = None
        if self._sub_properties:
            after_property = self._sub_properties[-1]
        return self.insertProperty(property_, after_property)

    def insertProperty(
        self,
        property_: QtProperty[Any],
        after: QtProperty[Any] | None
    ) -> QtBrowserItem:
        """
        Insert a property after another property.

        :param property_: The property to insert
        :param after: The property to insert after, or None for beginning
        :return: The created browser item
        """
        # If the property was already inserted...
        if property_ in self._top_level_property_to_browser_item:
            return self._top_level_property_to_browser_item[property_]

        self.createBrowserItems(property_, None, after)
        self.insertSubTree(property_, None)

        idx = len(self._sub_properties)
        if after and after in self._sub_properties:
            idx = self._sub_properties.index(after) + 1
        self._sub_properties.insert(idx, property_)

        return self._top_level_property_to_browser_item[property_]

    def createBrowserItems(
        self,
        property_: QtProperty[Any],
        parent: QtProperty[Any] | None,
        after: QtProperty[Any] | None
    ) -> None:
        """
        Create browser items for a property in all relevant parent contexts.

        :param property_: The property to create items for
        :param parent: The parent property, or None for top-level
        :param after: The sibling property to insert after
        """
        parent_to_after: dict[QtBrowserItem | None, QtBrowserItem | None] = dict()

        if after:
            prop_browser_items = self._properties_to_browser_items.get(after, list())
            if not prop_browser_items:
                return
            for b_item in prop_browser_items:
                parent_item = b_item.parent()
                if ((parent and parent_item and parent_item.itemProperty() == parent)
                    or (not parent and not parent_item)):
                    parent_to_after[parent_item] = b_item
        elif parent:
            prop_browser_items = self._properties_to_browser_items.get(parent, list())
            if not prop_browser_items:
                return
            for b_item in prop_browser_items:
                parent_to_after[b_item] = None
        else:
            parent_to_after[None] = None

        for item in parent_to_after:
            self.createBrowserItem(property_, item, parent_to_after[item])

    def createBrowserItem(
        self,
        property_: QtProperty[Any],
        parent: QtBrowserItem | None,
        after: QtBrowserItem | None
    ) -> QtBrowserItem:
        """
        Create a single browser item for a property.

        Recursively creates items for all sub-properties.

        :param property_: The property to create an item for
        :param parent: The parent browser item, or None for top-level
        :param after: The sibling item to insert after
        :return: The created browser item
        """
        browser_item = QtBrowserItem(self, property_, parent)
        if parent:
            parent.addChild(browser_item, after)
        else:
            self._top_level_property_to_browser_item[property_] = browser_item
            pos = len(self._top_level_items)
            if after and after in self._top_level_items:
                pos = self._top_level_items.index(after) + 1
            self._top_level_items.insert(pos, browser_item)
        self._properties_to_browser_items.setdefault(
            property_,
            list()
        ).append(browser_item)

        self.itemInserted(browser_item, after)

        after_child = None
        for child in property_.subProperties():
            after_child = self.createBrowserItem(child, browser_item, after_child)

        return browser_item

    def insertSubTree(
        self,
        property_: QtProperty[Any],
        parent: QtProperty[Any] | None
    ) -> None:
        """
        Insert a property subtree into the browser's internal tracking.

        Connects manager signals if this is the first property from that
        manager in the browser.

        :param property_: The property to insert
        :param parent: The parent property, or None for top-level
        """
        if property_ in self._property_to_parents:
            # If the property was already inserted, its manager is connected
            # and all its children are inserted and theirs managers are connected.
            # We just register the new parent, (parent has to be new).
            # There's no need to update _manager_to_properties dict, since
            # _manager_to_properties[manager] already contains the property.
            if parent not in self._property_to_parents[property_]:
                self._property_to_parents[property_].append(parent)
            return

        manager = property_.manager()
        if manager:
            properties_on_browser = self._manager_to_properties.get(manager, list())
            # If this is the first time this manager comes up
            if not properties_on_browser:
                manager.propertyInserted.connect(self.onPropertyInserted)
                manager.propertyRemoved.connect(self.onPropertyRemoved)
                manager.propertyDestroyed.connect(self.onPropertyDestroyed)
                manager.propertyChanged.connect(self.onPropertyDataChanged)

            self._manager_to_properties.setdefault(manager, list()).append(property_)
            self._property_to_parents.setdefault(property_, list()).append(parent)

        for sub_prop in property_.subProperties():
            self.insertSubTree(sub_prop, property_)

    def removeProperty(self, property_: QtProperty[Any]) -> None:
        """
        Remove a property from the browser.

        :param property_: The property to remove
        """
        if property_ not in self._sub_properties:
            return
        idx = self._sub_properties.index(property_)
        self._sub_properties.pop(idx)
        self.removeBrowserItems(property_, None)

    def removeSubTree(
        self,
        property_: QtProperty[Any],
        parent: QtProperty[Any] | None
    ) -> None:
        """
        Remove a property subtree from the browser's internal tracking.

        Disconnects manager signals if this is the last property from that
        manager in the browser.

        :param property_: The property to remove
        :param parent: The parent property, or None for top-level
        """
        if property_ not in self._property_to_parents:
            return

        if parent in self._property_to_parents[property_]:
            self._property_to_parents[property_].remove(parent)
        # If there are still elements in the list, there's no need to do more cleanup
        if self._property_to_parents[property_]:
            return

        self._property_to_parents.pop(property_)
        manager = property_.manager()
        if manager:
            properties_on_browser = self._manager_to_properties.get(manager, list())
            if property_ in properties_on_browser:
                self._manager_to_properties[manager].remove(property_)
            # IF there are no more properties in the browser for by this manager, disconnect
            if not properties_on_browser:
                manager.propertyChanged.disconnect(self.onPropertyDataChanged)
                manager.propertyInserted.disconnect(self.onPropertyInserted)
                manager.propertyRemoved.disconnect(self.onPropertyRemoved)
                manager.propertyDestroyed.disconnect(self.onPropertyDestroyed)
                self._manager_to_properties.pop(manager, None)

        for sub_property in property_.subProperties():
            self.removeSubTree(sub_property, property_)

    def removeBrowserItems(
        self,
        property_: QtProperty[Any],
        parent: QtProperty[Any] | None
    ) -> None:
        """
        Remove browser items for a property in a specific parent context.

        :param property_: The property to remove items for
        :param parent: The parent property context, or None for top-level
        """
        if property_ not in self._properties_to_browser_items:
            return

        items_to_remove: list[QtBrowserItem] = list()
        browser_items = self._properties_to_browser_items.get(property_, list())
        for item in browser_items:
            parent_item = item.parent()
            if ((parent and parent_item and parent_item.itemProperty() == parent)
                or (not parent and not parent_item)):
                items_to_remove.append(item)
        for item in items_to_remove:
            self.removeBrowserItem(item)

    def removeBrowserItem(self, item: QtBrowserItem) -> None:
        """
        Remove a single browser item and all its children.

        :param item: The browser item to remove
        """
        for child in item.children()[::-1]:
            self.removeBrowserItem(child)
        self.itemRemoved(item)

        property_ = item.itemProperty()
        if parent := item.parent():
            parent.removeChild(item)
        else:
            if property_:
                self._top_level_property_to_browser_item.pop(property_, None)
            if item in self._top_level_items:
                self._top_level_items.remove(item)

        if not property_:
            return
        if item in self._properties_to_browser_items.get(property_, list()):
            self._properties_to_browser_items[property_].remove(item)
        if not self._properties_to_browser_items.get(property_, None):
            self._properties_to_browser_items.pop(property_, None)

    # </editor-fold>

    # <editor-fold desc="--- Editors and factories ---">

    def hasEditor(self, browser_item: QtBrowserItem | None) -> bool:
        if browser_item:
            if prop := browser_item.itemProperty():
                if manager := prop.manager():
                    return BROWSERS_CONNECTIONS_REGISTRY.has_connections_in_browser(manager, self)
        return False

    def createEditor(
        self,
        property_: QtProperty[Any],
        parent: QWidget | None
    ) -> QWidget | None:
        """
        Create an editor widget for a property.

        Uses the factory registered for the property's manager to create
        an appropriate editor widget.

        :param property_: The property to create an editor for
        :param parent: The parent widget for the editor
        :return: The created editor widget, or None if no factory is registered
        """
        connection_registry = BROWSERS_CONNECTIONS_REGISTRY
        manager = property_.manager()
        if manager is None:
            return None
        factory = connection_registry.get_factory_for_browser(manager, self)
        if factory is not None:
            return factory.findEditor(property_, parent)
        return None

    def setFactoryForManager(
        self,
        manager: QtAbstractPropertyManager[Any],
        factory: QtAbstractEditorFactory[Any]
    ) -> None:
        """
        Set the editor factory for a property manager.

        Associates a factory with a manager in this browser, enabling
        automatic editor creation for properties of that manager type.

        :param manager: The property manager
        :param factory: The editor factory to use
        """
        # Check if it needs connecting
        if self._addFactory(manager, factory):
            factory.addPropertyManager(manager)
            # TODO: Manage the case when we're swapping a factory for another

    def _addFactory(
        self,
        manager: QtAbstractPropertyManager[Any],
        factory: QtAbstractEditorFactory[Any]
    ) -> bool:
        """
        Add a factory for a manager, handling existing connections.

        If a different factory was previously associated with the manager,
        it is removed first.

        :param manager: The property manager
        :param factory: The editor factory to associate
        :return: True if a new connection is needed, False if already connected
        """
        connection_registry = BROWSERS_CONNECTIONS_REGISTRY
        # If this specific factory is already linked to the manager in this
        # browser, do nothing
        if connection_registry.has_factory_in_browser(manager, self, factory):
            return False

        connection_needed = True
        # If the manager is linked to some other factory in the browser,
        # unlink that factory
        if connection_registry.has_connections_in_browser(manager, self):
            connection_needed = False
            previous_factory = connection_registry.pop_manager_factory_from_browser(
                manager,
                self
            )
            if previous_factory is not None:
                previous_factory.removePropertyManager(manager)
        connection_registry.set_factory_for_browser(manager, factory, self)

        return connection_needed

    # </editor-fold>

    # <editor-fold desc="--- Slot functions ---">

    def updateItem(self, item: QtBrowserItem) -> None:
        """
        Update the visual representation of a browser item.

        Subclasses should override this method to refresh the item's
        associated widget object when property data changes.

        :param item: The browser item to update
        """
        pass

    def onPropertyDataChanged(self, property_: QtProperty[Any]) -> None:
        """
        Handle property data changes.

        Updates all browser items representing the property to reflect
        the new data.

        :param property_: The property that changed
        """
        if not property_ in self._properties_to_browser_items:
            return
        browser_items = self._properties_to_browser_items.get(property_, list())
        for item in browser_items:
            self.updateItem(item)

    def onPropertyInserted(
        self,
        property_: QtProperty[Any],
        parent: QtProperty[Any] | None,
        after: QtProperty[Any] | None
    ) -> None:
        """
        Handle property insertion from the manager.

        Creates browser items for the newly inserted property.

        :param property_: The inserted property
        :param parent: The parent property
        :param after: The sibling the property is inserted after
        """
        # TODO: Check the logic here: If there's no grandparent?
        if not parent or not self._property_to_parents.get(parent, None):
            return
        self.createBrowserItems(property_, parent, after)
        self.insertSubTree(property_, parent)

    def onPropertyRemoved(
        self,
        property_: QtProperty[Any],
        parent: QtProperty[Any] | None
    ) -> None:
        """
        Handle property removal from the manager.

        Removes browser items for the property.

        :param property_: The removed property
        :param parent: The parent property
        """
        # TODO: Check the logic here: If there's no grandparent?
        if not parent or not self._property_to_parents.get(parent, list()):
            return
        self.removeSubTree(property_, parent)
        self.removeBrowserItems(property_, parent)

    def onPropertyDestroyed(self, property_: QtProperty[Any]) -> None:
        """
        Handle property destruction.

        Removes the property from the browser when it is destroyed.

        :param property_: The destroyed property
        """
        if not property_ in self._sub_properties:
            return
        self.removeProperty(property_)

    # </editor-fold>

    def __del__(self):
        """
        Clean up browser items on destruction.
        """
        for browser_item in self._top_level_items:
            self.clearBrowserItem(browser_item)

    def clearBrowserItem(self, item: QtBrowserItem) -> None:
        """
        Clear a browser item and all its children.

        Recursively removes all child items before clearing the item itself.

        :param item: The browser item to clear
        """
        for child in item.children()[:]:
            self.clearBrowserItem(child)
            item.removeChild(child)
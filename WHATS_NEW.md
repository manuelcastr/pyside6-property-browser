# Qt Solutions Component: Property Browser

A property browser framework enabling the user to display and edit a set of
properties.

The framework provides a browser widget that displays the given properties with
labels and corresponding editing widgets (e.g. line edits or combo boxes). 
The various types of editing widgets are provided by the framework's editor 
factories: For each property type, the framework provides a property manager 
(e.g. QtIntPropertyManager and QtStringPropertyManager) which can be associated 
with the preferred editor factory (e.g. QtSpinBoxFactory and QtLineEditFactory). 

The framework provides three ready-made implementations of the browser widget:
QtTreePropertyBrowser, QtButtonPropertyBrowser and QtGroupBoxPropertyBrowser.



# What's changed in this version

- The code has been rewritten in a more pythonic style, taking advantage of the
language's native data structures and functionalities. Extensive type 
annotations have been added to the code.

- Custom data structures (e.g. QMap, QList) have been replaced with container
types from the standard library that serve the same function.

- The original paired class design of a public classes and a private classes from 
the original code has been reworked to include all functionality into singular, 
public, classes.

- Custom editing widgets have been replaced with widgets from the Qt framework 
where possible (e.g. custom QtKeySequenceEdit replaced with a QKeySequenceEdit),
or reimplemented using Qt widgets as base classes for a simpler design with 
smaller custom code signature (e.g. QtCharEdit now inherits from QLineEdit and
adds its flavor to it.)

- The base QtProperty class has been extended and made generic on value type.
  * The function **hasValue()** now resolves directly in the QtProperty object 
  by checking the value field against **None** value.
  * QtProperty instances now allow setting/getting their value directly, but
  this behavior is not encouraged unless no validation of the value is required
  or the property has no sub properties that need updating. The manager is still
  the recommended route to set property values.
  * QtProperty instances can emit Qt signals via an internal emitter QObject. 
  This allows property objects to notify its manager if the value or attributes
  are changed. The signals are connected to similar signals in the managers and
  can work to update properties upstream (e.g. a subproperty changes and the 
  signal starts the process to update its parent property); but there's no
  downstream path if a property with sub properties has his value changed
  directly and not via the manager.

- The base manager class (QtAbstractPropertyManager) has been extended and made
generic on value type, same as QtProperty. Managers no longer inherit from the
QObject class and, like QtProperty, handle Qt signals via an internal emitter.
Although it is now possible to set property values directly on the property 
object instance, the manager's **setValue()** function is the preferred route
to ensure proper value validation and sub-property/parent-property updates.

- The base editor factory class (QtAbstractEditorFactory) has been extended and
made generic on widget type. When using custom editing widgets that follow the 
default pattern for setting/getting their values, as defined in the base editor 
factory class, it is possible to declare their factory subclasses just by 
defining the widget type parameter. Examples of this pattern are the subclasses: 
QtCharEditorFactory, QtColorEditorFactory, QtFontEditorFactory.


----
Version history:

2.1: - QtTreePropertyBrowser - tooltip of property applied to
     first column, while second column shows the value text of property
     in its tooltip
     - QtAbstractPropertyManager - initializeProperty() and
     uninitializeProperty() without const modifier now
     - QtTreePropertyBrowser and QtGroupBoxPropertyBrowser - internal
     margin set to 0
     - QtProperty - setEnabled() and isEnabled() methods added
     - QtTreePropertyBrowser - "rootIsDecorated", "indentation" and
     "headerVisible" properties added
     - QtProperty - hasValue() method added, useful for group
     properties

2.2: - FocusOut event now filtered out in case of
     Qt::ActiveWindowFocusReason reason. In that case editor is not
     closed when its sub dialog is executed
     - Removed bug in color icon generation
     - Decimals attribute added to "double" property type
     - PointF, SizeF and RectF types supported
     - Proper translation calls for tree property browser
     - QtProperty - ensure inserted subproperty is different from
     "this" property
     - QtBrowserItem class introduced, useful for identifying browser's
     gui elements
     - Possibility to control expanded state of QtTreePropertyBrowser's
     items from code
     - QtTreePropertyBrowser - "resizeMode" and "splitterPosition"
     properties added
     - QtGroupBoxPropertyBrowser - fixed crash in case of deleting the
     editor factory and then deleting the manager
     - "Decoration" example added - it shows how to add new
     responsibilities to the existing managers and editor factories

2.3: - Various bugfixes and improvements
     - QtProperty - setModified() and isModified() methods added
     - QtTreePropertyBrowser - disabling an item closes its editor
     - KeySequence, Char, Locale and Cursor types supported
     - Support for icons in enum type added
     - Kerning subproperty exposed in Font type
     - New property browser class added - QtButtonPropertyBrowser with
     drop down button as a grouping element

2.4: - Fixed memory leak of QtProperty
     - QtTreePropertyBrowser - group items are rendered better
     - QtTreePropertyBrowser - propertiesWithoutValueMarked and
     alternatingRowColors features added
     - QtTreePropertyBrowser - possibility of coloring properties added
     - QtTreePropertyBrowser - keyboard navigation improved
     - New factories providing popup dialogs added:
     QtColorEditorFactory and QtFontEditorFactory
     - Single step attribute added to: QtIntPropertyManager and
     QtDoublePropertyManager

2.5: - "Object Controller" example added. It implements a similar
     widget to the property editor in QDesigner
     - Compile with QT_NO_CURSOR
     - Expand root item with single click on the '+' icon
     - QtRectPropertyManager and QtRectFPropertyManager - by default
     constraint is null rect meaning no constraint is applied

2.6: - QtGroupPropertyBrowser - don't force the layout to show the
     whole labels' contents for read only properties, show tooltips for
     them in addition.
     - QtTreePropertyBrowser - fixed painting of the editor for color
     property type when style sheet is used (QTSOLBUG-64).
     - Make it possible to change the style of the checkboxes with a
     stylesheet (QTSOLBUG-61).
     - Change the minimum size of a combobox so that it can show at
     least one character and an icon.
     - Make it possible to properly style custom embedded editors (e.g.
     the color editor provided with the solution).
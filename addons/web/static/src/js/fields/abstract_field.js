odoo.define('web.AbstractField', function (require) {
"use strict";

/**
 * This is the basic field widget used by all the views to render a field in a view.
 * These field widgets are mostly common to all views, in particular form and list
 * views.
 *
 * The responsabilities of a field widget are mainly:
 * - render a visual representation of the current value of a field
 * - that representation is either in 'readonly' or in 'edit' mode
 * - notify the rest of the system when the field has been changed by
 *   the user (in edit mode)
 *
 * Notes
 * - the widget is not supposed to be able to switch between modes.  If another
 *   mode is required, the view will take care of instantiating another widget.
 * - notify the system when its value has changed and its mode is changed to 'readonly'
 * - notify the system when some action has to be taken, such as opening a record
 * - the Field widget should not, ever, under any circumstance, be aware of
 *   its parent.  The way it communicates changes with the rest of the system is by
 *   triggering events (with trigger_up).  These events bubble up and are interpreted
 *   by the most appropriate parent.
 *
 * Also, in some cases, it may not be practical to have the same widget for all
 * views. In that situation, you can have a 'view specific widget'.  Just register
 * the widget in the registry prefixed by the view type and a dot.  So, for example,
 * a form specific many2one widget should be registered as 'form.many2one'.
 *
 * @module web.AbstractField
 */

var field_utils = require('web.field_utils');
var ViewWidget = require('web.ViewWidget');

var AbstractField = ViewWidget.extend({
    /**
     * If this flag is set to true, the field widget will be reset on every
     * change which is made in the view (if the view supports it). This is
     * currently a form view feature.
     */
    resetOnAnyFieldChange: false,
    /**
     * If this flag is given a string, the related BasicModel will be used to
     * initialize specialData the field might need. This data will be available
     * through this.record.specialData[this.name].
     *
     * @see BasicModel._fetchSpecialData
     */
    specialData: false,
    /**
     * to override to indicate which field types are supported by the widget
     */
    supportedFieldTypes: [],

    /**
     * Abstract field class
     *
     * @constructor
     * @param {Widget} parent
     * @param {string} name The field name defined in the model
     * @param {Object} record A record object (result of the get method of
     *   a basic model)
     * @param {Object} [options]
     * @param {string} [options.mode=readonly] should be 'readonly' or 'edit'
     */
    init: function (parent, name, record, options) {
        this._super(parent, record);
        options = options || {};

        // 'name' is the field name displayed by this widget
        this.name = name;

        // the 'field' property is a description of all the various field properties,
        // such as the type, the comodel (relation), ...
        this.field = record.fields[name];

        // the 'viewType' is the type of the view in which the field widget is
        // instantiated. For standalone widgets, a 'default' viewType is set.
        this.viewType = options.viewType || 'default';

        // the 'attrs' property contains the attributes of the xml 'field' tag,
        // the inner views...
        var fieldsInfo = record.fieldsInfo[this.viewType];
        this.attrs = options.attrs || (fieldsInfo && fieldsInfo[name]) || {};

        // this property tracks the current (parsed if needed) value of the field.
        // Note that we don't use an event system anymore, using this.get('value')
        // is no longer valid.
        this.value = record.data[name];

        // recordData tracks the values for the other fields for the same record.
        // note that it is expected to be mostly a readonly property, you cannot
        // use this to try to change other fields value, this is not how it is
        // supposed to work. Also, do not use this.recordData[this.name] to get
        // the current value, this could be out of sync after a _setValue.
        this.recordData = record.data;

        // the 'string' property is a human readable (and translated) description
        // of the field. Mostly useful to be displayed in various places in the
        // UI, such as tooltips or create dialogs.
        this.string = this.attrs.string || this.field.string || this.name;

        // Widget can often be configured in the 'options' attribute in the
        // xml 'field' tag.  These options are saved (and evaled) in nodeOptions
        this.nodeOptions = this.attrs.options || {};

        // dataPointID is the id corresponding to the current record in the model.
        // Its intended use is to be able to tag any messages going upstream,
        // so the view knows which records was changed for example.
        this.dataPointID = record.id;

        // this is the res_id for the record in database.  Obviously, it is
        // readonly.  Also, when the user is creating a new record, there is
        // no res_id.  When the record will be created, the field widget will
        // be destroyed (when the form view switches to readonly mode) and a new
        // widget with a res_id in mode readonly will be created.
        this.res_id = record.res_id;

        // useful mostly to trigger rpcs on the correct model
        this.model = record.model;

        // a widget can be in two modes: 'edit' or 'readonly'.  This mode should
        // never be changed, if a view changes its mode, it will destroy and
        // recreate a new field widget.
        this.mode = options.mode || "readonly";

        // this flag tracks if the widget is in a valid state, meaning that the
        // current value represented in the DOM is a value that can be parsed
        // and saved.  For example, a float field can only use a number and not
        // a string.
        this._isValid = true;

        // this is the last value that was set by the user, unparsed.  This is
        // used to avoid setting the value twice in a row with the exact value.
        this.lastSetValue = undefined;

        // formatType is used to determine which format (and parse) functions
        // to call to format the field's value to insert into the DOM (typically
        // put into a span or an input), and to parse the value from the input
        // to send it to the server. These functions are chosen according to
        // the 'widget' attrs if is is given, and if it is a valid key, with a
        // fallback on the field type, ensuring that the value is formatted and
        // displayed according to the choosen widget, if any.
        this.formatType = this.attrs.widget in field_utils.format ?
                            this.attrs.widget :
                            this.field.type;
        // formatOptions (resp. parseOptions) is a dict of options passed to
        // calls to the format (resp. parse) function.
        this.formatOptions = {};
        this.parseOptions = {};
    },
    /**
     * When a field widget is appended to the DOM, its start method is called,
     * and will automatically call render. Most widgets should not override this.
     *
     * @returns {Deferred}
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.$el.attr('name', self.name);
            self.$el.addClass('o_field_widget');
            return self._render();
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * This function should be implemented by widgets that are not able to
     * notify their environment when their value changes (maybe because their
     * are not aware of the changes) or that may have a value in a temporary
     * state (maybe because some action should be performed to validate it
     * before notifying it). This is typically called before trying to save the
     * widget's value, so it should call _setValue() to notify the environment
     * if the value changed but was not notified.
     *
     * @abstract
     * @returns {Deferred|undefined}
     */
    commitChanges: function () {},
    /**
     * this method is used to determine if the field value is set to a meaningful
     * value.  This is useful to determine if a field should be displayed as empty
     *
     * @returns {boolean}
     */
    isSet: function () {
        return !!this.value;
    },
    /**
     * A field widget is valid if it was checked as valid the last time its
     * value was changed by the user. This is checked before saving a record, by
     * the view.
     *
     * Note: this is the responsability of the view to check that required
     * fields have a set value.
     *
     * @returns {boolean} true/false if the widget is valid
     */
    isValid: function () {
        return this._isValid;
    },
    isBlank: function () {
        return false;
    },
    /**
     * this method is supposed to be called from the outside of field widgets.
     * The typical use case is when an onchange has changed the widget value.
     * It will reset the widget to the values that could have changed, then will
     * rerender the widget.
     *
     * @param {any} record
     * @param {OdooEvent} [event] an event that triggered the reset action. It
     *   is optional, and may be used by a widget to share information from the
     *   moment a field change event is triggered to the moment a reset
     *   operation is applied.
     * @returns {Deferred} A Deferred, which resolves when the widget rendering
     *   is complete
     */
    reset: function (record, event) {
        this._reset(record, event);
        return this._render() || $.when();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Converts the value from the field to a string representation.
     *
     * @private
     * @param {any} value (from the field type)
     * @returns {string}
     */
    _formatValue: function (value) {
        var options = _.extend({}, this.nodeOptions, { data: this.recordData }, this.formatOptions);
        return field_utils.format[this.formatType](value, this.field, options);
    },
    /**
     * This method check if a value is the same as the current value of the
     * field.  For example, a fieldDate widget might want to use the moment
     * specific value isSame instead of ===.
     *
     * This method is used by the _setValue method.
     *
     * @private
     * @param {any} value
     * @returns {boolean}
     */
    _isSameValue: function (value) {
        return this.value === value;
    },
    /**
     * Converts a string representation to a valid value.
     *
     * @private
     * @param {string} value
     * @returns {any}
     */
    _parseValue: function (value) {
        return field_utils.parse[this.formatType](value, this.field, this.parseOptions);
    },
    /**
     * main rendering function.  Override this if your widget has the same render
     * for each mode.  Note that this function is supposed to be idempotent:
     * the result of calling 'render' twice is the same as calling it once.
     * Also, the user experience will be better if your rendering function is
     * synchronous.
     *
     * @private
     * @returns {Deferred|undefined}
     */
    _render: function () {
        if (this.mode === 'edit') {
            return this._renderEdit();
        } else if (this.mode === 'readonly') {
            return this._renderReadonly();
        }
    },
    /**
     * Render the widget in edit mode.  The actual implementation is left to the
     * concrete widget.
     *
     * @private
     * @returns {Deferred|undefined}
     */
    _renderEdit: function () {
    },
    /**
     * Render the widget in readonly mode.  The actual implementation is left to
     * the concrete widget.
     *
     * @private
     * @returns {Deferred|undefined}
     */
    _renderReadonly: function () {
    },
    /**
     * pure version of reset, can be overridden, called before render()
     *
     * @private
     * @param {any} record
     * @param {OdooEvent} event the event that triggered the change
     */
    _reset: function (record, event) {
        this.lastSetValue = undefined;
        this.record = record;
        this.value = record.data[this.name];
        this.recordData = record.data;
    },
    /**
     * this method is called by the widget, to change its value and to notify
     * the outside world of its new state.  This method also validates the new
     * value.  Note that this method does not rerender the widget, it should be
     * handled by the widget itself, if necessary.
     *
     * @private
     * @param {any} value
     * @param {Object} [options]
     * @param {boolean} [options.doNotSetDirty=false] if true, the basic model
     *   will not consider that this field is dirty, even though it was changed.
     *   Please do not use this flag unless you really need it.  Our only use
     *   case is currently the pad widget, which does a _setValue in the
     *   renderEdit method.
     * @param {boolean} [options.forceChange=false] if true, the change event will be
     *   triggered even if the new value is the same as the old one
     * @returns {Deferred}
     */
    _setValue: function (value, options) {
        // we try to avoid doing useless work, if the value given has not
        // changed.  Note that we compare the unparsed values.
        if (this.lastSetValue === value || (this.value === false && value === '')) {
            return $.when();
        }
        this.lastSetValue = value;
        try {
            value = this._parseValue(value);
            this._isValid = true;
        } catch (e) {
            this._isValid = false;
            return $.Deferred().reject();
        }
        if (!(options && options.forceChange) && this._isSameValue(value)) {
            return $.when();
        }
        var def = $.Deferred();
        var changes = {};
        changes[this.name] = value;
        this.trigger_up('field_changed', {
            dataPointID: this.dataPointID,
            changes: changes,
            viewType: this.viewType,
            doNotSetDirty: options && options.doNotSetDirty,
            onSuccess: def.resolve.bind(def),
            onFailure: def.reject.bind(def),
        });
        return def;
    },
    _onNavigationMove: function (ev) {
        if (ev.data.direction == "next" && this.isBlank() && this.$el.hasClass("o_required_modifier")) {
            this.$el.toggleClass('o_field_invalid', true);
            ev.data.required_error = true;
        }
        return this._super.apply(this, arguments);
    }
});

return AbstractField;

});

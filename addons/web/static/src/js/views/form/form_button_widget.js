odoo.define('web.ButtonWidget', function (require) {
"use strict";

var core = require('web.core');
var ViewWidget = require('web.ViewWidget');

var _t = core._t;
var qweb = core.qweb;

var ButtonWidget = ViewWidget.extend({
    template: 'WidgetButton',
    /**
     * Button Widget  class
     *
     * @constructor
     * @param {Widget} parent
     * @param {string} node
     * @param {Object} record A record object (result of the get method of a basic model)
     * @param {Object} [options]
     * @param {string} [options.mode=readonly] should be 'readonly' or 'edit'
     */
    init: function (parent, node, record, options) {
        this._super(parent);

        this.node = node;
        this.__node = node // To get rid of this, added because we are finding first button based on this

        // the datapoint fetched from the model
        this.record = record;

        this.string = this.node.attrs.string; // Should be on ViewWidget

        if (node.attrs.icon) {
            this.fa_icon = node.attrs.icon.indexOf('fa-') === 0;
        }
    },
    start: function() {
        var self = this;
        this._super.apply(this, arguments);
        var enterPressed = false;
        this.$el.click(function (e) {
            if (enterPressed) {
                self.trigger_up('set_last_tabindex', {target: self});
            }
            self.trigger_up('button_clicked', {
                attrs: self.node.attrs,
                record: self.record,
                callback: function(direction) {
                    self.trigger_up('navigation_move', {direction: direction || 'next'});
                }
            });
        });
        this.$el.on("keydown", function(e) {
            // Note: For setting enterPressed variable which will be helpful to set next widget or not, if mouse is used then do not set next widget focus
            e.stopPropagation();
            if (e.which === $.ui.keyCode.ENTER) {
                enterPressed = true;
            }
        });
        // TODO: To implement
        // if (this.node.attrs.help || core.debug) {
        //     this._addTooltip();
        // }
        this._addOnFocusAction();
    },
    /**
     * @override
     * @returns {jQuery} the focusable checkbox input
     */
    getFocusableElement: function() {
        return this.$el || $();
    },

    _getFocusTip: function(node) {
        var show_focus_tip = function() {
            var content = node.attrs.on_focus_tip ? node.attrs.on_focus_tip : _.str.sprintf(_t("Press ENTER to %s"), node.attrs.string);
            return content;
        }
        return show_focus_tip;
    },
    _addOnFocusAction: function() {
        var self = this;
        var options = _.extend({
            delay: { show: 1000, hide: 0 },
            trigger: 'focus',
            title: function() {
                return qweb.render('FocusTooltip', {
                    getFocusTip: self._getFocusTip(self.node)
                });
            }
        }, {});
        this.$el.tooltip(options);
    },
    _addTooltip: function(widget, $node) {
        var self = this;
        this.$el.tooltip({
            delay: { show: 1000, hide: 0 },
            title: function () {
                return qweb.render('WidgetLabel.tooltip', {
                    debug: core.debug,
                    widget: self,
                });
            }
        });
    },

    // TODO: Try to remove this whole method re-writing

    // Note: We added _onKeydowm on ViewWidget and as soon as Enter key is pressed on button it goes for next widget
    // Next button should be focused once reload is done and once lastTabindex variable is set
    // Otherwise _onNavigationMove is called before new buttons are displayed and we will not have focus on next widget properly
    _onKeydown: function (ev) {
        switch (ev.which) {
            case $.ui.keyCode.TAB:
                ev.preventDefault();
                ev.stopPropagation();
                this.trigger_up('navigation_move', {
                    direction: ev.shiftKey ? 'previous' : 'next',
                });
                break;
            case $.ui.keyCode.ENTER:
                // Do nothing, as we bind Enter key explicitly
                break;
            case $.ui.keyCode.ESCAPE:
                this.trigger_up('navigation_move', {direction: 'cancel'});
                break;
            case $.ui.keyCode.UP:
                ev.stopPropagation();
                this.trigger_up('navigation_move', {direction: 'up'});
                break;
            case $.ui.keyCode.RIGHT:
                ev.stopPropagation();
                this.trigger_up('navigation_move', {direction: 'right'});
                break;
            case $.ui.keyCode.DOWN:
                ev.stopPropagation();
                this.trigger_up('navigation_move', {direction: 'down'});
                break;
            case $.ui.keyCode.LEFT:
                ev.stopPropagation();
                this.trigger_up('navigation_move', {direction: 'left'});
                break;
        }
    },
    getFocusableElement: function() {
        return this.$el;
    }
});

return ButtonWidget;

});
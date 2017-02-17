odoo.define('hr_holidays.dashboard', function (require) {
"use strict";

/**
 * This file defines the Leaves Dashboard view (alongside its renderer, model
 * and controller), extending the Kanban view.
 * The Leaves Dashboard view is registered to the view registry.
 * A large part of this code should be extracted in an AbstractDashboard
 * widget in web, to avoid code duplication (see SalesTeamDashboard, HelpdeskDashboard).
 */

var core = require('web.core');
var KanbanController = require('web.KanbanController');
var KanbanModel = require('web.KanbanModel');
var KanbanRenderer = require('web.KanbanRenderer');
var KanbanView = require('web.KanbanView');
var view_registry = require('web.view_registry');

var QWeb = core.qweb;

var _t = core._t;
var _lt = core._lt;

var HrHolidaysDashboardRenderer = KanbanRenderer.extend({
    events: _.extend({}, KanbanRenderer.prototype.events, {
        'click .o_dashboard_action': '_onDashboardActionClicked',
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @returns {Deferred}
     */
    _render: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var values = self.state.dashboardValues;
            var hr_holidays_dashboard = QWeb.render('hr_holidays.HrHolidaysDashboard', {
                data: values,
            });
            self.$el.prepend(hr_holidays_dashboard);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent}
     */
    _onDashboardActionClicked: function (e) {
        e.preventDefault();
        var $action = $(e.currentTarget);
        this.trigger_up('dashboard_open_action', {
            action_name: $action.attr('name'),
            action_context: $action.data('context'),
        });
    },
});

var HrHolidaysDashboardModel = KanbanModel.extend({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {Deferred}
     */
    load: function () {
        return this._loadDashboard(this._super.apply(this, arguments));
    },
    /**
     * @override
     * @returns {Deferred}
     */
    reload: function () {
        return this._loadDashboard(this._super.apply(this, arguments));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Deferred} super_def a deferred that resolves with a dataPoint id
     * @returns {Deferred -> string} resolves to the dataPoint id
     */
    _loadDashboard: function (super_def) {
        var self = this;
        var dashboard_def = this._rpc({
            model: 'hr.department',
            method: 'retrieve_dashboard_data',
        });
        return $.when(super_def, dashboard_def).then(function(id, dashboardValues) {
            var dataPoint = self.localData[id];
            dataPoint.dashboardValues = dashboardValues;
            return id;
        });
    },
});

var HrHolidaysDashboardController = KanbanController.extend({
    custom_events: _.extend({}, KanbanController.prototype.custom_events, {
        dashboard_open_action: '_onDashboardOpenAction',
    }),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} e
     */
    _onDashboardOpenAction: function (e) {
        var action_name = e.data.action_name;
        var action_context = e.data.action_context;
        return this.do_action(action_name, {additional_context: action_context});
    },
});

var HrHolidaysDashboardView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Model: HrHolidaysDashboardModel,
        Renderer: HrHolidaysDashboardRenderer,
        Controller: HrHolidaysDashboardController,
    }),
    display_name: _lt('Dashboard'),
    icon: 'fa-dashboard',
    searchview_hidden: true,
});

view_registry.add('hr_holidays_dashboard', HrHolidaysDashboardView);

return {
    Model: HrHolidaysDashboardModel,
    Renderer: HrHolidaysDashboardRenderer,
    Controller: HrHolidaysDashboardController,
};

});

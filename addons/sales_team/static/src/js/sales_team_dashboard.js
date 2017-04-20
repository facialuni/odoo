odoo.define('sales_team.dashboard', function (require) {
"use strict";

/**
 * This file defines the Sales Team Dashboard view (alongside its renderer,
 * model and controller), extending the Kanban view.
 * The Sales Team Dashboard view is registered to the view registry.
 */

var core = require('web.core');
var DashboardMixins = require('web.DashboardMixins');
var field_utils = require('web.field_utils');
var KanbanController = require('web.KanbanController');
var KanbanModel = require('web.KanbanModel');
var KanbanRenderer = require('web.KanbanRenderer');
var KanbanView = require('web.KanbanView');
var session = require('web.session');
var view_registry = require('web.view_registry');

var QWeb = core.qweb;
var _t = core._t;


var SalesTeamDashboardRenderer = KanbanRenderer.extend(DashboardMixins.Renderer, {
    events: _.extend({}, KanbanRenderer.prototype.events,
                     DashboardMixins.Renderer.events),
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
            var sales_team_dashboard = QWeb.render('sales_team.SalesDashboard', {
                widget: self,
                show_demo: values && values.nb_opportunities === 0,
                values: values,
            });
            self.$el.prepend(sales_team_dashboard);
        });
    },
    /**
     * Called from the template to format the monetary value.
     *
     * @todo: use field_utils.format.monetary
     * @private
     * @returns {string} formatted value
     */
    _renderMonetaryField: function (value, currency_id) {
        var currency = session.get_currency(currency_id);
        var digits_precision = currency && currency.digits;
        value = field_utils.format.float(value || 0, {digits: digits_precision});
        if (currency) {
            if (currency.position === "after") {
                value += currency.symbol;
            } else {
                value = currency.symbol + value;
            }
        }
        return value;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @param {MouseEvent}
     */
    _onDashboardTargetClicked: function () {
        // The user is not allowed to modify the targets in demo mode
        if (!this.show_demo) {
            DashboardMixins.Renderer._onDashboardTargetClicked.apply(this, arguments);
        }
    },
});

var SalesTeamDashboardModel = KanbanModel.extend(DashboardMixins.Model, {
    /**
     * @override
     */
    init: function () {
        DashboardMixins.Model.init.apply(this, arguments);
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    get: function (localID) {
        var result = this._super.apply(this, arguments);
        return DashboardMixins.Model.get.call(this, localID, result);
    },
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
});

var SalesTeamDashboardController = KanbanController.extend(DashboardMixins.Controller, {
    custom_events: _.extend({}, KanbanController.prototype.custom_events,
        DashboardMixins.Controller.custom_events),
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @param {OdooEvent} e
     */
    _onDashboardEditTarget: function (e) {
        var targetName = e.data.target_name;
        var targetValue = e.data.target_value;
        if(isNaN(targetValue)) {
            this.do_warn(_t("Wrong value entered!"), _t("Only Integer Value should be valid."));
        } else {
            this._rpc({
                    model: 'crm.lead',
                    method: 'modify_target_sales_dashboard',
                    args: [targetName, parseInt(targetValue)],
                })
                .then(this.reload.bind(this));
        }
    },
});

var SalesTeamDashboardView = KanbanView.extend(DashboardMixins.View, {
    config: _.extend({}, KanbanView.prototype.config, {
        Controller: SalesTeamDashboardController,
        Model: SalesTeamDashboardModel,
        Renderer: SalesTeamDashboardRenderer,
    }),
    searchview_hidden: false,
});

view_registry.add('sales_team_dashboard', SalesTeamDashboardView);

return {
    Controller: SalesTeamDashboardController,
    Model: SalesTeamDashboardModel,
    Renderer: SalesTeamDashboardRenderer,
    View: SalesTeamDashboardView,
};

});

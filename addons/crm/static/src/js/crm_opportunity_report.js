odoo.define('crm.opportunity_report', function (require) {
"use strict";

var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var Widget = require('web.Widget');

var QWeb = core.qweb;

var OpportunityReport = Widget.extend(ControlPanelMixin, {
    template: 'crm.pipelineReview',

    init: function () {
        this._super.apply(this, arguments);
    },
    start: function () {
        this._super.apply(this, arguments);
        this.get_stages();
        this.start_date = '07/01/2017'
        this.end_date = '07/31/2017'
    },
    renderElement: function () {
        this._super.apply(this, arguments);
    },
    get_stages: function () {
        this.stages = [];
        var self = this;
        this._rpc({
            model: 'crm.stage',
            method: 'search_read',
        }).then(function (result) {
            _.each(result, function (stage) {
                self.stages.push(stage.name);
            })
            self.calculation();
        });
    },
    calculation: function () {
        var self = this;
        this._rpc({
            model: 'crm.lead',
            method: 'calculate_percentage',
            args: [, this.start_date, this.end_date, this.stages],
        }).then(function (result) {
            self.new_deals = result.data.new_deals;
            self.deals_left = result.data.deals_left;
            self.renderElement();
        })
    },
})

core.action_registry.add('crm_opportunity_report', OpportunityReport);
return OpportunityReport;

});
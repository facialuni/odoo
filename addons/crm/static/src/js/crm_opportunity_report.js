odoo.define('crm.opportunity_report', function (require) {
"use strict";

var ActionManager = require('web.ActionManager');
var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var datepicker = require('web.datepicker');
var Widget = require('web.Widget');
var rpc = require('web.rpc');

var QWeb = core.qweb;

var OpportunityReport = Widget.extend(ControlPanelMixin, {
    template: 'crm.pipelineReview',

    init: function (parent) {
        this.actionManager = parent;
        this._super.apply(this, arguments);
    },
    start: function () {
        this._super.apply(this, arguments);
        this.get_stages();
        this.start_date = '07/01/2017';
        this.end_date = '07/31/2017';
        this.user_id = '1';
        this.team_id = '1';
        this.$searchview_buttons = $(QWeb.render('crm.searchView'));
        this.render_searchview_buttons();
    },
    // We need this method to rerender the control panel when going back in the breadcrumb
    do_show: function() {
        this._super.apply(this, arguments);
        this.update_cp();
    },
    // Updates the control panel and render the elements that have yet to be rendered
    update_cp: function() {
        console.log("update_cp");
        var status = {
            breadcrumbs: this.actionManager.get_breadcrumbs(),
            cp_content: {$searchview_buttons: this.$searchview_buttons, $pager: this.$pager, $searchview: this.$searchview},
        };
        return this.update_control_panel(status, {clear: true});
    },
    renderElement: function () {
        this._super.apply(this, arguments);
        this.update_cp();
    },
    render_searchview_buttons: function () {
        var self = this;
        var $datetimepickers = this.$searchview_buttons.find('.js_report_datetimepicker');
        var options = { // Set the options for the datetimepickers
            locale : moment.locale(),
            format : 'L',
            icons: {
                date: "fa fa-calendar",
            },
        };
        // attach datepicker
        $datetimepickers.each(function () {
            $(this).datetimepicker(options);
            var date = new datepicker.DateWidget(options);
            date.replace($(this));
            date.$el.find('input').attr('name', $(this).find('input').attr('name'));
            if($(this).data('default-value')) {
                date.setValue(moment($(this).data('default-value')));
            }
        });
        this.$searchview_buttons.find('.js_foldable_trigger').click(function (event) {
            $(this).toggleClass('o_closed_menu o_open_menu');
            self.$searchview_buttons.find('.o_foldable_menu[data-filter="'+$(this).data('filter')+'"]').toggleClass('o_closed_menu o_open_menu');
        });
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
        rpc.query({
            model: 'crm.opportunity.history',
            method: 'calculate_moves',
            args: [null, this.start_date, this.end_date, this.stages, this.user_id, this.team_id],
        }).then(function (result) {
            self.data = result;
            self.render_graph();
            self.renderElement();
        });
    },
    render_graph: function () {
        var total_deals = this.data.lost_deals + this.data.won_deals;
        var won_percent = this.data.won_deals * 100 / total_deals;
        var lost_percent = 100 - won_percent
        var graphData = [won_percent, lost_percent];
        nv.addGraph(function() {
            var pieChart = nv.models.pieChart()
                .x(function(d) { return d; })
                .y(function(d) { return d; })
                .showLabels(true)
                .labelThreshold(0.2)
                .labelType("percent")
                .showLegend(false)
                .margin({ "left": 0, "right": 0, "top": 0, "bottom": 0 })
                .color(['#00ff00', '#ff0000']);
        var svg = d3.select(".oe_piechart").append("svg");

        svg
            .attr("height", "15em")
            .datum(graphData)
            .call(pieChart);

        nv.utils.windowResize(pieChart.update);
        return pieChart;
        });
    },
})

core.action_registry.add('crm_opportunity_report', OpportunityReport);
return OpportunityReport;

});
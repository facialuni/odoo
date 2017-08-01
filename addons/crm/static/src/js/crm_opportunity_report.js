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
        this.start_date = '07/01/2017';
        this.end_date = '07/31/2017';
        this.user_id = '1';
        this.team_id = '1';
        this.$searchview_buttons = $(QWeb.render('crm.searchView'));
        this.reload();
    },
    willStart: function () {
        return $.when(this._super.apply(this, arguments), this.get_stages());
    },
    // We need this method to rerender the control panel when going back in the breadcrumb
    do_show: function () {
        this._super.apply(this, arguments);
        this.update_cp();
    },
    // Updates the control panel and render the elements that have yet to be rendered
    update_cp: function () {
        var status = {
            breadcrumbs: this.actionManager.get_breadcrumbs(),
            cp_content: {$searchview_buttons: this.$searchview_buttons, $pager: this.$pager, $searchview: this.$searchview},
        };
        return this.update_control_panel(status, {clear: true});
    },
    reload: function () {
        this.update_cp();
        this.options = this._get_options();
        this.render_searchview_buttons();
        this.calculation();
        this.renderElement();
    },
    _get_options: function () {
        this.options = this.options || {
                    date: {filter: 'this_week'},
                    my_channel: true,
                    my_pipeline: true,
        };
        var date = new Date()
        var year = date.getFullYear();
        var month = date.getMonth();
        var date_filter = this.options.date.filter;
        if (date_filter === 'this_week') {
            var date_from = moment().startOf('week').format('MM-DD-YYYY');
            var date_to = moment().endOf('week').format('MM-DD-YYYY');
        } else if (date_filter === 'this_month') {
            var date_from = moment().startOf('month').format('MM-DD-YYYY');
            var date_to = moment().endOf('month').format('MM-DD-YYYY');
        } else if (date_filter === 'this_year') {
            var date_from = moment().startOf('year').format('MM-DD-YYYY');
            var date_to = moment().endOf('year').format('MM-DD-YYYY');
        }
        return {
            date: { start_date: date_from,
                    end_date: date_to,
                    filter: date_filter}
        };
    },
    get_stages: function () {
        this.stages = [];
        var self = this;
        return this._rpc({
                model: 'crm.stage',
                method: 'search_read',
            }).then(function (result) {
                _.each(result, function (stage) {
                    self.stages.push(stage.name);
                })
        });
    },
    calculation: function () {
        var self = this;
        rpc.query({
            model: 'crm.opportunity.history',
            method: 'calculate_moves',
            args: [null, this.options.date.start_date, this.options.date.end_date, this.stages, this.user_id, this.team_id],
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
        _.each(this.$searchview_buttons.find('.oe_crm_opportunity_report_date_filter'), function(k) {
            $(k).toggleClass('selected', self.options.date.filter === $(k).data('filter'));
        });
        this.$searchview_buttons.find('.oe_crm_opportunity_report_date_filter').click(function (event) {
            self.options.date.filter = $(this).data('filter');
            var error = false;
            if ($(this).data('filter') === 'custom') {
                var date_from = self.$searchview_buttons.find('.o_datepicker_input[name="date_from"]');
                var date_to = self.$searchview_buttons.find('.o_datepicker_input[name="date_to"]');
                if (date_from.length > 0){
                    error = date_from.val() === "" || date_to.val() === "";
                    self.options.date.date_from = new moment(date_from.val(), 'L').format('MM-DD-YYYY');
                    self.options.date.date_to = new moment(date_to.val(), 'L').format('MM-DD-YYYY');
                }
                else {
                    error = date_to.val() === "";
                    self.options.date.date = self.format_date(new moment(date_to.val(), 'L'));
                }
            }
            if (error) {
                crash_manager.show_warning({data: {message: _t('Date cannot be empty')}});
            } else {
                self.reload();
            }
        });
    },
})

core.action_registry.add('crm_opportunity_report', OpportunityReport);
return OpportunityReport;

});
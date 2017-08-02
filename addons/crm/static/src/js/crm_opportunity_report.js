odoo.define('crm.opportunity_report', function (require) {
"use strict";

var ActionManager = require('web.ActionManager');
var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var crash_manager = require('web.crash_manager');
var datepicker = require('web.datepicker');
var rpc = require('web.rpc');
var session = require('web.session');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var OpportunityReport = Widget.extend(ControlPanelMixin, {
    template: 'crm.pipelineReview',

    init: function (parent) {
        this.actionManager = parent;
        this._super.apply(this, arguments);
    },
    start: function () {
        this._super.apply(this, arguments);
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
        this.options = this._get_options();
        this.$searchview_buttons = $(QWeb.render('crm.searchView', {
            date: {start_date: this.options.date.start_date,
                   end_date: this.options.date.end_date,
                   filter: this.options.date.filter},
            stages: this.stages,
        }));
        this.parse_data();
        this.update_cp();
        this.render_searchview_buttons();
    },
    _get_options: function () {
        var options = this.options || {
                    date: {filter: 'this_week'},
                    my_channel: true,
                    my_pipeline: true,
                    stages: this.stages,
        };
        var date_filter = options.date.filter;
        if (date_filter === 'this_week') {
            options.date.start_date = moment().startOf('week').format('MM-DD-YYYY');
            options.date.end_date = moment().endOf('week').format('MM-DD-YYYY');
        } else if (date_filter === 'this_month') {
            options.date.start_date = moment().startOf('month').format('MM-DD-YYYY');
            options.date.end_date = moment().endOf('month').format('MM-DD-YYYY');
        } else if (date_filter === 'this_quarter') {
            options.date.start_date = moment().startOf('quarter').format('MM-DD-YYYY');
            options.date.end_date = moment().endOf('quarter').format('MM-DD-YYYY');
        } else if (date_filter === 'this_year') {
            options.date.start_date = moment().startOf('year').format('MM-DD-YYYY');
            options.date.end_date = moment().endOf('year').format('MM-DD-YYYY');
        }
        return options
    },
    get_stages: function () {
        this.stages = [];
        var self = this;
        return this._rpc({
                model: 'crm.stage',
                method: 'search_read',
            }).then(function (result) {
                _.each(result, function (stage) {
                    self.stages.push({id: stage.id,
                        name: stage.name});
                });
        });
    },
    parse_data: function () {
        var self = this;
        var filter = {start_date: this.options.date.start_date,
                      end_date: this.options.date.end_date}
        if (this.options.my_pipeline) {
            filter.user_id = session.uid;
        };
        if (this.options.my_channel) {
            filter.user_channel = session.uid;
        }
        var stages = _.filter(this.options.stages, function (el) { return el.selected === true });
        if (stages.length === 0){
            stages = this.stages;
        }
        return rpc.query({
            model: 'crm.opportunity.history',
            method: 'calculate_moves',
            args: [null, stages, filter],
        }).then(function (result) {
            self.data = result;
            if (self.data.lost_deals !== 0 || self.data.won_deals !== 0) {
                self.render_graph();
            }
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
        var $datetimepickers = this.$searchview_buttons.find('.oe_report_datetimepicker');
        var options = { // Set the options for the datetimepickers
            locale : moment.locale(),
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
        });
        this.$searchview_buttons.find('.js_foldable_trigger').click(function (event) {
            $(this).toggleClass('o_closed_menu o_open_menu');
            self.$searchview_buttons.find('.o_foldable_menu[data-filter="'+$(this).data('filter')+'"]').toggleClass('o_closed_menu o_open_menu');
        });
        _.each(this.$searchview_buttons.find('.oe_crm_opportunity_report_date_filter'), function(k) {
            $(k).toggleClass('selected', self.options.date.filter === $(k).data('filter'));
        });
        _.each(this.$searchview_buttons.find('.oe_crm_opportunity_report_filter_extra'), function(k) {
            $(k).toggleClass('selected', self.options[$(k).data('filter')]);
        });
        _.each(this.$searchview_buttons.find('.oe_crm_opportunity_report_stage_filter'), function(k) {
            $(k).toggleClass('selected', (_.filter(self.options[$(k).data('filter')], function(el){
                    return el.id == $(k).data('id') && el.selected === true;
                })).length > 0);
        });
        this.$searchview_buttons.find('.oe_crm_opportunity_report_date_filter').click(function (event) {
            self.options.date.filter = $(this).data('filter');
            var error = false;
            if ($(this).data('filter') === 'custom') {
                var date_from = self.$searchview_buttons.find('.o_datepicker_input[name="date_from"]');
                var date_to = self.$searchview_buttons.find('.o_datepicker_input[name="date_to"]');
                if (date_from.length > 0){
                    error = date_from.val() === "" || date_to.val() === "";
                    self.options.date.start_date = new moment(date_from.val(), 'L').format('MM-DD-YYYY');
                    self.options.date.end_date = new moment(date_to.val(), 'L').format('MM-DD-YYYY');
                }
                else {
                    error = date_to.val() === "";
                }
            }
            if (error) {
                crash_manager.show_warning({data: {message: _t('Date cannot be empty')}});
            } else {
                self.reload();
            }
        });
        this.$searchview_buttons.find('.oe_crm_opportunity_report_filter_extra').click(function (event) {
            var option_value = $(this).data('filter');
            self.options[option_value] = !self.options[option_value];
            self.reload();
        });
        this.$searchview_buttons.find('.oe_crm_opportunity_report_stage_filter').click(function (event) {
            var option_value = $(this).data('filter');
            var option_id = $(this).data('id');
            _.filter(self.options[option_value], function(el) {
                if (el.id == option_id){
                    if (el.selected === undefined || el.selected === null){el.selected = false;}
                    el.selected = !el.selected;
                }
                return el;
            });
            self.reload();
        });

    },
})

core.action_registry.add('crm_opportunity_report', OpportunityReport);
return OpportunityReport;

});
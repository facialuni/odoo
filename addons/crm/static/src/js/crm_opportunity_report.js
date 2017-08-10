odoo.define('crm.opportunity_report', function (require) {
"use strict";

var ActionManager = require('web.ActionManager');
var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var crashManager = require('web.crash_manager');
var datepicker = require('web.datepicker');
var rpc = require('web.rpc');
var session = require('web.session');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var OpportunityReport = Widget.extend(ControlPanelMixin, {
    template: 'crm.pipelineReview',
    /**
     * @override
     * @constructor
    **/
    init: function (parent, params) {
        this.actionManager = parent;
        this.active_id = params.context.active_id;
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    willStart: function () {
        return $.when(this._super.apply(this, arguments), this._getInitiatValues());
    },
    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments);
        this.reload();
    },
    // We need this method to rerender the control panel when going back in the breadcrumb
    /**
     * @override
     */
    do_show: function () {
        this._super.apply(this, arguments);
        this.update_cp();
    },
    // Updates the control panel and render the elements that have yet to be rendered
    /**
     * @override
     */
    update_cp: function () {
        var status = {
            breadcrumbs: this.actionManager.get_breadcrumbs(),
            cp_content: {$searchview_buttons: this.$searchview_buttons, $pager: this.$pager, $searchview: this.$searchview},
        };
        return this.update_control_panel(status, {clear: true});
    },
    reload: function () {
        this.options = this._getOptions();
        this.$searchview_buttons = $(QWeb.render('crm.searchView', {options: this.options,
            users: this.users,
            salesTeam: this.salesTeam}));
        this._parseData();
        this.update_cp();
        this._renderSearchviewButtons();
    },
    /**
     * @private
     */
    _getInitiatValues: function () {
        this.stages = [];
        var self = this;
        return this._rpc({
                model: 'crm.opportunity.history',
                method: 'get_value',
                args: [null],
            }).then(function (result) {
                self.stages = result.stages;
                self.users = result.users;
                self.salesTeam = result.sales_team;
        });
    },
    /**
     * @private
     */
    _getOptions: function () {
        var options = this.options || {
                    date: {filter: 'this_week'},
                    my_channel: this.active_id ? false : true,
                    my_pipeline: this.active_id ? false : true,
                    stages: this.stages,
                    salesTeam: this.active_id ? [this.active_id] : []
        };

        var dateFilter = options.date.filter;
        if (dateFilter === 'this_week') {
            options.date.start_date = moment().startOf('week').format('MM-DD-YYYY');
            options.date.end_date = moment().endOf('week').format('MM-DD-YYYY');
        } else if (dateFilter === 'this_month') {
            options.date.start_date = moment().startOf('month').format('MM-DD-YYYY');
            options.date.end_date = moment().endOf('month').format('MM-DD-YYYY');
        } else if (dateFilter === 'this_quarter') {
            options.date.start_date = moment().startOf('quarter').format('MM-DD-YYYY');
            options.date.end_date = moment().endOf('quarter').format('MM-DD-YYYY');
        } else if (dateFilter === 'this_year') {
            options.date.start_date = moment().startOf('year').format('MM-DD-YYYY');
            options.date.end_date = moment().endOf('year').format('MM-DD-YYYY');
        }
        return options
    },
    /**
     * @private
     */
    _parseData: function () {
        var self = this;
        var filter = {start_date: this.options.date.start_date,
                      end_date: this.options.date.end_date,
                      users: this.options.users,
                      teams: this.options.salesTeam}
        if (this.options.my_pipeline) {
            filter.user_id = session.uid;
        };
        if (this.options.my_channel) {
            filter.user_channel = session.uid;
        };
        var stages = _.filter(this.options.stages, function (el) { return el.selected === true });
        if (stages.length === 0){
            stages = this.stages;
        };
        return rpc.query({
            model: 'crm.opportunity.history',
            method: 'action_pipeline_analysis',
            args: [null, stages, filter],
        }).then(function (result) {
            self.data = result;
            self.renderElement();
            if (self.data.lost_deals !== 0 || self.data.won_deals !== 0) {
                self._renderGraph();
            };
            if (self.data.expected_revenues.length > 0) {
                self._renderFunnelchart();
            };
        });
    },
    /**
     * @private
     */
    _renderFunnelchart: function () {
        var funnelchart = new FunnelChart({
                        data: this.data.expected_revenues,
                        height: 350,
                        width: 300,
                        bottomPct: 1/8
                    });
        funnelchart.draw('.o_funnelchart');
    },
    /**
     * @private
     */
    _renderGraph: function () {
        var totalDeals = this.data.lost_deals + this.data.won_deals;
        var wonPercent = this.data.won_deals * 100 / totalDeals;
        var lostPercent = 100 - wonPercent
        var graphData = [wonPercent, lostPercent];
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
        var svg = d3.select(".o_piechart").append("svg");

        svg
            .attr("height", "15em")
            .datum(graphData)
            .call(pieChart);

        nv.utils.windowResize(pieChart.update);
        return pieChart;
        });
    },
    /**
     * @private
     */
    _renderSearchviewButtons: function () {
        var self = this;
        var $datetimepickers = this.$searchview_buttons.find('.o_report_datetimepicker');
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
        // add select2 for multiple filter on salesmen and sales channel
        this.$searchview_buttons.find('.o_auto_complete').select2();
        // fold all menu
        this.$searchview_buttons.find('.js_foldable_trigger').click(function (event) {
            $(this).toggleClass('o_closed_menu o_open_menu');
            self.$searchview_buttons.find('.o_foldable_menu[data-filter="'+$(this).data('filter')+'"]').toggleClass('o_closed_menu o_open_menu');
        });
        _.each(this.$searchview_buttons.find('.o_crm_opportunity_report_date_filter'), function(k) {
            $(k).toggleClass('selected', self.options.date.filter === $(k).data('filter'));
        });
        _.each(this.$searchview_buttons.find('.o_crm_opportunity_report_filter_extra'), function(k) {
            $(k).toggleClass('selected', self.options[$(k).data('filter')]);
        });
        _.each(this.$searchview_buttons.find('.o_crm_opportunity_report_stage_filter'), function(k) {
            $(k).toggleClass('selected', (_.filter(self.options[$(k).data('filter')], function(el){
                    return el.id == $(k).data('id') && el.selected === true;
                })).length > 0);
        });

        // click events for filter
        this.$searchview_buttons.find('.o_crm_opportunity_report_date_filter').click(function (event) {
            self.options.date.filter = $(this).data('filter');
            var error = false;
            if ($(this).data('filter') === 'custom') {
                var dateFrom = self.$searchview_buttons.find('.o_datepicker_input[name="date_from"]');
                var dateTo = self.$searchview_buttons.find('.o_datepicker_input[name="date_to"]');
                if (dateFrom.length > 0){
                    error = dateFrom.val() === "" || dateTo.val() === "";
                    self.options.date.start_date = new moment(dateFrom.val(), 'L').format('MM-DD-YYYY');
                    self.options.date.end_date = new moment(dateTo.val(), 'L').format('MM-DD-YYYY');
                }
                else {
                    error = dateTo.val() === "";
                }
            }
            if (error) {
                crashManager.show_warning({data: {message: _t('Date cannot be empty')}});
            } else {
                self.reload();
            }
        });
        this.$searchview_buttons.find('.o_crm_opportunity_report_filter_extra').click(function (event) {
            var optionValue = $(this).data('filter');
            self.options[optionValue] = !self.options[optionValue];
            self.reload();
        });
        this.$searchview_buttons.find('.o_crm_opportunity_report_stage_filter').click(function (event) {
            var optionValue = $(this).data('filter');
            var optionId = $(this).data('id');
            _.filter(self.options[optionValue], function(el) {
                if (el.id == optionId){
                    if (el.selected === undefined || el.selected === null){el.selected = false;}
                    el.selected = !el.selected;
                }
                return el;
            });
            self.reload();
        });
        // custom filter on salesmen and sales channels
        self.$searchview_buttons.find('[data-filter="salesmen"]').select2("val", self.options.users);
        self.$searchview_buttons.find('[data-filter="sales_channel"]').select2("val", self.options.salesTeam);
        this.$searchview_buttons.find('.o_opportunity_button_custom').click(function(event) {
            var users = self.$searchview_buttons.find('[data-filter="salesmen"]').val();
            self.options.users = _.map(users, function(num){ return parseInt(num)})
            var salesTeam = self.$searchview_buttons.find('[data-filter="sales_channel"]').val();
            self.options.salesTeam = _.map(salesTeam, function(num){ return parseInt(num)})
            self.reload();
        });

    },
});

core.action_registry.add('crm_opportunity_report', OpportunityReport);
return OpportunityReport;

});
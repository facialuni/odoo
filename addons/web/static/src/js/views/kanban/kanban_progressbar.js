odoo.define('kanban.progressBar', function (require) {
"use strict";

var Widget = require('web.Widget');
var session = require('web.session');


var ColumnProgressBar =  Widget.extend({
    template: 'KanbanView.ProgressBar',
    events: {
        'click .progress-bar': function (e) {
            $('.o_content').scrollTop(0);
            this.clicked_bar = $(e.currentTarget);
            var state = this.clicked_bar.data('state');
            this.animateTotal(state, false);
        }
    },
    init: function (parent, barOptions, fieldsInfo, header) {
        this._super.apply(this, arguments);
        this.sum_field = barOptions.attrs.sum;
        this.fieldName = barOptions.attrs.field;
        this.colors = JSON.parse(barOptions.attrs.colors);
        this.currency_prefix = "";
        this.currency_suffix = "";
        this.is_monetary = false;
        this.$header = header;

        if (this.sum_field && fieldsInfo[this.sum_field]['widget'] == 'monetary') {
            this.is_monetary = true;
            this.findCurrency();
        }
    },
    animateTotal: function (state, is_reverse) {
        var is_toggle = this.$kanban_group.is('.o_kanban_group_show_'+this.colors[state]);
        is_toggle = is_reverse ? !is_toggle : is_toggle;
        this.removeAllClass(this.$kanban_group);
        if(is_toggle ){
            var sum = _.reduce(this.result, function(sum, data){ return sum + data.val || 0;}, 0)
            this._animateNumber(sum, this.$side_c, 1000, this.currency_prefix, this.remaining > 0 ? this.currency_prefix+"+":this.currency_suffix);
        } else {
            this._animateNumber(this.result[state].val, this.$side_c, 1000, this.currency_prefix, this.remaining > 0 ? this.currency_prefix+"+":this.currency_suffix);
            this.$kanban_group.toggleClass('o_kanban_group_show_'+this.colors[state]).toggleClass('o_kanban_group_show');
            this.$kanban_group.data('state', state);
        }
        if (!is_reverse) {
            this.clicked_bar.toggleClass('active progress-bar-striped').siblings().removeClass('active progress-bar-striped');
        }
    },
    removeAllClass: function($el) {
        _.each(this.colors, function(val,key){
            $el.removeClass('o_kanban_group_show_'+val);
        })
        $el.removeClass('o_kanban_group_show');
    },
    findCurrency: function () {
        this.trigger_up('setProgressCounter');
        if (this.is_monetary) {
            if (session.currencies[session.active_currency_id].position === 'before') {
                this.currency_prefix = session.currencies[session.active_currency_id].symbol + " ";
            } else {
                this.currency_suffix = " " + session.currencies[session.active_currency_id].symbol;
            }
        }
    },
    sideCounter: function (records) {
        this.result = {};
        var self = this;

        $(records).each(function () {
            var group_field = this.state.data[self.fieldName];
            if (!self.result.hasOwnProperty(group_field)) {
                self.result[group_field] = {
                    val: 0,
                    count: 0
                };
            }
            var data = self.result[group_field];
            if (self.sum_field) {
                data.val += this.state.data[self.sum_field];
            } else {
                data.val += 1;
            }
            data.count += 1;
            if(self.colors[group_field]){
                this.$el.addClass('oe_kanban_card_'+ self.colors[group_field]);
            }
        });

        this.animateTotal(this.$kanban_group.data('state'), true);
        var sum_count = _.reduce(self.result, function(sum, data){ return sum + data.count;}, 0)
        var self = this;
        _.each(this.colors, function (val, key) {
            var data_temp_val = self['bar_n_'+val];
            var $data_temp_model = self['$bar_'+val];
            data_temp_val = self.result[key] ? self.result[key].count : 0;
            if ($data_temp_model.length) {
                if (data_temp_val  === 0 && self.$kanban_group.hasClass('o_kanban_group_show_'+val)) {
                    self.removeAllClass(self.$kanban_group);
                } 
                data_temp_val > 0 ? $data_temp_model.width((data_temp_val / sum_count) * 100 + "%").addClass('o_bar_active') : $data_temp_model.width(0).removeClass('o_bar_active');
            }
        });
    },
    _animateNumber: function (end, $el, duration, prefix, suffix) {
        suffix = suffix || "";
        prefix = prefix || "";
        var start = session.total_counter_value[session.active_column];
        this.trigger_up('setProgressCounter', { value: end });

        if (end > 1000000) {
            end = end / 1000000;
            suffix = "M " + suffix;
        }
        else if (end > 1000) {
            end = end / 1000;
            suffix = "K " + suffix;
        }
        if (start > 1000000) {
            start = start / 1000000;
        }
        else if (start > 1000) {
            start = start / 1000;
        }

        var progress_bar_length = (90 - (2.8)*parseInt(end).toString().length).toString() + '%';
        this.$('.o_kanban_counter_progress').animate({width: progress_bar_length}, 300);
        if (end > start) {
            $({ someValue: start}).animate({ someValue: end || 0 }, {
                duration: duration,
                easing: 'swing',
                step: function () {
                    $el.html(prefix + Math.round(this.someValue) + suffix);
                },
                complete: function () {
                    $el.removeClass('o-kanban-grow');
                }
            });

            //for sync between Grow effect and Number Swing Effect
            setTimeout(function (){
                $el.addClass('o-kanban-grow');
            },200)
        } else {
            $el.html(prefix + Math.round(end || 0) + suffix);
        }
    },
    _barAttrs: function () {
        var self = this;
        _.each(this.result, function (val, key) {
            var data_temp_val = self['bar_n_'+self.colors[key]];
            var $data_temp_model = self['$bar_'+self.colors[key]];
            data_temp_val = self.result[key].count;
            if ($data_temp_model) {
                $data_temp_model.attr({
                    'data-original-title': data_temp_val + ' '+key,
                    'data-state': key
                });
                $data_temp_model.tooltip({
                    delay: '0',
                    trigger:'hover',
                    placement: 'top'
                });
            }
        });
    },
    _fixBarPosition: function ($el) {
        $el.affix({
            offset: {
                top: function () {
                    return 2;
                }
            },
            target: $('.o_content'),
        });
    },
    _update: function (records, remaining) {
        this.$kanban_group = this.$el.closest('.o_kanban_group');
        this.$side_c = this.$('.o_kanban_counter_side');
        this.$counter = this.$('.o_kanban_counter_progress');
        var self = this;
        $('<div/>',{class: 'o_progressBar_ghost'}).insertAfter(this.$el);

        _.each(this.colors, function (val, key) {
            if (self.$('.o_progress_'+val).length) {
                var $div_color = self.$('.o_progress_'+val);
            } else {
                var $div_color = $('<div/>');
                $div_color.addClass('progress-bar o_progress_'+val);
                self.$('.o_kanban_counter_progress').append($div_color);
            }
            self['$bar_'+val] = $div_color;
            self['bar_n_'+val] = 0;
        });

        this.remaining = remaining;
        this.records = records;
        this.trigger_up('setProgressCounter');
        var self = this;

        // In xml template data-delay of 500 ms is given so to work affixBar properly
        // we require to apply time delay of 500 ms.
        setTimeout(function(){
            self._fixBarPosition(self.$header);
            self._fixBarPosition(self.$el);
        }, 500);
        this.sideCounter(this.records);
        this._barAttrs();
        this.removeAllClass(this.$el);
    },
});


return {
    ColumnProgressBar: ColumnProgressBar,
}

});

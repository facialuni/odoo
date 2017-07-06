odoo.define('web.KanbanColumn', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var Dialog = require('web.Dialog');
var kanban_quick_create = require('web.kanban_quick_create');
var KanbanRecord = require('web.KanbanRecord');
var view_dialogs = require('web.view_dialogs');
var Widget = require('web.Widget');

var _t = core._t;
var QWeb = core.qweb;
var RecordQuickCreate = kanban_quick_create.RecordQuickCreate;

var KanbanColumn = Widget.extend({
    template: 'KanbanView.Group',
    custom_events: {
        cancel_quick_create: '_onCancelQuickCreate',
        kanban_record_delete: '_onDeleteRecord',
        quick_create_add_record: '_onQuickCreateAddRecord',
    },
    events: {
        'click .o_column_edit': '_onEditColumn',
        'click .o_column_delete': '_onDeleteColumn',
        'click .o_column_archive': '_onArchiveRecords',
        'click .o_column_unarchive': '_onUnarchiveRecords',
        'click .o_kanban_quick_add': '_onAddQuickCreate',
        'click .o_kanban_load_more': '_onLoadMore',
        'click .o_kanban_toggle_fold': '_onToggleFold',
        'record_update' : '_updateCounter',
    },
    /**
     * @override
     */
    init: function (parent, data, options, recordOptions) {
        this._super(parent);
        this.db_id = data.id;
        this.data_records = data.data;
        this.data = data;

        var value = data.value;
        this.id = data.res_id || value;
        this.folded = !data.isOpen;
        this.has_active_field = 'active' in data.fields;
        this.size = data.count;
        this.fields = data.fields;
        this.records = [];
        this.modelName = data.model;

        this.quick_create = options.quick_create;
        this.grouped_by_m2o = options.grouped_by_m2o;
        this.editable = options.editable;
        this.deletable = options.deletable;
        this.draggable = recordOptions.draggable;
        this.records_editable = options.records_editable;
        this.records_deletable = options.records_deletable;
        this.relation = options.relation;
        this.offset = 0;
        this.remaining = this.size - this.data_records.length;

        this.record_options = _.clone(recordOptions);

        if (options.grouped_by_m2o) {
            // For many2one, a false value means that the field is not set.
            this.title = value ? value : _t('Undefined');
        } else {
            // False and 0 might be valid values for these fields.
            this.title = value === undefined ? _t('Undefined') : value;
        }

        if (options.group_by_tooltip) {
            this.tooltipInfo = _.map(options.group_by_tooltip, function (help, field) {
                return (data.tooltipData && data.tooltipData[field] && "<div>" + help + "<br>" + data.tooltipData[field] + "</div>") || '';
            }).join('');
        } else {
            this.tooltipInfo = "";
        }
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        this.$header = this.$('.o_kanban_header');
        this.$counter = this.$('.o_kamban_counter');

        for (var i = 0; i < this.data_records.length; i++) {
            this.addRecord(this.data_records[i], {no_update: true});
        }
        this.$header.tooltip();

        if (config.device.size_class > config.device.SIZES.XS && this.draggable !== false) {
            // deactivate sortable in mobile mode.  It does not work anyway,
            // and it breaks horizontal scrolling in kanban views.  Someday, we
            // should find a way to use the touch events to make sortable work.
            this.$el.sortable({
                connectWith: '.o_kanban_group',
                revert: 0,
                delay: 0,
                items: '> .o_kanban_record:not(.o_updating)',
                helper: 'clone',
                cursor: 'move',
                over: function () {
                    self.$el.addClass('o_kanban_hover');
                    self._update();
                },
                out: function () {
                    self.$el.removeClass('o_kanban_hover');
                },
                update: function (event, ui) {
                    var record = ui.item.data('record');
                    var index = self.records.indexOf(record);
                    record.$el.removeAttr('style');  // jqueryui sortable add display:block inline
                    ui.item.addClass('o_updating');
                    if (index >= 0) {
                        if ($.contains(self.$el[0], record.$el[0])) {
                            // resequencing records
                            self.trigger_up('kanban_column_resequence', {ids: self._getIDs()});
                        }
                    } else {
                        // adding record to this column
                        self.trigger_up('kanban_column_add_record', {record: record, ids: self._getIDs()});
                    }
                }
            });
        }
        this.$el.click(function (event) {
            if (self.folded) {
                self._onToggleFold(event);
            }
        });
        this._update();

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Adds the quick create record to the top of the column.
     */
    addQuickCreate: function () {
        if (this.quickCreateWidget) {
            return;
        }
        var self = this;
        var width = this.records.length ? this.records[0].$el.innerWidth() : this.$el.width() - 8;
        this.quickCreateWidget = new RecordQuickCreate(this, width);
        this.quickCreateWidget.insertAfter(this.$header);
        this.quickCreateWidget.insertAfter(this.$counter);
        this.quickCreateWidget.$el.focusout(function () {
            var taskName = self.quickCreateWidget.$('[type=text]')[0].value;
            if (!taskName && self.quickCreateWidget) {
                self._cancelQuickCreate();
            }
        });
    },
    /**
     * Adds a record in the column.
     *
     * @param {Object} recordState
     * @param {Object} options
     * @params {string} options.position 'before' to add the record at the top,
     *                  added at the bottom by default
     * @params {Boolean} options.no_update set to true not to update the column
     */
    addRecord: function (recordState, options) {
        var record = new KanbanRecord(this, recordState, this.record_options);
        this.records.push(record);
        if (options.position === 'before') {
            record.insertAfter(this.quickCreateWidget ? this.quickCreateWidget.$el : this.$header);
        } else {
            var $load_more = this.$('.o_kanban_load_more');
            if ($load_more.length) {
                record.insertBefore($load_more);
            } else {
                record.appendTo(this.$el);
            }
        }
        if (!options.no_update) {
            this._update();
        }
    },
    /**
     * @returns {Boolean} true iff the column is empty
     */
    isEmpty: function () {
        return !this.records.length;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Destroys the QuickCreate widget.
     *
     * @private
     */
    _cancelQuickCreate: function () {
        this.quickCreateWidget.destroy();
        this.quickCreateWidget = undefined;
    },
    /**
     * @returns {integer[]} the res_ids of the records in the column
     */
    _getIDs: function () {
        var ids = [];
        this.$('.o_kanban_record').each(function (index, r) {
            ids.push($(r).data('record').id);
        });
        return ids;
    },
    /**
     * @private
     */
    _update: function () {
        var self = this;
        var title = this.folded ? this.title + ' (' + this.size + ')' : this.title;
        this.$header.find('.o_column_title').text(title);
        this.$header.find('.o-kanban-count').text(this.records.length);

        this.$el.toggleClass('o_column_folded', this.folded);
        var tooltip = this.size + _t(' records');
        tooltip = '<p>' + tooltip + '</p>' + this.tooltipInfo;
        this.$header.tooltip({html: true}).attr('data-original-title', tooltip);
        if (!this.remaining) {
            this.$('.o_kanban_load_more').remove();
        } else {
            this.$('.o_kanban_load_more').html(QWeb.render('KanbanView.LoadMore', {widget: this}));
        }
        if (!this.folded) {
            self._updateCounter();
        }
    },
    _updateCounter: function() {
        var self = this;
        var $counter = this.$('.o_kamban_counter');
        var $label = $counter.find('.o_kamban_counter_label');
        var $side_c = $counter.find('.o_kamban_counter_side');
        var $bar_success = $counter.find('.o_progress_success');
        var $bar_blocked = $counter.find('.o_progress_blocked');
        var $bar_warning = $counter.find('.o_progress_warning');

        var bar_n_success = 0;
        var bar_n_blocked = 0;
        var bar_n_warning = 0;
        var tot_n = parseInt($side_c.text()) || this.records.length;
        $side_c.data('current-value', tot_n);

        switch (self.relation) {
            case "project.task.type":
                $(self.records).each(function() {
                    if (this.state.data.kanban_state == "done") {
                        bar_n_success++;
                        this.$el.removeClass('oe_kanban_card_blocked');
                        this.$el.addClass('oe_kanban_card_success');
                    } else if (this.state.data.kanban_state == "blocked") {
                        bar_n_blocked++;
                        this.$el.removeClass('oe_kanban_card_success');
                        this.$el.addClass('oe_kanban_card_blocked');
                    }
                });


                self._animateNumber(tot_n, $side_c, 1000);
                if (bar_n_success == 0 && bar_n_blocked > 0) {
                    // Use blocked as label in this particular condition only
                    self._animateNumber(bar_n_blocked, $label, 1000, "", " blocked");
                } else {
                    self._animateNumber(bar_n_success, $label, 1000, "", " ready");
                }


                bar_n_success > 0 ? $bar_success.width((bar_n_success / tot_n) * 100 + "%").addClass('o_bar_active') : $bar_success.width(0).removeClass('o_bar_active');
                bar_n_blocked > 0 ? $bar_blocked.width((bar_n_blocked / tot_n) * 100 + "%").addClass('o_bar_active') : $bar_blocked.width(0).removeClass('o_bar_active');

                $bar_success.add($bar_blocked).css('cursor', 'pointer');

                $bar_success.attr('title', bar_n_success + ' ready');
                $bar_blocked.attr('title', bar_n_blocked + ' blocked');

                $bar_success.add($bar_blocked).tooltip({
                    delay: '0',
                    trigger:'hover',
                    placement: 'top'
                });

                // TODO: Unbind if bars are empty
                $bar_success.on('click', function() {
                    $('.o_content').scrollTop(0);
                    self.$el.removeClass('o_kanban_group_show_blocked');
                    self.$el.toggleClass('o_kanban_group_show_success');
                    return false;
                });
                $bar_blocked.on('click', function() {
                    $('.o_content').scrollTop(0);
                    self.$el.removeClass('o_kanban_group_show_success');
                    self.$el.toggleClass('o_kanban_group_show_blocked');
                    return false;
                });
                break;

            case "crm.stage":
                // TODO: It should automatically retrive the right symbol
                var currency = "$ ";
                var tot_value = parseInt($side_c.text()) || 0;

                tot_n = 0;

                $counter.addClass('o_counter_number');

                // Reorder bars to match CRM needs
                $bar_warning.insertBefore($bar_success);
                $bar_blocked.insertBefore($bar_warning);


                $(self.records).each(function() {
                    var state = this.state.data.activity_state;

                    tot_value = tot_value + this.record.planned_revenue.raw_value;
                    tot_n++;

                    if (state == "planned") {
                        bar_n_success++;
                        this.$el.removeClass('oe_kanban_card_blocked oe_kanban_card_warning');
                        this.$el.addClass('oe_kanban_card_success');
                    } else if (state == "today") {
                        bar_n_warning++;
                        this.$el.removeClass('oe_kanban_card_success oe_kanban_card_blocked');
                        this.$el.addClass('oe_kanban_card_warning');
                    } else if (state == "overdue") {
                        bar_n_blocked++;
                        this.$el.removeClass('oe_kanban_card_success oe_kanban_card_warning');
                        this.$el.addClass('oe_kanban_card_blocked');
                    }
                });

                self._animateNumber(tot_value, $side_c, 1000, currency);

                $bar_success.attr('title', bar_n_success + ' future activities');
                $bar_blocked.attr('title', bar_n_blocked + ' overdue activities');
                $bar_warning.attr('title', bar_n_warning + ' today activities');

                $bar_success.add($bar_blocked).add($bar_warning).tooltip({
                    delay: '0',
                    trigger:'hover',
                    placement: 'top'
                });

                bar_n_success > 0 ? $bar_success.width((bar_n_success / tot_n) * 100 + "%").addClass('o_bar_active') : $bar_success.width(0).removeClass('o_bar_active');
                bar_n_blocked > 0 ? $bar_blocked.width((bar_n_blocked / tot_n) * 100 + "%").addClass('o_bar_active') : $bar_blocked.width(0).removeClass('o_bar_active');
                bar_n_warning > 0 ? $bar_warning.width((bar_n_warning / tot_n) * 100 + "%").addClass('o_bar_active') : $bar_warning.width(0).removeClass('o_bar_active');

                self.$el.removeClass('o_kanban_group_show_blocked o_kanban_group_show_success o_kanban_group_show_warning');

                // TODO: Unbind if bars are empty
                $bar_success.on('click', function() {
                    $('.o_content').scrollTop(0);
                    self.$el.removeClass('o_kanban_group_show_blocked o_kanban_group_show_warning');
                    self.$el.toggleClass('o_kanban_group_show_success');
                    return false;
                });
                $bar_warning.on('click', function() {
                    $('.o_content').scrollTop(0);
                    self.$el.removeClass('o_kanban_group_show_blocked o_kanban_group_show_success');
                    self.$el.toggleClass('o_kanban_group_show_warning');
                    return false;
                });
                $bar_blocked.on('click', function() {
                    $('.o_content').scrollTop(0);
                    self.$el.removeClass('o_kanban_group_show_success o_kanban_group_show_warning');
                    self.$el.toggleClass('o_kanban_group_show_blocked');
                    return false;
                });
                break;

            default:
                console.info("kanban_counter layout for " + self.relation + " not definied");
        }
    },

    _animateNumber: function (end, $el, duration, prefix, suffix, bold_value) {
        suffix = suffix || "";
        prefix = prefix || "";
        bold_value = bold_value || false;

        // Retrive current value (buggy)
        var start = $el.data('current-value') || 0;

        if (end > 100) {
            end = end / 100;
            suffix = "K " + suffix;
        }

        $({ someValue: start }).animate({ someValue: end }, {
            duration: duration,
            easing: 'swing',
            step: function() {
                if (bold_value) {
                    $el.html(prefix + "<b>" + Math.round(this.someValue) + "</b>" + suffix);
                } else {
                    $el.html(prefix + Math.round(this.someValue) + suffix);
                }
            },
            complete: function() {
                // Apply new current value
                $el.data('current-value', end);
            }
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAddQuickCreate: function () {
        this.addQuickCreate();
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onArchiveRecords: function (event) {
        event.preventDefault();
        this.trigger_up('kanban_column_archive_records', {archive: true});
    },
    /**
     * @private
     */
    _onCancelQuickCreate: function () {
        this._cancelQuickCreate();
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onDeleteColumn: function (event) {
        event.preventDefault();
        var buttons = [
            {
                text: _t("Ok"),
                classes: 'btn-primary',
                close: true,
                click: this.trigger_up.bind(this, 'kanban_column_delete'),
            },
            {text: _t("Cancel"), close: true}
        ];
        new Dialog(this, {
            size: 'medium',
            buttons: buttons,
            $content: $('<div>', {
                text: _t("Are you sure that you want to remove this column ?")
            }),
        }).open();
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onDeleteRecord: function (event) {
        var self = this;
        event.data.parent_id = this.db_id;
        event.data.after = function cleanup() {
            var index = self.records.indexOf(event.data.record);
            self.records.splice(index, 1);
            self._update();
        };
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onEditColumn: function (event) {
        event.preventDefault();
        new view_dialogs.FormViewDialog(this, {
            res_model: this.relation,
            res_id: this.id,
            title: _t("Edit Column"),
            on_saved: this.trigger_up.bind(this, 'reload'),
        }).open();
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onLoadMore: function (event) {
        event.preventDefault();
        this.trigger_up('kanban_load_more');
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onQuickCreateAddRecord: function (event) {
        this.trigger_up('quick_create_record', event.data);
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onToggleFold: function (event) {
        event.preventDefault();
        this.trigger_up('column_toggle_fold');
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onUnarchiveRecords: function (event) {
        event.preventDefault();
        this.trigger_up('kanban_column_archive_records', {archive: false});
    },
});

return KanbanColumn;

});

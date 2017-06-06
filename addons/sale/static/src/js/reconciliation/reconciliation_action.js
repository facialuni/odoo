odoo.define('sale.ReconciliationClientAction', function (require) {
"use strict";

var ReconciliationClientAction = require('account.ReconciliationClientAction');
var core = require('web.core');
var fieldUtils = require('web.field_utils');
var Dialog = require('web.view_dialogs');

var _t = core._t;
var saleOrderSelectViewId;
var saleOrderSearchViewId;


ReconciliationClientAction.StatementAction.include({
    custom_events: _.extend({}, ReconciliationClientAction.StatementAction.prototype.custom_events, {
        reconcile_with_sale_order: '_onReconcileWithSaleOrder',
    }),

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        if (!saleOrderSelectViewId) {
            this._rpc({
                model: 'ir.model.data',
                method: 'xmlid_to_res_id',
                kwargs: {xmlid: 'sale.view_sales_order_reconciliation_tree'},
            }).then(function (id) {
                saleOrderSelectViewId = id;
            });
            this._rpc({
                model: 'ir.model.data',
                method: 'xmlid_to_res_id',
                kwargs: {xmlid: 'sale.view_sales_order_reconciliation_filter'},
            }).then(function (id) {
                saleOrderSearchViewId = id;
            });
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} event
     */
    _openReconcileWithSaleOrderView: function (handle, record) {
        var self = this;
        var domain = [['state', 'in', ['sent', 'sale']], ['invoice_status', '!=', 'invoiced'], ['currency_id', '=', record.currency_id]];
        if (record.partner_id) {
            domain.push(['partner_id', '=', record.partner_id]);
        }
        return new Dialog.SelectCreateDialog(this, {
            listViewId: saleOrderSelectViewId,
            searchViewId: saleOrderSearchViewId,
            no_create: true,
            readonly: true,
            res_model: 'sale.order',
            domain: domain,
            context: {
                search_default_name: record.ref || record.name,
            },
            buttons: [{
                text: _t("Confirm & Invoice  selected Sales Orders"),
                classes: "btn-primary o_select_button",
                disabled: true,
                close: true,
                click: function () {
                    this.on_selected(this.list_controller.getSelectedIds());
                },
            }, {
                text: _t("Cancel"),
                classes: "btn-default o_form_button_cancel",
                close: true,
            }],
            on_selected: function (element_ids) {
                self._reconcileWithSaleOrder(handle, record, element_ids);
            },
        }).open();
    },
    /**
     * @private
     * @param {Object} record
     * @param {int[]} saleOrderIds
     */
    _reconcileWithSaleOrder: function (handle, record, saleOrderIds) {
        var self = this;
        var line = this.model.getLine(handle);
        line.blockUI = true;
        this._getWidget(handle).update(line);

        this._rpc({
            model: 'sale.order',
            method: 'read',
            args: [saleOrderIds, ['name', 'partner_id', 'client_order_ref', 'amount_total', 'currency_id', 'state', 'invoice_status']],
        }).then(function (orders) {
            if (!orders.length) {
                line.blockUI = false;
                self._getWidget(handle).update(line);
                return;
            }

            var partner = orders[0].partner_id;
            var total = 0;
            for (var k=0; k<orders.length; k++) {
                if (partner[0] !== orders[k].partner_id[0]) {
                    self._openReconcileWithSaleOrderView(handle, record);
                    line.blockUI = false;
                    this._getWidget(handle).update(line);
                    return;
                }
                total += orders[k].amount_total;
            }

            // convert quotation in sale order
            var def = $.when();
            var toConfirm = _.pluck(_.filter(orders, {state: 'sent'}), 'id');
            if (toConfirm.length) {
                def = self._rpc({
                    model: 'sale.order',
                    method: 'action_confirm',
                    args: [toConfirm],
                });
            }

            var props = [];
            return def
                .then(function () {
                    var defs = [];
                    if (Math.abs(record.amount) === total) { // Math.abs because in manual the amount is negative
                        defs.push(self._rpc({
                            model: 'sale.advance.payment.inv',
                            method: 'reconciliation_create_invoices',
                            args: [saleOrderIds],
                        })).then(function (prop) {
                            props.push.apply(props, prop);
                        });
                    } else {
                        defs = _.map(orders, function (order) {
                            var def = $.Deferred();
                            var amount = fieldUtils.format.monetary(order.amount_total, {}, {currency_id: order.currency_id[0]});
                            var dialog = new Dialog.FormViewDialog(self, {
                                title: _.str.sprintf(core._t('Invoice Orders: %s (%s) to be reconciled with: %s (%s)'), order.client_order_ref || order.name, amount, record.ref || record.name, record.amount_str),
                                type: 'ir.actions.act_window',
                                res_model: 'sale.advance.payment.inv',
                                view_type: 'form',
                                view_mode: 'form',
                                target: 'new',
                                context: {
                                    default_advance_payment_method: 'fixed',
                                    default_amount: orders.length === 1 ? (Math.abs(record.amount) <= order.amount_total ? Math.abs(record.amount) : order.amount_total) : null
                                },
                                buttons: [{
                                        text: core._t("Create Invoice"),
                                        classes: "btn-primary",
                                        click: function () {
                                            this._save().always(this.close.bind(this));
                                        }
                                    }, {
                                        text: core._t("Discard"),
                                        classes: "btn-default o_form_button_cancel",
                                        close: true,
                                        click: function () {
                                            this.form_view.model.discardChanges(this.form_view.handle, {
                                                rollback: this.shouldSaveLocally,
                                            });
                                        }
                                    }
                                ],
                                on_saved: function (record) {
                                    return self._rpc({
                                        model: 'sale.advance.payment.inv',
                                        method: 'create_invoices',
                                        context: {
                                            get_move_line_id: true,
                                            active_ids: [order.id]
                                        },
                                        args: [[record.data.id]]
                                    }).then(function (prop) {
                                        props.push.apply(props, prop);
                                    });
                                }
                            });
                            dialog.on('closed', self, def.resolve.bind(def));
                            dialog.open();
                            return def;
                        });
                    }
                    return $.when.apply($, defs);
                }).then(function () {
                    return self.model.addMultiPropositions(handle, props);
                }).then(function () {
                    if (!record.partner_id) {
                        return self.model.changePartner(handle, {
                            id: partner[0],
                            display_name: partner[1]
                        });
                    }
                }).then(function () {
                    line.blockUI = false;
                    self._getWidget(handle).update(line);
                }).then(function () {
                    var order_ids = _.uniq(_.flatten(_.pluck(self.model.lines, 'order_ids')));
                    self._rpc({
                        model: 'sale.order',
                        method: 'search',
                        args: [[['id', 'in', order_ids], ['invoice_status', '!=', 'invoiced']]],
                    }).then(function (ids) {
                        _.each(self.model.lines, function (line, handle) {
                            if (line.order_ids.length) {
                                return;
                            }
                            line.order_ids = _.intersection(line.order_ids, ids);
                            if (!line.order_ids.length) {
                                self._getWidget(handle).update(line);
                            }
                        });
                    });
                });
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} event
     */
    _onReconcileWithSaleOrder: function (event) {
        var handle = event.target.handle;
        var line = this.model.getLine(handle);
        this._openReconcileWithSaleOrderView(handle, line.st_line);
    },
});

ReconciliationClientAction.ManualAction.include({

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onReconcileWithSaleOrder: function (event) {
        var handle = event.target.handle;
        var line = this.model.getLine(handle);
        var record = _.extend({}, line.reconciliation_proposition[0]);
        if (!record.currency_id) {
            record.currency_id = line.currency_id;
        }
        this._openReconcileWithSaleOrderView(handle, record);
    },
});

return ReconciliationClientAction;
});

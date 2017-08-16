# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class HrExpense(models.Model):
    _inherit = "hr.expense"

    sale_order_id = fields.Many2one('sale.order', string='Sale Order', readonly=True, states={'draft': [('readonly', False)]}, domain=[('state', 'not in', ['draft', 'sent', 'done'])])

    def create_update_lines(self):
        OrderLine = self.env['sale.order.line']
        for expense in self.filtered('sale_order_id'):
            quantity_delivered = expense.quantity
            order_line_vals = {
                'order_id': expense.sale_order_id.id,
                'name': expense.name,
                'product_uom_qty': quantity_delivered,
                'qty_delivered': quantity_delivered,
                'product_id': expense.product_id.id,
                'product_uom': expense.product_uom_id.id,
                'price_unit': expense.unit_amount,
                'tax_id': [(4, [tid.id]) for tid in expense.tax_ids],
                'expense_ids': [(4, expense.id)]
            }
            if expense.product_id.expense_policy == 'sales_price':
                sale_order_line = OrderLine.search([('order_id', '=', expense.sale_order_id.id), ('product_id', '=', expense.product_id.id)], limit=1)
                if sale_order_line:
                    if sale_order_line.price_unit == expense.unit_amount:
                        qty_delivered = sale_order_line.qty_delivered and sale_order_line.qty_delivered or sale_order_line.product_uom_qty
                        sale_order_line.write({'expense_ids': [(4, expense.id)], 'qty_delivered': qty_delivered + quantity_delivered})
                    else:
                        OrderLine.create(order_line_vals)
                else:
                    OrderLine.create(order_line_vals)
            else:
                OrderLine.create(order_line_vals)


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    @api.multi
    def approve_expense_sheets(self):
        res = super(HrExpenseSheet, self).approve_expense_sheets()
        for sheet in self:
            sheet.expense_line_ids.create_update_lines()

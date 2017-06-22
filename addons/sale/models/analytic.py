# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    so_line = fields.Many2one('sale.order.line', string='Sales Order Line')

    @api.model
    def create(self, values):
        result = super(AccountAnalyticLine, self).create(values)
        result._sale_postprocess()
        return result

    @api.multi
    def write(self, values):
        # get current so lines for which update qty wil be required
        sale_order_lines = self.env['sale.order.line']
        if 'so_line' in values:
            sale_order_lines = self.mapped('so_line')
        result = super(AccountAnalyticLine, self).write(values)
        # trigger the update of qty_delivered if one of the depending fields are modified
        if any(field_name in values for field_name in ['so_line', 'unit_amount', 'product_uom_id']):
            self._sale_postprocess(additional_so_lines=sale_order_lines)
        return result

    @api.multi
    def unlink(self):
        sale_order_lines = self.sudo().mapped('so_line')
        res = super(AccountAnalyticLine, self).unlink()
        self.env['account.analytic.line']._sale_postprocess(unlinked_so_lines=sale_order_lines)
        return res

    @api.multi
    def _sale_postprocess(self, additional_so_lines=None, unlinked_so_lines=None):
        """ Trigger the update of qty_delivered on related SO lines (of `self`) and other given
            additionnal lines.
            NOTE: This method should be overriden if you want to determine and set the so line of the
            current analytic line, or do stuff analytic line by analytic line (compute values on the fly
            depending on other line fields)
        """
        sale_order_lines = self.filtered(lambda aal: aal.so_line).mapped('so_line')
        if additional_so_lines:
            sale_order_lines |= additional_so_lines

        # trigger the update of qty_delivered
        if sale_order_lines:
            sale_order_lines._analytic_compute_delivered_quantity(unlinked_so_lines=unlinked_so_lines)

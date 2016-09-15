# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrExpenseRefuseWizard(models.TransientModel):

    _name = "hr.expense.refuse.wizard"
    _description = "Expense refuse Reason wizard"

    reason = fields.Char(string='Reason', required=True)

    @api.multi
    def expense_refuse_reason(self):
        self.ensure_one()
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        expense = self.env['hr.expense'].browse(active_ids)
        expense.refuse_expense(self.reason)
        return {'type': 'ir.actions.act_window_close'}

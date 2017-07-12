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
        active_ids = self.env.context.get('active_ids', [])
        print active_ids
        model = self.env.context.get('model')
        expense_sheet = self.env[model].browse(active_ids)
        expense_sheet.refuse_expense(self.reason)
        return {'type': 'ir.actions.act_window_close'}

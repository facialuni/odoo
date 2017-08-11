# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountTaxReport(models.TransientModel):
    _inherit = "account.common.account.report"
    _name = 'account.tax.report'
    _description = 'Tax Report'

    target_move = fields.Selection([('cash_basis', 'Cash Basis Method')], string='Options')
    
    def _print_report(self, data):
        data = self.pre_print_report(data)
        records = self.env[data['model']].browse(data.get('ids', []))
        return self.env.ref('account.action_report_account_tax').report_action(records, data=data)
# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountTaxReport(models.TransientModel):
    _name = 'account.tax.report'
    _inherit = "account.common.account.report"
    _description = 'Tax Report'

    target_move = fields.Selection([('cash_basis', ' Cash Basis')], string='Options')
    
    def _print_report(self, data):
        data['form'].update(self.read(['date_from', 'date_to'])[0])
        records = self.env[data['model']].browse(data.get('ids', []))
        return self.env.ref('account.action_report_account_tax').report_action(self, data=data, config=False)

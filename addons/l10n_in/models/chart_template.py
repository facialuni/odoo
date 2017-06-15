# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class ChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    @api.multi
    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        journals = super(ChartTemplate, self)._prepare_all_journals(acc_template_ref, company, journals_dict)
        if not self == self.env.ref('l10n_in.indian_chart_template_standard'):
            return journals
        #For India, rename customer Invoices journal
        for journal in journals:
            if journal['code'] == 'INV':
                journal['name'] = 'Tax Invoice'
        exp_acc = self.env.ref('l10n_in.p20013').id
        ret_acc = self.env.ref('l10n_in.p20012').id
        journals = journals + [{'name': _('Retail Invoice'), 'type': 'sale', 'code': _('RET'), 'default_credit_account_id': ret_acc,'default_debit_account_id': ret_acc},
                                {'name': _('Export Invoice'), 'type': 'sale', 'code': _('EXP'), 'default_credit_account_id': exp_acc,'default_debit_account_id': exp_acc},]
        return journals

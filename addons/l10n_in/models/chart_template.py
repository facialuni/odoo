# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class ChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    @api.model
    def generate_journals(self, acc_template_ref, company, journals_dict=None):
        res = super(ChartTemplate, self).generate_journals(acc_template_ref, company, journals_dict)
        cust_inv_journal = self.env['account.journal'].search([('type', '=', 'sale'), ('code', '=', 'INV')], limit=1)
        cust_inv_journal.write({'name': _('Tax Invoice')})
        return res

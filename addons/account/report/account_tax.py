# -*- coding: utf-8 -*-

import time
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportTax(models.AbstractModel):
    _name = 'report.account.report_tax'


    @api.model
    def get_report_values(self, docids, data=None):
        sale_tax_line= self.env['account.tax'].search([('type_tax_use', '=', 'sale')])
        purchase_tax_line= self.env['account.tax'].search([('type_tax_use', '=', 'purchase')])
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_ids', []))
        return {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'data': data['form'],
            'docs': docs,
            'sale_line': sale_tax_line.type_tax_use,
            'sale_tax': sale_tax_line.name,
            'purchase_line': purchase_tax_line.type_tax_use,
            'purchase_tax': purchase_tax_line.name,
        }

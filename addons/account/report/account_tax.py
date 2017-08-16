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
        all_sales = self.env['account.invoice'].search([('type', '=', 'out_invoice')])
        all_sale_price = sum(all_sales.mapped('amount_untaxed'))
        all_sale_tax = sum(all_sales.mapped('amount_tax'))
        all_purchase = self.env['account.invoice'].search([('type', '=', 'in_invoice')])
        all_purchase_price = sum(all_purchase.mapped('amount_untaxed'))
        all_purchase_tax = sum(all_purchase.mapped('amount_tax'))

        return {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'data': data['form'],
            'docs': docs,
            'sale_line': sale_tax_line.type_tax_use,
            'sale_tax': sale_tax_line.name,
            'purchase_line': purchase_tax_line.type_tax_use,
            'purchase_tax': purchase_tax_line.name,
            'all_sale_price': all_sale_price,
            'all_sale_tax': all_sale_tax,
            'all_purchase_price': all_purchase_price,
            'all_purchase_tax':all_purchase_tax,
        }

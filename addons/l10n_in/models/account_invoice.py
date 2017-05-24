# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import amount_to_text_en
from odoo import api, fields, models


class AccountInvoice(models.Model):

    _inherit = "account.invoice"


    @api.one
    @api.depends('amount_total')
    def _compute_amount_total_words(self):
        amount_in_words = amount_to_text_en.amount_to_text(self.amount_total, lang='en', currency=self.company_id.currency_id.name)
        amount_in_words = amount_in_words.replace(' and Zero Cent', '').replace('INR', 'Rupees').replace('Cents', 'Paisa')
        self.amount_total_words = amount_in_words

    amount_total_words = fields.Char("Total (In Words)", compute="_compute_amount_total_words")

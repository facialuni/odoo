# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = 'account.invoice'
    
    l10n_sg_permit_number = fields.Char(string="PermitNo")
    
    l10n_sg_permit_number_date = fields.Date(string="Date of permit number")

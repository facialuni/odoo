# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountInvoice(models.Model):

    _inherit = "res.company"

    excise_no = fields.Char()

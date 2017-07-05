# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    gstin = fields.Char(related="partner_id.gstin", string="GSTIN", size=15, help="GST Identification Number")

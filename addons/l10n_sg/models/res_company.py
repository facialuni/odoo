# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'
    
    l10n_sg_unique_entity_number = fields.Char(string='UEN')

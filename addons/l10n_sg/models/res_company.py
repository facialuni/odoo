# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'
    
    unique_entity_number = fields.Char(string='UEN')

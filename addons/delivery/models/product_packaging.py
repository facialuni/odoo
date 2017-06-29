# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    height = fields.Integer('Height')
    width = fields.Integer('Width')
    length = fields.Integer('Length')
    max_weight = fields.Float('Max Weight', help='Maximum weight shippable in this packaging')
    weight_uom_id = fields.Many2one('product.uom', string='Weight Unit of Measure', compute='_compute_weight_uom_id', readonly=1)
    shipper_package_code = fields.Char('Package Code')
    package_carrier_type = fields.Selection([('none', 'No carrier integration')], string='Carrier', default='none')

    _sql_constraints = [
        ('positive_height', 'CHECK(height>=0)', 'Height must be positive'),
        ('positive_width', 'CHECK(width>=0)', 'Width must be positive'),
        ('positive_length', 'CHECK(length>=0)', 'Length must be positive'),
        ('positive_max_weight', 'CHECK(max_weight>=0.0)', 'Max Weight must be positive'),
    ]

    def _compute_weight_uom_id(self):
        weight_uom_id = int(self.env['ir.config_parameter'].sudo().get_param('database_weight_uom_id'))
        for p in self:
            p.weight_uom_id = weight_uom_id

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def _compute_need_procurement(self):
        super(ProductProduct, self)._compute_need_procurement()
        for product in self:
            if product.type not in ['service', 'digital']:
                product.need_procurement = True

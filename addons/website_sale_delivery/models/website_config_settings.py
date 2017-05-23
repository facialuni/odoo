# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields

class WebsiteConfigSettings(models.TransientModel):
    _inherit = 'website.config.settings'

    is_installed_dhl = fields.Boolean()
    is_installed_fedex = fields.Boolean()
    is_installed_usps = fields.Boolean()
    is_installed_bpost = fields.Boolean()

    @api.model
    def get_values(self):
        res = super(WebsiteConfigSettings, self).get_values()
        IrModule = self.env['ir.module.module'].sudo()
        res.update(
            is_installed_dhl=IrModule.search([('name', '=', 'delivery_dhl'), ('state', '=', 'installed')]).id,
            is_installed_fedex=IrModule.search([('name', '=', 'delivery_fedex'), ('state', '=', 'installed')]).id,
            is_installed_usps=IrModule.search([('name', '=', 'delivery_usps'), ('state', '=', 'installed')]).id,
            is_installed_bpost=IrModule.search([('name', '=', 'delivery_bpost'), ('state', '=', 'installed')]).id
        )
        return res

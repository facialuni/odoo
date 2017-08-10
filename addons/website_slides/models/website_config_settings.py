# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class WebsiteConfigSettings(models.TransientModel):
    _inherit = "website.config.settings"

    website_slide_google_app_key = fields.Char(string='Google Doc Key', config_parameter='website_slides.google_app_key')

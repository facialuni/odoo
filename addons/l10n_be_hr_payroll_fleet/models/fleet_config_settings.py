# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class FleetConfigSettings(models.TransientModel):
    _name = 'fleet.config.settings'
    _inherit = ['res.config.settings']

    max_unused_cars = fields.Integer(string='Maximum unused cars', default=3, config_parameter='l10n_be_hr_payroll_fleet.max_unused_cars')

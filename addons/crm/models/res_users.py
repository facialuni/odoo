# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Users(models.Model):

    _inherit = 'res.users'

    target_sales_won = fields.Float('Won in Opportunities Target')
    target_sales_done = fields.Float('Activities Done Target')

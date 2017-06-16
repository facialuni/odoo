# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons.mail.models.mail_digest import PERIODICITY_DATE


class MailDigest(models.Model):
    _inherit = 'mail.digest'

    kpi_website_sale_total = fields.Boolean(string='eCommerce Sales')
    kpi_website_sale_total_value = fields.Monetary(compute='_compute_kpi_website_sale_total_value')

    def _compute_kpi_website_sale_total_value(self):
        """get total website sales having sale state and team name is website in specific time frame(Daily, Weekly, Monthly, Quarterly)"""

        periodicity = self.env.context.get('periodicity', 'monthly')
        total_sale_order = self.env['sale.order'].search([('state', 'not in', ['draft', 'cancel', 'sent']), ('team_id.team_type', '=', 'website'), ('date_order', '>=', PERIODICITY_DATE[periodicity])])
        website_sale = sum(total_sale_order.mapped('amount_total'))
        for record in self:
            record.kpi_website_sale_total_value = website_sale

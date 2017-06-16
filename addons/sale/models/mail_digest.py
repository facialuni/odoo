# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons.mail.models.mail_digest import PERIODICITY_DATE


class MailDigest(models.Model):
    _inherit = 'mail.digest'

    kpi_sale_total = fields.Boolean(string='Sales')
    kpi_sale_total_value = fields.Monetary(compute='_compute_kpi_sale_total_value')

    def _compute_kpi_sale_total_value(self):
        """get total sales having sale state in specific time frame(Daily, Weekly, Monthly)"""

        periodicity = self.env.context.get('periodicity', "monthly")
        total_sale = sum(self.env['sale.order'].search([('state', 'not in', ['draft', 'cancel', 'sent']), ('date_order', '>=', PERIODICITY_DATE[periodicity])]).mapped('amount_total'))
        for record in self:
            record.kpi_sale_total_value = total_sale

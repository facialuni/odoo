# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons.mail.models.mail_digest import PERIODICITY_DATE


class MailDigest(models.Model):
    _inherit = 'mail.digest'

    kpi_hr_recruitment_new_colleagues = fields.Boolean(string='New Employees')
    kpi_hr_recruitment_new_colleagues_value = fields.Integer(compute='_compute_kpi_hr_recruitment_new_colleagues_value')

    def _compute_kpi_hr_recruitment_new_colleagues_value(self):
        """ Get total number of new employees created in specific time frame(Daily, Weekly, Monthly, Quarterly) to send
        kpi's to specific group of users."""

        periodicity = self.env.context.get('periodicity', 'monthly')
        new_colleagues = self.env['hr.employee'].search_count([("create_date", ">=", PERIODICITY_DATE[periodicity])])
        for record in self:
            record.kpi_hr_recruitment_new_colleagues_value = new_colleagues

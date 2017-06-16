# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons.mail.models.mail_digest import PERIODICITY_DATE


class MailDigest(models.Model):
    _inherit = 'mail.digest'

    kpi_crm_lead_created = fields.Boolean(string='Leads Created')
    kpi_crm_lead_created_value = fields.Integer(compute='_compute_lead_opportunity_value')
    kpi_crm_opportunities_won = fields.Boolean(string='Opportunities Won')
    kpi_crm_opportunities_won_value = fields.Integer(compute='_compute_lead_opportunity_value')

    def _compute_lead_opportunity_value(self):
        """ Get total number of lead created in specific time frame(Daily, weekly, Monthly, Quarterly) to send
        kpi's to specific group of users. """

        CrmLead = self.env['crm.lead']
        periodicity = self.env.context.get('periodicity', 'monthly')
        lead_created = CrmLead.search_count([("create_date", ">=", PERIODICITY_DATE[periodicity])])
        opp_won = CrmLead.search_count([("create_date", ">=", PERIODICITY_DATE[periodicity]), ('type', '=', 'opportunity'), ('probability', '=', '100')])
        for record in self:
            record.kpi_crm_lead_created_value = lead_created
            record.kpi_crm_opportunities_won_value = opp_won

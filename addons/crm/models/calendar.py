# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CalendarEvent(models.Model):

    _inherit = 'calendar.event'

    def _compute_is_highlighted(self):
        super(CalendarEvent, self)._compute_is_highlighted()
        if self.env.context.get('active_model') == 'crm.lead':
            opportunity_id = self.env.context.get('active_id')
            for event in self:
                if event.opportunity_id.id == opportunity_id:
                    event.is_highlighted = True

    opportunity_id = fields.Many2one('crm.lead', 'Opportunity', domain="[('type', '=', 'opportunity')]")

    @api.model
    def create(self, vals):
        event = super(CalendarEvent, self).create(vals)
        if event.opportunity_id:
            event.opportunity_id.log_meeting(event.name, event.start, event.duration)
        return event

    # Due to same model crm.lead need to give opportunity view when opening document from event.
    def action_open_resource_document(self):
        self.ensure_one()
        res = super(CalendarEvent, self).action_open_resource_document()
        if self.activity_ids.res_model == 'crm.lead':
            form_view_id = self.env.ref('crm.crm_case_form_view_oppor').id
            res['views'] = [[form_view_id, 'form']]
        return res

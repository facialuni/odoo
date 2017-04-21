# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class MailActivity(models.Model):

    _inherit = "mail.activity"

    activity_meeting_type = fields.Boolean(related='activity_type_id.meeting_type')

    @api.multi
    def action_open_calendar(self):
        self.ensure_one()
        action = self.env.ref('calendar.action_calendar_event').read()[0]
        action['context'] = {
            'create_activity': True,
        }
        self.unlink()
        return action


class MailActivityType(models.Model):

    _inherit = "mail.activity.type"

    meeting_type = fields.Boolean(string='Manage through Calendar')

    @api.multi
    def action_open_calendar(self):
        self.ensure_one()
        action = self.env.ref('calendar.action_calendar_event').read()[0]
        action['context'] = {
            'create_activity': True,
        }
        self.unlink()
        return action

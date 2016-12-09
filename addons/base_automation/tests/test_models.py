# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LeadTest(models.Model):
    _name = "base.automation.lead.test"
    _description = "Automation Test"

    name = fields.Char(string='Subject', required=True, index=True)
    state = fields.Selection(
        [('draft', 'New'), ('open', 'In Progress'), ('pending', 'Pending'), ('done', 'Closed')],
        string="Status", readonly=True, default='draft')
    date_action_last = fields.Datetime(string='Last Action', readonly=True)
    value = fields.Char(string="Date Value")
    line_ids = fields.One2many('base.automation.line.test', 'lead_id', string="Automation Line")


class LineTest(models.Model):
    _name = "base.automation.line.test"
    _description = "Automation Line Test"

    name = fields.Char()
    lead_id = fields.Many2one('base.automation.lead.test', string="Lead", ondelete='cascade')

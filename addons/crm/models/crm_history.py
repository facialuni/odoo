# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from odoo import api, fields, models


class History(models.Model):
    _name = "crm.opportunity.history"
    _description = "crm moves History"

    user_id = fields.Many2one('res.users', string='User')
    team_id = fields.Many2one('crm.team', 'Sales Channel')
    date_deadline = fields.Date('Expected Closing for opportunity', readonly=True)
    opp_create_date = fields.Datetime('Creation Date of opportunity', readonly=True)
    date_closed = fields.Datetime('Close Date of opportunity', readonly=True)
    stage_id = fields.Many2one('crm.stage', string='Stage')
    stage_name = fields.Char(string='Stage Name', related='stage_id.name', store=True)
    res_id = fields.Many2one('crm.lead', string='related document')

    @api.multi
    def calculate_moves(self, start_date, end_date, stages, user_id, team_id):
        records = self.search_read([
            ('team_id', '=', team_id),
            ('user_id', '=', user_id),
            ('create_date', '>=', start_date),
        ], ['stage_id'])
        stage_record_lists = [line['stage_id'][1] for line in records]
        counts = {stage: stage_record_lists.count(stage)
                  for stage in stages[1:]}
        return counts

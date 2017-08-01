# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from datetime import datetime


class History(models.Model):
    _name = "crm.opportunity.history"
    _description = "crm stage History"

    user_id = fields.Integer(string='User')
    team_id = fields.Integer('Sales Channel')
    stage_id = fields.Many2one('crm.stage', string='Stage')
    stage_name = fields.Char(string='Stage Name', related='stage_id.name', store=True)
    res_id = fields.Many2one('crm.lead', string='related document')

    @api.multi
    def calculate_moves(self, start_date, end_date, stages, user_id, team_id):
        new_deals = self.env['crm.lead'].search_count([('create_date', '>=', start_date), ('create_date', '<=', end_date), ('type', '=', 'opportunity')])
        deals_left = self.env['crm.lead'].search_count(['|', ('date_deadline', '<', datetime.today().strftime('%Y-%m-%d')), '&', ('date_deadline', '=', None), '&', ('date_closed', '=', None), ('type', '=', 'opportunity')])
        won_deals = self.env['crm.lead'].search_count([('probability', '=', 100), ('date_closed', '<=', end_date), ('date_closed', '>=', start_date), ('type', '=', 'opportunity')])
        lost_deals = self.env['crm.lead'].search_count([('active', '=', False), ('date_closed', '<=', end_date), ('date_closed', '>=', start_date), ('type', '=', 'opportunity')])

        records = self.env['crm.lead'].search_read([('type', '=', 'opportunity')], ['day_close'])
        total_days = sum(record['day_close'] for record in records)
        average_days = round(total_days / len(records), 3)

        stage_moves = []
        for stage in stages:
            result = self.env['crm.opportunity.history'].search_count([('stage_name', '=', stage)])
            stage_moves.append((stage, result))

        total_revenue = self.env['crm.lead'].read_group([('create_date', '>=', start_date), ('create_date', '<=', end_date)], ['stage_id', 'planned_revenue'], ['stage_id'])
        expected_revenues = {revenue['stage_id'][1]: revenue['planned_revenue'] for revenue in total_revenue}

        return {'stage_moves': stage_moves,
                'new_deals': new_deals,
                'left_deals': deals_left,
                'won_deals': won_deals,
                'lost_deals': lost_deals,
                'average_days': average_days,
                'expected_revenues': expected_revenues}

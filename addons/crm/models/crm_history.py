# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class History(models.Model):
    _name = "crm.opportunity.history"
    _description = "crm moves History"

    user_id = fields.Integer(string='User')
    team_id = fields.Integer('Sales Channel')
    stage_id = fields.Many2one('crm.stage', string='Stage')
    stage_name = fields.Char(string='Stage Name', related='stage_id.name', store=True)
    res_id = fields.Many2one('crm.lead', string='related document')

    @api.multi
    def calculate_moves(self, start_date, end_date, stages, user_id, team_id):
        select_clause = 'SELECT'
        for stage in stages[1:]:
            select_clause += " COUNT(DISTINCT CASE WHEN stage_name = '" + stage + "' THEN res_id END) as " + stage + ","

        from_clause = """
            FROM crm_opportunity_history
        """
        where_clause = "WHERE create_date BETWEEN %(start_date)s AND %(end_date)s "
        condition = ''
        if team_id and user_id:
            condition = "AND user_id = '" + user_id + "' AND team_id = '" + team_id + "'"
        elif user_id:
            condition = "AND user_id = '" + user_id + "'"
        elif team_id:
            condition = "AND team_id = '" + team_id + "'"
        if condition:
            where_clause += condition
        query = select_clause[:-1] + from_clause + where_clause
        self.env.cr.execute(query, {
                    'start_date': start_date,
                    'end_date': end_date,
            })
        query_result = self.env.cr.dictfetchone()
        result = self.res_id.calculate_percentage(start_date, end_date, user_id, team_id, condition)
        return {'stages_moves': query_result,
                'new_deals': result['new_deals'],
                'left_deals': result['deals_left'],
                'won_deals': result['won_deals'],
                'lost_deals': result['lost_deals']}

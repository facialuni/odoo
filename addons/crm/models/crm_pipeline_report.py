# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools, api


class OpportunityReport(models.Model):
    """ CRM Opportunity Analysis """

    _name = "crm.pipeline.report"
    _auto = False
    _description = "CRM Pipeline Analysis"

    new_deals = fields.Integer('New Deals', readonly=True)
    won_deals = fields.Integer('Won Deals', readonly=True)
    lost_deals = fields.Integer('Lost Deals', readonly=True)
    deals_left = fields.Integer('Deals Left', readonly=True)

    def _select(self):
        select_str = """
            SELECT
                MIN(c.id) as id,
                COUNT(DISTINCT CASE WHEN c.create_date >= %(start_date)s THEN c.id END) as new_deals,
                COUNT(DISTINCT CASE WHEN (c.date_deadline <= %(end_date)s or c.date_deadline is null) and c.date_closed IS null THEN c.id END) as deals_left,
                COUNT(DISTINCT CASE WHEN c.probability = 100 AND c.date_closed BETWEEN %(start_date)s AND %(end_date)s THEN c.id END) as won_deals,
                COUNT(DISTINCT CASE WHEN c.active = FALSE AND c.date_closed BETWEEN %(start_date)s AND %(end_date)s THEN c.id END) as lost_deals
        """
        return select_str

    def _from(self):
        return " FROM crm_lead c join crm_opportunity_history h on c.id = h.res_id "

    def _where(self, args):
        where_str = """
                WHERE
                    c.type = 'opportunity'
                AND
                    h.create_date BETWEEN %(start_date)s AND %(end_date)s
            """
        if args['user_id']:
            where_str += "AND c.user_id = '" + args['user_id'] + "'"
        if args['team_id']:
            where_str += "AND c.team_id = '" + args['team_id'] + "'"
        return where_str

    @api.model_cr
    def init(self, arguments=None):
        tools.drop_view_if_exists(self.env.cr, self._table)
        if arguments:
            self.env.cr.execute("""CREATE VIEW %s AS (
                %s
                %s
                %s
            )""" % (self._table, self._select(), self._from(),
                    self._where({'user_id': arguments['user_id'], 'team_id': arguments['team_id']})), {'start_date': arguments['start_date'], 'end_date': arguments['end_date']})

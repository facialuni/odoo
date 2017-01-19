# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    department_id = fields.Many2one('hr.department', "Department", related='user_id.employee_ids.department_id', store=True, readonly=True)
    timesheet_pack_id = fields.Many2one('timesheet.pack', 'TS Pack')

    res_model = fields.Char('Model')
    res_id = fields.Integer('ID')

    @api.onchange('timesheet_pack_id')
    def _onchange_timesheet_pack_id(self):
        if self.timesheet_pack_id:
            self.account_id = self.timesheet_pack_id.account_analytic_account.id

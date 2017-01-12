# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class TimesheetPack(models.Model):
    _name = 'timesheet.pack'

    name = fields.Char()
    analytic_account_id = fields.Many2one(
        'account.analytic.account', 'Contract/Analytic',
        auto_join=True,
        ondelete="restrict", required=True,
        help="UPDATE ME",
    )
    timesheet_line_ids = fields.One2many(
        'account.analytic.line', 'timesheet_pack_id',
        'Timesheet Lines',
        help="UPDATE ME"
    )


class TimesheetMixin(models.AbstractModel):
    _name = 'timesheet.mixin'

    timesheet_ids = fields.One2many('account.analytic.line', 'res_id', string='Timesheet', domain=lambda self: [('res_model', '=', self._name)], auto_join=True)
    timesheet_pack_id = fields.Many2one('timesheet.pack', 'Timesheet Pack')

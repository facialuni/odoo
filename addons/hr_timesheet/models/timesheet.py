# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class TimesheetPack(models.Model):
    _inherit = 'timesheet.pack'

    task_id = fields.Many2one('project.task', 'Task')
    project_id = fields.Many2one('project.project', 'Project', domain=[('allow_timesheets', '=', True)])

    @api.onchange('project_id')
    def onchange_project_id(self):
        self.task_id = False

    @api.model
    def create(self, vals):
        if vals.get('project_id'):
            project = self.env['project.project'].browse(vals.get('project_id'))
            vals['analytic_account_id'] = project.analytic_account_id.id
        return super(TimesheetPack, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('project_id'):
            project = self.env['project.project'].browse(vals.get('project_id'))
            vals['analytic_account_id'] = project.analytic_account_id.id
        return super(TimesheetPack, self).write(vals)

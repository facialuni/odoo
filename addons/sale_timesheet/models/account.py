# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo import api, fields, models, _


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    timesheet_invoice_type = fields.Selection([
        ('billable_time', 'Billable Time'),
        ('billable_fixed', 'Billable Fixed'),
        ('non_billable', 'Non Billable'),
        ('non_billable_project', 'No task found')], string="Billable Type", readonly=True, copy=False)
    timesheet_invoice_id = fields.Many2one('account.invoice', string="Invoice", readonly=True, copy=False, help="Invoice created from the timesheet")
    timesheet_revenue = fields.Monetary("Revenue", default=0.0, readonly=True, currency_field='company_currency_id', copy=False)

    @api.model
    def create(self, values):
        result = super(AccountAnalyticLine, self).create(values)
        # applied only for timesheet
        if result.project_id:
            result._timesheet_postprocess(values)
        return result

    @api.multi
    def write(self, values):
        # prevent to update invoiced timesheets
        if self.filtered(lambda timesheet: timesheet.timesheet_invoice_id):
            if any([field_name in values for field_name in ['unit_amount', 'employee_id', 'task_id', 'timesheet_revenue', 'so_line', 'amount', 'date']]):
                raise UserError(_('You can not modify already invoiced timesheets.'))
        result = super(AccountAnalyticLine, self).write(values)
        # applied only for timesheet
        self.filtered(lambda t: t.project_id)._timesheet_postprocess(values)
        return result

    @api.model
    def _timesheet_preprocess(self, values):
        values = super(AccountAnalyticLine, self)._timesheet_preprocess(values)
        # task implies so line
        if 'task_id' in values:
            task = self.env['project.task'].sudo().browse(values['task_id'])
            values['so_line'] = task.sale_line_id.id or values.get('so_line', False)
        return values

    @api.multi
    def _timesheet_postprocess(self, values):
        # (re)compute the amount (depending on unit_amount, employee_id for the cost, and account_id for currency)
        if any([field_name in values for field_name in ['unit_amount', 'employee_id', 'account_id']]):
            for timesheet in self:
                uom = timesheet.employee_id.company_id.project_time_mode_id
                cost = timesheet.employee_id.timesheet_cost or 0.0
                amount = -timesheet.unit_amount * cost
                amount_converted = timesheet.employee_id.currency_id.compute(amount, timesheet.account_id.currency_id)
                timesheet.write({
                    'amount': amount_converted,
                    'product_uom_id': uom.id,
                })
        # (re)compute the theorical revenue
        if any([field_name in values for field_name in ['so_line', 'unit_amount', 'account_id']]):
            self._timesheet_compute_theorical_revenue()
        return values

    @api.multi
    def _timesheet_compute_theorical_revenue(self):
        """ This method set the theorical revenue on the current timesheet lines.

            If invoice on delivered quantity:
                timesheet hours * (SO Line Price) * (1- discount),
            elif invoice on ordered quantities & create task:
                min (
                    timesheet hours * (SO Line unit price) * (1- discount),
                    TOTAL SO - TOTAL INVOICED - sum(timesheet revenues with invoice_id=False)
                )
            else:
                0
        """
        for timesheet in self:
            unit_amount = timesheet.unit_amount
            so_line = timesheet.so_line
            # default values
            billable_type = 'non_billable_project' if not timesheet.task_id else 'non_billable'
            revenue = 0.0
            # set the revenue and billable type according to the product and the SO line
            if timesheet.task_id and so_line.product_id.type == 'service' and so_line.product_id.service_type == 'timesheet':
                # find the analytic account to convert revenue into its currency
                analytic_account = timesheet.account_id
                # calculate the revenue on the timesheet
                if so_line.product_id.invoice_policy == 'delivery':
                    sale_price_unit = so_line.currency_id.compute(so_line.price_unit, analytic_account.currency_id)  # amount from SO should be convert into analytic account currency
                    revenue = analytic_account.currency_id.round(unit_amount * sale_price_unit * (1-so_line.discount))
                    billable_type = 'billable_time'
                elif so_line.product_id.invoice_policy == 'order':
                    # compute the total revenue the SO since we are in fixed price
                    sale_price_unit = so_line.currency_id.compute(so_line.price_unit, analytic_account.currency_id)
                    total_revenue_so = analytic_account.currency_id.round(so_line.product_uom_qty * sale_price_unit * (1-so_line.discount))
                    # compute the total revenue already existing (without the current timesheet line)
                    domain = [('so_line', '=', so_line.id)]
                    if timesheet.ids:
                        domain += [('id', 'not in', timesheet.ids)]
                    analytic_lines = timesheet.sudo().search(domain)
                    total_revenue_invoiced = sum(analytic_lines.mapped('timesheet_revenue'))
                    # compute (new) revenue of current timesheet line
                    revenue = min(
                        analytic_account.currency_id.round(unit_amount * so_line.currency_id.compute(so_line.price_unit, analytic_account.currency_id) * (1-so_line.discount)),
                        total_revenue_so - total_revenue_invoiced
                    )
                    billable_type = 'billable_fixed'

            timesheet.write({
                'timesheet_revenue': revenue,
                'timesheet_invoice_type': billable_type,
            })
        return True

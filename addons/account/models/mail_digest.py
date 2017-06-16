from odoo import fields, models
from odoo.addons.mail.models.mail_digest import PERIODICITY_DATE


class MailDigest(models.Model):
    _inherit = 'mail.digest'

    kpi_account_bank_cash = fields.Boolean(string='Bank & Cash')
    kpi_account_bank_cash_value = fields.Integer(compute='_compute_kpi_account_total_revenue_value')
    kpi_account_total_revenue = fields.Boolean(string='Revenues')
    kpi_account_total_revenue_value = fields.Integer(compute='_compute_kpi_account_total_revenue_value')

    def _compute_kpi_account_total_revenue_value(self):
        periodicity = self.env.context.get('periodicity', 'monthly')
        account_moves = self.env['account.move'].search([('journal_id.type', 'in', ['sale', 'cash', 'bank']), ('date', '>=', PERIODICITY_DATE[periodicity])])

        def _account_move_amount(journal_type):
            return sum(account_moves.filtered(lambda r: r.journal_id.type in journal_type).mapped('amount'))

        for record in self:
            record.kpi_account_total_revenue_value = _account_move_amount(['sale'])
            record.kpi_account_bank_cash_value = _account_move_amount(['bank', 'cash'])

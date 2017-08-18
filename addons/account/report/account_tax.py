# -*- coding: utf-8 -*-

import time
from odoo import api, models, _
from odoo.exceptions import UserError
from odoo.tools import pycompat
from odoo.tools.translate import _
from odoo.tools.misc import formatLang


class ReportTax(models.AbstractModel):
    _name = 'report.account.report_tax'


    @api.model
    def get_report_values(self, docids, data=None):
        sale_tax_line= self.env['account.tax'].search([('type_tax_use', '=', 'sale')])
        purchase_tax_line= self.env['account.tax'].search([('type_tax_use', '=', 'purchase')])
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_ids', []))
        report_lines = self.get_lines(data)
        return {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'data': data['form'],
            'docs': docs,
            'lines': report_lines,
        }

    def _get_with_statement(self, user_types, domain=None):
        """ This function allow to define a WITH statement as prologue to the usual queries returned by query_get().
            It is useful if you need to shadow a table entirely and let the query_get work normally although you're
            fetching rows from your temporary table (built in the WITH statement) instead of the regular tables.

            @returns: the WITH statement to prepend to the sql query and the parameters used in that WITH statement
            @rtype: tuple(char, list)
        """
        sql = ''
        params = []

        #Cash basis option
        #-----------------
        #In cash basis, we need to show amount on income/expense accounts, but only when they're paid AND under the payment date in the reporting, so
        #we have to make a complex query to join aml from the invoice (for the account), aml from the payments (for the date) and partial reconciliation
        #(for the reconciled amount).
        if self.env.context.get('cash_basis'):
            if not user_types:
                return sql, params
            #we use query_get() to filter out unrelevant journal items to have a shadowed table as small as possible
            tables, where_clause, where_params = self.env['account.move.line']._query_get(domain=domain)
            sql = """WITH account_move_line AS (
              SELECT \"account_move_line\".id, \"account_move_line\".date, \"account_move_line\".name, \"account_move_line\".debit_cash_basis, \"account_move_line\".credit_cash_basis, \"account_move_line\".move_id, \"account_move_line\".account_id, \"account_move_line\".journal_id, \"account_move_line\".balance_cash_basis, \"account_move_line\".amount_residual, \"account_move_line\".partner_id, \"account_move_line\".reconciled, \"account_move_line\".company_id, \"account_move_line\".company_currency_id, \"account_move_line\".amount_currency, \"account_move_line\".balance, \"account_move_line\".user_type_id, \"account_move_line\".tax_line_id, \"account_move_line\".tax_exigible
               FROM """ + tables + """
               WHERE (\"account_move_line\".journal_id IN (SELECT id FROM account_journal WHERE type in ('cash', 'bank'))
                 OR \"account_move_line\".move_id NOT IN (SELECT DISTINCT move_id FROM account_move_line WHERE user_type_id IN %s))
                 AND """ + where_clause + """
              UNION ALL
              (
               WITH payment_table AS (
                 SELECT aml.move_id, \"account_move_line\".date, CASE WHEN aml.balance = 0 THEN 0 ELSE part.amount / ABS(aml.balance) END as matched_percentage
                   FROM account_partial_reconcile part LEFT JOIN account_move_line aml ON aml.id = part.debit_move_id, """ + tables + """
                   WHERE part.credit_move_id = "account_move_line".id
                    AND "account_move_line".user_type_id IN %s
                    AND """ + where_clause + """
                 UNION ALL
                 SELECT aml.move_id, \"account_move_line\".date, CASE WHEN aml.balance = 0 THEN 0 ELSE part.amount / ABS(aml.balance) END as matched_percentage
                   FROM account_partial_reconcile part LEFT JOIN account_move_line aml ON aml.id = part.credit_move_id, """ + tables + """
                   WHERE part.debit_move_id = "account_move_line".id
                    AND "account_move_line".user_type_id IN %s
                    AND """ + where_clause + """
               )
               SELECT aml.id, ref.date, aml.name,
                 CASE WHEN aml.debit > 0 THEN ref.matched_percentage * aml.debit ELSE 0 END AS debit_cash_basis,
                 CASE WHEN aml.credit > 0 THEN ref.matched_percentage * aml.credit ELSE 0 END AS credit_cash_basis,
                 aml.move_id, aml.account_id, aml.journal_id,
                 ref.matched_percentage * aml.balance AS balance_cash_basis,
                 aml.amount_residual, aml.partner_id, aml.reconciled, aml.company_id, aml.company_currency_id, aml.amount_currency, aml.balance, aml.user_type_id, aml.tax_line_id, aml.tax_exigible
                FROM account_move_line aml
                RIGHT JOIN payment_table ref ON aml.move_id = ref.move_id
                WHERE journal_id NOT IN (SELECT id FROM account_journal WHERE type in ('cash', 'bank'))
                  AND aml.move_id IN (SELECT DISTINCT move_id FROM account_move_line WHERE user_type_id IN %s)
              )
            ) """
            params = [tuple(user_types.ids)] + where_params + [tuple(user_types.ids)] + where_params + [tuple(user_types.ids)] + where_params + [tuple(user_types.ids)]
        return sql, params


    def _sql_from_amls_one(self):
        sql = """SELECT "account_move_line".tax_line_id, COALESCE(SUM("account_move_line".debit-"account_move_line".credit), 0)
                    FROM %s
                    WHERE %s AND "account_move_line".tax_exigible GROUP BY "account_move_line".tax_line_id"""
        return sql

    def _sql_from_amls_two(self):
        sql = """SELECT r.account_tax_id, COALESCE(SUM("account_move_line".debit-"account_move_line".credit), 0)
                 FROM %s
                 INNER JOIN account_move_line_account_tax_rel r ON ("account_move_line".id = r.account_move_line_id)
                 INNER JOIN account_tax t ON (r.account_tax_id = t.id)
                 WHERE %s AND "account_move_line".tax_exigible GROUP BY r.account_tax_id"""
        return sql

    def _compute_from_amls(self, options, taxes, period_number):
        sql = self._sql_from_amls_one()
        if options['form']['options']:
            sql = sql.replace('debit', 'debit_cash_basis').replace('credit', 'credit_cash_basis')
        user_types = self.env['account.account.type'].search([('type', 'in', ('receivable', 'payable'))])
        with_sql, with_params = self._get_with_statement(user_types)
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        query = sql % (tables, where_clause)
        self.env.cr.execute(with_sql + query, with_params + where_params)
        results = self.env.cr.fetchall()
        for result in results:
            if result[0] in taxes:
                taxes[result[0]]['periods'][period_number]['tax'] = result[1]
                taxes[result[0]]['show'] = True
        sql = self._sql_from_amls_two()
        if options.get('cash_basis'):
            sql = sql.replace('debit', 'debit_cash_basis').replace('credit', 'credit_cash_basis')
        query = sql % (tables, where_clause)
        self.env.cr.execute(with_sql + query, with_params + where_params)
        results = self.env.cr.fetchall()
        for result in results:
            if result[0] in taxes:
                taxes[result[0]]['periods'][period_number]['net'] = result[1]
                taxes[result[0]]['show'] = True

    @api.model
    def get_lines(self, options, line_id=None):
        taxes = {}
        for tax in self.env['account.tax'].search([]):
            taxes[tax.id] = {'obj': tax, 'show': False, 'periods': [{'net': 0, 'tax': 0}]}
        period_number = 0
        self.with_context(date_from=options['form']['date_from'], date_to=options['form']['date_to'])._compute_from_amls(options, taxes, period_number)
        lines = []
        types = ['sale', 'purchase']
        groups = dict((tp, {}) for tp in types)
        for key, tax in pycompat.items(taxes):
            if tax['obj'].type_tax_use == 'none':
                continue
            if tax['obj'].children_tax_ids:
                tax['children'] = []
                for child in tax['obj'].children_tax_ids:
                    if child.type_tax_use != 'none':
                        continue
                    tax['children'].append(taxes[child.id])
            if tax['obj'].children_tax_ids and not tax.get('children'):
                continue
            groups[tax['obj'].type_tax_use][key] = tax
        line_id = 0
        for tp in types:
            sign = tp == 'sale' and -1 or 1
            lines.append({
                    'id': tp,
                    'name': tp == 'sale' and _('Sale') or _('Purchase'),
                    'unfoldable': False,
                    'columns': [{} for k in range(0, 2*(period_number+1) or 2)],
                    'level': 2,
                })
            for key, tax in sorted(pycompat.items(groups[tp]), key=lambda k: k[1]['obj'].sequence):
                if tax['show']:
                    columns = []
                    for period in tax['periods']:
                        columns += [{'net': self.format_value(period['net'] * sign)},{'tax': self.format_value(period['tax'] * sign)}]
                    lines.append({
                        'id': tax['obj'].id,
                        'name': tax['obj'].name + ' (' + str(tax['obj'].amount) + ')',
                        'unfoldable': False,
                        'columns': columns,
                        'level': 1,
                        'caret_options': 'account.tax',
                    })
            line_id += 1
        return lines

    def format_value(self, value, currency=False):
        if self.env.context.get('no_format'):
            return value
        currency_id = currency or self.env.user.company_id.currency_id
        if currency_id.is_zero(value):
            # don't print -0.0 in reports
            value = abs(value)
        res = formatLang(self.env, value, currency_obj=currency_id)
        return res
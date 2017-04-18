# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestAccountInvoiceState(TransactionCase):

    post_install = True

    def test_00_account_invoice_state_flow(self):
        """Test Account Invoice State"""

        Account = self.env['account.account']
        AccountInvoice = self.env['account.invoice']

        # Code to skip chart of account
        if not Account.search_count([('company_id', '=', self.ref('base.main_company'))]):
            self.skipTest("No Chart of account found")

        # Find data account receivable
        receivable_account_id = Account.search([('user_type_id', '=', self.ref('account.data_account_type_receivable'))], limit=1).id
        # Find data account type expenses
        expence_account_id = Account.search([('user_type_id', '=', self.ref('account.data_account_type_expenses'))], limit=1).id
        # Create an invoice and confirm it with this wizard
        account_invoice = AccountInvoice.create({
            'partner_id': self.ref('base.res_partner_12'),
            'account_id': receivable_account_id,
            'invoice_line_ids': [(0, 0, {
                    'name': 'Computer SC234',
                    'account_id': expence_account_id,
                    'price_unit': 450.0,
                    'quantity': 1.0,
                    'product_id': self.ref('product.product_product_3'),
                    'uom_id': self.ref('product.product_uom_unit'),
                })]
        })

        # Check account invoice and account invoice_line created
        self.assertTrue(account_invoice, 'Account invoice not created')
        self.assertTrue(account_invoice.invoice_line_ids, 'Account invoice line not created')
        # Check account invoice state
        self.assertEqual(account_invoice.state, 'draft', 'Account: Invoice state should be draft')

        # Clicked on "Confirm Invoices" Button
        self.env['account.invoice.confirm'].with_context({"lang": 'en_US', "tz": False, "active_model": "account.invoice", "active_ids": [account_invoice.id], "type": "out_invoice",  "active_id": account_invoice.id }).invoice_confirm()

        # Check that customer invoice state is "Open"
        self.assertEqual(account_invoice.state, 'open', 'Account: invoice state should be open')

        # Check the journal associated and put this journal as not
        moves_line = self.env['account.move.line'].search([('invoice_id', '=', account_invoice.id)])
        # Check you have multiple move lines
        self.assertEqual(len(moves_line), 2, 'You should have multiple move lines')

        moves_line[0].journal_id.write({'update_posted': True})

        # Clicked on Cancel Invoices Button
        self.env['account.invoice.cancel'].with_context({"lang": 'en_US', "tz": False, "active_model": "account.invoice", "active_ids": [account_invoice.id], "type": "out_invoice",  "active_id": account_invoice.id }).invoice_cancel()
        # Check that customer invoice is in the cancel state
        self.assertEqual(account_invoice.state, 'cancel', 'Account: invoice state should be cancelled')

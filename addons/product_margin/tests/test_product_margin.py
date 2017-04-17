# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import tools
from odoo.tests import common
from odoo.modules.module import get_resource_path


class TestProductMargin(common.TransactionCase):

    def create_account_invoice(self, invoice_type, partner, quantity=0.0, price_unit=0.0):
        return self.env['account.invoice'].create({
            'partner_id': partner.id,
            'account_id': self.receivable_account_id if invoice_type == 'out_invoice' else self.payable_account_id,
            'type': invoice_type,
            'invoice_line_ids': [(0, 0, {
                        'name': self.ipad_product.name,
                        'account_id': self.expense_account_id if invoice_type == 'out_invoice' else self.product_sale_account_id,
                        'product_id': self.ipad_product.id,
                        'quantity': quantity,
                        'uom_id': self.uom_unit_id,
                        'price_unit': price_unit,
                    })],
        }).action_invoice_open()

    def test_product_margin(self):
        ''' In order to test the product_margin module '''

        # load account_minimal_test.xml file for chart of account in configuration
        tools.convert_file(self.cr, 'product_margin',
                           get_resource_path('account', 'test', 'account_minimal_test.xml'),
                           {}, 'init', False, 'test', self.registry._assertion_report)

        self.ipad_product = self.env.ref("product.product_product_4")
        self.payable_account_id = self.ref('product_margin.a_pay')
        self.receivable_account_id = self.ref('product_margin.a_recv')
        self.expense_account_id = self.ref('product_margin.a_expense')
        self.product_sale_account_id = self.ref('product_margin.a_sale')
        self.uom_unit_id = self.ref('product.product_uom_unit')

        self.supplier = self.env.ref("base.res_partner_1")
        self.customer = self.env.ref("base.res_partner_2")

        ''' Create supplier invoice and customer invoice to test product margin.'''

        # Define supplier invoice
        self.create_account_invoice('in_invoice', self.supplier, 10.0, 300.00)
        self.create_account_invoice('in_invoice', self.supplier, 4.0, 450.00)

        # Define Customer Invoice
        self.create_account_invoice('out_invoice', self.customer, 20.0, 750.00)
        self.create_account_invoice('out_invoice', self.customer, 10.0, 550.00)

        result = self.ipad_product._compute_product_margin_fields_values()

        # Sale turnover ( Quantity * Unit price)
        sale_turnover = ((20.0 * 750.00) + (10.0 * 550.00))

        # Expected sale (Total quantity * Sale price)
        sale_expected = (750.00 * 30.0)

        # Purchase total cost (Quantity * Unit price)
        purchase_total_cost = ((10.0 * 300.00) + (4.0 * 450.00))

        # Purchase normal cost ( Total quantity * Cost price)
        purchase_normal_cost = (14.0 * 500.00)

        total_margin = sale_turnover - purchase_total_cost
        expected_margin = sale_expected - purchase_normal_cost

        # Check total margin
        self.assertEqual(result[self.ipad_product.id]['total_margin'], total_margin, "Wrong Total Margin.")

        # Check expected margin
        self.assertEqual(result[self.ipad_product.id]['expected_margin'], expected_margin, "Wrong Expected Margin.")

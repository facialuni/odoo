# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_timesheet.tests.common import CommonTest


class TestSaleService(CommonTest):
    """ This test suite provide checks for miscellaneous small things. """

    def test_sale_service(self):
        """ Test task creation when confirming a sale_order with the corresponding product """
        sale_order_vals = {
            'partner_id': self.partner_usd.id,
            'partner_invoice_id': self.partner_usd.id,
            'partner_shipping_id': self.partner_usd.id,
            'order_line': [(0, 0, {
                'name': self.product_delivery_timesheet2.name,
                'product_id': self.product_delivery_timesheet2.id,
                'product_uom_qty': 50,
                'product_uom': self.product_delivery_timesheet2.uom_id.id,
                'price_unit': self.product_delivery_timesheet2.list_price
                }),
            ],
            'pricelist_id': self.pricelist_usd.id,
        }
        sale_order = self.env['sale.order'].create(sale_order_vals)
        sale_order.action_confirm()
        self.assertEqual(sale_order.invoice_status, 'no', 'Sale Service: there should be nothing to invoice after validation')

        # check task creation
        project = self.project_global
        task = project.task_ids.filtered(lambda t: t.name == '%s:%s' % (sale_order.name, self.product_delivery_timesheet2.name))
        self.assertTrue(task, 'Sale Service: task is not created')
        self.assertEqual(task.partner_id, sale_order.partner_id, 'Sale Service: customer should be the same on task and on SO')
        # register timesheet on task
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': project.id,
            'task_id': task.id,
            'unit_amount': 50,
            'employee_id': self.employee_manager.id,
        })
        self.assertEqual(sale_order.invoice_status, 'to invoice', 'Sale Service: there should be sale_ordermething to invoice after registering timesheets')
        sale_order.action_invoice_create()
        line = sale_order.order_line
        self.assertTrue(line.product_uom_qty == line.qty_delivered == line.qty_invoiced, 'Sale Service: line should be invoiced completely')
        self.assertEqual(sale_order.invoice_status, 'invoiced', 'Sale Service: SO should be invoiced')

    def test_timesheet_uom(self):
        """ Test timesheet invoicing and uom conversion """
        # create SO and confirm it
        uom_days = self.env.ref('product.product_uom_day')
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_usd.id,
            'partner_invoice_id': self.partner_usd.id,
            'partner_shipping_id': self.partner_usd.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_delivery_timesheet3.name,
                    'product_id': self.product_delivery_timesheet3.id,
                    'product_uom_qty': 5,
                    'product_uom': uom_days.id,
                    'price_unit': self.product_delivery_timesheet3.list_price
                })
            ],
            'pricelist_id': self.pricelist_usd.id,
        })
        sale_order.action_confirm()
        task = self.env['project.task'].search([('sale_line_id', '=', sale_order.order_line.id)])

        # let's log some timesheets
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': sale_order.project_project_id.id,
            'task_id': task.id,
            'unit_amount': 16,
            'employee_id': self.employee_manager.id,
        })
        self.assertEqual(sale_order.order_line.qty_delivered, 2, 'Sale: uom conversion of timesheets is wrong')

        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': sale_order.project_project_id.id,
            'task_id': task.id,
            'unit_amount': 24,
            'employee_id': self.employee_user.id,
        })
        sale_order.action_invoice_create()
        self.assertEqual(sale_order.invoice_status, 'invoiced', 'Sale Timesheet: "invoice on delivery" timesheets should not modify the invoice_status of the so')

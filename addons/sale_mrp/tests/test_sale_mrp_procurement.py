# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.addons.stock.tests.common2 import TestStockCommon


class TestSaleMrpProcurement(TestStockCommon):

    def setUp(self):
        super(TestSaleMrpProcurement, self).setUp()

        # Useful models
        self.ProcurementOrder = self.env['procurement.order']

        # Update the product_2 with type and route
        self.product_2.write({
            'type': 'product',
            'route_ids': [(6, 0, [self.warehouse_1.manufacture_pull_id.route_id.id, self.warehouse_1.mto_pull_id.route_id.id])],
        })
        # Create Bill of materials for product_2 with product quantity '1.0' and type 'normal'
        self.mrp_bom_product_2 = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_2.product_tmpl_id.id,
            'product_id': self.product_2.id,
        })

        # Create sale order for product_2 with shipping policy 'direct'
        self.sale_order = self.env['sale.order'].create({
            'client_order_ref': 'ref1',
            'name': 'Test_SO001',
            'date_order': datetime.today(),
            'warehouse_id': self.warehouse_1.id,
            'partner_id': self.partner_1.id,
            'pricelist_id': self.env.ref('product.list0').id,
            'order_line': [(0, 0, {'product_id': self.product_2.id, 'product_uom': self.product_2.uom_id.id, 'product_uom_qty': 500.0, 'price_unit': 200, 'customer_lead': 7.0})]
        })

    def test_procurement(self):
        '''Test that a procurement has been generated for sale order'''

        self.sale_order.action_confirm()
        procurements = self.ProcurementOrder.search([('origin', 'like', self.sale_order.name)])
        # Check procurement generated or not.
        self.assertEqual(len(procurements.ids), 2, 'No Procurements!')

        # Test that a procurement state is "running"
        procurements.run()
        procurements.filtered(lambda x: x.state != 'running')
        self.assertFalse(procurements.filtered(lambda x: x.state != 'running'), 'Procurement should be with a state "running".')

        # Test that a production order has been generated, and that its name and reference are correct
        production_order = procurements.mapped('production_id')
        self.assertTrue(production_order, 'Production order should be generated !')
        self.assertEqual(production_order.sale_name, self.sale_order.name, 'Wrong Name for the Production Order.')
        self.assertEqual(production_order.sale_ref, self.sale_order.client_order_ref, 'Wrong Sale Reference for the Production Order.')

    def test_cancellation_propagated(self):
        '''Check the propagation when we cancel the main procurement'''

        self.warehouse_1.write({'delivery_steps': 'pick_pack_ship', 'manufacture_to_resupply': True})
        # Confirm sale order
        self.sale_order.action_confirm()
        # Run scheduler
        self.ProcurementOrder.run_scheduler()
        procurements = self.ProcurementOrder.search([('group_id.name', '=', self.sale_order.name)])
        self.assertEqual(len(procurements.ids), 4, 'No procurements are found for sale order.')

        # Check that all procurements are running.
        self.assertFalse(procurements.filtered(lambda x: x.state != 'running'), 'Procurement should be with a state "running".')
        # Check that one production order exist
        production_order = procurements.mapped('production_id')
        self.assertEqual(len(production_order), 1, 'No production order found !')
        # Cancel the main procurement
        procurement = self.ProcurementOrder.search([('origin', '=', self.sale_order.name)])
        self.assertEqual(len(procurement.ids), 1, 'Main procurement not identified !')
        procurement.cancel()
        self.assertEqual(procurement.state, 'cancel', 'Main procurement should be cancelled !')

        # Check that the production order is running
        self.assertEqual(production_order.state, 'confirmed', 'Production order %d should be running since the pick does not propagate but is in state : %s!' %(production_order.id, production_order.state))

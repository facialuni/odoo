# -*- coding: utf-8 -*-

from odoo.addons.stock_dropshipping.tests.common import TestStockDropshippingCommon
import time
from odoo import tools
from odoo.modules.module import get_module_resource


class TestLifoPrice(TestStockDropshippingCommon):

    def _load(self, module, *args):
        tools.convert_file(
            self.cr, 'stock_dropshipping', get_module_resource(module, *args), {}, 'init', False, 'test', self.registry._assertion_report)

    def _create_purchase(self, product, product_qty=0.0, price_unit=0.0):
        return self.PurchaseOrder.create({
            'partner_id': self.partner_id,
            'order_line': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_qty': product_qty,
                'product_uom': self.uom_kg_id,
                'price_unit': price_unit,
                'date_planned': time.strftime('%Y-%m-%d'),
                })]
            })

    def test_lifoprice(self):
        """ Test that create Product and Purchase order to test LIFO category of Product."""

        self._load('account', 'test', 'account_minimal_test.xml')
        self._load('stock_account', 'test', 'stock_valuation_account.xml')

        # Set product category removal strategy as LIFO.
        product_category = self.env['product.category'].create({
            'name': 'Lifo Category',
            'removal_strategy_id': self.ref('stock.removal_lifo')})
        # Set a product as using lifo price.
        icecream = self.Product.create({
                'default_code': 'LIFO',
                'name': 'LIFO Ice Cream',
                'type': 'product',
                'categ_id': product_category.id,
                'list_price': 100.0,
                'standard_price': 70.0,
                'uom_id': self.uom_kg_id,
                'uom_po_id': self.uom_kg_id,
                'valuation': 'real_time',
                'cost_method': 'fifo',
                'property_stock_account_input': self.ref('stock_dropshipping.o_expense'),
                'property_stock_account_output': self.ref('stock_dropshipping.o_income'),
            })

        # I create a draft purchase Order for first in move for 10 kg at 60€/kg.
        purchase_order1 = self._create_purchase(product=icecream, product_qty=10.0, price_unit=60.0)

        # I create a draft purchase oder for second in move for 30 kg at 80€/kg.
        purchase_order2 = self._create_purchase(product=icecream, product_qty=30.0, price_unit=80.0)

        # I confirm the first purchase order.
        purchase_order1.button_confirm()
        #  I check the 'Approved' status of first purchase order.
        self.assertEqual(purchase_order1.state, 'purchase', 'Wrong state of purchase order!')
        pickings = purchase_order1.picking_ids
        wiz = self.env['stock.immediate.transfer'].create({'pick_id': pickings.id})
        wiz.process()

        # Check the standard price of the product (lifo icecream)
        self.assertEqual(icecream.standard_price, 70.0, 'Standard price should not have changed!')

        # I confirm the second purchase order and receive goods.
        purchase_order2.button_confirm()
        pickings = purchase_order2.picking_ids
        wiz = self.env['stock.immediate.transfer'].create({'pick_id': pickings.id})
        wiz.process()

        # Let us send some goods to customer.
        self.outgoing_shipment = self.Picking.create({
            'picking_type_id': self.pick_type_out_id,
            'location_id': self.stock_location_id,
            'location_dest_id': self.customer_location_id,
            'move_lines': [(0, 0, {
                'name': icecream.name,
                'product_id': icecream.id,
                'product_uom': self.uom_kg_id,
                'product_uom_qty': 20.0,
                'location_id':  self.stock_location_id,
                'location_dest_id': self.customer_location_id,
                'picking_type_id': self.pick_type_out_id})]
            })
        # I assign this outgoing shipment.
        self.outgoing_shipment.action_confirm()
        self.outgoing_shipment.action_assign()
        Wiz = self.env['stock.immediate.transfer'].create({'pick_id': self.outgoing_shipment.id})
        Wiz.process()
        self.assertEqual(self.outgoing_shipment.move_lines.value, -1400.0, 'Stock move value should have been 1400 euro')

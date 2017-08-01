# -*- coding: utf-8 -*-

# from odoo.tests import common
from odoo.addons.stock.tests.common2 import TestStockCommon


class TestWiseOperator(TestStockCommon):

    def test_00_wiseoperator(self):

        # Create a new stockable product
        self.product_wise = self.Product.create({
            'name': 'Wise Unit',
            'type': 'product',
            'categ_id': self.ref('product.product_category_1'),
            'uom_id': self.uom_unit_id,
            'uom_po_id': self.uom_unit_id
        })

        # Create an incoming picking for this product of 10 PCE from suppliers to stock
        self.pick1_wise = self.StockPicking.create({
            'name': 'Incoming picking (wise unit)',
            'partner_id': self.ref('base.res_partner_2'),
            'picking_type_id': self.picking_type_out_id,
            'location_id': self.supplier_location_id,
            'location_dest_id': self.stock_location_id,
            'move_lines': [(0, 0, {
                'product_id': self.product_wise.id,
                'name': self.product_wise.name,
                'product_uom_qty': 10.00,
                'location_id': self.supplier_location_id,
                'location_dest_id': self.stock_location_id,
                'product_uom': self.uom_unit_id,
            })],
        })

        # Confirm and assign picking and prepare partial
        self.pick1_wise.action_confirm()
        self.pick1_wise.action_assign()

        # Put 6 pieces in shelf1 and 4 pieces in shelf2
        self.package1 = self.Package.create({'name': 'Pack 1'})
        self.pick1_wise.move_line_ids[0][0].write({
            'result_package_id': self.package1.id,
            'qty_done': 4,
            'location_dest_id': self.ref('stock.stock_location_components')
        })
        self.env['stock.move.line'].create({
            'product_id': self.product_wise.id,
            'product_uom_id': self.uom_unit_id,
            'picking_id': self.pick1_wise.id,
            'qty_done': 6.0,
            'location_id': self.supplier_location_id,
            'location_dest_id': self.ref('stock.stock_location_14')
        })

        # Transfer the receipt
        self.pick1_wise.do_transfer()

        # Check the system created 2 quants
        self.records = self.StockQuant.search([('product_id', '=', self.product_wise.id)])
        self.assertEqual(len(self.records.ids), 2, "The number of quants created is not correct")

        # Make a delivery order of 5 pieces to the customer
        self.delivery_order_wise1 = self.StockPicking.create({
            'name': 'outgoing picking 1 (wise unit)',
            'partner_id': self.ref('base.res_partner_4'),
            'picking_type_id': self.picking_type_out_id,
            'location_id': self.stock_location_id,
            'location_dest_id': self.customer_location_id,
            'move_lines': [(0, 0, {
                'product_id': self.product_wise.id,
                'name': self.product_wise.name,
                'product_uom_qty': 5.00,
                'location_id': self.stock_location_id,
                'location_dest_id': self.customer_location_id,
                'product_uom': self.uom_unit_id
            })]
        })

        # Assign and confirm
        self.delivery_order_wise1.action_confirm()
        self.delivery_order_wise1.action_assign()
        self.assertEqual(self.delivery_order_wise1.state, 'assigned', 'wrong state in delivery oreder.')

        # Make a delivery order of 5 pieces to the customer
        self.delivery_order_wise2 = self.StockPicking.create({
            'name': 'outgoing picking 2 (wise unit)',
            'partner_id': self.env.ref('base.res_partner_4').id,
            'picking_type_id': self.picking_type_out_id,
            'location_id': self.stock_location_id,
            'location_dest_id': self.customer_location_id,
            'move_lines': [(0, 0, {
                'product_id': self.product_wise.id,
                'name': self.product_wise.name,
                'product_uom_qty': 5.00,
                'location_id': self.stock_location_id,
                'location_dest_id': self.customer_location_id,
                'product_uom': self.uom_unit_id,
            })]
        })

        # Assign and confirm
        self.delivery_order_wise2.action_confirm()
        self.delivery_order_wise2.action_assign()
        self.assertEqual(self.delivery_order_wise2.state, 'assigned', 'wrong state indelivery order.')
        location_id = self.delivery_order_wise1.move_line_ids.location_id.id
        loc_14 = self.ref('stock.stock_location_14')
        self.assertEqual(location_id, loc_14, 'stock store in same location.')

        # The operator is a wise guy and decides to do the opposite of what Odoo proposes.  He uses the products reserved on picking 1 on picking 2 and vice versa

        self.delivery_order_wise1.move_line_ids.write({'picking_id': self.delivery_order_wise2.id})
        self.delivery_order_wise2.move_line_ids.write({'picking_id': self.delivery_order_wise1.id})

        # put the move lines from picking2 into picking1
        new_move_lines = self.pick1_wise.move_line_ids.filtered(lambda p: p.qty_done)

        # The recompute remaining qtys does not take into account that pack operations change picking
        self.links = self.env['stock.move.operation.link'].search([('operation_id', 'in', self.delivery_order_wise1.move_line_ids.ids + self.delivery_order_wise2.move_line_ids.ids)])
        self.links.unlink()

        # Process this picking
        self.delivery_order_wise1.do_transfer()

        # Check there was no negative quant created by this picking
        self.records = self.StockQuant.search([('product_id', '=', self.product_wise.id), ('qty', '<', 0.0)])
        self.assertEqual(len(self.records.ids), 0, 'This should not have created a negative quant')

        # Check the other delivery order has changed its state back to partially available
        self.assertEqual(self.delivery_order_wise2.state, 'partially_available', "Delivery order 2 should be back in confirmed state")

        # Process the second picking
        self.delivery_order_wise2.do_transfer()

        # Check all quants are in Customers and there are no negative quants anymore
        self.records = self.StockQuant.search([('product_id', '=', self.product_wise.id)])
        self.assertTrue(all([x.location_id.id == self.customer_location_id and x.qty > 0.0 for x in self.records]), 'Wrong location detected')

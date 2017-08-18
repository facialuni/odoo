# -*- coding: utf-8 -*-

# Author: Tejas Shahu
# Date: 08/14/2017
from odoo.addons.stock.tests.common import TestStockCommon


class TestStockPickingWave(TestStockCommon):

    def setUp(self):
        super(TestStockPickingWave, self).setUp()
        self.ProductObj = self.env['product.product']
        self.PickingObj = self.env['stock.picking']
        # stocklocation 1
        self.stock_location1 = self.env.ref('stock.stock_location_stock')
        # stocklocation 2
        self.stock_location2 = self.env.ref('stock.stock_location_stock')
        # stocklocation 3
        self.stock_location3 = self.env.ref('stock.stock_location_stock')
        # picking_type 1
        self.picking_type_out1 = self.env['ir.model.data'].xmlid_to_res_id('stock.picking_type_out')
        # picking_type 2
        self.picking_type_out2 = self.env['ir.model.data'].xmlid_to_res_id('stock.picking_type_out')

        self.batch_picking = self.env['stock.picking.wave']

    def test_stock_picking_wave(self):

        # create three product
        print "\n\nTest case execution started\n\n"

        # Product Created A, B, C
        self.productA = self.ProductObj.create({'name': 'Product A', 'type': 'product'})
        self.productB = self.ProductObj.create({'name': 'Product B', 'type': 'product'})
        self.productC = self.ProductObj.create({'name': 'Product C', 'type': 'product'})

        print "\n\nThree Product created Successfully\n\n"

        # warehouse and it's three location
        print "\n\nWarehouse testcase called\n\n"

        # Create Warehouse
        self.warehouse_1 = self.env['stock.warehouse'].create({
            'name': 'Base Warehouse',
            'code': 'BWH'})

        print "\n\nwarehouse 1 created\n\n"

        # Locations
        self.location_1 = self.env['stock.location'].create({
            'name': 'TestLocation1',
            'location_id': self.warehouse_1.lot_stock_id.id,
        })

        print "\n\nlocation 1 created inside warehouse\n\n"

        self.location_2 = self.env['stock.location'].create({
            'name': 'TestLocation2',
            'location_id': self.warehouse_1.lot_stock_id.id,
        })

        self.location_3 = self.env['stock.location'].create({
            'name': 'TestLocation3',
            'location_id': self.warehouse_1.lot_stock_id.id,
        })

        print "\n\nWarehouse and it's 3 location created\n\n"
        print self.location_1.name, self.location_2.name, self.location_3.name

        # Update_Inventory

        print "\n\nUpdate Inventory called\n\n"

        # make some stock
        self.env['stock.quant']._update_available_quantity(
            self.productA, self.stock_location1, 100)

        self.assertEqual(len(self.env['stock.quant']._gather(
            self.productA, self.stock_location1)), 1.0)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(
            self.productA, self.stock_location1), 100.0)

        # check available stock 100 != 0
        # self.assertEqual(self.env['stock.quant']._get_available_quantity(
        #     self.productA, self.stock_location1), 0.0)

        # self.assertEqual(len(self.env['stock.quant']._gather(
        #     self.productA, self.stock_location1)), 0.0)

        print "\n\nlocation 1 stock updated:", self.stock_location1

        # make some stock
        self.env['stock.quant']._update_available_quantity(
            self.productB, self.stock_location2, 200)

        self.assertEqual(len(self.env['stock.quant']._gather(
            self.productB, self.stock_location2)), 1.0)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(
            self.productB, self.stock_location2), 200.0)

        # # check
        # self.assertEqual(self.env['stock.quant']._get_available_quantity(
        #     self.productB, self.stock_location2), 0.0)

        # self.assertEqual(len(self.env['stock.quant']._gather(
        #     self.productB, self.stock_location2)), 0.0)

        print "\n\nLocation 2 stock updated\n\n"

        # make some stock
        self.env['stock.quant']._update_available_quantity(
            self.productC, self.stock_location3, 300)

        self.assertEqual(len(self.env['stock.quant']._gather(
            self.productC, self.stock_location3)), 1.0)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(
            self.productC, self.stock_location3), 300.0)

        # # check
        # self.assertEqual(self.env['stock.quant']._get_available_quantity(
        #     self.productC, self.stock_location3), 0.0)

        # self.assertEqual(len(self.env['stock.quant']._gather(
        #     self.productC, self.stock_location3)), 0.0)

        print "\n\nLocation 3 stock updated\n\n"
        print "\n\nUpdate Inventory Ends\n\n" 

        # Outgoing shipment

        # ======================================================================
        #   Create Outgoing shipment with ...
        #   product A ( 10 Unit ) , product B ( 5 Unit )
        #   product C (  3 unit )
        # ======================================================================

        print "\n\nOutgoing shipment starts\n\n"

        picking_out1 = self.PickingObj.create({
            'partner_id': self.partner_agrolite_id,
            'picking_type_id': self.picking_type_out1,
            'location_id': self.stock_location1.id,
            'location_dest_id': self.customer_location})

        move_cust_a = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 10,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_out1.id,
            'location_id': self.stock_location1.id,
            'location_dest_id': self.customer_location})

        print "checking product A availability"

        # Check availability for product A
        aval_a_qty = self.MoveObj.search(
            [('product_id', '=', self.productA.id),
             ('picking_id', '=', picking_out1.id)],
            limit=1)

        print "\n\nOutgoing Shipment 1:\n\n", self.stock_location1

        # Confirm outgoing shipment.
        picking_out1.action_confirm()
        print "\n\npicking#1 state:", move_cust_a.state

        # Product assign to outgoing shipments
        picking_out1.action_assign()
        print "\n\npicking#1 state:", move_cust_a.state

        print "\n\nAval_a_qty:", aval_a_qty, "\nAval_a_qty:", aval_a_qty.reserved_availability
        print "\n\nproduct_uom_qty:", aval_a_qty.product_uom_qty

        self.assertEqual(
            aval_a_qty.product_uom_qty, 10.0, 
            'Wrong move quantity availability \
             of product A (%s found instead of 10)' % (aval_a_qty.product_uom_qty))

        # Second outgoing shipment
        print "\n\nOutgoing Shipment 2:\n\n", self.stock_location2

        picking_out2 = self.PickingObj.create({
            'partner_id': self.partner_agrolite_id,
            'picking_type_id': self.picking_type_out2,
            'location_id': self.stock_location2.id,
            'location_dest_id': self.customer_location})

        move_cust_b = self.MoveObj.create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 40,
            'product_uom': self.productB.uom_id.id,
            'picking_id': picking_out2.id,
            'location_id': self.stock_location2.id,
            'location_dest_id': self.customer_location})

        # Check availability for product B
        aval_b_qty = self.MoveObj.search(
            [('product_id', '=', self.productB.id),
             ('picking_id', '=', picking_out2.id)],
            limit=1)

        move_cust_c = self.MoveObj.create({
            'name': self.productC.name,
            'product_id': self.productC.id,
            'product_uom_qty': 20,
            'product_uom': self.productC.uom_id.id,
            'picking_id': picking_out2.id,
            'location_id': self.stock_location3.id,
            'location_dest_id': self.customer_location})

        # Check availability for product C
        aval_c_qty = self.MoveObj.search(
            [('product_id', '=', self.productC.id),
             ('picking_id', '=', picking_out2.id)],
            limit=1)

        # Confirm outgoing shipment.
        picking_out2.action_confirm()
        print "\n\npicking#2 state:", move_cust_b.state, move_cust_c.state

        # Product assign to outgoing shipments
        picking_out2.action_assign()
        print "\n\npicking#2 state:", move_cust_b.state, move_cust_c.state

        print "\n\nAval_b_qty:", aval_b_qty, "\nAval_b_qty:", aval_b_qty.reserved_availability
        print "\n\nproduct_uom_qty:", aval_b_qty.product_uom_qty

        self.assertEqual(
            aval_b_qty.product_uom_qty, 40.0, 
            'Wrong move quantity availability \
             of product B (%s found instead of 4)' % (aval_b_qty.product_uom_qty))

        print "\n\nAval_c_qty:", aval_c_qty, "\nAval_c_qty:", aval_c_qty.reserved_availability
        print "\n\nproduct_uom_qty:", aval_c_qty.product_uom_qty

        self.assertEqual(
            aval_c_qty.product_uom_qty, 20.0, 
            'Wrong move quantity availability \
             of product C (%s found instead of 4)' % (aval_c_qty.product_uom_qty))

        # Batch picking for two picking
        # self.batch_picking1 = self.batch_picking.create({
        #     'name': self.,
        #     'user_id': ,
        #     'picking_ids':
        #     })

        # picking_out = self.PickingObj.create({
        #     'partner_id': self.partner_agrolite_id,
        #     'picking_type_id': self.picking_type_out,
        #     'location_id': self.stock_location2,
        #     'location_dest_id': self.customer_location})
        # move_cust_b = self.MoveObj.create({
        #     'name': self.productB.name,
        #     'product_id': self.productB.id,
        #     'product_uom_qty': 5,
        #     'product_uom': self.productB.uom_id.id,
        #     'picking_id': picking_out.id,
        #     'location_id': self.stock_location2,
        #     'location_dest_id': self.customer_location})

        # # Third outgoing shipment
        # picking_out = self.PickingObj.create({
        #     'partner_id': self.partner_agrolite_id,
        #     'picking_type_id': self.picking_type_out,
        #     'location_id': self.stock_location3,
        #     'location_dest_id': self.customer_location})
        # move_cust_c = self.MoveObj.create({
        #     'name': self.productC.name,
        #     'product_id': self.productC.id,
        #     'product_uom_qty': 3,
        #     'product_uom': self.productC.uom_id.id,
        #     'picking_id': picking_out.id,
        #     'location_id': self.stock_location3,
        #     'location_dest_id': self.customer_location})
        # for move in picking_out.move_lines:
        #     self.assertEqual(move.state, 'confirmed', 'Wrong state of move line.')

        # self.assertEqual(move_cust_a.state, 'partially_available', 'Wrong state of move line.')

        # self.assertEqual(move_cust_b.state, 'assigned', 'Wrong state of move line.')
        # self.assertEqual(move_cust_c.state, 'assigned', 'Wrong state of move line.')
        # Check availability for product A

        # # Check availability for product B
        # aval_b_qty = self.MoveObj.search([('product_id', '=', self.productB.id), ('picking_id', '=', picking_out.id)], limit=1).reserved_availability
        # self.assertEqual(aval_b_qty, 5.0, 'Wrong move quantity availability of product B (%s found instead of 5)' % (aval_b_qty))
        # # Check availability for product C
        # aval_c_qty = self.MoveObj.search([('product_id', '=', self.productC.id), ('picking_id', '=', picking_out.id)], limit=1).reserved_availability
        # self.assertEqual(aval_c_qty, 3.0, 'Wrong move quantity availability of product C (%s found instead of 3)' % (aval_c_qty))

        print "Congratulations, Test case successfully executed"
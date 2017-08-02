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
            'picking_type_id': self.picking_type_in_id,
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

        # Put 4 pieces in shelf1 and 6 pieces in shelf2
        self.package1 = self.Package.create({'name': 'Pack 1'})
        self.pick1_wise.move_line_ids.write({
            'result_package_id': self.package1.id,
            'qty_done': 4,
            'location_dest_id': self.ref('stock.stock_location_components')
        })
        self.StockMoveLine.create({
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
        self.delivery_order_wise2.action_confirm()
        self.delivery_order_wise2.action_assign()
        self.assertEqual(self.delivery_order_wise2.state, 'assigned', 'wrong state in delivery order.')

        # The operator is a wise guy and decides to do the opposite of what Odoo proposes.  He uses the products reserved on picking 1 on picking 2 and vice versa

        loc_14 = self.ref('stock.stock_location_14')
        pack_ids1_loc = self.delivery_order_wise1.move_line_ids.location_id.id
        pack_ids2 = self.delivery_order_wise2.move_line_ids
        self.assertEqual(pack_ids1_loc, loc_14, 'wrong stock location.')
        self.assertEqual(set(pack_ids2.mapped('location_id.id')), set([self.ref('stock.stock_location_components'), loc_14]), 'worng location.')

        self.delivery_order_wise1.move_line_ids.write({'picking_id': self.delivery_order_wise2.id})
        self.delivery_order_wise2.move_line_ids.write({'picking_id': self.delivery_order_wise1.id})

        # put the move lines from picking2 into picking1
        picking1 = self.delivery_order_wise1
        picking2 = self.delivery_order_wise2
        pack_ids1 = self.delivery_order_wise1.move_line_ids
        move1 = self.delivery_order_wise1.move_lines[0]
        move2 = self.delivery_order_wise2.move_lines[0]
        for pack_id2 in pack_ids2:
            new_pack_id1 = pack_id2.copy(default={'picking_id': picking1.id, 'move_id': move1.id})
            new_pack_id1.qty_done = new_pack_id1.product_qty
            new_pack_id1.with_context(bypass_reservation_update=True).product_uom_qty = 0

        new_move_lines = picking1.move_line_ids.filtered(lambda p: p.qty_done)
        qty_sum = sum(new_move_lines.mapped('product_qty'))
        qty_done_sum = sum(new_move_lines.mapped('qty_done'))
        self.assertEqual(qty_sum, 0.0, 'wrong product quantity.')
        self.assertEqual(qty_done_sum, 5.0, 'wrong product done quantity.')
        self.assertEqual(set(new_move_lines.mapped('location_id.id')), set([self.ref('stock.stock_location_components'), loc_14]), 'wrong location')

        # put the move line from picking1 into picking2
        new_pack_id2 = pack_ids1[0].copy(default={'picking_id': self.delivery_order_wise1.id, 'move_id': move2.id})
        new_pack_id2.qty_done = new_pack_id2.product_qty
        new_pack_id2.with_context(bypass_reservation_update=True).product_uom_qty = 0

        new_move_lines = picking2.move_line_ids.filtered(lambda p: p.qty_done)

        # Process this picking
        self.delivery_order_wise1.do_transfer()

        # Check there was no negative quant created by this picking
        self.records = self.StockQuant.search([('product_id', '=', self.product_wise.id), ('quantity', '<', 0.0)])
        self.assertEqual(len(self.records.ids), 0, 'This should not have created a negative quant')

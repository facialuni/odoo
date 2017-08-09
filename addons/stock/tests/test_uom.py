from odoo.addons.stock.tests.common import TestStockCommon


class TestStockUOM(TestStockCommon):

    def test_pickings_transfer_with_different_uom_and_back_orders(self):
        """ Picking transfer with diffrent unit of meassure. """

        # weight category
        categ_test = self.env['product.uom.categ'].create({'name': 'Bigger than tons'})

        T_LBS = self.env['product.uom'].create({
            'name': 'T-LBS',
            'category_id': categ_test.id,
            'uom_type': 'reference',
            'rounding': 0.01
        })
        T_GT = self.env['product.uom'].create({
            'name': 'T-GT',
            'category_id': categ_test.id,
            'uom_type': 'bigger',
            'rounding': 0.0000001,
            'factor_inv': 2240.00,
        })
        T_TEST = self.env['product.product'].create({
            'name': 'T_TEST',
            'type': 'product',
            'uom_id': T_LBS.id,
            'uom_po_id': T_LBS.id,
            'tracking': 'lot',
        })
        picking_in = self.env['stock.picking'].create({
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location
        })
        move = self.env['stock.move'].create({
            'name': 'First move with 60 GT',
            'product_id': T_TEST.id,
            'product_uom_qty': 60,
            'product_uom': T_GT.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location
        })
        picking_in.action_confirm()

        self.assertEqual(move.product_uom_qty, 60.00, 'Wrong T_GT quantity')
        self.assertEqual(move.product_qty, 134400.00, 'Wrong T_LBS quantity')

        lot = self.env['stock.production.lot'].create({'name': 'Lot TEST', 'product_id': T_TEST.id})
        self.env['stock.move.line'].create({
            'move_id': move.id,
            'product_id': T_TEST.id,
            'product_uom_id': T_LBS.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'qty_done': 42760.00,
            'lot_id': lot.id,
        })

        picking_in.action_done()
        back_order_in = self.env['stock.picking'].search([('backorder_id', '=', picking_in.id)])

        self.assertEqual(len(back_order_in), 1.00, 'There should be one back order created')
        self.assertEqual(back_order_in.move_lines.product_qty, 91640.00, 'There should be one back order created')

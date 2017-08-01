from odoo.addons.stock.tests.common2 import TestStockCommon


class TestPacking(TestStockCommon):

    def test_create_packing(self):
        """ Test packaging with shipments"""

        partner2 = self.ref('base.res_partner_2')
        # Create a new stackable product """
        hardisk = self.Product.create({
                            "name": "SSD HDD",
                            "type": "product",
                            "categ_id": self.ref("product.product_category_1"),
                            "list_price": 100.0,
                            "standard_price": 70.0,
                            "seller_ids": [(0, 0, {"delay": 1,
                                                   "name": partner2,
                                                   "min_qty": 2.0})],
                    })

        # Create an incoming picking for this hardisk of 300 PCE from suppliers to stock
        picking_in = self.StockPicking.create({
                        "name": "Incoming picking",
                        "partner_id": partner2,
                        "picking_type_id": self.picking_type_in_id,
                        "location_id": self.supplier_location_id,
                        "location_dest_id": self.stock_location_id
            })
        self._create_move(hardisk, self.supplier_location_id, self.stock_location_id, **{"product_uom_qty": 300, "picking_id": picking_in.id})
        # Confirm and assign picking and prepare partial
        picking_in.action_confirm()
        picking_in.action_assign()

        # ----------------------------------------------------------------------
        # Put 120 pieces on Pallet 1 (package), 120 pieces on Pallet 2 with lot A and 60 pieces on Pallet 3
        # ----------------------------------------------------------------------

        # Create lot A
        lot_a = self.ProductionLot.create({'name': 'Lot A', 'product_id': hardisk.id})

        # Create package
        package1 = self.Package.create({'name': 'Pallet 1'})
        package2 = self.Package.create({'name': 'Pallet 2'})
        package3 = self.Package.create({'name': 'Pallet 3'})

        # Change operation line.
        picking_in.move_line_ids[0].write({'result_package_id': package1.id, 'qty_done': 120})
        self.StockMoveLine.create({
          'product_id': hardisk.id,
          'product_uom_id': self.uom_unit_id,
          'picking_id': picking_in.id,
          'lot_id': lot_a.id,
          'result_package_id': package2.id,
          'qty_done': 120,
          'location_id': self.supplier_location_id,
          'location_dest_id': self.stock_location_id
        })
        self.StockMoveLine.create({
          'product_id': hardisk.id,
          'product_uom_id': self.uom_unit_id,
          'picking_id': picking_in.id,
          'result_package_id': package3.id,
          'qty_done': 60,
          'location_id': self.supplier_location_id,
          'location_dest_id': self.stock_location_id
        })
        # Transfer the receipt.
        picking_in.do_transfer()

        # ----------- Test after receive goods ---------------------------------

        # Check the system created 3 quants one with 120 pieces on pallet 1, one with 120 pieces on pallet 2 with lot A and 60 pieces on pallet 3
        self._check_system_created_quants(hardisk)
        # Check there is no backorder or extra moves created
        self._check_no_back_order(picking_in)

        # ----------------------------------------------------------------------

        # Make a delivery order of 300 pieces hardisk to the customer
        picking_out = self.StockPicking.create({
                                    "name": "outgoing picking",
                                    "partner_id": self.env.ref("base.res_partner_4").id,
                                    "picking_type_id": self.picking_type_out_id,
                                    "location_id": self.stock_location_id,
                                    "location_dest_id": self.customer_location_id
                            })
        self._create_move(hardisk, self.stock_location_id, self.customer_location_id, **{"product_uom_qty": 300.00, "picking_id": picking_out.id})

        # Confirm and assign
        picking_out.action_confirm()
        picking_out.action_assign()

        # Instead of doing the 300 pieces, you decide to take pallet 1 (do not mention product in operation here) and 20 pieces from lot A and 10 pieces from pallet 3
        for rec in picking_out.move_line_ids:
            if rec.package_id.name == 'Pallet 1':
                rec.qty_done = 120
            if rec.package_id.name == 'Pallet 2':
                rec.qty_done = 20
            if rec.package_id.name == 'Pallet 3':
                rec.qty_done = 10
        # Transfer the delivery.
        picking_out.do_transfer()

        # ------------------- Test after transfer partial goods ----------------

        # Check existing quants in stock for hardisk.
        self._check_the_quants(hardisk)
        # Check a backorder was created and on that backorder, prepare partial and process backorder
        backorder = self.StockPicking.search([('backorder_id', '=', picking_out.id)])
        self.assertTrue(backorder, "Backorder should have been created")
        backorder.action_assign()
        picking_out_bo = backorder[0]
        self.assertEqual(len(picking_out_bo.move_line_ids), 2, "Wrong number of pack operation")
        for pack_op in picking_out_bo.move_line_ids:
            self.assertTrue(pack_op.package_id.name in ('Pallet 2', 'Pallet 3'), "Wrong pallet info in pack operation (%s found)" % (pack_op.package_id.name))
            if pack_op.package_id.name == 'Pallet 2':
                self.assertEquals(pack_op.product_qty, 100)
                pack_op.qty_done = 100
            elif pack_op.package_id.name == 'Pallet 3':
                self.assertEquals(pack_op.product_qty, 50)
                pack_op.qty_done = 50
        # Transfer the delivery.
        picking_out_bo.do_transfer()
        # Check there are still 0 pieces in stock
        product_quants = self.StockQuant.search([('product_id', '=', hardisk.id), ('location_id', '=', self.stock_location_id)])
        total_qty = sum(product_quants.mapped('quantity'))
        self.assertEqual(total_qty, 0, "Total quantity in stock should be 0 as the backorder took everything out of stock")
        self.assertEqual(hardisk.qty_available, 0, "Quantity available should be 0 too")

    def _check_system_created_quants(self, product):
        quants = self.StockQuant.search([('product_id', '=', product.id)])
        self.assertEqual(len(quants.ids), 3, "The number of quants created is not correct")
        for quant in quants:
            if quant.package_id.name == 'Pallet 1':
                self.assertEqual(quant.quantity, 120, "Should have 120 pieces on pallet 1")
            elif quant.package_id.name == 'Pallet 2':
                self.assertEqual(quant.quantity, 120, "Should have 120 pieces on pallet 2")
            elif quant.package_id.name == 'Pallet 3':
                self.assertEqual(quant.quantity, 60, "Should have 60 pieces on pallet 3")

    def _check_no_back_order(self, picking):
        backorder = self.StockPicking.search([('backorder_id', '=', picking.id)])
        self.assertFalse(backorder)
        # Check extra moves created
        self.assertEqual(len(picking.move_lines), 1)

    def _check_the_quants(self, product):
        product_quants = self.StockQuant.search([('product_id', '=', product.id)])
        for quant in product_quants:
            if quant.package_id.name == 'Pallet 2' and quant.location_id.id == self.stock_location_id:
                self.assertEqual(quant.quantity, 100, "Should have 100 pieces on pallet 2, got %s" % quant.quantity)
            elif quant.package_id.name == 'Pallet 3' and quant.location_id.id == self.stock_location_id:
                self.assertEqual(quant.quantity, 50, "Should have 50 pieces in stock on pallet 3")
            else:
                self.assertFalse(True, "Unrecognized quant")

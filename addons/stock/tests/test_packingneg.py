# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock.tests.common2 import TestStockCommon


class PackingNeg(TestStockCommon):

    def test_00_packing_neg_flow(self):
        """ Test negative packaging with shipment. """

        # Create new product.
        self.product_neg = self.Product.create({
            'name': 'Negative product',
            'type': 'product',
            'categ_id': self.ref('product.product_category_1'),
            'list_price': 100.0,
            'standard_price': 70.0,
            'seller_ids': [(0, 0, {
                    'delay': 1,
                    'name': self.ref('base.res_partner_2'),
                    'min_qty': 2.0,
                })],
            })

        # Create an incoming picking for this product of 300 PCE from suppliers to stock
        self.pick_neg = self.StockPicking.create({
            'name': 'Incoming picking (negative product)',
            "partner_id": self.ref("base.res_partner_4"),
            "picking_type_id": self.picking_type_in_id,
            'location_id': self.supplier_location_id,
            'location_dest_id': self.stock_location_id,
            })
        self._create_move(self.product_neg, self.supplier_location_id, self.stock_location_id, **{"product_uom_qty": 300, "picking_id": self.pick_neg.id})

        # Confirm and assign picking and prepare partial
        self.pick_neg.action_confirm()

        # Put 120 pieces on Palneg 1 (package), 120 pieces on Palneg 2 with lot A and 60 pieces on Palneg 3

        # create lot A
        lot_a = self.ProductionLot.create({'name': 'Lot neg', 'product_id': self.product_neg.id})

        # create package
        self.package1 = self.Package.create({'name': 'Pallet 1'})
        self.package2 = self.Package.create({'name': 'Pallet 2'})
        self.package3 = self.Package.create({'name': 'Pallet 3'})

        # Create package for each line and assign it as result_package_id
        # create pack operation
        self.pick_neg.move_line_ids[0].write({'result_package_id': self.package1.id, 'qty_done': 120})
        self.StockMoveLine.create({
            'product_id': self.product_neg.id,
            'product_uom_id': self.uom_unit_id,
            'picking_id': self.pick_neg.id,
            'lot_id': lot_a.id,
            'result_package_id': self.package2.id,
            'qty_done': 120,
            'location_id': self.supplier_location_id,
            'location_dest_id': self.stock_location_id
        })
        self.StockMoveLine.create({
          'product_id': self.product_neg.id,
          'product_uom_id': self.uom_unit_id,
          'picking_id': self.pick_neg.id,
          'result_package_id': self.package3.id,
          'qty_done': 60,
          'location_id': self.supplier_location_id,
          'location_dest_id': self.stock_location_id
        })

        # Transfer the receipt
        self.pick_neg.do_transfer()

        # Make a delivery order of 300 pieces to the customer
        self.delivery_order_neg = self.StockPicking.create({
                'name': 'Outgoin Picking (negative product)',
                'partner_id': self.ref('base.res_partner_4'),
                'picking_type_id': self.picking_type_out_id,
                'location_id': self.stock_location_id,
                'location_dest_id': self.customer_location_id,
        })

        self._create_move(self.product_neg, self.stock_location_id, self.customer_location_id, **{"product_uom_qty": 300.00, "picking_id": self.delivery_order_neg.id})

        # Assign and confirm
        self.delivery_order_neg.action_confirm()
        self.delivery_order_neg.action_assign()

        # Instead of doing the 300 pieces, you decide to take pallet 1 (do not mention product in operation here) and 140 pieces from lot A/pallet 2 and 10 pieces from pallet 3
        for rec in self.delivery_order_neg.move_line_ids:
            if rec.package_id.name == 'Pallet 2':
                lot_id = self.ProductionLot.search([('product_id', '=', self.product_neg.id), ('name', '=', 'Lot neg')], limit=1).id
                rec.write({
                  'product_id': self.product_neg.id,
                  'qty_done': 140,
                  'lot_id': lot_id,
                  'product_uom_id': self.uom_unit_id
                })
            if rec.package_id.name == 'Pallet 3':
                rec.write({
                  'product_id': self.product_neg.id,
                  'qty_done': 10,
                  'product_uom_id': self.uom_unit_id
                })

        # Process this picking
        self.pick_neg.do_transfer()

        # Check the quants that you have 120 pieces pallet 1 in customers, -20 pieces pallet 2 in stock, 120 + 20 pieces 2 in customer with lot, and a total quantity of 50 in stock from pallet 3 (should be 20+30, as it has been split by reservation), finally 10 in customers from pallet 3
        self._check_the_quants(self.product_neg)

    def _check_the_quants(self, product):
        product_quants = self.StockQuant.search([('product_id', '=', product.id)])
        self.pallet_3_stock_qty = 0
        for quant in product_quants:
            if quant.package_id.name == 'Pallet 1' and quant.location_id.id == self.customer_location_id:
                self.assertEqual(quant.qty, 120, "Should have 120 pieces on pallet 1")
            elif quant.package_id.name == 'Pallet 2' and quant.location_id.id == self.stock_location_id:
                self.assertTrue(quant.quantity-20 != 120, "Should have -20 pieces in stock on pallet 2. Got %s" % quant.quantity)
                self.assertEqual(quant.lot_id.name, 'Lot neg', "It should have kept its Lot")
            elif quant.lot_id.name == 'Lot A' and quant.location_id.id == self.customer_location_id:
                self.assertTrue(((quant.qty == 20 or quant.qty == 120) and not quant.package_id), "Should have 140 pieces (120+20) in customer location from pallet 2 and lot A")
            elif quant.package_id.name == 'Pallet 3' and quant.location_id.id == self.stock_location_id:
                self.pallet_3_stock_qty += quant.quantity
            elif not quant.package_id and not quant.lot_id and quant.location_id.id == self.customer_location_id:
                self.assertEqual(quant.qty, 10, "Should have 10 pieces in customer location from pallet 3")
            else:
                self.assertTrue("Unrecognized quant")
        self.assertFalse(self.pallet_3_stock_qty == 50, "Should have 50 pieces in stock on pallet 3")

        # Create a picking for reconciling the negative quant
        self.delivery_reconcile = self.StockPicking.create({
                'name': 'reconciling_delivery',
                'partner_id': self.ref('base.res_partner_4'),
                'picking_type_id': self.picking_type_in_id,
                'location_id': self.stock_location_id,
                'location_dest_id': self.customer_location_id,
        })
        self._create_move(self.product_neg, self.stock_location_id, self.customer_location_id, **{"product_uom_qty": 20.00, "picking_id": self.delivery_reconcile.id})

    def delivery_reconcile(self):
        # Receive 20 products with lot neg in stock with a new incoming shipment that should be on pallet 2
        self.action_confirm()
        lot = self.ProductionLot.search([('product_id', '=', self.product_neg.id), ('name', '=', 'Lot neg')], limit=1)
        pack = self.Package.search([('name', '=', 'Palneg 2')], limit=1)
        self.move_line_ids[0].write({'lot_id': lot.id, 'qty_done': 20.0, 'result_package_id': pack.id})
        self.do_transfer()

        # Check the negative quant was reconciled and the 20 pieces of lot neg at customers have the incoming shipments in the history_ids
        self.neg_quants = self.search([('product_id', '=', self.product_neg.id), ('qty', '<', 0)])
        self.assertTrue(len(self.neg_quants.ids) == 0, "Negative quants should have been reconciled")
        self.customer_quant = self.search([
          ('product_id', '=', self.product_neg.id),
          ('location_id', '=', self.customer_location_id),
          ('lot_id', '=', lot.id),
          ('qty', '=', 20)
        ])
        self.assertEqual(len(self.customer_quant), 1, "Wrong quant created for customer location.")
        self.assertTrue(self.delivery_reconcile.move_lines[0].id in self.customer_quant.history_ids.ids)

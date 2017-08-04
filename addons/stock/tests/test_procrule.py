from odoo.addons.stock.tests.common2 import TestStockCommon


class TestProcrule(TestStockCommon):

    def test_00_create_product_route(self):
        """  Create a product route containing a procurement rule that will
      generate a move from Stock for every procurement created in Output """

        # Create new product.
        product = self.Product.create({
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

        # define new route...
        product_route = self.env['stock.location.route'].create({
            "name": "Stock -> output rule",
            "product_selectable": True,
            "pull_ids": [(0, 0, {
                "name": "Stock -> output rule",
                "action": "move",
                "picking_type_id": self.picking_type_int_id,
                "location_src_id": self.stock_location_id,
                "location_id": self.output_location_id,
                })]
        })

        # Set route on product
        product.write({'route_ids': [(4, product_route.id)]})

        # Create Delivery Order of 10 ( from Output -> Customer )
        pick_output = self.StockPicking.create({
                            "name": "Delivery order for procurement",
                            "partner_id": self.ref("base.res_partner_2"),
                            "picking_type_id": self.picking_type_out_id,
                            "location_id": self.output_location_id,
                            "location_dest_id": self.customer_location_id})

        # Create Move
        self._create_move(product, self.env.ref("stock.stock_location_output"), self.env.ref("stock.stock_location_output"), **{"product_uom_qty": 10.0, "procure_method": "make_to_order", "picking_id": pick_output.id})
        # Confirm delivery order.
        pick_output.action_confirm()

        # Check that a picking was created from stock to output.
        moves = self.StockMove.search([
          ('product_id', '=', product.id),
          ('location_id', '=', self.stock_location_id),
          ('location_dest_id', '=', self.output_location_id),
          ('move_dest_ids', '=', pick_output.move_lines.id)
        ])

        # It should have created a picking from Stock to Output with the original picking as destination

        self.assertEqual(len(moves.ids), 1, 'should not created a move')

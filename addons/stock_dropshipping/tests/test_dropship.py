# -*- coding: utf-8 -*-

from odoo.addons.stock_dropshipping.tests.common import TestStockDropshippingCommon


class TestDropship(TestStockDropshippingCommon):

    def test_00_dropship(self):
        """Test drop shipping Flow"""

        supplier_dropship = self.Partner.create({'name': 'Vendor of Dropshipping test'})

        # Creating Product
        product = self.Product.create({
            'name': "pendrive",
            'list_price': 100.0,
            'standard_price': 70.0,
            'type': "product",
            'categ_id': self.category_all.id,
            'seller_ids': [(0, 0, {'delay': 1, 'name': supplier_dropship.id, 'min_qty': 2.0})]})

        # Creating Sale Order
        sale_order_drp_shpng = self._create_sale_order(
                                        partner_id=self.partner.id,
                                        product=product,
                                        product_qty=200,
                                        uom_id=self.uom_unit.id)
        # Set route on sale order line
        sale_order_drp_shpng.order_line.route_id = self.ref('stock_dropshipping.route_drop_shipping')
        # Confirm sale order
        sale_order_drp_shpng.action_confirm()

        # Check the sales order created a procurement group which has a procurement of 200 pieces
        procurement_order = self.ProcurementOrder.search([('group_id', '=', sale_order_drp_shpng.procurement_group_id.id)], limit=1)
        self.assertEquals(procurement_order.product_qty, 200.0, 'procurement group should have 200 pieces.')

        # Check a quotation was created to a certain vendor and confirm so it becomes a confirmed purchase order
        purchase = self.PurchaseOrder.search([('partner_id', '=', supplier_dropship.id)])
        self.assertEquals(len(purchase), 1, 'There should be one purchase order.')
        # Confirm Purchase order
        purchase.button_confirm()
        self.assertEquals(purchase.state, 'purchase', 'Purchase order should be in the approved state')

        # Use 'Receive Products' button to immediately view this picking, it should have created a picking with 200 pieces
        # Send the 200 pieces.
        pickings = purchase[0].picking_ids
        wiz = self.env['stock.immediate.transfer'].create({'pick_id': pickings.id})
        wiz.process()

        # Check one move line was created in Customers location
        move_line = self.env['stock.move.line'].search([('location_dest_id', '=', self.customer_location_id), ('product_id', '=', product.id)])
        self.assertEquals(len(move_line.ids), 1, 'There should be exactly one move line')
        deliver_qty = sale_order_drp_shpng.order_line.qty_delivered
        self.assertEquals(deliver_qty, 200, 'Wrong delivered quantity on sale order.')

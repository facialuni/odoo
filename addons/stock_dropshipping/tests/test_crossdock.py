from odoo.addons.stock_dropshipping.tests.common import TestStockDropshippingCommon


class TestCrossdock(TestStockDropshippingCommon):

    def test_00_crossdock(self):
        """ Test the sales/purchase order flow with cross dock. """

        # set a warehouse in'two_steps' reception steps
        self.warehouse.reception_steps = 'two_steps'

        # Creating Product
        pendrive = self.Product.create({
            'name': "pendrive",
            'list_price': 100.0,
            'standard_price': 70.0,
            'type': "product",
            'categ_id': self.category_all.id,
            'seller_ids': [(0, 0, {'delay': 1, 'name': self.partner.id, 'min_qty': 2.0})]})

        # Creating Sale Order
        sale_order_crossdock = self._create_sale_order(
                                        partner_id=self.partner.id,
                                        product=pendrive,
                                        product_qty=100,
                                        uom_id=self.uom_unit.id)

        # Check that cross-dock route active or not.
        self.assertTrue(self.warehouse.crossdock_route_id.active, "Crossdock route should be active when reception_steps is not in 'single_step'")

        # Set cross dock route on order line.
        sale_order_crossdock.order_line.write({'route_id': self.warehouse.crossdock_route_id.id})

        # Confirming Sale Order
        sale_order_crossdock.action_confirm()

        # Searching purchase Order by their partner.
        purchase_order = self.PurchaseOrder.search([('partner_id', '=', self.partner.id), ('state', '=', 'draft')])

        # Check purchase order created or not.
        self.assertTrue(purchase_order, 'No Purchase order!')

        # Confirming Purchase Order
        purchase_order.button_confirm()

    def test_01_procurement_exceptions(self):
        """ Test procurement exception when no supplier define on product with cross dock route. """

        # set a warehouse in 'two_steps' reception steps
        self.warehouse.reception_steps = 'two_steps'

        product_with_no_seller = self.Product.create({
            'name': 'pendrive',
            'list_price': 20.0,
            'standard_price': 15.00,
            'categ_id': self.category_all.id})

        # Creating Sale Order
        sale_order_crossdock = self._create_sale_order(
                                        partner_id=self.partner.id,
                                        product=product_with_no_seller,
                                        product_qty=1,
                                        uom_id=self.uom_unit.id)

        # Set route on sale order line
        sale_order_crossdock.order_line.write({'route_id': self.warehouse.crossdock_route_id.id})

        # Confirm sale order
        sale_order_crossdock.action_confirm()

        # Procurement should be in exception state.
        proc = self.ProcurementOrder.search([('group_id', '=', sale_order_crossdock.procurement_group_id.id), ('state', '=', 'exception')])
        self.assertTrue(proc, 'No procurement in exception state !')

        # Set the at least one supplier on the product.
        product_with_no_seller.write({'seller_ids': [(0, 0, {'delay': 1, 'name': self.partner.id, 'min_qty': 2.0})]})

        # Run procurement again.
        proc.run()

        # Check the status changed there is no procurement order in exception any more from that procurement group
        self.assertEquals(proc.state, 'running', 'Procurement should be in running state.')

        # Check a purchase quotation was created or not.
        purchase_order = proc.purchase_line_id.order_id
        self.assertTrue(purchase_order, 'No Purchase order!')
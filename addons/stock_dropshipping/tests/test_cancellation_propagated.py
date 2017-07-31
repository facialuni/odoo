# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_dropshipping.tests.common import TestStockDropshippingCommon


class TestCancellationPropagated(TestStockDropshippingCommon):

    def test_cancelation_propogation(self):
        """ Test cancellation propagation """

        # Supplier
        partner_id = self.ref('base.res_partner_2')

        # Useful Reference
        uom_dozen_id = self.ref('product.product_uom_dozen')

        # Create a new product
        pendrive = self.Product.create({
            'name': 'Pendrive',
            'type': 'product',
            'seller_ids': [(0, 0, {
                'delay': 1,
                'name': partner_id,
                'min_qty': 2.0,
                 })]
            })

        # Create a sales order of 5 Units "My Product"
        saleorder_1 = self._create_sale_order(
                                        partner_id=self.partner_id,
                                        product=pendrive,
                                        product_qty=5.00,
                                        uom_id=self.uom_unit.id)

        # Create another sales order with 2 Dozen of "My Product"
        saleorder_2 = self._create_sale_order(
                                        partner_id=self.ref('base.res_partner_4'),
                                        product=pendrive,
                                        product_qty=2.00,
                                        uom_id=uom_dozen_id)

        # Set routes on product to be MTO and Buy
        pendrive.write({'route_ids': [(6, 0, [self.warehouse.mto_pull_id.route_id.id, self.warehouse.buy_pull_id.route_id.id])]})

        # Confirm sales orders
        saleorder_1.action_confirm()
        saleorder_2.action_confirm()

        """ Check the propagation when we cancel the main procurement
            * Retrieve related procurements and check that there are all running
            * Check that a purchase order is well created
            * Cancel the main procurement
            * Check that all procurements related and the purchase order are well canceled
        """

        # Check procurements created or not.
        procus = self.ProcurementOrder.search([('group_id.name', 'in', [saleorder_1.name, saleorder_2.name])])
        self.assertEquals(len(procus), 8, 'No procurement found!')

        # Check all procurement should be in 'running' state.
        self.assertEquals(set(procus.mapped('state')), set(['running']), "Wrong state on procurement !")

        # Check single purchase order created or not.
        purchases = procus.mapped('purchase_line_id').mapped('order_id')

        # Check that one purchase order has been created
        self.assertEquals(len(purchases), 1, 'No purchase order found !')

        # Check purchase order line
        # -------------------------

        purchase_line = purchases.order_line
        self.assertEquals(len(purchase_line), 1, 'No purchase order found !')
        self.assertEquals(len(purchase_line.procurement_ids), 2, 'Wrong procurement on order line !')
        self.assertEquals(purchase_line.product_qty, 29.0, "The product quantity of the order line should be 29 and not %s" % (purchase_line.product_qty,))
        self.assertEquals(purchase_line.product_uom.id, self.uom_unit.id, "The product uom of the order line should be %s and not %s" % (self.uom_unit.name, purchase_line.product_uom.name,))

        # Cancel the sales order of 2 dozen.
        # ----------------------------------

        saleorder_2.action_cancel()
        procs2_cancel = self.ProcurementOrder.search([('group_id.name', '=', saleorder_2.name), ('rule_id', '!=', self.warehouse.buy_pull_id.id)])
        procs2_running = self.ProcurementOrder.search([('group_id.name', '=', saleorder_2.name), ('rule_id', '=', self.warehouse.buy_pull_id.id)])
        self.assertEquals(set(procs2_cancel.mapped('state')), set(['cancel']), "Procurement should be cancelled.")
        self.assertEquals(set(procs2_running.mapped('state')), set(['running']), "Procurement with buy rule should be in running state")

        # Cancel sales order of 5 unit.
        # ----------------------------

        saleorder_1.action_cancel()
        procs_cancel = self.ProcurementOrder.search([('group_id.name', '=', saleorder_1.name), ('rule_id', '!=', self.warehouse.buy_pull_id.id)])
        procs_running = self.ProcurementOrder.search([('group_id.name', '=', saleorder_1.name), ('rule_id', '=', self.warehouse.buy_pull_id.id)])
        self.assertEquals(set(procs_cancel.mapped('state')), set(['cancel']), "Procurement should be cancelled.")
        self.assertEquals(set(procs_running.mapped('state')), set(['running']), "Procurement with buy rule should be in running state")
        self.assertEquals(len(purchases.order_line), 1, 'The PO line should not have been unlinked since the pick does not cancel the delivery nor the purchase!')

        # Check that all procurements related are cancelled or not.
        self.assertEquals(set(procus.mapped('state')), set(['cancel', 'running']), "Procurement all should not be cancelled !")

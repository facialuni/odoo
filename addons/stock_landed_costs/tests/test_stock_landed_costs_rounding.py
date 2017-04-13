# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_landed_costs.tests.common import TestStockLandedCostsCommon


class TestLandedCostsRounding(TestStockLandedCostsCommon):

    def _create_landed_cost(self, price_unit, pickings):
        return self.LandedCost.create({
            'picking_ids': [(6, 0, pickings.ids)],
            'account_journal_id': self.expenses_journal.id,
            'cost_lines': [
                (0, 0, {
                    'name': 'equal split',
                    'split_method': 'equal',
                    'price_unit': price_unit,
                    'product_id': self.landed_cost.id})]
                })

    def test_00_landed_cost_rounding(self):
        """ Test the rounding in landed costs """

        product_rounding = self._create_product('Product Rounding', uom_id=self.product_uom_unit_round_1.id)
        picking_in_1 = self._create_shipment(product_rounding, self.product_uom_unit_round_1.id, self.picking_type_in_id, self.customer_location_id, self.stock_location_id, 13, 1)

        # I receive picking and check how many quants are created
        picking_in_1.action_confirm()
        picking_in_1.action_assign()
        operation = picking_in_1.move_lines[0].move_line_ids[0]
        operation.qty_done = 13
        picking_in_1.move_lines[0].value = 1.0
        quants = picking_in_1.move_lines
        self.assertEqual(len(quants), 1)
        self.assertEqual((operation.qty_done), 13, 'Wrong quantity on quant!')
        self.assertEqual((picking_in_1.move_lines[0].value), 1.0, 'Wrong cost on quant!')
        picking_in_1.do_transfer()
        # Create landed cost for first incoming shipment.
        self.stock_landed_cost = self._create_landed_cost(15, picking_in_1)
        # Compute landed costs
        self.stock_landed_cost.compute_landed_cost()
        valid_vals = {'equal': 15.0}
        # Check valuation adjustment line recognized or not
        self._validate_additional_landed_cost_lines(valid_vals)
        # I confirm the landed cost
        self.stock_landed_cost.button_validate()
        # I check that the landed cost is now "Closed" and that it has an accounting entry
        self.assertEqual(self.stock_landed_cost.state, 'done', 'Landed cost should be in done state')
        self.assertTrue(self.stock_landed_cost.account_move_id, 'Account move should be generated.')
        # I check the quants quantity and cost
        objQuants = self.env['stock.quant']
        quants = objQuants.search([('product_id', '=', picking_in_1.product_id.id),('location_id', '=', picking_in_1.location_dest_id.id)])
        for valuation in self.stock_landed_cost.valuation_adjustment_lines:
            self.assertEqual(quants.quantity, 13, 'Wrong quantity of quants')
            self.assertEqual(valuation.move_id.value, 13.0, 'Wrong cost on quants')

            # ----------------------------------------------------------
        # We perform all the tests for rounding with dozen.
        # ----------------------------------------------------------

        price = 17.00 / 12.00
        cooler = self._create_product('Cooler Bajaj', self.product_uom_unit_round_1.id)
        picking_in_2 = self._create_shipment(cooler, self.ref('product.product_uom_dozen'), self.picking_type_in_id, self.customer_location_id, self.stock_location_id, 1, price)
        # I receive picking cooler bajaj, and check how many quants are created
        picking_in_2.action_confirm()
        picking_in_2.action_assign()
        operation = picking_in_2.move_lines.move_line_ids
        operation.qty_done = 1
        picking_in_1.move_lines[0].value = round(price, 2)
        picking_in_2.do_transfer()
        # quants = picking_in_2.move_lines.quant_ids
        quants = self.env['stock.quant'].search([('product_id', '=', picking_in_2.product_id.id),('location_id', '=', picking_in_2.location_dest_id.id)])
        self.assertEqual(len(quants), 1)
        self.assertEqual(quants.quantity, 12.0, 'Wrong quantity on quants')
        self.assertEqual(valuation.move_id.value, 1.42, 'Wrong cost on quants!')
        # Create landed cost for second incoming shipment.
        self.stock_landed_cost = self._create_landed_cost(11, picking_in_2)
        # Compute landed costs
        self.stock_landed_cost.compute_landed_cost()
        valid_vals = {'equal': 11.0}
        # # Check valuation adjustment line recognized or not
        self._validate_additional_landed_cost_lines(valid_vals)
        # I confirm the landed cost
        self.stock_landed_cost.button_validate()
        # I check that the landed cost is now "Closed" and that it has an accounting entry
        self.assertEqual(self.stock_landed_cost.state, 'done', 'Landed cost should be in done state')
        self.assertTrue(self.stock_landed_cost.account_move_id, 'Account move should be linked to landed cost.')
        # I check quantity and cost of quants.
        for valuation in self.stock_landed_cost.valuation_adjustment_lines:
            self.assertEqual(quants.quantity, 12.0, 'Wrong quantity of quants')
            self.assertEqual(valuation.move_id.value, 17.0, 'not equal cost')

    def _validate_additional_landed_cost_lines(self, valid_vals):
        for valuation in self.stock_landed_cost.valuation_adjustment_lines:
            if valuation.cost_line_id.split_method == 'equal':
                self.assertEqual(valuation.additional_landed_cost, valid_vals['equal'], self._error_message(valid_vals['equal'], valuation.additional_landed_cost))

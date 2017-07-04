# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mrp.tests.common import TestMrpCommon


class TestMultistepManufacturing(TestMrpCommon):

    def setUp(self):
        super(TestMultistepManufacturing, self).setUp()

        # Create warehouse
        self.warehouse = self.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TWH',
        })
        self.route_manufacture = self.warehouse.manufacture_pull_id.route_id.id
        self.route_mto = self.warehouse.mto_pull_id.route_id.id
        self.Partner = self.env.ref('base.res_partner_1')
        self.uom_unit = self.env.ref('product.product_uom_unit')
        self.product_manu = self.env['product.product'].create({
            'name': 'Stick',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id})
        self.product_raw = self.env['product.product'].create({
            'name': 'raw Stick',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id})
        self.product_manu.write({'route_ids': [(6, 0, [self.route_manufacture, self.route_mto])]})
        self.bom_prod_manu = self.env['mrp.bom'].create({
            'product_id': self.product_manu.id,
            'product_tmpl_id': self.product_manu.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_raw.id, 'product_qty': 2})
            ]})

        # Create sale order
        self.sale_order = self.env['sale.order'].create({
            'partner_id': self.Partner.id,
            'picking_policy': 'direct',
            'warehouse_id': self.warehouse.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_manu.name,
                    'product_id': self.product_manu.id,
                    'product_uom_qty': 1.0,
                    'product_uom': self.uom_unit.id,
                    'price_unit': 10.0
                })
            ]
        })

    def test_00_manufacturing_step_one(self):
        """ Testing for Step-1 """
        # Change steps of manufacturing.
        self.warehouse.manufacture_steps = 'manu_only'
        # Confirm sale order.
        self.sale_order.action_confirm()
        # Check all procurements for created sale order
        all_procurements = self.env['procurement.order'].search([('group_id', '=', self.sale_order.procurement_group_id.id)])
        # Get manufactured procurement
        mo_procurement = all_procurements.filtered(lambda x: x.rule_id == self.warehouse.manufacture_pull_id)
        self.assertEqual(mo_procurement.production_id.location_src_id.id, self.warehouse.lot_stock_id.id, "Source loction does not match.")
        self.assertEqual(mo_procurement.production_id.location_dest_id.id, self.warehouse.lot_stock_id.id, "Destination location does not match.")
        self.assertEqual(len(mo_procurement), 1, "No Procurement !")
        self.assertTrue(mo_procurement.production_id)

    def test_01_manufacturing_step_two(self):
        """ Testing for Step-2 """
        self.warehouse.manufacture_steps = 'pick_manu'
        self.sale_order.action_confirm()
        # Check all procurements for created sale order
        all_procurements = self.env['procurement.order'].search([('group_id', '=', self.sale_order.procurement_group_id.id), ('product_id', '=', self.product_manu.id)])
        # Get manufactured procurement
        mo_procurement = all_procurements.filtered(lambda x: x.rule_id == self.warehouse.manufacture_pull_id)
        self.assertEqual(mo_procurement.production_id.location_src_id.id, self.warehouse.wh_input_manu_loc_id.id, "Source loction does not match.")
        self.assertEqual(mo_procurement.production_id.location_dest_id.id, self.warehouse.lot_stock_id.id, "Destination location does not match.")

        self.assertEqual(len(mo_procurement), 1, "No Procurement !")
        self.assertIsNotNone(mo_procurement.production_id)
        
    def test_02_manufacturing_step_three(self):
        """ Testing for Step-3 """
        self.warehouse.manufacture_steps = 'pick_manu_out'
        self.sale_order.action_confirm()
        all_procurements = self.env['procurement.order'].search([('group_id', '=', self.sale_order.procurement_group_id.id), ('product_id', '=', self.product_manu.id)])
        mo_procurement = all_procurements.filtered(lambda x: x.rule_id == self.warehouse.manufacture_pull_id)
        self.assertEqual(mo_procurement.production_id.location_src_id.id, self.warehouse.wh_input_manu_loc_id.id, "Source loction does not match.")
        self.assertEqual(mo_procurement.production_id.location_dest_id.id, self.warehouse.wh_output_manu_loc_id.id, "Destination location does not match.")
        self.assertEqual(len(mo_procurement), 1, "No rule defined for this Procurement Order.")
        self.assertIsNotNone(mo_procurement.production_id)
        total_mo_pickings = len(mo_procurement.production_id.picking_ids)
        self.assertEqual(total_mo_pickings, 0, "No picking generated for production order")

    def test_03_manufacturing_cancel_mo(self):
        """ Testing for cancelling manufacture order """
        self.warehouse.manufacture_steps = 'pick_manu_out'
        self.sale_order.action_confirm()
        # Check all procurements for created sale order
        all_procurements = self.env['procurement.order'].search([('group_id', '=', self.sale_order.procurement_group_id.id), ('product_id', '=', self.product_manu.id)])
        # Get manufactured procurement
        mo_procurement = all_procurements.filtered(lambda x: x.rule_id == self.warehouse.manufacture_pull_id)
        self.assertEqual(mo_procurement.production_id.location_src_id.id, self.warehouse.wh_input_manu_loc_id.id, "Source loction does not match.")
        self.assertEqual(mo_procurement.production_id.location_dest_id.id, self.warehouse.wh_output_manu_loc_id.id, "Destination location does not match.")
        self.assertEqual(len(mo_procurement), 1, "No rule defined for this Procurement Order.")
        self.assertIsNotNone(mo_procurement.production_id)
        # Cancel manufacture order
        mo_procurement.production_id.action_cancel()
        self.assertNotEqual(mo_procurement.state, 'cancel', 'State of procurement is cancelled.')

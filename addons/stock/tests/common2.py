# -*- coding: utf-8 -*-

from odoo.addons.product.tests import common


class TestStockCommon(common.TestProductCommon):

    def _create_pack_operation(self, product, product_qty, picking_id, **values):
        StockMoveLine = self.StockMoveLine.sudo(self.user_stock_manager)
        vals = {
            'picking_id': picking_id.id,
            'product_id': product.id,
            'product_qty': product_qty,
            'qty_done': product_qty}
        vals.update(**values)
        pack_operation = self.StockMoveLine.new(vals)
        pack_operation.onchange_product_id()
        return StockMoveLine.create(pack_operation._convert_to_write(pack_operation._cache))

    def _create_picking_in(self, warehouse):
        picking_values = {
            'picking_type_id': warehouse.in_type_id.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': warehouse.lot_stock_id.id,
        }
        return self.StockPicking.create(picking_values)

    def _create_move(self, product, src_location_id, dst_location_id, **values):
        # simulate create + onchange
        move = self.StockMove.new({'product_id': product.id, 'location_id': src_location_id, 'location_dest_id': dst_location_id})
        move.onchange_product_id()
        move_values = move._convert_to_write(move._cache)
        move_values.update(**values)
        return self.StockMove.create(move_values)

    def _create_move_in(self, product, warehouse, picking=None, create_picking=False, **values):
        if not picking and create_picking:
            picking = self._create_picking_in(warehouse)
        if picking:
            values['picking_id'] = picking.id
        # TDE FIXME: shouldn't location come from picking ??
        return self._create_move(product, self.ref('stock.stock_location_suppliers'), warehouse.lot_stock_id.id, **values)

    @classmethod
    def setUpClass(cls):
        super(TestStockCommon, cls).setUpClass()

        # Model
        cls.StockInventory = cls.env['stock.inventory']
        cls.Warehouse = cls.env['stock.warehouse']
        cls.StockLocation = cls.env['stock.location']
        cls.StockQuant = cls.env['stock.quant']
        cls.ResUsers = cls.env['res.users']
        cls.StockPicking = cls.env['stock.picking']
        cls.StockMove = cls.env['stock.move']
        cls.StockMoveLine = cls.env['stock.move.line']
        cls.Package = cls.env['stock.quant.package']
        cls.ProductionLot = cls.env['stock.production.lot']
        cls.Procurement = cls.env['procurement.order']
        cls.Product = cls.env['product.product']

        # Fetch stock-related user groups
        cls.group_employee_id = cls.env.ref('base.group_user').id
        cls.group_stock_user_id = cls.env.ref('stock.group_stock_user').id
        cls.group_stock_manager_id = cls.env.ref('stock.group_stock_manager').id

        # Fetch stock-related locations and measure
        cls.supplier_location_id = cls.env.ref("stock.stock_location_suppliers").id
        cls.stock_location_id = cls.env.ref("stock.stock_location_stock").id
        cls.customer_location_id = cls.env.ref("stock.stock_location_customers").id
        cls.output_location_id = cls.env.ref("stock.stock_location_output").id
        cls.uom_unit_id = cls.env.ref('product.product_uom_unit').id

        # Fetch picking types
        cls.picking_type_in_id = cls.env.ref("stock.picking_type_in").id
        cls.picking_type_out_id = cls.env.ref("stock.picking_type_out").id
        cls.picking_type_int_id = cls.env.ref("stock.picking_type_internal").id

        # User Data: stock user and stock manager
        Users = cls.ResUsers.with_context({'no_reset_password': True, 'mail_create_nosubscribe': True})
        cls.user_stock_user = Users.create({
            'name': 'Pauline Poivraisselle',
            'login': 'pauline',
            'email': 'p.p@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [cls.group_stock_user_id])]})
        cls.user_stock_manager = Users.create({
            'name': 'Julie Tablier',
            'login': 'julie',
            'email': 'j.j@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [cls.group_stock_manager_id])]})

        # Warehouses
        cls.warehouse_1 = cls.Warehouse.create({
            'name': 'Base Warehouse',
            'reception_steps': 'one_step',
            'delivery_steps': 'ship_only',
            'code': 'BWH'})

        # Locations
        cls.location_1 = cls.StockLocation.create({
            'name': 'TestLocation1',
            'posx': 3,
            'location_id': cls.warehouse_1.lot_stock_id.id,
        })

        # # Existing data
        cls.existing_inventories = cls.StockInventory.search([])
        cls.existing_quants = cls.StockQuant.search([])

        # Inventory
        cls.product_1.type = 'product'

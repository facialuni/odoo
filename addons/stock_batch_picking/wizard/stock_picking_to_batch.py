# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockPickingToBatch(models.TransientModel):
    _name = 'stock.picking.to.batch'
    _description = 'Add pickings to a batch picking'

    batch_picking_id = fields.Many2one('stock.batch.picking', string='Batch Picking', required=True)

    @api.multi
    def attach_pickings(self):
        # use active_ids to add picking line to the selected batch
        self.ensure_one()
        picking_ids = self.env.context.get('active_ids')
        return self.env['stock.picking'].browse(picking_ids).write({'batch_picking_id': self.batch_picking_id.id})

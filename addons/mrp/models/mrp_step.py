# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import decimal_precision as dp


class MrpWorkorderStep(models.Model):
    _name = 'mrp.step'
    _description = 'Work Order Step'

    name = fields.Char('Work Order Step', required=True)
    type = fields.Selection([
        ('pass_fail', 'Pass - Fail Test'),
        ('measure', 'Take a measure'),
        ('picture', 'Take a picture'),
        ('dummy', 'Dummy'),
        ('record_component', 'Record Component'),
        ('record_product', 'Record Finished Product'),
    ], required=True, default='pass_fail')
    operation_id = fields.Many2one('mrp.routing.workcenter', 'Routing')
    product_id = fields.Many2one('product.product', 'Product')
    operation_type = fields.Selection([
        ('all_operations', 'All Operations')
    ])
    worksheet_aftereffect = fields.Selection([
        ('no_update', 'Do not update page'),
        ('scroll', 'Scroll to specific page')
    ], default='no_update')
    worksheet_scroll_to_page = fields.Integer('Page Number')
    note = fields.Text('Note')

    # Quality check fields
    instruction = fields.Text('Note')
    failure_message = fields.Text('Note')
    # Measure
    norm = fields.Float('Norm', digits=dp.get_precision('Quality Tests'))  # TDE RENAME ?
    tolerance_min = fields.Float('Min Tolerance', digits=dp.get_precision('Quality Tests'))
    tolerance_max = fields.Float('Max Tolerance', digits=dp.get_precision('Quality Tests'))
    norm_unit = fields.Char('Unit of Measure', default=lambda self: 'mm')  # TDE RENAME ?


class MrpRoutingWorkcenter(models.Model):
    _name = 'mrp.routing.workcenter'
    _inherit = 'mrp.routing.workcenter'

    step_ids = fields.One2many(
        'mrp.step', 'operation_id', 'Step', copy=True
    )

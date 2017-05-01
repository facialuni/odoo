# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Noviat nv/sa (www.noviat.be). All rights reserved.

from odoo import api, fields, models


class AccountConfigSettings(models.TransientModel):
    """ add field to indicate default 'Communication Type' on customer invoices """
    _inherit = 'account.config.settings'

    @api.model
    def _get_comm_type(self):
        return self.env['account.invoice']._get_reference_type()

    use_out_inv_comm = fields.Boolean(string='Structured Communication')
    out_inv_comm_type = fields.Selection('_get_comm_type', string='Communication Type', change_default=True,
        help='Select Default Communication Type for Outgoing Invoices.', default='none')
    out_inv_comm_algorithm = fields.Selection([
        ('random', 'Random'),
        ('date', 'Date'),
        ('partner_ref', 'Customer Reference'),
        ], string='Communication Algorithm',
        help='Select Algorithm to generate the Structured Communication on Outgoing Invoices.')

    @api.onchange('use_out_inv_comm')
    def _onchange_use_out_inv_comm(self):
        if self.use_out_inv_comm:
            self.out_inv_comm_type = 'bba'
        else:
            self.out_inv_comm_type = 'none'
            self.out_inv_comm_algorithm = 'random'

    @api.model
    def get_default_fields(self, fields):
        company_id = self.env.user.company_id.id
        IrProperty = self.env['ir.property']
        out_inv_comm_type = IrProperty.get('property_out_inv_comm_type', 'res.partner')
        out_inv_comm_algorithm = IrProperty.get('property_out_inv_comm_algorithm', 'res.partner')
        return {
            'use_out_inv_comm': self.env['ir.values'].get_default('account.config.settings', 'use_out_inv_comm', company_id=company_id),
            'out_inv_comm_type': out_inv_comm_type,
            'out_inv_comm_algorithm': out_inv_comm_algorithm,
        }

    @api.multi
    def set_default_fields(self):
        current_values = {
            'property_out_inv_comm_type': self.out_inv_comm_type,
            'property_out_inv_comm_algorithm': self.out_inv_comm_algorithm
        }
        company_id = self.env.user.company_id.id
        self.env['ir.values'].sudo().set_default('account.config.settings', 'use_out_inv_comm', self.use_out_inv_comm, company_id=company_id)
        model_fields = self.env['ir.model.fields'].search([
            ('model', '=', 'res.partner'),
            ('name', 'in', ['property_out_inv_comm_type', 'property_out_inv_comm_algorithm'])
        ])
        properties = self.env['ir.property'].search([
            ('res_id', '=', False), ('fields_id', 'in', model_fields.ids),
            ('company_id', '=', company_id)
        ])
        for field in model_fields:
            if field not in properties.mapped('fields_id'):
                self.env['ir.property'].create({
                    'name': field.name,
                    'company_id': company_id,
                    'value': current_values[field.name],
                    'fields_id': field.id,
                    'type': 'selection',
                })
            else:
                properties.filtered(lambda x: x.fields_id == field).write({
                    'value': current_values[field.name]
                })

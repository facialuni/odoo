# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _

class stock_invoice_onshipping(osv.osv_memory):
    def _get_journal(self, cr, uid, context=None):
        journal_obj = self.pool.get('account.journal')
        journal_type = self._get_journal_type(cr, uid, [0], ['journal_type'], [], context=context)[0]['journal_type']
        journals = journal_obj.search(cr, uid, [('type', '=', journal_type)])
        return journals and journals[0] or False
    
    def _get_journal_type(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        res_ids = context and context.get('active_ids', [])
        pick_obj = self.pool.get('stock.picking')
        pickings = pick_obj.browse(cr, uid, res_ids, context=context)
        pick = pickings and pickings[0]
        if not pick or not pick.move_lines:
            return {'journal_type': 'sale', 'invoice_type': 'out_invoice'}
        src_usage = pick.move_lines[0].location_id.usage
        dest_usage = pick.move_lines[0].location_dest_id.usage
        type = pick.picking_type_id.code
        if type == 'outgoing' and dest_usage == 'supplier':
            journal_type = 'purchase'
            invoice_type = 'in_refund'
        elif type == 'outgoing' and dest_usage == 'customer':
            journal_type = 'sale'
            invoice_type = 'out_invoice'
        elif type == 'incoming' and src_usage == 'supplier':
            journal_type = 'purchase'
            invoice_type = 'in_invoice'
        elif type == 'incoming' and src_usage == 'customer':
            journal_type = 'sale'
            invoice_type = 'out_refund'
        else:
            journal_type = 'sale'
            invoice_type = 'out_invoice'
        return {id: {'journal_type': journal_type, 'invoice_type': invoice_type} for id in ids}

    _name = "stock.invoice.onshipping"
    _description = "Stock Invoice Onshipping"
    _columns = {
        'journal_id': fields.many2one('account.journal', 'Destination Journal', required=True),
        'journal_type': fields.function(_get_journal_type, type='selection', selection=[
            ('purchase', 'Create Supplier Invoice'),
            ('sale', 'Create Customer Invoice')
        ], string='Journal Type', readonly=True, multi=True),
        'group': fields.boolean("Group by partner"),
        'invoice_date': fields.date('Invoice Date'),
        'invoice_type': fields.function(_get_journal_type, type='selection', selection=[
            ('out_invoice', 'Customer Invoice'),
            ('in_invoice', 'Supplier Invoice'),
            ('out_refund', 'Customer Refund'),
            ('in_refund', 'Supplier Refund'),
        ], string='Invoice type', readonly=True, multi=True),
    }
    _defaults = {
        'journal_id' : _get_journal,
    }

    def view_init(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        res = super(stock_invoice_onshipping, self).view_init(cr, uid, fields_list, context=context)
        pick_obj = self.pool.get('stock.picking')
        count = 0
        active_ids = context.get('active_ids',[])
        for pick in pick_obj.browse(cr, uid, active_ids, context=context):
            if pick.invoice_state != '2binvoiced':
                count += 1
        if len(active_ids) == count:
            raise osv.except_osv(_('Warning!'), _('None of these picking lists require invoicing.'))
        return res

    def open_invoice(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        
        invoice_ids = self.create_invoice(cr, uid, ids, context=context)
        if not invoice_ids:
            raise osv.except_osv(_('Error!'), _('No invoice created!'))

        action_model = False
        action = {}
        
        inv_type = self.browse(cr, uid, ids[0], context=context).invoice_type
        data_pool = self.pool.get('ir.model.data')
        if inv_type == "out_invoice":
            action_id = data_pool.xmlid_to_res_id(cr, uid, 'account.action_invoice_tree1')
        elif inv_type == "in_invoice":
            action_id = data_pool.xmlid_to_res_id(cr, uid, 'account.action_invoice_tree2')
        elif inv_type == "out_refund":
            action_id = data_pool.xmlid_to_res_id(cr, uid, 'account.action_invoice_tree3')
        elif inv_type == "in_refund":
            action_id = data_pool.xmlid_to_res_id(cr, uid, 'account.action_invoice_tree4')

        if action_id:
            action_pool = self.pool['ir.actions.act_window']
            action = action_pool.read(cr, uid, action_id, context=context)
            action['domain'] = "[('id','in', ["+','.join(map(str,invoice_ids))+"])]"
            return action
        return True

    def create_invoice(self, cr, uid, ids, context=None):
        context = dict(context or {})
        picking_pool = self.pool.get('stock.picking')
        data = self.browse(cr, uid, ids[0], context=context)
        context['date_inv'] = data.invoice_date
        acc_journal = self.pool.get("account.journal")
        inv_type = data.invoice_type
        context['inv_type'] = inv_type

        active_ids = context.get('active_ids', [])
        res = picking_pool.action_invoice_create(cr, uid, active_ids,
              journal_id = data.journal_id.id,
              group = data.group,
              type = inv_type,
              context=context)
        return res


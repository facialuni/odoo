# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError, AccessError

class ProcurementRule(models.Model):
    _inherit = 'procurement.rule'

    action = fields.Selection(selection_add=[('buy', 'Buy')])


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.multi
    def _run(self, values, rule, doraise=True):
        if rule.action == 'buy':
            cache = {}
            suppliers = values['product_id'].seller_ids\
                .filtered(lambda r: (not r.company_id or r.company_id == values['company_id']) and (not r.product_id or r.product_id == values['product_id']))
            if not suppliers:
                msg = _('No vendor associated to product %s. Unable to generate the purchase order.') % (values['product_id'].display_name(),)
                if doraise:
                    raise UserError(msg)
                else:
                    activity = self.env['mail.activity'].sudo(self.crm_salesman.id).create({
                        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                        'note': msg,
                        'res_id': values['product_id'].product_tmpl_id.id,
                        'res_model_id': self.env.ref('product.model_product_template').id,
                    })
                    return False
            supplier = self._make_po_select_supplier(values, rule, suppliers)
            partner = supplier.name

            domain = self._make_po_get_domain(values, rule, partner)

            if domain in cache:
                po = cache[domain]
            else:
                po = self.env['purchase.order'].search([dom for dom in domain])
                po = po[0] if po else False
                cache[domain] = po
            if not po:
                vals = self._prepare_purchase_order(values, rule, partner)
                po = self.env['purchase.order'].create(vals)
                cache[domain] = po
            elif not po.origin or values['origin'] not in po.origin.split(', '):
                if po.origin:
                    if values['origin']:
                        po.write({'origin': po.origin + ', ' + values['origin']})
                    else:
                        po.write({'origin': po.origin})
                else:
                    po.write({'origin': values['origin']})

            # Create Line
            po_line = False
            for line in po.order_line:
                if line.product_id == values['product_id'] and line.product_uom == values['product_id'].uom_po_id:
                    procurement_uom_po_qty = values['product_uom']._compute_quantity(values['product_qty'], values['product_id'].uom_po_id)
                    seller = values['product_id']._select_seller(
                        partner_id=partner,
                        quantity = line.product_qty + procurement_uom_po_qty,
                        date = po.date_order and po.date_order[:10],
                        uom_id=values['product_id'].uom_po_id)

                    price_unit = self.env['account.tax']._fix_tax_included_price(seller.price, line.product_id.supplier_taxes_id, line.taxes_id) if seller else 0.0
                    if price_unit and seller and po.currency_id and seller.currency_id != po.currency_id:
                        price_unit = seller.currency_id.compute(price_unit, po.currency_id)

                    po_line = line.write({
                        'product_qty': line.product_qty + procurement_uom_po_qty,
                        'price_unit': price_unit,
                    })
                    break
            if not po_line:
                vals = self._prepare_purchase_order_line(values, rule, po, supplier)
                self.env['purchase.order.line'].create(vals)
            return True
        return super(ProcurementGroup, self)._run(values, rule, doraise=True)

    def _get_purchase_schedule_date(self, values, rule):
        """Return the datetime value to use as Schedule Date (``date_planned``) for the
           Purchase Order Lines created to satisfy the given procurement. """
        procurement_date_planned = datetime.strptime(values['date_planned'], DEFAULT_SERVER_DATETIME_FORMAT)
        schedule_date = (procurement_date_planned - relativedelta(days=values['company_id'].po_lead))
        return schedule_date

    def _get_purchase_order_date(self, values, rule, partner, schedule_date):
        """Return the datetime value to use as Order Date (``date_order``) for the
           Purchase Order created to satisfy the given procurement. """
        seller = values['product_id']._select_seller(
            partner_id=partner,
            quantity=values['product_qty'],
            date=fields.Date.to_string(schedule_date),
            uom_id=values['product_uom'])

        return schedule_date - relativedelta(days=int(seller.delay))

    @api.model
    def _prepare_purchase_order_line(self, values, rule, po, supplier):
        procurement_uom_po_qty = values['product_uom']._compute_quantity(values['product_qty'], values['product_id'].uom_po_id)
        seller = values['product_id']._select_seller(
            partner_id=supplier.name,
            quantity=procurement_uom_po_qty,
            date=po.date_order and po.date_order[:10],
            uom_id=values['product_id'].uom_po_id)

        taxes = values['product_id'].supplier_taxes_id
        fpos = po.fiscal_position_id
        taxes_id = fpos.map_tax(taxes) if fpos else taxes
        if taxes_id:
            taxes_id = taxes_id.filtered(lambda x: x.company_id.id == values['company_id'].id)

        price_unit = self.env['account.tax']._fix_tax_included_price(seller.price, values['product_id'].supplier_taxes_id, taxes_id) if seller else 0.0
        if price_unit and seller and po.currency_id and seller.currency_id != po.currency_id:
            price_unit = seller.currency_id.compute(price_unit, po.currency_id)

        product_lang = values['product_id'].with_context({
            'lang': supplier.name.lang,
            'partner_id': supplier.name.id,
        })
        name = product_lang.display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase

        date_planned = self.env['purchase.order.line']._get_date_planned(seller, po=po).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        return {
            'name': name,
            'product_qty': procurement_uom_po_qty,
            'product_id': values['product_id'].id,
            'product_uom': values['product_id'].uom_po_id.id,
            'price_unit': price_unit,
            'date_planned': date_planned,
            'orderpoint_id': values.get('orderpoint_id', False) and values.get('orderpoint_id').id,
            'taxes_id': [(6, 0, taxes_id.ids)],
            'order_id': po.id,
        }

    def _prepare_purchase_order(self, values, rule, partner):
        schedule_date = self._get_purchase_schedule_date(values, rule)
        purchase_date = self._get_purchase_order_date(values, rule, partner, schedule_date)
        fpos = self.env['account.fiscal.position'].with_context(company_id=values['company_id'].id).get_fiscal_position(partner.id)

        gpo = rule.group_propagation_option
        group = (gpo == 'fixed' and rule.group_id.id) or \
                (gpo == 'propagate' and values['group_id'].id) or False

        return {
            'partner_id': partner.id,
            'picking_type_id': rule.picking_type_id.id,
            'company_id': values['company_id'].id,
            'currency_id': partner.property_purchase_currency_id.id or self.env.user.company_id.currency_id.id,
            'dest_address_id': values.get('partner_dest_id', False) and values['partner_dest_id'].id,
            'origin': values['origin'],
            'payment_term_id': partner.property_supplier_payment_term_id.id,
            'date_order': purchase_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'fiscal_position_id': fpos,
            'group_id': group
        }

    def _make_po_select_supplier(self, values, rule, suppliers):
        """ Method intended to be overridden by customized modules to implement any logic in the
            selection of supplier.
        """
        return suppliers[0]

    def _make_po_get_domain(self, values, rule, partner):
        gpo = rule.group_propagation_option
        group = (gpo == 'fixed' and rule.group_id) or \
                (gpo == 'propagate' and values['group_id']) or False

        domain = (
            ('partner_id', '=', partner.id),
            ('state', '=', 'draft'),
            ('picking_type_id', '=', rule.picking_type_id.id),
            ('company_id', '=', values['company_id'].id),
            )
        if group:
            domain += (('group_id', '=', group.id),)
        return domain


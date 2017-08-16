# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round, pycompat

import logging
_logger = logging.getLogger(__name__)


class StockInventory(models.Model):
    _inherit = "stock.inventory"

    accounting_date = fields.Date(
        'Force Accounting Date',
        help="Choose the accounting date at which you want to value the stock "
             "moves created by the inventory instead of the default one (the "
             "inventory end date)")

    @api.multi
    def post_inventory(self):
        acc_inventories = self.filtered(lambda inventory: inventory.accounting_date)
        for inventory in acc_inventories:
            res = super(StockInventory, inventory.with_context(force_period_date=inventory.accounting_date)).post_inventory()
        other_inventories = self - acc_inventories
        if other_inventories:
            res = super(StockInventory, other_inventories).post_inventory()
        return res


class StockLocation(models.Model):
    _inherit = "stock.location"

    valuation_in_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account (Incoming)',
        domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)],
        help="Used for real-time inventory valuation. When set on a virtual location (non internal type), "
             "this account will be used to hold the value of products being moved from an internal location "
             "into this location, instead of the generic Stock Output Account set on the product. "
             "This has no effect for internal locations.")
    valuation_out_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account (Outgoing)',
        domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)],
        help="Used for real-time inventory valuation. When set on a virtual location (non internal type), "
             "this account will be used to hold the value of products being moved out of this location "
             "and into an internal location, instead of the generic Stock Output Account set on the product. "
             "This has no effect for internal locations.")


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'
    
    @api.multi
    def write(self, vals):
        if 'qty_done' in vals:
            # We need to update the `value`, `remaining_value` and `remaining_qty` on the linked
            # stock move.
            moves_to_update = {}
            for move_line in self.filtered(lambda ml: ml.state == 'done'):
                moves_to_update[move_line.move_id] = vals['qty_done'] - move_line.qty_done

            for move_id, qty_difference in moves_to_update.items():
                if qty_difference > 0:
                    # more units are available, update `value`, `remaining_value` and
                    # `remaining_qty` on the linked stock move.
                    move_vals = {
                        'value': move_id.value + qty_difference * move_id.price_unit,
                        'remaining_value': move_id.remaining_value + qty_difference * move_id.price_unit,
                        'remaining_qty': move_id.remaining_qty + qty_difference,
                    }
                    move_id.write(move_vals)
                else:
                    # Less units are available, get rid of the extra units at the value of today.
                    pass
        return super(StockMoveLine, self).write(vals)


class StockMove(models.Model):
    _inherit = "stock.move"

    to_refund = fields.Boolean(string="To Refund (update SO/PO)",
                               help='Trigger a decrease of the delivered/received quantity in the associated Sale Order/Purchase Order')

    value = fields.Float()
    remaining_qty = fields.Float()
    remaining_value = fields.Float()

    @api.multi
    def _get_price_unit(self):
        self.ensure_one()
        if self.product_id.cost_method == 'average':
            return self.product_id.average_price or self.product_id.standard_price
        if self.product_id.cost_method == 'fifo':
            move = self.search([('product_id', '=', self.product_id.id),
                         ('state', '=', 'done'), 
                         ('location_id.usage', '=', 'internal'), 
                         ('location_dest_id.usage', '!=', 'internal')], order='date desc', limit=1)
            if move:
                return move.price_unit or self.product_id.standard_price
        return self.product_id.standard_price

    @api.model
    def _get_in_base_domain(self, company_id=False):
        domain = [
            ('state', '=', 'done'),
            ('location_id.company_id', '=', False),
            ('location_dest_id.company_id', '=', company_id or self.env.user.company_id.id)
        ]
        return domain

    @api.model
    def _get_out_base_domain(self, company_id=False):
        domain = [
            ('state', '=', 'done'),
            ('location_id.company_id', '=', company_id or self.env.user.company_id.id),
            ('location_dest_id.company_id', '=', False)
        ]
        return domain

    @api.model
    def _get_all_base_domain(self, company_id=False):
        domain = [
            ('state', '=', 'done'),
            '|',
                '&',
                    ('location_id.company_id', '=', False),
                    ('location_dest_id.company_id', '=', company_id or self.env.user.company_id.id),
                '&',
                    ('location_id.company_id', '=', company_id or self.env.user.company_id.id),
                    ('location_dest_id.company_id', '=', False)
        ]
        return domain

    def _get_in_domain(self):
        return [('product_id', '=', self.product_id.id)] + self._get_in_base_domain(company_id=self.company_id.id)

    def _get_out_domain(self):
        return [('product_id', '=', self.product_id.id)] + self._get_out_base_domain(company_id=self.company_id.id)

    def _get_all_domain(self):
        return [('product_id', '=', self.product_id.id)] + self._get_all_base_domain(company_id=self.company_id.id)

    def _is_in(self):
        """ Check if the move should be considered as entering the company so that the cost method
        will be able to apply the correct logic.

        :return: True if the move is entering the company else False
        """
        return not self.location_id.company_id and self.location_dest_id.company_id.id == self.company_id.id

    def _is_out(self):
        """ Check if the move should be considered as leaving the company so that the cost method
        will be able to apply the correct logic.

        :return: True if the move is leaving the company else False
        """
        return self.location_id.company_id.id == self.company_id.id and not self.location_dest_id.company_id

    @api.multi
    def action_done(self):
        average_price = {}
        for move in self.filtered(lambda m: m.product_id.cost_method == 'average'):
            # For the average costing method, the value depends of the quantity in stock at the
            # moment of the transfer, so fetch the value before calling super.
            average_price[move.product_id.id] = move.product_id.average_price
        res = super(StockMove, self).action_done()
        for move in res:
            if move._is_in():
                if move.product_id.cost_method in ['fifo', 'average']:
                    if not move.price_unit:
                        move.price_unit = move._get_price_unit()
                    move.value = move.price_unit * move.product_qty
                    move.remaining_value = move.price_unit * move.product_qty
                    if move.product_id.cost_method == 'fifo':
                        move.remaining_qty = move.product_qty
                else:
                    move.price_unit = move.product_id.standard_price
                    move.value = move.price_unit * move.product_qty
            elif move._is_out():
                if move.product_id.cost_method == 'fifo':
                    qty_to_take = move.product_qty
                    candidates = move.product_id._get_fifo_candidates_in_move()
                    for candidate in candidates:
                        if candidate.remaining_qty <= qty_to_take:
                            qty_taken_on_candidate = candidate.remaining_qty
                        else:
                            qty_taken_on_candidate = qty_to_take
                        candidate.remaining_qty -= qty_taken_on_candidate
                        candidate.remaining_value -= qty_taken_on_candidate * candidate.price_unit
                        qty_to_take -= qty_taken_on_candidate
                        if qty_to_take == 0:
                            break
                    if qty_to_take > 0:
                        move.remaining_qty = -qty_to_take # In case there are no candidates to match, put standard price on it
                        move.remaining_value = candidates[-1].price_unit * -qty_to_take  # FIXME just to go forward a little
                elif move.product_id.cost_method == 'average':
                    curr_rounding = move.company_id.currency_id.rounding
                    avg_price_unit = average_price[move.product_id.id]
                    move.value = float_round(-avg_price_unit * move.product_qty, precision_rounding=curr_rounding)
                    move.remaining_qty = 0
                    move.available_qty = move.product_id.with_context(company_owned=True).qty_available
                elif move.product_id.cost_method == 'standard':
                    move.value = - move.product_id.standard_price * move.product_qty
                
        for move in res.filtered(lambda m: m.product_id.valuation == 'real_time'):
            move._account_entry_move()
        return res

    @api.model
    def _fifo_vacuum(self):
        # FIXME: sort by date (does filtered lose the order?)
        for move in self.filtered(lambda m: m._is_out() and m.remaining_qty < 0):
            domain = [
                '|',
                    ('date', '>', move.date),
                    '&',
                        ('date', '=', move.date),
                        ('id', '>', move.id)
            ]
            domain += self._get_in_domain()
            candidates = self.search(domain, order='date, id')
            qty_to_take = abs(move.remaining_qty)
            tmp_value = 0
            # !00% copy pasted from action_done. gai.
            for candidate in candidates:
                if candidate.remaining_qty <= qty_to_take:
                    qty_taken_on_candidate = candidate.remaining_qty
                else:
                    qty_taken_on_candidate = qty_to_take
                value_taken_on_candidate = qty_taken_on_candidate * candidate.price_unit
                tmp_value += value_taken_on_candidate
                candidate.remaining_qty -= qty_taken_on_candidate
                candidate.remaining_value -= qty_taken_on_candidate * candidate.price_unit
                qty_to_take -= qty_taken_on_candidate
                if qty_to_take == 0:
                    break
            if qty_to_take > 0:
                move.remaining_qty -= -qty_to_take  # In case there are no candidates to match, put standard price on it
                move.remaining_value = candidates[-1].price_unit * -qty_to_take  # FIXME just to go forward a little
            elif qty_to_take == 0:
                move.remaining_value = 0
                move.remaining_qty = 0

    @api.multi
    def _get_accounting_data_for_valuation(self):
        """ Return the accounts and journal to use to post Journal Entries for
        the real-time valuation of the quant. """
        self.ensure_one()
        accounts_data = self.product_id.product_tmpl_id.get_product_accounts()

        if self.location_id.valuation_out_account_id:
            acc_src = self.location_id.valuation_out_account_id.id
        else:
            acc_src = accounts_data['stock_input'].id

        if self.location_dest_id.valuation_in_account_id:
            acc_dest = self.location_dest_id.valuation_in_account_id.id
        else:
            acc_dest = accounts_data['stock_output'].id

        acc_valuation = accounts_data.get('stock_valuation', False)
        if acc_valuation:
            acc_valuation = acc_valuation.id
        if not accounts_data.get('stock_journal', False):
            raise UserError(_('You don\'t have any stock journal defined on your product category, check if you have installed a chart of accounts'))
        if not acc_src:
            raise UserError(_('Cannot find a stock input account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (self.product_id.name))
        if not acc_dest:
            raise UserError(_('Cannot find a stock output account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (self.product_id.name))
        if not acc_valuation:
            raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))
        journal_id = accounts_data['stock_journal'].id
        return journal_id, acc_src, acc_dest, acc_valuation
    
    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given quant.
        """
        self.ensure_one()

        if self._context.get('force_valuation_amount'):
            valuation_amount = self._context.get('force_valuation_amount')
        else:
            valuation_amount = cost

        # the standard_price of the product may be in another decimal precision, or not compatible with the coinage of
        # the company currency... so we need to use round() before creating the accounting entries.
        debit_value = self.company_id.currency_id.round(valuation_amount)

        # check that all data is correct
        if self.company_id.currency_id.is_zero(debit_value):
            if self.product_id.cost_method == 'standard':
                raise UserError(_("The found valuation amount for product %s is zero. Which means there is probably a configuration error. Check the costing method and the standard price") % (self.product_id.name,))
            return []
        credit_value = debit_value

        if self.product_id.cost_method == 'average' and self.company_id.anglo_saxon_accounting:
            # in case of a supplier return in anglo saxon mode, for products in average costing method, the stock_input
            # account books the real purchase price, while the stock account books the average price. The difference is
            # booked in the dedicated price difference account.
            if self.location_dest_id.usage == 'supplier' and self.origin_returned_move_id and self.origin_returned_move_id.purchase_line_id:
                debit_value = self.origin_returned_move_id.price_unit * qty
            # in case of a customer return in anglo saxon mode, for products in average costing method, the stock valuation
            # is made using the original average price to negate the delivery effect.
            if self.location_id.usage == 'customer' and self.origin_returned_move_id:
                debit_value = self.origin_returned_move_id.price_unit * qty
                credit_value = debit_value
        partner_id = (self.picking_id.partner_id and self.env['res.partner']._find_accounting_partner(self.picking_id.partner_id).id) or False
        debit_line_vals = {
            'name': self.name,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': self.picking_id.name,
            'partner_id': partner_id,
            'debit': debit_value if debit_value > 0 else 0,
            'credit': -debit_value if debit_value < 0 else 0,
            'account_id': debit_account_id,
        }
        credit_line_vals = {
            'name': self.name,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': self.picking_id.name,
            'partner_id': partner_id,
            'credit': credit_value if credit_value > 0 else 0,
            'debit': -credit_value if credit_value < 0 else 0,
            'account_id': credit_account_id,
        }
        res = [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
        if credit_value != debit_value:
            # for supplier returns of product in average costing method, in anglo saxon mode
            diff_amount = debit_value - credit_value
            price_diff_account = self.product_id.property_account_creditor_price_difference
            if not price_diff_account:
                price_diff_account = self.product_id.categ_id.property_account_creditor_price_difference_categ
            if not price_diff_account:
                raise UserError(_('Configuration error. Please configure the price difference account on the product or its category to process this operation.'))
            price_diff_line = {
                'name': self.name,
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'ref': self.picking_id.name,
                'partner_id': partner_id,
                'credit': diff_amount > 0 and diff_amount or 0,
                'debit': diff_amount < 0 and -diff_amount or 0,
                'account_id': price_diff_account.id,
            }
            res.append((0, 0, price_diff_line))
        return res

    def _create_account_move_line(self, credit_account_id, debit_account_id, journal_id):
        self.ensure_one()
        AccountMove = self.env['account.move']
        move_lines = self._prepare_account_move_line(self.product_qty, abs(self.value), credit_account_id, debit_account_id)
        if move_lines:
            date = self._context.get('force_period_date', fields.Date.context_today(self))
            new_account_move = AccountMove.create({
                'journal_id': journal_id,
                'line_ids': move_lines,
                'date': date,
                'ref': self.picking_id.name})
            new_account_move.post()

    def _account_entry_move(self):
        """ Accounting Valuation Entries """
        self.ensure_one()
        if self.product_id.type != 'product':
            # no stock valuation for consumable products
            return False
        if self.restrict_partner_id:
            # if the move isn't owned by the company, we don't make any valuation
            return False

        location_from = self.location_id
        location_to = self.location_dest_id
        company_from = location_from.usage == 'internal' and location_from.company_id or False
        company_to = location_to and (location_to.usage == 'internal') and location_to.company_id or False

        # Create Journal Entry for products arriving in the company; in case of routes making the link between several
        # warehouse of the same company, the transit location belongs to this company, so we don't need to create accounting entries
        if company_to and (self.location_id.usage not in ('internal', 'transit') and self.location_dest_id.usage == 'internal' or company_from != company_to):
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
            if location_from and location_from.usage == 'customer':  # goods returned from customer
                self.with_context(force_company=company_to.id)._create_account_move_line(acc_dest, acc_valuation, journal_id)
            else:
                self.with_context(force_company=company_to.id)._create_account_move_line(acc_src, acc_valuation, journal_id)

        # Create Journal Entry for products leaving the company
        if company_from and (self.location_id.usage == 'internal' and self.location_dest_id.usage not in ('internal', 'transit') or company_from != company_to):
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
            if location_to and location_to.usage == 'supplier':  # goods returned to supplier
                self.with_context(force_company=company_from.id)._create_account_move_line(acc_valuation, acc_src, journal_id)
            else:
                self.with_context(force_company=company_from.id)._create_account_move_line(acc_valuation, acc_dest, journal_id)

        if self.company_id.anglo_saxon_accounting and self.location_id.usage == 'supplier' and self.location_dest_id.usage == 'customer':
            # Creates an account entry from stock_input to stock_output on a dropship move. https://github.com/odoo/odoo/issues/12687
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
            self.with_context(force_company=self.company_id.id)._create_account_move_line(acc_src, acc_dest, journal_id)


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    @api.multi
    def _create_returns(self):
        new_picking_id, pick_type_id = super(StockReturnPicking, self)._create_returns()
        new_picking = self.env['stock.picking'].browse([new_picking_id])
        for move in new_picking.move_lines:
            return_picking_line = self.product_return_moves.filtered(lambda r: r.move_id == move.origin_returned_move_id)
            if return_picking_line and return_picking_line.to_refund:
                move.to_refund = True
        return new_picking_id, pick_type_id


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    to_refund = fields.Boolean(string="To Refund (update SO/PO)", help='Trigger a decrease of the delivered/received quantity in the associated Sale Order/Purchase Order')

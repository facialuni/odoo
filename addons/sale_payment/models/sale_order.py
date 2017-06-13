# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_tx_id = fields.Many2one('payment.transaction', string='Last Transaction', copy=False)
    payment_acquirer_id = fields.Many2one('payment.acquirer', string='Payment Acquirer', related='payment_tx_id.acquirer_id', store=True)
    sale_payment_mode = fields.Selection([
        ('signature', 'Signature'),
        ('payment', 'Payment'),
    ], string="Quotation Signature & Payment", default='signature', compute='_get_sale_payment_mode')
    require_payment = fields.Selection([
        (0, 'Not mandatory on online quote validation'),
        (1, 'Immediate after online order validation'),
    ], string="Payment", help="Require immediate payment by the customer when validating the order from the online quote")

    def _force_lines_to_invoice_policy_order(self):
        for line in self.order_line:
            if self.state in ['sale', 'done']:
                line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

    @api.multi
    def _get_sale_payment_mode(self):
        """ Get sale payment mode, which is define in sale config.
            that configuration use for set payment require option in quotation
            and also update frontend view(if we choose payment then
            show all published payment method for payment process else just
            open modal for confirmation process with sign option for quotation.
        """
        sale_payment_mode = self.env['ir.values'].sudo().get_default('sale.config.settings', 'sale_payment_mode')
        for order in self:
            if sale_payment_mode == 'signature':
                order.sale_payment_mode = sale_payment_mode
                order.require_payment = False
            else:
                order.sale_payment_mode = sale_payment_mode or 'signature'

    @api.multi
    def get_access_action(self):
        """ Instead of the classic form view, redirect to the online quote if it exists. """
        self.ensure_one()
        if not self.env.user.share and not self.env.context.get('force_website'):
            return super(SaleOrder, self).get_access_action()
        return {
            'type': 'ir.actions.act_url',
            'url': '/quote/%s/%s' % (self.id, self.access_token),
            'target': 'self',
            'res_id': self.id,
        }

    # ==============
    # Payment #
    # ==============

    @api.multi
    def _get_payment_type(self):
        self.ensure_one()
        if self.require_payment == 2:
            return 'form_save'
        else:
            return 'form'

    @api.multi
    def _confirm_online_quote(self, transaction):
        """ Payment callback: validate the order and write transaction details in chatter """
        # create draft invoice if transaction is ok
        if transaction and transaction.state == 'done':
            transaction._confirm_so()
            message = _('Order paid by %s. Transaction: %s. Amount: %s.') % (transaction.partner_id.name, transaction.acquirer_reference, transaction.amount)
            self.message_post(body=message)
            return True
        return False

    @api.multi
    def _prepare_payment_acquirer(self, values=None):
        self.ensure_one()
        env = self.env
        # auto-increment reference with a number suffix
        # if the reference already exists
        reference = env['payment.transaction'].get_next_reference(self.name)
        acquirers = env['payment.acquirer'].sudo().search([
            ('website_published', '=', True),
            ('company_id', '=', self.company_id.id)
        ])
        payment_method = []
        for acquirer in acquirers:
            acquirer.button = acquirer.render(reference, self.amount_total, self.currency_id.id, values=values)
            payment_method.append(acquirer)

        return {'acquirers': payment_method, 'tokens': None, 'save_option': False}

    @api.multi
    def _prepare_payment_transaction(self, acquirer, tx_type='form', transaction=None, payment_token=None, add_tx_values=None, reset_draft=True):
        self.ensure_one()
        Transaction = self.env['payment.transaction'].sudo()
        # incorrect state or unexisting tx
        if not transaction or transaction.state in ['error', 'cancel']:
            transaction = False
        # unmatching
        if (transaction and acquirer and transaction.acquirer_id != acquirer) or (transaction and transaction.sale_order_id != self):
            transaction = False
        # new or distinct token
        if payment_token and transaction.payment_token_id and payment_token != transaction.payment_token_id:
            transaction = False

        # still draft tx, no more info -> rewrite on tx or create a new one depending on parameter
        if transaction and transaction.state == 'draft':
            if reset_draft:
                transaction.write(dict(
                    transaction.on_change_partner_id(self.partner_id.id).get('value', {}),
                    amount=self.amount_total,
                    type=tx_type)
                )
            else:
                transaction = False

        if not transaction:
            tx_values = {
                'acquirer_id': acquirer.id,
                'type': tx_type,
                'amount': self.amount_total,
                'currency_id': self.currency_id.id,
                'partner_id': self.partner_id.id,
                'partner_country_id': self.partner_id.country_id.id,
                'reference': Transaction.get_next_reference(self.name),
            }
            if add_tx_values:
                tx_values.update(add_tx_values)
            if payment_token and payment_token.sudo().partner_id == self.partner_id:
                tx_values['payment_token_id'] = payment_token.id

            transaction = Transaction.create(tx_values)
            # update record
        self.write({
            'payment_acquirer_id': acquirer.id,
            'payment_tx_id': transaction.id,
        })
        return transaction

    @api.multi
    def render_sale_payment_button(self, transaction, return_url, submit_txt=None, render_values=None):
        self.ensure_one()
        values = {
            'return_url': return_url,
            'partner_id': self.partner_shipping_id.id or self.partner_invoice_id.id,
            'billing_partner_id': self.partner_invoice_id.id,
        }
        if render_values:
            values.update(render_values)

        return transaction.acquirer_id.with_context(submit_class='btn btn-primary', submit_txt=submit_txt or _('Pay Now')).sudo().render(
            transaction.reference,
            self.amount_total,
            self.pricelist_id.currency_id.id,
            values=values,
        )

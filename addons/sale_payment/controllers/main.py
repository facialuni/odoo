# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, http, _
from odoo.http import request
from odoo.addons.payment.controllers.main import _message_post_helper


class SaleQuotation(http.Controller):

    def _get_sale_order(self, order_id, access_token=None, **post):
        if access_token:
            Order = request.env['sale.order'].sudo().search([('id', '=', order_id), ('access_token', '=', access_token)])
        else:
            Order = request.env['sale.order'].search([('id', '=', order_id)])
        return Order

    def _get_quotation_value(self, order_sudo, transaction, token=None, **post):
        days = 0
        if order_sudo.validity_date:
            days = (fields.Date.from_string(order_sudo.validity_date) - fields.Date.from_string(fields.Date.today())).days + 1
        values = {
            'quotation': order_sudo,
            'order_valid': (not order_sudo.validity_date) or (fields.Date.today() <= order_sudo.validity_date),
            'days_valid': days,
            'action': request.env.ref('sale.action_quotations').id,
            'tx_id': transaction.id if transaction else False,
            'tx_state': transaction.state if transaction else False,
            'tx_post_msg': transaction.acquirer_id.post_msg if transaction else False,
            'need_payment': transaction.state in ['draft', 'cancel', 'error'],
            'token': token,
            'save_option': False,
            'show_button_modal_cancel': True,
            'call_url': '/quote/%s/transaction' % order_sudo.id,
        }
        return values

    def _print_invoice_pdf(self, id, xml_id):
        # print report as sudo, since it require access to taxes, payment term, ... and portal
        # does not have those access rights.
        pdf = request.env.ref(xml_id).sudo().with_context(set_viewport_size=True).render_qweb_pdf([id])[0]
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)

    @http.route("/quote/report/html", type='json', auth="public", website=True)
    def quote_html_report(self, order_id=None, token=None, **kwargs):
        # the real quotation report (displayed in HTML format)
        order = self._get_sale_order(order_id, token, **kwargs)
        return request.env.ref('sale.action_report_saleorder').sudo().render_qweb_html([order.id])[0]

    @http.route("/quote/<int:order_id>", type='http', auth="user", website=True)
    def quote_view_user(self, *args, **kwargs):
        return self.quote_view(*args, **kwargs)

    @http.route("/quote/<int:order_id>/<token>", type='http', auth="public", website=True)
    def quote_view(self, order_id, pdf=None, token=None, message=False, **post):
        # use sudo to allow accessing/viewing orders for public user
        # only if he knows the private token
        Order = self._get_sale_order(order_id, token, **post)

        if not Order:
            return request.render('payment.404')

        # Token or not, sudo the order, since portal user has not access on
        # taxes, required to compute the total_amout of SO.
        order_sudo = Order.sudo()
        if pdf:
            return self._print_invoice_pdf(order_sudo.id, 'sale.action_report_saleorder')

        transaction_id = request.session.get('quote_%s_transaction_id' % order_sudo.id)
        if not transaction_id:
            transaction = request.env['payment.transaction'].sudo().search([('reference', '=', order_sudo.name)])
        else:
            transaction = request.env['payment.transaction'].sudo().search([('id', '=', transaction_id)])

        values = self._get_quotation_value(order_sudo, transaction, **post)
        values['message'] = message and int(message) or False

        if order_sudo.require_payment or values['need_payment']:
            render_values = {
                'return_url': '/quote/%s/%s' % (order_id, token) if token else '/quote/%s' % order_id,
                'type': 'form',
                'alias_usage': _('If we store your payment information on our server, subscription payments will be made automatically.'),
                'partner_id': order_sudo.partner_id.id,
            }

            values.update(order_sudo.with_context(submit_class="btn btn-primary", submit_txt=_('Pay & Confirm'))._prepare_payment_acquirer(values=render_values))

        return request.render('sale_payment.so_quotation', values)

    @http.route(['/quote/<int:order_id>/transaction/<int:acquirer_id>'], type='json', auth="public", website=True)
    def quote_payment_transaction(self, acquirer_id, order_id, access_token=None, tx_type=None):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.
        :param int acquirer_id: id of a payment.acquirer record. If not set the
                                user is redirected to the checkout page
        """
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order or not order.order_line or acquirer_id is None:
            return request.redirect("/quote/%s" % order_id)

        # find an already existing transaction
        acquirer = request.env['payment.acquirer'].browse(int(acquirer_id))
        token = request.env['payment.token'].sudo()  # currently no support of payment tokens
        tx = request.env['payment.transaction'].sudo().search([('reference', '=', order.name)], limit=1)
        tx_type = order._get_payment_type()
        tx = order._prepare_payment_transaction(acquirer, tx_type=tx_type, transaction=tx, payment_token=token, add_tx_values={
            'callback_model_id': request.env['ir.model'].sudo().search([('model', '=', order._name)], limit=1).id,
            'callback_res_id': order.id,
            'callback_method': '_confirm_online_quote',
        })
        request.session['quote_%s_transaction_id' % order.id] = tx.id

        return order.render_sale_payment_button(
            tx, '/quote/%s/%s' % (order_id, token) if token else '/quote/%s' % order_id,
            submit_txt=_('Pay & Confirm'), render_values={
                'type': order._get_payment_type(),
                'alias_usage': _('If we store your payment information on our server, subscription payments will be made automatically.'),
            }
        )

    @http.route(['/quote/accept'], type='json', auth="public", website=True)
    def quote_accept(self, order_id, token=None, signer=None, sign=None, **post):
        Order = request.env['sale.order'].sudo().browse(order_id)
        if token != Order.access_token or Order.require_payment:
            return request.render('payment.404')
        if Order.state != 'sent':
            return False
        attachments = [('signature.png', sign.decode('base64'))] if sign else []
        Order.action_confirm()
        message = _('Order signed by %s') % (signer,)
        _message_post_helper(message=message, res_id=order_id, res_model='sale.order', attachments=attachments, **({'token': token, 'token_field': 'access_token'} if token else {}))
        return True

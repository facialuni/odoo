# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models

class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        context = self._context
        one_hour_before = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        if context.get('default_model') == 'sale.order':
            abandoned_cart_domain = [
                ('id', 'in', context.get('active_ids')),
                ('state', '=', 'draft'),
                ('partner_id.id', '!=', self.env.ref('base.public_partner').id),
                ('order_line', '!=', 'False'),
                ('team_id.team_type', '=', 'website'),
                ('date_order', '<', fields.Datetime.to_string(one_hour_before))]
            for order in self.env['sale.order'].search(abandoned_cart_domain):
                order.cart_recovery_email_sent = True
            self = self.with_context(mail_post_autofollow=True)
        return super(MailComposeMessage, self).send_mail(auto_commit=auto_commit)

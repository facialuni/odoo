# -*- coding: utf-8 -*-
import time

from openerp import models, fields, api, _
from openerp.exceptions import Warning
import openerp.addons.decimal_precision as dp

class account_register_payment(models.TransientModel):

    """Register a payment"""

    _name = "account.register.payment"
    _description = "Register payment"
    
    invoice_id = fields.Many2one('account.invoice', String="Related invoice", required=True)
    payment_amount = fields.Float(String='Amount paid', required=True, digits=dp.get_precision('Account'))
    date_paid = fields.Date(String='Date paid', default=fields.Date.context_today, required=True)
    reference = fields.Char('Ref #', help="Transaction reference number.")
    journal_id = fields.Many2one('account.journal', String='Payment Method', required=True, domain=[('type', 'in', ('bank', 'cash'))])
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', readonly=True,
        default=lambda self: self.env.user.company_id)
    partner_id = fields.Many2one('res.partner', related='invoice_id.partner_id', String='Partner', store=True)

    @api.model
    def default_get(self, fields):
        context = dict(self._context or {})
        res = super(account_register_payment, self).default_get(fields)
        if context.get('active_id', False):
            invoice = self.env['account.invoice'].browse(context.get('active_id'))
            res.update({
                'invoice_id': invoice.id,
                'payment_amount': invoice.residual,
            })
        return res

    @api.multi
    def pay(self):
        #create an account_move and account_move_line based on payment
        if self.journal_id.sequence_id:
            if not self.journal_id.sequence_id.active:
                raise Warning(_('Configuration Error !'),
                    _('Please activate the sequence of selected journal !'))
            # name = self.journal_id.sequence_id.next_by_id()
            name = self.pool.get('ir.sequence').next_by_id(self._cr, self._uid, self.journal_id.id, self._context)
        else:
            raise Warning(_('The associated journal does not have a sequence_id, please specify one'))
        move_id = self.env['account.move'].create({
            'name': name,
            'date': self.date_paid,
            'ref': self.reference,
            'company_id': self.company_id.id,
            'journal_id': self.journal_id.id,
            })
        ac_move_line = self.env['account.move.line']
        debit = credit = over_value = 0.0
        #convert to company currency
        currency_payment_amount = self.journal_id.currency and self.journal_id.currency.compute(self.payment_amount, self.company_id.currency_id) or self.payment_amount
        if self.invoice_id.type in ('out_invoice', 'in_refund'):
            credit = max(currency_payment_amount, credit)
        else:
            debit = max(currency_payment_amount, debit)
        sign = debit - credit < 0 and -1 or 1

        name_preffix = 'payment from ' if credit != 0 else 'payment to '
        acl_dict_value = {
            'name': name_preffix+self.partner_id.name,
            'account_id': self.invoice_id.account_id.id,
            'move_id': move_id.id,
            'journal_id': self.journal_id.id,
            'debit': debit,
            'credit': credit,
            'partner_id': self.invoice_id.partner_id.id,
            'currency_id': self.journal_id.currency and self.journal_id.currency.id or False,
            'amount_currency': sign * abs(self.payment_amount) if self.journal_id.currency and self.journal_id.currency != self.company_id.currency_id else 0.0,
            'date': self.date_paid,
            'invoice': self.invoice_id.id,
            }
        payment_line = ac_move_line.create(acl_dict_value)
        
        #create balanced line
        acl_dict_value.update({
            'account_id': self.journal_id.default_debit_account_id.id,
            'debit': credit,
            'credit': debit,
            })
        balanced_line = ac_move_line.create(acl_dict_value)

        move_id.post()

        #reconcile
        if self.invoice_id:
            self.invoice_id.register_payment(payment_line)
        return True

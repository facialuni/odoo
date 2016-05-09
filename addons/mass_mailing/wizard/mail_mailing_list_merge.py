# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MergeMassMailingList(models.TransientModel):
    _name = 'mail.mailing_list.merge'
    _description = 'Merge Mass Mailing List'

    mailing_list_ids = fields.Many2many('mail.mass_mailing.list', string='Mass mail List')
    dst_massmail_list_id = fields.Many2one('mail.mass_mailing.list', string='Destination Mailing List')

    @api.model
    def default_get(self, fields):
        res = super(MergeMassMailingList, self).default_get(fields)
        if self.env.context.get('active_model') == 'mail.mass_mailing.list' and self.env.context.get('active_ids'):
            mail_list = self.env['mail.mass_mailing.list'].browse(self.env.context.get('active_ids')).sorted(key=lambda x: x.id)
            if any(mail_list.filtered(lambda m: not m.active)):
                raise UserError(_('You can not select Archived Maillist to merge!'))
            res['mailing_list_ids'] = mail_list.ids
            res['dst_massmail_list_id'] = mail_list.ids[0]
        return res

    @api.multi
    def action_massmail_merge(self):
        if not self.dst_massmail_list_id:
            raise UserError(_('Please select destination mailing list.'))
        self.dst_massmail_list_id.merge_massmail_list(self.mailing_list_ids, self.dst_massmail_list_id)
        self.dst_massmail_list_id.delete_duplicate_contact()

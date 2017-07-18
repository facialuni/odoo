# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import float_compare


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        model = self._context.get('thread_model') or self._name
        if model == 'hr.expense':
            RecordModel = self.env[model]
            custom_values['product_id'] = self.env['product.product'].search(['|', ('name', '=ilike', custom_values['name']), ('default_code', '=ilike', custom_values['name'])]).id or custom_values['product_id']
            if custom_values.get('employee_id'):
                res = super(MailThread, self).message_new(msg_dict, custom_values)
                template_id = self.env.ref('hr_expense.email_template_hr_expense_success')
                template_id.send_mail(res.id)
                return res
            else:
                base_partner = self.env.ref('base.partner_root')
                template_id = self.env.ref('hr_expense.email_template_hr_expense_falied')
                template_id.write({'email_to': msg_dict['from'].split('<')[1].split('>')[0]})
                template_id.sudo().send_mail(base_partner.id, force_send=True)
                return False
        return super(MailThread, self).message_new(msg_dict, custom_values)

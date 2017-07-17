# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import float_compare


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        model = self._context.get('thread_model') or self._name
        res = super(MailThread, self).message_new(msg_dict, custom_values)
        if model == 'hr.expense':
            data = {}
            RecordModel = self.env[model]
            if isinstance(custom_values, dict):
                data = custom_values.copy()
            data['product_id'] = self.env['product.product'].search(['|', ('name', '=ilike', data['name']), ('default_code', '=ilike', data['name'])]).id or data['product_id']
            res.write({'product_id': data['product_id']})
            if res:
                template_id = self.env.ref('hr_expense.email_template_hr_expense_success')
            else:
                template_id = self.env.ref('hr_expense.email_template_hr_expense_falied')
            template_id.send_mail(res.employee_id.user_id.partner_id.id)
        return res

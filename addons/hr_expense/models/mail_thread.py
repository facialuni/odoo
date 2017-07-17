# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import float_compare


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def message_new(self, msg_dict, custom_values=None):
    	res = super(MailThread, self).message_new(msg_dict, custom_values)
        if model == 'hr.expense':
        	data = {}
	        model = self._context.get('thread_model') or self._name
	        RecordModel = self.env[model]
	        if isinstance(custom_values, dict):
	            data = custom_values.copy()
        	data['product_id'] = self.env['product.product'].search(['|',('name', 'like', data['name']), ('default_code', 'like', data['name'])]).id or data['product_id']
        	expense = RecordModel.create(data)
        return res

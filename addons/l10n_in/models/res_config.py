# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    @api.model
    def get_default_tax_fields(self, fields):
        res = super(AccountConfigSettings, self).get_default_tax_fields(fields=fields)
        if self.env.user.company_id.chart_template_id == self.env.ref('l10n_in.indian_chart_template_standard'):
            res['default_purchase_tax_id'] = self.env.ref('l10n_in.sgst_purchase_5').id
            res['default_sale_tax_id'] = self.env.ref('l10n_in.sgst_sale_5').id
        return res

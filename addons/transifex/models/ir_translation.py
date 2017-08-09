# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from odoo import models, fields


class IrTranslation(models.Model):

    _inherit = 'ir.translation'

    transifex_url = fields.Char("Transifex URL", compute='_get_transifex_url')

    def _get_transifex_url(self):
        """ Construct transifex URL based on the module on configuration """
        # e.g. 'https://www.transifex.com/odoo/odoo-10'
        base_url = self.env['ir.config_parameter'].sudo().get_param('transifex.project_url')

        if not base_url:
            self.transifex_url = False
        else:
            base_url = base_url.rstrip('/')

            # will probably be the same for all terms, avoid multiple searches
            translation_languages = list(set(self.mapped('lang')))
            languages = self.env['res.lang'].with_context(active_test=False).search(
                [('code', 'in', translation_languages)])

            language_codes = dict((l.code, l.iso_code) for l in languages)

            for translation in self:
                if not translation.module or not translation.source or translation.lang == 'en_US':
                    # custom or source term
                    continue

                lang_code = language_codes.get(translation.lang)
                if not lang_code:
                    continue

                translation.transifex_url = "%(url)s/translate/#%(lang)s/%(module)s/42?q=%(src)s" % {
                    'url': base_url,
                    'lang': lang_code,
                    'module': translation.module,
                    'src': werkzeug.url_quote_plus(translation.source[:15]),
                }

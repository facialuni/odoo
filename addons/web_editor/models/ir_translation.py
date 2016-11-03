# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from lxml import etree
from odoo.tools.translate import encode


class IrTranslation(models.Model):
    _inherit = "ir.translation"

    @api.model
    def save(self, translations):
        for trans in translations:
            wrapped = "<div>%s</div>" % encode(trans['value'])
            try:
                etree.fromstring(encode(wrapped)) # check the value with xml parser
            except etree.ParseError:
                root = etree.fromstring(wrapped, etree.HTMLParser(encoding='utf-8'))
                trans['value'] = etree.tostring(root[0][0])[5:-6]           # html > body > div then remove tags <div> and </div>

            trans['name'] = "%s,%s" % (trans.pop('model'), trans.pop('field'))
            trans['src'] = trans['seq']

            if trans.get('id'):
                self.browse(trans.pop('id')).write(trans)
            else:
                self.create(trans)

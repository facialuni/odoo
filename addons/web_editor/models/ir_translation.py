# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import models, api
from odoo.tools.translate import encode


class IrTranslation(models.Model):
    _inherit = 'ir.translation'

    @api.multi
    def save_html(self, value):
        """ Convert the HTML fragment ``value`` to XML if necessary, and write
        it as the value of translation ``self``.
        """
        assert len(self) == 1 and self.type == 'model'
        mname, fname = self.name.split(',')
        field = self.env[mname]._fields[fname]
        if field.translate == xml_translate:
            # wrap value inside a div and parse it as HTML
            div = "<div>%s</div>" % encode(value)
            root = etree.fromstring(div, etree.HTMLParser(encoding='utf-8'))
            # root is html > body > div
            # serialize div as XML and discard surrounding tags
            value = etree.tostring(root[0][0], encoding='utf-8')[5:-6]
        elif field.translate == html_translate:
            # wrap value inside a div and parse it as HTML
            div = "<div>%s</div>" % encode(value)
            root = etree.fromstring(div, etree.HTMLParser(encoding='utf-8'))
            # root is html > body > div
            # serialize div as HTML and discard surrounding tags
            value = etree.tostring(root[0][0], encoding='utf-8', method='html')[5:-6]
        return self.write({'value': value})

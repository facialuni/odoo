# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class TemplatePreview(models.TransientModel):
    _inherit = "mail.template"
    _name = "email_template.preview"
    _description = "Email Template Preview"

    @api.model
    def _get_records(self):
        """ Return Records of particular Email Template's Model """
        template_id = self._context.get('template_id')
        default_res_id = self._context.get('default_res_id')
        if not template_id:
            return []
        template = self.env['mail.template'].browse(int(template_id))
        records = self.env[template.model_id.model].search([], limit=10)
        records |= records.browse(default_res_id)
        return records.name_get()

    @api.model
    def default_get(self, fields):
        result = super(TemplatePreview, self).default_get(fields)

        if 'res_id' in fields and not result.get('res_id'):
            records = self._get_records()
            result['res_id'] = records and records[0][0] or False  # select first record as a Default
        if self._context.get('template_id') and 'model_id' in fields and not result.get('model_id'):
            result['model_id'] = self.env['mail.template'].browse(self._context['template_id']).model_id.id
        return result

    def _default_language(self):
        lang_code = self.env['ir.values'].get_default('res.partner', 'lang')
        def_lang = self.env['res.lang'].search([('code', '=', lang_code)], limit=1)
        return def_lang.id if def_lang else self.env['res.lang'].search([], limit=1)

    res_id = fields.Selection(_get_records, 'Sample Document')
    partner_ids = fields.Many2many('res.partner', string='Recipients')
    language_id = fields.Many2one('res.lang', string='Default Language', default=_default_language)

    @api.onchange('res_id')
    @api.multi
    def on_change_res_id(self):
        mail_values = {}
        if self.res_id and self._context.get('template_id'):
            template = self.env['mail.template'].browse(self._context['template_id'])
            self.name = template.name
            mail_values = template.generate_email(self.res_id)
        for field in ['email_from', 'email_to', 'email_cc', 'reply_to', 'subject', 'body_html', 'partner_to', 'partner_ids', 'attachment_ids']:
            setattr(self, field, mail_values.get(field, False))

    @api.onchange('language_id')
    def _onchange_language_id(self):
        # self.body_html = self.env['mail.template'].browse(self._context['template_id']).with_context(lang=self.language_id.code).body_html
        mail_values = {}
        if self.res_id and self._context.get('template_id'):
            template = self.env['mail.template'].browse(self._context['template_id'])
            template.lang = self.language_id.code
            mail_values = template.with_context(lang=self.language_id.code).generate_email(self.res_id)
            # print "\n\n\n\n\n mail_values -> ", mail_values
        for field in ['email_from', 'email_to', 'email_cc', 'reply_to', 'subject', 'body_html', 'partner_to', 'partner_ids', 'attachment_ids']:
            setattr(self, field, mail_values.get(field, False))

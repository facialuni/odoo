# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models
from odoo.tools import pycompat

PERIODICITY_DAY = {"daily": 1, "weekly": 7, "monthly": 30, "quarterly": 90}
PERIODICITY_DATE = {
    "daily": fields.Datetime.to_string(datetime.datetime.now() - datetime.timedelta(days=1)),
    "weekly": fields.Datetime.to_string(datetime.datetime.now() - datetime.timedelta(days=7)),
    "monthly": fields.Datetime.to_string(datetime.datetime.now() - datetime.timedelta(days=30))
}


class MailDigest(models.Model):
    """ Model of Mail Digest to send daily/weekly/monthly activity to group of users."""
    _name = 'mail.digest'
    _description = 'Mail Digest'

    name = fields.Char(string='Name', required=True)
    user_ids = fields.Many2many('res.users', string='Recipients', required=True)
    periodicity = fields.Selection([
            ('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('quarterly','Quarterly')], string='Periodicity', required=True)
    active = fields.Boolean(string='Active', default=True)
    next_run_date = fields.Date(string='Next Run Date')
    template_id = fields.Many2one('mail.template', string='Email Template', default=lambda self: self.env.ref('mail.mail_digest_mail_template'), required=True)
    kpi_res_users_connected = fields.Boolean(string='Connected Users')
    kpi_res_users_connected_value = fields.Integer(compute='_compute_kpi_res_users_connected_value')
    kpi_mail_message_total = fields.Boolean(string='Messages')
    kpi_mail_message_total_value = fields.Integer(compute='_compute_kpi_mail_message_total_value')
    currency_id = fields.Many2one('res.currency', string='Currency')

    @api.onchange('periodicity')
    def onchange_periodicity(self):
        if self.periodicity:
            self.next_run_date = fields.Date.to_string(fields.datetime.now() + datetime.timedelta(days=PERIODICITY_DAY[self.periodicity]))

    def _compute_kpi_res_users_connected_value(self):
        """ Get total number of user connected in specific time frame(Daily, weekly, Monthly ) to send
        kpi's to specific group of users. """

        periodicity = self.env.context.get("periodicity", "monthly")
        user_connected = self.env['res.users'].search_count([("login_date", ">=", PERIODICITY_DATE[periodicity])])
        for record in self:
            record.kpi_res_users_connected_value = user_connected

    def _compute_kpi_mail_message_total_value(self):
        """ Get total number of messages has been sent in specific time frame(Daily, Weekly, Monthly) to send
        kpi's to specific group of users."""

        periodicity = self.env.context.get("periodicity", "monthly")
        total_messages = self.env['mail.message'].search_count([("create_date", ">=", PERIODICITY_DATE[periodicity])])
        for record in self:
            record.kpi_mail_message_total_value = total_messages

    def compute_kpi_values(self):
        """ get the all kpi values"""
        result = {}
        all_fields = self.fields_get()
        for name, field in pycompat.items(all_fields):
            if field['type'] == "boolean" and (name.startswith("kpi") or name.startswith("x_kpi")):
                for record in self:
                    if record[name]:
                        periodicity_data_dict = {}
                        for periodicity_frequancy in ["daily", "weekly", "monthly"]:
                            periodicity_data_dict.update({"name": field['string'], periodicity_frequancy: record.with_context(periodicity=periodicity_frequancy)[name + '_value']})
                        result.update({name: periodicity_data_dict})
        return result

    def _process_mail_digest_email(self):
        """ Process all active mail digest and send mail digest to respected recipients """
        for mail_digest in self.env['mail.digest'].search([]):
            res_ids_email = mail_digest.user_ids.mapped('email')
            if res_ids_email and mail_digest.next_run_date == fields.Date.to_string(fields.datetime.now()):
                recipients = ",".join(res_ids_email)
                mail_id = mail_digest.template_id.with_context(email_to=recipients).send_mail(mail_digest.id)
                if mail_id:
                    mail_digest.onchange_periodicity()

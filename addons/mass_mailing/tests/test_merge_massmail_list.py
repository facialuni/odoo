# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestMassMailingCommon


class TestMergeMassmailList(TestMassMailingCommon):

    def test_00_merge_massmail_list(self):
        """Merge massmail list with remove duplicate recipients"""

        # Select mass mailing list from mailing list.
        dst_massmail_list = self.merge_mailing_wizard.dst_massmail_list_id
        mass_mail_lists = self.merge_mailing_wizard.mailing_list_ids - dst_massmail_list

        dst_recipients_counts = self.env['mail.mass_mailing.contact'].search_count([('list_ids', 'in', dst_massmail_list.ids), ('opt_out', '!=', True)])
        mass_mailing_recipients_counts = self.env['mail.mass_mailing.contact'].search_count([('list_ids', 'in', mass_mail_lists.ids), ('opt_out', '!=', True)])

        # Check Current recipients of mass mailing before going to merge.
        self.assertEqual(mass_mailing_recipients_counts, 1, 'Recipients of Mass Mailing list should be 1.')
        self.assertEqual(dst_recipients_counts, 2, 'Recipients of Destination Mailing list should be 2 before merged with mailing list .')

        # Merge mass mailing list without removing duplicate.
        self.merge_mailing_wizard.action_massmail_merge()

        #Get recipients of destination mailing list after merge.
        dst_mass_mailing_contacts = self.env['mail.mass_mailing.contact'].search([('list_ids', 'in', dst_massmail_list.ids), ('opt_out', '!=', True)])

        #Check recipients of Destination mailing list after merge with recipients of mailing lists, it should be 3.
        self.assertEqual(len(dst_mass_mailing_contacts), 2, 'Recipients of Destination Mailing list should be 2 after merged  with mailing list.')
        dst_massmail_recipients_emails = dst_mass_mailing_contacts.mapped('email')

        #Check for duplicate recipient in destination mailing list
        self.assertEqual(len(dst_massmail_recipients_emails), len(set(dst_massmail_recipients_emails)), 'Recipients of destination Mailing list should not be duplicate.')

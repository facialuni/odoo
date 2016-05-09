# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestMassMailingCommon(common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestMassMailingCommon, cls).setUpClass()

        mass_mailing_list = cls.env['mail.mass_mailing.list']
        mass_mailing_contact = cls.env['mail.mass_mailing.contact']

        cls.mass_mailing_list_01 = mass_mailing_list.create({
            'name': 'Employee Contact',
            })

        cls.mass_mailing_contact_01 = mass_mailing_contact.create({
            'name': 'Aristide Antario',
            'email': 'aa@example.com',
            'list_ids': [(4, cls.mass_mailing_list_01.ids)]
            })

        cls.mass_mailing_list_02 = mass_mailing_list.create({
            'name': 'sales Contact',
            })

        cls.mass_mailing_contact_02 = mass_mailing_contact.create({
            'name': 'Aristide Antario',
            'email': 'aa@example.com',
            'list_ids': [(4, cls.mass_mailing_list_02.ids)]
            })

        cls.mass_mailing_contact_03 = mass_mailing_contact.create({
            'name': 'Robert Antario',
            'email': 'ra@example.com',
            'list_ids': [(4, cls.mass_mailing_list_02.ids)]
            })

        cls.merge_mailing_wizard = cls.env['mail.mailing_list.merge'].with_context({'active_model': 'mail.mass_mailing.list',
            'active_ids': [cls.mass_mailing_list_01.id, cls.mass_mailing_list_02.id]}).create(
            {'mailing_list_ids': [(6, 0, [cls.mass_mailing_list_01.id, cls.mass_mailing_list_02.id])], 'dst_massmail_list_id': cls.mass_mailing_list_02.id})

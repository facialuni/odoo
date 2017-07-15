# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError

from odoo.addons.mail.tests.common import TestMail


class TestMailFollowers(TestMail):

    def setUp(self):
        super(TestMailFollowers, self).setUp()
        Subtype = self.env['mail.message.subtype']
        self.mt_mg_def = Subtype.create({'name': 'mt_mg_def', 'default': True, 'res_model': 'mail.test'})
        self.mt_cl_def = Subtype.create({'name': 'mt_cl_def', 'default': True, 'res_model': 'crm.lead'})
        self.mt_al_def = Subtype.create({'name': 'mt_al_def', 'default': True, 'res_model': False})
        self.mt_mg_nodef = Subtype.create({'name': 'mt_mg_nodef', 'default': False, 'res_model': 'mail.test'})
        self.mt_al_nodef = Subtype.create({'name': 'mt_al_nodef', 'default': False, 'res_model': False})
        self.default_group_subtypes = Subtype.search([('default', '=', True), '|', ('res_model', '=', 'mail.test'), ('res_model', '=', False)])

    def test_m2o_command_new(self):
        test_channel = self.env['mail.channel'].create({'name': 'Test'})
        groups = self.test_pigs | self.test_public
        self.env['mail.followers']._add_follower_command(
            'mail.test', groups.ids,
            [self.user_employee.partner_id.id],
            [test_channel.id])


    def test_m2o_command_update_selective(self):
        test_channel = self.env['mail.channel'].create({'name': 'Test'})
        groups = self.test_pigs | self.test_public
        self.env['mail.followers'].create({'partner_id': self.user_employee.partner_id.id, 'res_model': 'mail.test', 'res_id': self.test_pigs.id})
        generic, specific = self.env['mail.followers']._add_follower_command(
            'mail.test', groups.ids,
            [self.user_employee.partner_id.id],
            [test_channel.id])

    def test_message_is_follower(self):
        qty_followed_before = len(self.test_pigs.sudo(self.user_employee).search([('message_is_follower', '=', True)]))
        self.assertFalse(self.test_pigs.sudo(self.user_employee).message_is_follower)
        self.test_pigs.message_subscribe_users(user_ids=[self.user_employee.id])
        qty_followed_after = len(self.test_pigs.sudo(self.user_employee).search([('message_is_follower', '=', True)]))
        self.assertTrue(self.test_pigs.sudo(self.user_employee).message_is_follower)
        self.assertEqual(qty_followed_before + 1, qty_followed_after)

    def test_followers_subtypes_default(self):
        self.test_pigs.message_subscribe_users(user_ids=[self.user_employee.id])
        self.assertEqual(self.test_pigs.message_follower_ids.mapped('partner_id'), self.user_employee.partner_id)
        self.assertEqual(self.test_pigs.message_follower_ids.mapped('channel_id'), self.env['mail.channel'])
        follower = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.test'),
            ('res_id', '=', self.test_pigs.id),
            ('partner_id', '=', self.user_employee.partner_id.id)])
        self.assertEqual(len(follower), 1)
        self.assertEqual(follower.subtype_ids, self.default_group_subtypes)

    def test_followers_subtypes_default_internal(self):
        mt_mg_def_int = self.env['mail.message.subtype'].create({'name': 'mt_mg_def', 'default': True, 'res_model': 'mail.test', 'internal': True})
        self.test_pigs.message_subscribe_users(user_ids=[self.user_employee.id])
        print '1i'
        follower = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.test'),
            ('res_id', '=', self.test_pigs.id),
            ('partner_id', '=', self.user_employee.partner_id.id)])
        print '2i'
        self.assertEqual(follower.subtype_ids, self.default_group_subtypes | mt_mg_def_int)
        print '3i'

        self.test_pigs.message_subscribe_users(user_ids=[self.user_portal.id])
        print '4i'
        follower = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.test'),
            ('res_id', '=', self.test_pigs.id),
            ('partner_id', '=', self.user_portal.partner_id.id)])
        print '5i'
        self.assertEqual(follower.subtype_ids, self.default_group_subtypes.filtered(lambda subtype: not subtype.internal))
        print '7i'

    def test_followers_subtypes_specified(self):
        self.test_pigs.sudo(self.user_employee).message_subscribe_users(subtype_ids=[self.mt_mg_nodef.id])
        print '1'
        self.assertEqual(self.test_pigs.message_follower_ids.mapped('partner_id'), self.user_employee.partner_id)
        print '2'
        self.assertEqual(self.test_pigs.message_follower_ids.mapped('channel_id'), self.env['mail.channel'])
        print '3'
        follower = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.test'),
            ('res_id', '=', self.test_pigs.id),
            ('partner_id', '=', self.user_employee.partner_id.id)])
        print '4'
        self.assertEqual(len(follower), 1)
        print '5'
        self.assertEqual(follower.subtype_ids, self.mt_mg_nodef)
        print '6'

    def test_followers_multiple_subscription(self):
        self.test_pigs.sudo(self.user_employee).message_subscribe_users(subtype_ids=[self.mt_mg_nodef.id])
        self.assertEqual(self.test_pigs.message_follower_ids.mapped('partner_id'), self.user_employee.partner_id)
        self.assertEqual(self.test_pigs.message_follower_ids.mapped('channel_id'), self.env['mail.channel'])
        follower = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.test'),
            ('res_id', '=', self.test_pigs.id),
            ('partner_id', '=', self.user_employee.partner_id.id)])
        self.assertEqual(len(follower), 1)
        self.assertEqual(follower.subtype_ids, self.mt_mg_nodef)

        self.test_pigs.sudo(self.user_employee).message_subscribe_users(subtype_ids=[self.mt_mg_nodef.id, self.mt_al_nodef.id])
        self.assertEqual(self.test_pigs.message_follower_ids.mapped('partner_id'), self.user_employee.partner_id)
        self.assertEqual(self.test_pigs.message_follower_ids.mapped('channel_id'), self.env['mail.channel'])
        follower = self.env['mail.followers'].search([
            ('res_model', '=', 'mail.test'),
            ('res_id', '=', self.test_pigs.id),
            ('partner_id', '=', self.user_employee.partner_id.id)])
        self.assertEqual(len(follower), 1)
        self.assertEqual(follower.subtype_ids, self.mt_mg_nodef | self.mt_al_nodef)

    def test_no_DID(self):
        """Test that a follower cannot suffer from dissociative identity disorder.
           It cannot be both a partner and a channel.
        """
        test_record = self.env['mail.channel'].create({
            'name': 'I used to be schizo, but now we are alright.'
        })
        test_channel = self.env['mail.channel'].create({'name': 'Follower Channel'})
        with self.assertRaises(IntegrityError):
            self.env['mail.followers'].create({
                'res_model_id': self.env['ir.model']._get('mail.test').id,
                'res_id': test_record.id,
                'partner_id': self.user_employee.partner_id.id,
                'channel_id': test_channel.id,
            })

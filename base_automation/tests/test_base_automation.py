# # -*- coding: utf-8 -*-
# # Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


@common.at_install(False)
@common.post_install(True)
class BaseAutomationTest(common.TransactionCase):

    def setUp(self):
        super(BaseAutomationTest, self).setUp()
        self.user_admin = self.env.ref('base.user_root')
        self.user_demo = self.env.ref('base.user_demo')

    def create_lead(self, **vals):
        return self.env['base.automation.lead.test'].create(vals)

    def test_00_check_to_state_open_pre(self):
        """
        Check that a new record (with state = open) doesn't change its value
        when there is a precondition filter which check that the state is open.
        """
        lead = self.create_lead(state='open', name='Lead Test', value="init")
        self.assertEqual(lead.state, 'open')
        self.assertEqual(lead.value, 'init', "Date value should not change on creation of Lead with state 'open'.")

    def test_01_check_to_state_draft_post(self):
        lead = self.create_lead(state='open', name='Lead Test 2')
        self.assertEqual(lead.state, 'open', "Lead state should stay 'open'")
        self.assertFalse(lead.value, "Lead should not have a value")

        lead.write({'state': 'draft'})
        self.assertEqual(lead.value, 'reinit', "Lead should have value 'reinit'")
        lead.write({'state': 'open'})
        self.assertEqual(lead.state, 'done', "Lead should have value 'done'")

    def test_10_recomputed_field(self):
        """
        Check that a rule is executed whenever a field is recomputed after a
        change on another model.
        """
        lead = self.create_lead(state='open', name="Lead Test 3")
        lead.write({'state': 'done'})
        self.assertEqual(len(lead.line_ids), 1, "A line should have been created")

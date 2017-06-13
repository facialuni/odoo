# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestIrValues(TransactionCase):

    def test_actions(self):
        # Create some action bindings for a model.
        act_id_1 = self.ref('base.act_values_form_action')
        act_id_2 = self.ref('base.act_values_form_defaults')
        act_id_3 = self.ref('base.action_res_company_form')
        ir_values = self.env['ir.values']
        ir_values.set_action('OnDblClick Action', action_slot='tree_but_open', model='res.partner', action='ir.actions.act_window,%d' % act_id_1, res_id=False)
        ir_values.set_action('OnDblClick Action 2', action_slot='tree_but_open', model='res.partner', action='ir.actions.act_window,%d' % act_id_2, res_id=False)
        ir_values.set_action('Side Wizard', action_slot='client_action_multi', model='res.partner', action='ir.actions.act_window,%d' % act_id_3, res_id=False)

        reports = self.env['ir.actions.report'].search([])
        report_id = next(report.id for report in reports if not report.groups_id)
        ir_values.set_action('Nice Report', action_slot='client_print_multi', model='res.partner', action='ir.actions.report,%d' % report_id, res_id=False)

        # Replace one action binding to set a new name.
        ir_values.set_action('OnDblClick Action New', action_slot='tree_but_open', model='res.partner', action='ir.actions.act_window,%d' % act_id_1, res_id=False)

        # Retrieve the action bindings and check they're correct
        actions = ir_values.get_actions(action_slot='tree_but_open', model='res.partner', res_id=False)
        self.assertEqual(len(actions), 2, "Mismatching number of bound actions")
        # first action
        self.assertEqual(len(actions[0]), 3, "Malformed action definition")
        self.assertEqual(actions[0][1], 'OnDblClick Action 2', 'Bound action does not match definition')
        self.assertTrue(isinstance(actions[0][2], dict) and actions[0][2]['id'] == act_id_2,
                        'Bound action does not match definition')
        # second action - this ones comes last because it was re-created with a different name
        self.assertEqual(len(actions[1]), 3, "Malformed action definition")
        self.assertEqual(actions[1][1], 'OnDblClick Action New', 'Re-Registering an action should replace it')
        self.assertTrue(isinstance(actions[1][2], dict) and actions[1][2]['id'] == act_id_1,
                        'Bound action does not match definition')

        actions = ir_values.get_actions(action_slot='client_action_multi', model='res.partner', res_id=False)
        self.assertEqual(len(actions), 1, "Mismatching number of bound actions")
        self.assertEqual(len(actions[0]), 3, "Malformed action definition")
        self.assertEqual(actions[0][1], 'Side Wizard', 'Bound action does not match definition')
        self.assertTrue(isinstance(actions[0][2], dict) and actions[0][2]['id'] == act_id_3,
                        'Bound action does not match definition')

        actions = ir_values.get_actions(action_slot='client_print_multi', model='res.partner', res_id=False)
        self.assertEqual(len(actions), 1, "Mismatching number of bound actions")
        self.assertEqual(len(actions[0]), 3, "Malformed action definition")
        self.assertEqual(actions[0][1], 'Nice Report', 'Bound action does not match definition')
        self.assertTrue(isinstance(actions[0][2], dict) and actions[0][2]['id'] == report_id,
                        'Bound action does not match definition')

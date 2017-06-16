# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestIrBinding(TransactionCase):

    def test_bindings(self):
        """ check the action bindings on models and records """
        Binding = self.env['ir.binding']

        # first make sure there is no binding
        bindings = Binding.get_all('res.partner')
        self.assertFalse(bindings['client_action_multi'])
        self.assertFalse(bindings['client_print_multi'])
        self.assertFalse(bindings['client_action_relate'])

        # create action bindings, and check the returned bindings
        action1 = self.env.ref('base.ir_binding_menu_action')
        action2 = self.env.ref('base.ir_default_menu_action')
        action3 = self.env['ir.actions.report'].search([('groups_id', '=', False)], limit=1)
        Binding.set('client_action_multi', 'res.partner', action1.id)
        Binding.set('client_action_multi', 'res.partner', action2.id)
        Binding.set('client_print_multi', 'res.partner', action3.id)

        bindings = Binding.get_all('res.partner')
        self.assertItemsEqual(
            [a['id'] for a in bindings['client_action_multi']],
            (action1 + action2).ids,
            "Wrong action bindings",
        )
        self.assertItemsEqual(
            [a['id'] for a in bindings['client_print_multi']],
            action3.ids,
            "Wrong action bindings",
        )
        self.assertItemsEqual(
            [a['id'] for a in bindings['client_action_relate']],
            [],
            "Wrong action bindings",
        )

        # add a group on an action, and check that it is not returned
        group = self.env.ref('base.group_user')
        action2.groups_id += group
        self.env.user.groups_id -= group

        bindings = Binding.get_all('res.partner')
        self.assertItemsEqual(
            [a['id'] for a in bindings['client_action_multi']],
            action1.ids,
            "Wrong action bindings",
        )
        self.assertItemsEqual(
            [a['id'] for a in bindings['client_print_multi']],
            action3.ids,
            "Wrong action bindings",
        )
        self.assertItemsEqual(
            [a['id'] for a in bindings['client_action_relate']],
            [],
            "Wrong action bindings",
        )

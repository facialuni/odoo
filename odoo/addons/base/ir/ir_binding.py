# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import AccessError, MissingError


BINDING_TYPES = [
    ('client_action_multi', "Sidebar action"),
    ('client_print_multi', "Sidebar report print"),
    ('client_action_relate', "Sidebar related link"),
]


class IrBinding(models.Model):
    """ Binding of an action to a model or a specific record. """
    _name = 'ir.binding'
    _rec_name = 'action_id'

    type = fields.Selection(BINDING_TYPES, string="Binding Type", required=True)
    model_id = fields.Many2one('ir.model', string="Model",
                               required=True, ondelete='cascade',
                               help="The model to which the action applies.")
    action_id = fields.Many2one('ir.actions.actions', string='Action',
                                required=True, ondelete='restrict')

    @api.model
    @api.returns('self', lambda value: value.id)
    def set(self, type, model_name, action_id):
        """ Create if necessary a binding for the given model and action. """
        model = self.env['ir.model']._get(model_name)
        binding = self.search([('model_id', '=', model.id), ('action_id', '=', action_id)])
        if not binding:
            binding = self.create({'type': type, 'model_id': model.id, 'action_id': action_id})
        elif binding.type != type:
            binding.write({'type': type})
        return binding

    @api.model
    def get_all(self, model_name):
        """ Retrieve the list of actions bound to the given model.

           :return: a dict mapping binding types to a list of dict describing
                    actions, where the latter is given by calling the method
                    ``read`` on the action record.
        """
        cr = self.env.cr
        query = """ SELECT b.type, a.type AS action_model, b.action_id
                    FROM ir_binding b
                    JOIN ir_model m ON b.model_id=m.id AND m.model=%s
                    JOIN ir_actions a ON b.action_id=a.id
                    ORDER BY b.id """
        cr.execute(query, [model_name])

        # discard unauthorized actions, and read action definitions
        result = defaultdict(list)
        user_groups = self.env.user.groups_id
        for type, action_model, action_id in cr.fetchall():
            try:
                action = self.env[action_model].browse(action_id)
                action_groups = getattr(action, 'groups_id', ())
                if action_groups and not action_groups & user_groups:
                    # the user may not perform this action
                    continue
                result[type].append(action.read()[0])
            except (AccessError, MissingError):
                continue

        return result

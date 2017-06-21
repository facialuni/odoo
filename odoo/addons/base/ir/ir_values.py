# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models, tools
from odoo.tools import pickle

import logging
_logger = logging.getLogger(__name__)

#: Possible slots to bind an action to with :meth:`~.set_action`
ACTION_SLOTS = [
    "client_action_multi",      # sidebar wizard action
    "client_print_multi",       # sidebar report printing button
    "client_action_relate",     # sidebar related link
    "tree_but_open",            # double-click on item in tree view
    "tree_but_action",          # deprecated: same as tree_but_open
]


class IrValues(models.Model):
    """Holds internal model-specific action bindings and user-defined default
       field values. definitions. This is a legacy internal model, mixing
       two different concepts, and will likely be updated or replaced in a
       future version by cleaner, separate models. You should not depend
       explicitly on it.

       The purpose of each ``ir.values`` entry depends on its type, defined
       by the ``key`` column:

        * 'default': user-defined default values, used when creating new
          records of this model:
        * 'action': binding of an action to a particular *action slot* of
          this model, making the action easily available in the user
          interface for this model.

       The ``key2`` column acts as a qualifier, further refining the type
       of the entry. The possible values are:

        * for 'default' entries: an optional condition restricting the
          cases where this particular default value will be applicable,
          or ``False`` for no condition
        * for 'action' entries: the ``key2`` qualifier is one of the available
          action slots, defining how this action can be invoked:

            * ``'client_print_multi'`` for report printing actions that will
              be available on views displaying items from this model
            * ``'client_action_multi'`` for assistants (wizards) actions
              that will be available in views displaying objects of this model
            * ``'client_action_relate'`` for links towards related documents
              that should be available in views displaying objects of this model
            * ``'tree_but_open'`` for actions that will be triggered when
              double-clicking an item from this model in a hierarchical tree view

       Each entry is specific to a model (``model`` column), and for ``'actions'``
       type, may even be made specific to a given record of that model when the
       ``res_id`` column contains a record ID (``False`` means it's global for
       all records).

       The content of the entry is defined by the ``value`` column, which may either
       contain an arbitrary value, or a reference string defining the action that
       should be executed.

       .. rubric:: Usage: default values
       
       The ``'default'`` entries are usually defined manually by the
       users, and set by their UI clients calling :meth:`~.set_default`.
       These default values are then automatically used by the
       ORM every time a new record is about to be created, i.e. when
       :meth:`~odoo.models.Model.default_get`
       or :meth:`~odoo.models.Model.create` are called.

       .. rubric:: Usage: action bindings

       Business applications will usually bind their actions during
       installation, and Odoo UI clients will apply them as defined,
       based on the list of actions included in the result of
       :meth:`~odoo.models.Model.fields_view_get`,
       or directly returned by explicit calls to :meth:`~.get_actions`.
    """
    _name = 'ir.values'

    name = fields.Char(required=True)
    model = fields.Char(string='Model Name', index=True, required=True,
                        help="Model to which this entry applies")

    # TODO: model_id and action_id should be read-write function fields
    model_id = fields.Many2one('ir.model', string='Model (change only)',
                               help="Model to which this entry applies - "
                                    "helper field for setting a model, will "
                                    "automatically set the correct model name")
    action_id = fields.Many2one('ir.actions.actions', string='Action (change only)',
                                help="Action bound to this entry - "
                                     "helper field for binding an action, will "
                                     "automatically set the correct reference")

    value = fields.Text(help="Default value (pickled) or reference to an action")
    value_unpickle = fields.Text(string='Default value or action reference',
                                 compute='_value_unpickle', inverse='_value_pickle')
    key = fields.Selection([('action', 'Action')],
                           string='Type', index=True, required=True, default='action',
                           help="- Action: an action attached to one slot of the given model")
    key2 = fields.Char(string='Qualifier', index=True, default='tree_but_open',
                       help="For actions, one of the possible action slots: \n"
                            "  - client_action_multi\n"
                            "  - client_print_multi\n"
                            "  - client_action_relate\n"
                            "  - tree_but_open\n"
                            "For defaults, an optional condition")
    res_id = fields.Integer(string='Record ID', index=True,
                            help="Database identifier of the record to which this applies. "
                                 "0 = for all records")
    user_id = fields.Many2one('res.users', string='User', ondelete='cascade', index=True,
                              help="If set, action binding only applies for this user.")
    company_id = fields.Many2one('res.company', string='Company', ondelete='cascade', index=True,
                                 help="If set, action binding only applies for this company")

    @api.depends('key', 'value')
    def _value_unpickle(self):
        for record in self:
            value = record.value
            if record.key == 'default' and value:
                # default values are pickled on the fly
                with tools.ignore(Exception):
                    value = str(pickle.loads(value))
            record.value_unpickle = value

    def _value_pickle(self):
        context = dict(self._context)
        context.pop(self.CONCURRENCY_CHECK_FIELD, None)
        for record in self.with_context(context):
            value = record.value_unpickle
            # Only char-like fields should be written directly. Other types should be converted to
            # their appropriate type first.
            if record.model in self.env and record.name in self.env[record.model]._fields:
                field = self.env[record.model]._fields[record.name]
                if field.type not in ['char', 'text', 'html', 'selection']:
                    value = literal_eval(value)
            if record.key == 'default':
                value = pickle.dumps(value)
            record.value = value

    @api.onchange('model_id')
    def onchange_object_id(self):
        if self.model_id:
            self.model = self.model_id.model

    @api.onchange('action_id')
    def onchange_action_id(self):
        if self.action_id:
            self.value_unpickle = self.action_id

    @api.model_cr_context
    def _auto_init(self):
        res = super(IrValues, self)._auto_init()
        tools.create_index(self._cr, 'ir_values_key_model_key2_res_id_user_id_idx',
                           self._table, ['key', 'model', 'key2', 'res_id', 'user_id'])
        return res

    @api.model
    def create(self, vals):
        self.clear_caches()
        return super(IrValues, self).create(vals)

    @api.multi
    def write(self, vals):
        self.clear_caches()
        return super(IrValues, self).write(vals)

    @api.multi
    def unlink(self):
        self.clear_caches()
        return super(IrValues, self).unlink()

    @api.model
    @api.returns('self', lambda value: value.id)
    def set_default(self, model, field_name, value, for_all_users=True, company_id=False, condition=False):
        """ Deprecated, use the model 'ir.default' instead. """
        assert condition is False
        _logger.warning("Deprecated use of ir_values.set_default()")
        self.env['ir.default'].set(model, field_name, value, user_id=not for_all_users, company_id=company_id)
        return self

    @api.model
    def get_default(self, model, field_name, for_all_users=True, company_id=False, condition=False):
        """ Deprecated, use the model 'ir.default' instead. """
        assert condition is False
        _logger.warning("Deprecated use of ir_values.get_default()")
        return self.env['ir.default']._get(model, field_name, user_id=not for_all_users, company_id=company_id)

    @api.model
    def get_defaults(self, model, condition=False):
        """ Deprecated, use the model 'ir.default' instead. """
        assert condition is False
        _logger.warning("Deprecated use of ir_values.get_defaults()")
        defaults = self.env['ir.default'].get_all(model)
        return [(False, fname, value) for fname, value in defaults.values()]

    @api.model
    def get_defaults_dict(self, model, condition=False):
        """ Deprecated, use the model 'ir.default' instead. """
        assert condition is False
        _logger.warning("Deprecated use of ir_values.get_defaults_dict()")
        return self.env['ir.default'].get_all(model)

    @api.model
    @api.returns('self', lambda value: value.id)
    def set_action(self, name, action_slot, model, action, res_id=False):
        """ Deprecated, use the model 'ir.binding' instead. """
        assert isinstance(action, basestring) and ',' in action, \
               'Action definition must be an action reference, e.g. "ir.actions.act_window,42"'
        assert action_slot in ACTION_SLOTS, \
               'Action slot (%s) must be one of: %r' % (action_slot, ACTION_SLOTS)
        assert res_id is False

        _logger.warning("Deprecated use of ir_values.set_action()")
        action_id = int(action.split(',')[1])
        self.env['ir.binding'].set(action_slot, model, action_id)
        return self

    @api.model
    @tools.ormcache_context('self._uid', 'action_slot', 'model', 'res_id', keys=('lang',))
    def get_actions(self, action_slot, model, res_id=False):
        """ Deprecated, use the model 'ir.binding' instead. """
        assert action_slot in ACTION_SLOTS, 'Illegal action slot value: %s' % action_slot
        assert res_id is False

        _logger.warning("Deprecated use of ir_values.get_actions()")
        bindings = self.env['ir.binding'].get_all(model)
        return [(42, action['name'], action) for action in bindings[action_slot]]

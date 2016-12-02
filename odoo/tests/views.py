# -*- coding: utf-8 -*-
"""
Pseudo-view implementations for server-side testing, mostly for views which
heavily interact with the server and make testing the corresponding models
difficult.
"""
import collections

DEFAULTS = {
    'boolean': False,
    'integer': 0,
    'float': 0.0,
    'monetary': 0.0,
    'char': u'',
    'text': u'',
    'html': u'',
    'date': False,
    'datetime': False,
    'selection': False,
    'many2one': False,
    'one2many': [],
    'many2many': [],
}
class Form(collections.MutableMapping):
    """ Pseudo form view, implementing onchanges.

    Takes a model object and (optional) view id, the form will fill up based
    on default_get and default values for view fields not provided by the
    latter.

    Should be used as a map, setting fields with ``form[field_name] = value``
    or retrieving them with the same, onchange will automatically be called
    based on those setting.

    All calls are performed using the provided model object (and its
    environment).

    .. warning:: deleting a field from the form sets it to the default *for
                 the type* (not the one from default_get)

    .. todo:: loading existing records

        currently the form only supports creation mode (start from an empty
        form), could be useful to allow providing an object id (maybe a
        singleton recordset input?)

    .. todo:: save (create/write)

        use a ChainMap(local, remote), on saving create/write using local
        (possibly filtered cf next section), clear local, and read() back
        record to remote

        split makes it easy to know what has been changed either directly or
        via onchange

    .. todo:: modifiers (domains)

        * readonly: prevent setting the field explicitly ?exclude value during create/write?
        * invisible: prevent setting the field explicitly
        * required: fail if trying to save

    .. todo:: domain & warning returned from onchange
    """
    def __init__(self, model, view_id=None):
        self.Model = model

        fvg = model.fields_view_get(view_id=view_id, view_type='form')
        self.onchanges = model._onchange_spec(fvg)

        self.fields = fvg['fields']
        self.data = self._fixup(model.default_get(self.fields.keys()))

        # onchange() needs values in all the fields, so we need to fill all
        # those for which default_get didn't yield anything
        for k, v in self.fields.iteritems():
            self.data.setdefault(k, DEFAULTS[v['type']])

        # initial onchange with default_get values
        self._onchange(self.fields.keys())

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        assert key in self.fields, "trying to set field {} which is not in the view".format(key)
        self.data[key] = value
        self._onchange([key])

    def __delitem__(self, key):
        self[key] = DEFAULTS[self.fields[key]['type']]

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        return iter(self.data)

    def _fixup(self, values, fields=None):
        """ un-nameget-ify m2o fields (recursively into o2m and m2m) """
        if fields is None:
            fields = self.fields

        for k in list(values):
            # remove field of values not in view
            if k not in fields:
                del values[k]
                continue

            field = fields[k]
            field_type = field['type']
            if field_type == 'many2one' and isinstance(values[k], (list, tuple)):
                values[k] = values[k][0]
            elif field_type in ('one2many', 'many2many'):
                sub_fvg = field['views'].get('form') or \
                          self.Model.env[field['relation']].fields_view_get(view_type='form')
                for command in values[k] or []:
                    if command[0] in (0, 1):
                        self._fixup(command[2], sub_fvg['fields'])
        return values

    def _onchange(self, fields):
        self.Model.env.invalidate_all()
        self.data.update(self._fixup(self.Model.onchange(self.data, fields, self.onchanges).get('value', {})))

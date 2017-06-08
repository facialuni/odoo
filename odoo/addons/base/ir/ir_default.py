# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError


class IrDefault(models.Model):
    """ User-defined default values for fields. """
    _name = 'ir.default'
    _rec_name = 'field_id'

    field_id = fields.Many2one('ir.model.fields', string="Field", required=True,
                               ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string='User', ondelete='cascade', index=True,
                              help="If set, action binding only applies for this user.")
    company_id = fields.Many2one('res.company', string='Company', ondelete='cascade', index=True,
                                 help="If set, action binding only applies for this company")
    json_value = fields.Char('Default Value (JSON format)', required=True)

    @api.model
    def create(self, vals):
        self.clear_caches()
        return super(IrDefault, self).create(vals)

    @api.multi
    def write(self, vals):
        if self:
            self.clear_caches()
        return super(IrDefault, self).write(vals)

    @api.multi
    def unlink(self):
        if self:
            self.clear_caches()
        return super(IrDefault, self).unlink()

    @api.model
    def set(self, model_name, field_name, value, user_id=False, company_id=False):
        """ Defines a default value for the given field. Any entry for the same
            scope (field, user, company) will be replaced. The value is encoded
            in JSON to be stored to the database.

            :param user_id: may be ``False`` for all users, ``True`` for the
                            current user, or any user id
            :param company_id: may be ``False`` for all companies, ``True`` for
                               the current user's company, or any company id
        """
        if user_id is True:
            user_id = self.env.uid
        if company_id is True:
            company_id = self.env.user.company_id.id

        # check consistency of model_name, field_name, and value
        try:
            model = self.env[model_name]
            field = model._fields[field_name]
            field.convert_to_cache(value, model)
            json_value = json.dumps(value, ensure_ascii=False)
        except KeyError:
            raise ValidationError(_("Invalid field %s.%s") % (model_name, field_name))
        except Exception:
            raise ValidationError(_("Invalid value for %s.%s: %s") % (model_name, field_name, value))

        # update existing default for the same scope, or create one
        field = self.env['ir.model.fields']._get(model_name, field_name)
        default = self.search([
            ('field_id', '=', field.id),
            ('user_id', '=', user_id),
            ('company_id', '=', company_id),
        ])
        if default:
            default.write({'json_value': json_value})
        else:
            self.create({
                'field_id': field.id,
                'user_id': user_id,
                'company_id': company_id,
                'json_value': json_value,
            })
        return True

    @api.model
    def _get(self, model_name, field_name, user_id=False, company_id=False):
        """ Return the default value for the given field, user and company, or
            ``None`` if no default is available.

            :param user_id: may be ``False`` for all users, ``True`` for the
                            current user, or any user id
            :param company_id: may be ``False`` for all companies, ``True`` for
                               the current user's company, or any company id
        """
        if user_id is True:
            user_id = self.env.uid
        if company_id is True:
            company_id = self.env.user.company_id.id

        field = self.env['ir.model.fields']._get(model_name, field_name)
        default = self.search([
            ('field_id', '=', field.id),
            ('user_id', '=', user_id),
            ('company_id', '=', company_id),
        ], limit=1)
        return json.loads(default.json_value) if default else None

    @api.model
    def get(self, model_name, field_name):
        """ Return the default value for the given field, or ``None`` if no
            default is available. The defaults are considered in the following
            order, and the first available one is returned:

                * specific to the user and their company,
                * specific to the user,
                * specific to the user's company,
                * not specific.
        """
        return self.get_all(model_name).get(field_name)

    @api.model
    @tools.ormcache('self.env.uid', 'model_name')
    # Note about ormcache invalidation: it is not needed when deleting a field,
    # a user, or a company, as the corresponding defaults will no longer be
    # requested. It must only be done when a user's company is modified.
    def get_all(self, model_name):
        """ Return the available default values for the given model (for the
            current user), as a dict mapping field names to values.
        """
        cr = self.env.cr
        query = """ SELECT f.name, d.json_value FROM ir_default d
                    JOIN ir_model_fields f ON d.field_id=f.id
                    JOIN res_users u ON u.id=%s
                    WHERE f.model=%s
                        AND (d.user_id IS NULL OR d.user_id=u.id)
                        AND (d.company_id IS NULL OR d.company_id=u.company_id)
                    ORDER BY d.user_id, d.company_id, d.id
                """
        cr.execute(query, (self.env.uid, model_name))
        result = {}
        for row in cr.fetchall():
            # keep the highest priority default for each field
            if row[0] not in result:
                result[row[0]] = json.loads(row[1])
        return result

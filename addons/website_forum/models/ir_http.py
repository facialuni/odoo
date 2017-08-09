import odoo
from odoo import models
from odoo.http import request
from odoo.tools import pycompat
from odoo.exceptions import AccessError

from odoo.addons.base.ir.ir_http import RequestUID


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _postprocess_args(cls, arguments, rule):
        if rule.rule == '/forum/<model("forum.forum"):forum>':
            for key, val in list(pycompat.items(arguments)):
                if key == 'forum' and isinstance(val, models.BaseModel) and isinstance(val._uid, RequestUID):
                    arguments[key] = val.sudo(request.uid)
            try:
                _, path = rule.build(arguments)
                assert path is not None
            except AccessError:
                return request.env["ir.ui.view"].render_template('website_forum.error_403')
        super(IrHttp, cls)._postprocess_args(arguments, rule)

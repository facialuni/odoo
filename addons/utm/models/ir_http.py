# -*- coding: utf-8 -*-
from odoo.http import request
from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def get_utm_domain_cookies(self):
        return request.httprequest.host

    def _dispatch(self):
        tracked_fields = self.pool['utm.mixin'].tracking_fields()
        response = super(IrHttp, self)._dispatch()


        # no set_cookie on Exception
        if isinstance(response, Exception):
            return response

        for var, dummy, cook in tracked_fields:
            if var in request.params and request.httprequest.cookies.get(var) != request.params[var]:
                response.set_cookie(cook, request.params[var], domain=self.get_utm_domain_cookies())

        return response

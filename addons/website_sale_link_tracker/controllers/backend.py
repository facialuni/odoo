# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.website_sale.controllers.backend import WebsiteSaleBackend
from odoo.http import request


class WebsiteSaleLinkTrackerBackend(WebsiteSaleBackend):

    @http.route()
    def fetch_dashboard_data(self, date_from, date_to):
        results = super(WebsiteSaleLinkTrackerBackend, self).fetch_dashboard_data(date_from, date_to)
        results['dashboards']['sales']['utm_grpah'] = self.fetch_utm_data(date_from, date_to)

        return results

    def fetch_utm_data(self, date_from, date_to):
        utm_response_data = {}
        sale_utm_domain = [
            ('team_id.team_type', '=', 'website'),
            ('state', 'in', ['sale', 'done']),
            ('confirmation_date', '>=', date_from),
            ('confirmation_date', '<=', date_to)
        ]

        campaign_data = request.env['sale.order'].read_group(
            domain=sale_utm_domain + [('campaign_id', '!=', False)],
            fields=['amount_total', 'id', 'campaign_id'],
            groupby='campaign_id'
        )
        utm_campaign_data = self.compute_utm_graph_data('campaign_id', campaign_data)

        medium_data = request.env['sale.order'].read_group(
            domain=sale_utm_domain + [('medium_id', '!=', False)],
            fields=['amount_total', 'id', 'medium_id'],
            groupby='medium_id'
        )
        utm_medium_data = self.compute_utm_graph_data('medium_id', medium_data)

        source_data = request.env['sale.order'].read_group(
            domain=sale_utm_domain + [('source_id', '!=', False)],
            fields=['amount_total', 'id', 'source_id'],
            groupby='source_id'
        )
        utm_source_data = self.compute_utm_graph_data('source_id', source_data)

        utm_response_data = {
            'campaign_id': utm_campaign_data,
            'medium_id': utm_medium_data,
            'source_id': utm_source_data
        }

        return utm_response_data

    def compute_utm_graph_data(self, utm_type, utm_graph_data):
        utm_type_graph_data = []
        for data in utm_graph_data:
            utm_type_graph_data.append({
                'utmtype': data[utm_type][1],
                'amount_total': data['amount_total'],
            })

        return utm_type_graph_data

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2014 Tech Receptives (<http://techreceptives.com>)

{
    'name': 'Singapore - Accounting',
    'author': 'Tech Receptives',
    'website': 'http://www.techreceptives.com',
    'category': 'Localization',
    'description': """
Singapore accounting chart and localization.
=======================================================

This module add, for accounting:
    * The Chart of Accounts of Singapore
    * Field UEN (Unique Entity Number) to company and partner (used to generate IRAS Audit File)
    * Field PermitNo and PermitNoDate to invoice (used to generate IRAS Audit File) 

    """,
    'depends': ['base', 'account'],
    'data': [
             'data/l10n_sg_chart_data.xml',
             'data/account_tax_data.xml',
             'data/account_chart_template_data.yml',
             'views/res_company_view.xml',
             'views/res_partner_view.xml',
             'views/account_invoice_view.xml',
    ],
}

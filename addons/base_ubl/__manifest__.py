# -*- coding: utf-8 -*-
{
    'name': "base_ubl",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account', 'document'],

    'data': [
        'data/unece/unece_agencies.xml',
        'data/unece/unece_code_types.xml',
        'data/unece/unece_code_taxes.xml',
        'data/unece/unece_code_categories.xml',
        'views/account_tax_view.xml',
    ]
}
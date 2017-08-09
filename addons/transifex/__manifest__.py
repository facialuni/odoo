# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Transifex integration',
    'version': '1.0',
    'summary': 'Add a link to correct a translation in Transifex',
    'category': 'Extra Tools',
    'description':
    """
Transifex integration
=====================
This module will add a link to the Transifex project in the translation view.
The purpose of this module is to speed up translations of the interface.
        """,
    'data': [
        'data/transifex_data.xml',
        'data/ir_translation_view.xml',
    ],
    'depends': ['base'],
}

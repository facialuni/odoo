# -*- coding: utf-8 -*-
import cgi
import collections
import datetime
import json
import os.path
import re
import time
from lxml.doctestcompare import LXMLOutputChecker

import simplejson
import sys
import werkzeug

from dateutil import relativedelta
from lxml import etree

from openerp.addons.base.ir import ir_qweb

import openerp.modules

from openerp.tests import common


class TestQWebTField(common.TransactionCase):
    def setUp(self):
        super(TestQWebTField, self).setUp()
        self.engine = self.registry('ir.qweb')

    def context(self, values):
        return ir_qweb.QWebContext(
            self.cr, self.uid, values, context={'inherit_branding': True})

    def test_trivial(self):
        field = etree.Element('span', {'t-field': u'company.name'})

        Companies = self.registry('res.company')
        company_id = Companies.create(self.cr, self.uid, {
            'name': "My Test Company"
        })
        result = self.engine.render_node(field, self.context({
            'company': Companies.browse(self.cr, self.uid, company_id),
        }))

        self.assertEqual(
            result,
            '<span data-oe-model="res.company" data-oe-id="%d" '
            'data-oe-field="name" data-oe-type="char" '
            'data-oe-expression="company.name">%s</span>' % (
                company_id,
                "My Test Company",))

    def test_i18n(self):
        field = etree.Element('span', {'t-field': u'company.name'})

        Companies = self.registry('res.company')
        s = u"Testing «ταБЬℓσ»: 1<2 & 4+1>3, now 20% off!"
        company_id = Companies.create(self.cr, self.uid, {
            'name': s,
        })
        result = self.engine.render_node(field, self.context({
            'company': Companies.browse(self.cr, self.uid, company_id),
        }))

        self.assertEqual(
            result,
            '<span data-oe-model="res.company" data-oe-id="%d" '
            'data-oe-field="name" data-oe-type="char" '
            'data-oe-expression="company.name">%s</span>' % (
                company_id,
                cgi.escape(s.encode('utf-8')),))

    def test_reject_crummy_tags(self):
        field = etree.Element('td', {'t-field': u'company.name'})

        with self.assertRaisesRegexp(
                AssertionError,
                r'^RTE widgets do not work correctly'):
            self.engine.render_node(field, self.context({
                'company': None
            }))

    def test_reject_t_tag(self):
        field = etree.Element('t', {'t-field': u'company.name'})

        with self.assertRaisesRegexp(
                AssertionError,
                r'^t-field can not be used on a t element'):
            self.engine.render_node(field, self.context({
                'company': None
            }))


class TestQWeb(common.TransactionCase):
    matcher = re.compile('^qweb-test-(.*)\.xml$')

    @classmethod
    def get_cases(cls):
        path = cls.qweb_test_file_path()

        return (
            cls("test_qweb_{}".format(cls.matcher.match(f).group(1)))
            for f in os.listdir(path)
            # js inheritance
            if f != 'qweb-test-extend.xml'
            if cls.matcher.match(f)
        )

    @classmethod
    def qweb_test_file_path(cls):
        path = os.path.dirname(
            openerp.modules.get_module_resource(
                'web', 'static', 'lib', 'qweb', 'qweb2.js'))
        return path

    def __getattr__(self, item):
        if not item.startswith('test_qweb_'):
            raise AttributeError("No {} on {}".format(item, self))

        f = 'qweb-test-{}.xml'.format(item[10:])
        path = self.qweb_test_file_path()

        return lambda: self.run_test_file(os.path.join(path, f))

    def run_test_file(self, path):
        doc = etree.parse(path).getroot()
        loader = ir_qweb.FileSystemLoader(path)
        context = ir_qweb.QWebContext(self.cr, self.uid, {}, loader=loader)
        qweb = self.env['ir.qweb']
        for template in loader:
            if not template or template.startswith('_'):
                continue
            param = doc.find('params[@id="{}"]'.format(template))
            # OrderedDict to ensure JSON mappings are iterated in source order
            # so output is predictable & repeatable
            params = {} if param is None else json.loads(param.text,
                                                         object_pairs_hook=collections.OrderedDict)

            ctx = context.copy()
            ctx.update(params)
            result = doc.find('result[@id="{}"]'.format(template)).text
            self.assertEqual(
                qweb.render(template, qwebcontext=ctx).strip(),
                (result or u'').strip().encode('utf-8'),
                template
            )


from .large_rendering_data import qweb_test_data
R = collections.namedtuple('Record', 'name')
Request = collections.namedtuple('Request', 'cr uid env params')
def _w_init(self, name, menu_id, user_id):
    self.name = name
    self.menu_id = menu_id
    self.user_id = user_id
    self._fields = {
        'name': qweb_test_data.Field(type='char')
    }
W = type('Website', (qweb_test_data.Base,), {'__init__': _w_init})
M = collections.namedtuple('Menu', 'child_id')
class TestLargeRendering(common.TransactionCase):
    def test_forum_thread(self):
        QWeb = self.env['ir.qweb']
        curdir = os.path.dirname(__file__)
        loader = ir_qweb.FileSystemLoader(os.path.join(
            curdir, 'large_rendering_data', 'forum_templates.xml'
        ))
        user = qweb_test_data.ResUsers(
            login='public',
            partner_id=qweb_test_data.ResPartner(name="Public User", image=None),
            karma=666,
            email=None)
        context = ir_qweb.QWebContext(self.cr, self.uid, {
            'env': self.env,
            'keep_query': lambda *_, **kw: werkzeug.urls.url_encode(kw),
            'request': Request(cr=self.cr, uid=self.uid, env=self.env, params={}),
            'debug': False,
            'json': simplejson,
            'quote_plus': werkzeug.url_quote_plus,
            'time': time,
            'datetime': datetime,
            'relativedelta': relativedelta,
            'res_company': R(name="Bob Inc"),

            'main_object': qweb_test_data.long_question,
            'question': qweb_test_data.long_question,
            'can_bump': False,
            'header': {'question_data': False},
            'filters': 'question',
            'reversed': reversed,
            'user': user,
            'user_id': user,
            'website': W(name="Website", menu_id=M(child_id=[]), user_id=user),
            'is_public_user': True,
            'notifications': [],
            'searches': {},
            'forum_welcome_message': False,
            'validation_email_sent': True,
            'validation_email_done': True,
            'forum': qweb_test_data.website_forum.forum_help,
            'slug': lambda it: str(it[0] if isinstance(it, tuple) else it.id)
        }, loader=loader)

        result = QWeb.render('post_description_full', qwebcontext=context)
        got = etree.fromstring(result, parser=etree.HTMLParser(encoding='utf-8', remove_blank_text=True))
        with open(os.path.join(curdir, 'large_rendering_data', 'forum_result.html'), 'rb') as f:
            want = etree.fromstring(f.read(), parser=etree.HTMLParser(encoding='utf-8', remove_blank_text=True))

        checker = LXMLOutputChecker()
        assert checker.compare_docs(want, got), \
            checker.collect_diff(want, got, html=True, indent=2)


def load_tests(loader, suite, _):
    # can't override TestQWeb.__dir__ because dir() called on *class* not
    # instance
    suite.addTests(TestQWeb.get_cases())
    return suite

# -*- coding: utf-8 -*-
import ast
import collections
import copy
import cStringIO
import datetime
import hashlib
import json
import itertools
import logging
import math
import os
import re
import sys
import textwrap
import uuid
from subprocess import Popen, PIPE
from urlparse import urlparse

import __builtin__

import babel
import babel.dates
import werkzeug
from lxml import etree, html
from PIL import Image
import psycopg2

import openerp.http
import openerp.tools
import openerp.tools.lru

from openerp.http import request
from openerp.osv import osv, orm, fields
from openerp.tools import func, misc, safe_eval, html_escape as escape
from openerp.tools.translate import _

from . import _astgen

_logger = logging.getLogger(__name__)

MAX_CSS_RULES = 4095

#--------------------------------------------------------------------
# QWeb template engine
#--------------------------------------------------------------------
class QWebException(Exception):
    def __init__(self, message, **kw):
        Exception.__init__(self, message)
        self.qweb = dict(kw)
    def pretty_xml(self):
        if 'node' not in self.qweb:
            return ''
        return etree.tostring(self.qweb['node'], pretty_print=True)

class QWebTemplateNotFound(QWebException):
    pass

def raise_qweb_exception(etype=None, **kw):
    if etype is None:
        etype = QWebException
    orig_type, original, tb = sys.exc_info()
    try:
        raise etype, original, tb
    except etype, e:
        for k, v in kw.items():
            e.qweb[k] = v
        # Will use `raise foo from bar` in python 3 and rename cause to __cause__
        e.qweb['cause'] = original
        raise

def _build_attribute(name, value):
    value = escape(value)
    if isinstance(name, unicode): name = name.encode('utf-8')
    if isinstance(value, unicode): value = value.encode('utf-8')
    return ' %s="%s"' % (name, value)

class FileSystemLoader(object):
    def __init__(self, path):
        # TODO: support multiple files #add_file() + add cache
        self.path = path
        self.doc = etree.parse(path).getroot()

    def __iter__(self):
        for node in self.doc:
            name = node.get('t-name')
            if name:
                yield name

    def __call__(self, name):
        for node in self.doc:
            if node.get('t-name') == name:
                root = etree.Element('templates')
                root.append(copy.deepcopy(node))
                arch = etree.tostring(root, encoding='utf-8', xml_declaration=True)
                return arch

class EvalDict(collections.Mapping):
    """ Mapping proxying on an evaluation context, also builtins

    * prevents access to cr and loader
    * acts as a defaultdict(lambda: None) so code can try to access unset
      variables and will just get None
    """
    def __init__(self, ctx):
        self._ctx = ctx

    def __iter__(self):
        return (k for k in self._ctx if k not in ('cr', 'loader'))

    def __len__(self):
        l = len(self._ctx)
        if 'cr' in self._ctx:
            l -= 1
        if 'loader' in self._ctx:
            l -= 1
        return l

    def __getitem__(self, key):
        if key in ('cr', 'loader'):
            return None
        try:
            return self._ctx[key]
        except KeyError:
            return getattr(__builtin__, key, None)

# FIXME: raise_qweb_exception on errors
class QWebContext(dict):
    def __init__(self, cr, uid, data, loader=None, context=None, templates=None):
        self.cr = cr
        self.uid = uid
        self.loader = loader
        self.context = context
        dic = dict(data)
        super(QWebContext, self).__init__(dic)
        self['defined'] = lambda key: key in self
        self.templates = templates or {}
        self.eval_dict = EvalDict(self)

    def safe_eval(self, expr):
        locals_dict = collections.defaultdict(lambda: None)
        locals_dict.update(self)
        locals_dict.pop('cr', None)
        locals_dict.pop('loader', None)
        return safe_eval.safe_eval(expr, None, locals_dict, nocopy=True, locals_builtins=True)

    def copy(self):
        """ Clones the current context, conserving all data and metadata
        (loader, template cache, ...)
        """
        return QWebContext(self.cr, self.uid, dict.copy(self),
                           loader=self.loader,
                           context=self.context,
                           templates=self.templates)

    def __copy__(self):
        return self.copy()

_set_seq = iter(itertools.count())
class QWeb(orm.AbstractModel):
    """ Base QWeb rendering engine

    * to customize ``t-field`` rendering, subclass ``ir.qweb.field`` and
      create new models called :samp:`ir.qweb.field.{widget}`
    * alternatively, override :meth:`~.get_converter_for` and return an
      arbitrary model to use as field converter

    Beware that if you need extensions or alterations which could be
    incompatible with other subsystems, you should create a local object
    inheriting from ``ir.qweb`` and customize that.
    """

    _name = 'ir.qweb'

    _void_elements = frozenset([
        'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'keygen',
        'link', 'menuitem', 'meta', 'param', 'source', 'track', 'wbr'])
    _format_regex = re.compile(
        '(?:'
            # ruby-style pattern
            '#\{(.+?)\}'
        ')|(?:'
            # jinja-style pattern
            '\{\{(.+?)\}\}'
        ')')

    def get_template(self, name, qwebcontext):
        origin_template = qwebcontext.get('__caller__') or qwebcontext['__stack__'][0]
        try:
            document = qwebcontext.loader(name)
        except ValueError:
            raise_qweb_exception(message="Loader could not find template %r" % name, template=origin_template)
        else:
            if document is not None:
                if hasattr(document, 'documentElement'):
                    dom = document
                elif document.startswith("<?xml"):
                    dom = etree.fromstring(document)
                else:
                    dom = etree.parse(document).getroot()

                res_id = isinstance(name, (int, long)) and name or None
                for node in dom:
                    if node.get('t-name') or (res_id and node.tag == "t"):
                        return node

        raise raise_qweb_exception(message="Template %r not found" % name, template=origin_template)

    def _compile(self, element):
        ctx = _astgen.CompileContext()
        # TODO: load all templates in same module (no indirection via ctx.templates) or lazy load templates (!!!)
        # TODO: make locations work based on source element (?)
        mod = _astgen.base_module()

        doc_body = self._compile_document(element, ctx=ctx)
        call = ctx.call_body(doc_body)

        mod.body.extend(ctx._functions)
        ast.fix_missing_locations(mod)
        ns = {'nodes': ctx._nodes}
        eval(compile(mod, '<template>', 'exec'), ns)
        return ns[call.func.id]

    def _directives_eval_order(self):
        """ Should list all supported directives in the order in which they
        should evaluate when set on the same element. E.g. if a node bearing
        both ``foreach`` and ``if`` should see ``foreach`` executed before
        ``if`` aka

        .. code-block:: xml

            <el t-foreach="foo" t-as="bar" t-if="bar">

        should be equivalent to

        .. code-block:: xml

            <t t-foreach="foo" t-as="bar">
                <t t-if="bar">
                    <el>

        then this method should return ``['foreach', 'if']``
        """
        return [
            'call-assets',
            'foreach', 'if', 'call',
            'set', 'field', 'debug'
        ]

    def _nondirectives_ignore(self):
        """
        t-* attributes existing as support for actual directives, should just
        be ignored

        :returns: set
        """
        return {
            't-name', 't-field-options', 't-esc-options', 't-as',
            't-value', 't-valuef', 't-ignore',
            # they are directives but not handled via directive handlers so...
            't-esc', 't-raw'
        }

    def _compile_element(self, el, body, ctx):
        # doesn't generate any content itself
        body = self._compile_body(el, body, ctx)

        opening = []
        closing = []
        if el.tag != 't':
            # build opening tag
            opening = [_astgen.append(ast.Str(u'<' + el.tag + u''.join(
                u' {}="{}"'.format(name, escape(value))
                for name, value in el.attrib.iteritems()
                if not name.startswith('t-')
            )))]
            # dynamic attributes codegen
            # TODO: should be able to generate a single expression/append
            for name, value in el.attrib.iteritems():
                if name.startswith('t-attf-'):
                    opening.append(ast.Assign(
                        targets=[ast.Name(id='result', ctx=ast.Store())],
                        value=_astgen.compile_format(value)
                    ))
                    opening.extend(ast.parse(textwrap.dedent("""
                    if result:
                        output.append(u' {}="{{}}"'.format(escape(result)))
                    """.format(name[7:]))).body)
                elif name.startswith('t-att-'):
                    opening.append(ast.Assign(
                        targets=[ast.Name(id='result', ctx=ast.Store())],
                        value=_astgen.compile_strexpr(value)
                    ))
                    opening.extend(ast.parse(textwrap.dedent("""
                    if result:
                        output.append(u' {}="{{}}"'.format(escape(result)))
                    """.format(name[6:]))).body)
                elif name == 't-att':
                    opening.append(ast.Assign(
                        targets=[ast.Name(id='result', ctx=ast.Store())],
                        value=_astgen.compile_expr(value)
                    ))
                    opening.extend(ast.parse(textwrap.dedent("""
                        output.extend(
                            u' {}="{}"'.format(name, escape(value))
                            for name, value in (
                                result.iteritems() if isinstance(result, collections.Mapping)
                                else [result]
                            ) if value
                        )
                    """)).body)
            opening.append(_astgen.append(ast.Str(u'>')))

            if el.tag not in self._void_elements:
                closing = [_astgen.append(ast.Str(u'</%s>' % el.tag))]

        return opening + body + closing

    def _compile_body(self, el, body, ctx):
        if el.get('t-esc'):
            # TODO: widgets
            return [_astgen.append(ast.Call(
                func=ast.Name(id='escape', ctx=ast.Load()),
                args=[_astgen.compile_strexpr(el.get('t-esc'))],
                keywords=[],
            ))] + body
        elif el.get('t-raw'):
            return [_astgen.append(_astgen.compile_strexpr(el.get('t-raw')))] + body

        return self._compile_text(el, body, ctx)

    def _compile_directive_set(self, el, body, ctx):
        if 't-value' in el.attrib:
            value = _astgen.compile_expr(el.get('t-value'))
        elif 't-valuef' in el.attrib:
            value = _astgen.compile_format(el.get('t-valuef'))
        else:
            render = ctx.call_body(body, prefix='set')
            if render is None:
                value = ast.Str(u'')
            else:
                # concat body render to string
                value = ast.Call(
                    func=ast.Attribute(value=ast.Str(u''), attr='join', ctx=ast.Load()),
                    args=[render], keywords=[]
                )

        return [ast.Assign(
            [ast.Subscript(
                value=ast.Name(id='qwebcontext', ctx=ast.Load()),
                slice=ast.Index(ast.Str(el.get('t-set'))),
                ctx=ast.Store()
            )],
            value
        )]

    def _compile_directive_call(self, el, body, ctx):
        """
        :param etree._Element el:
        :param list body:
        :param _astgen.CompileContext ctx:
        :return: new body
        :rtype: list(ast.AST)
        """
        # TODO: add support for t-lang="<expr>"
        # if t-lang
        # * store old lang
        # * verify lang exists in res.lang
        # * set lang in context
        # * run with lang
        # * reset/don't copy back lang
        # TODO: template name as format string
        # TODO: integer template name
        tmpl = el.get('t-call')

        qw = 'qwebcontext_copy'
        call = ctx.call_body(body, ['self', qw], prefix='prepare_call')

        if call is None:
            val = ast.Str(u'')
        else:
            val = ast.Call(
                func=ast.Attribute(value=ast.Str(u''), attr='join', ctx=ast.Load()),
                args=[call], keywords=[]
            )
        body = [
            # qwebcontext_copy = qwebcontext.copy()
            ast.Assign(
                [ast.Name(id=qw, ctx=ast.Store())],
                ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='qwebcontext', ctx=ast.Load()),
                        attr='copy',
                        ctx=ast.Load()
                    ),
                    args=[], keywords=[]
                )
            ),
            # qwebcontext_copy[0] = $value
            ast.Assign(
                [ast.Subscript(
                    value=ast.Name(id=qw, ctx=ast.Load()),
                    slice=ast.Index(ast.Num(0)),
                    ctx=ast.Store()
                )],
                val
            ),
            # output.extend
            _astgen.extend(
                # (qwebcontext_copy)
                ast.Call(
                    # ($tmpl, qwebcontext)
                    func=ast.Call(
                        # self._get_template
                        func=ast.Attribute(
                            value=ast.Name(id='self', ctx=ast.Load()),
                            attr='_get_template',
                            ctx=ast.Load()
                        ),
                        args=[
                            ast.Str(str(tmpl)),
                            ast.Name(id='qwebcontext', ctx=ast.Load()),
                        ],
                        keywords=[]
                    ),
                    args=[
                        ast.Name(id='self', ctx=ast.Load()),
                        ast.Name(id=qw, ctx=ast.Load()),
                    ],
                    keywords=[]
                )
            )
        ]
        return body

    def _compile_directive_if(self, el, body, ctx):
        return [
            ast.If(
                test=_astgen.compile_expr(el.get('t-if')),
                body=body,
                orelse=[]
            )
        ]
    def _compile_directive_foreach(self, el, body, ctx):
        expr = _astgen.compile_expr(el.get('t-foreach'))
        varname = el.get('t-as').replace('.', '_')

        # foreach_iterator(qwebcontext, <expr>, varname)
        it = ast.Call(
            func=ast.Name(id='foreach_iterator', ctx=ast.Load()),
            args=[ast.Name(id='qwebcontext', ctx=ast.Load()), expr, ast.Str(varname)],
            keywords=[]
        )
        # itertools.repeat(self)
        selfs = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='itertools', ctx=ast.Load()),
                attr='repeat',
                ctx=ast.Load()
            ), args=[ast.Name(id='self', ctx=ast.Load())], keywords=[]
        )
        # itertools.imap($call, repeat(self), it)
        call = ctx.call_body(body, prefix='foreach')
        it = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='itertools', ctx=ast.Load()),
                attr='imap',
                ctx=ast.Load()
            ), args=[call.func, selfs, it], keywords=[]
        )
        # itertools.chain.from_iterable(previous)
        it = ast.Call(
            func=ast.Attribute(
                value=ast.Attribute(
                    value=ast.Name(id='itertools', ctx=ast.Load()),
                    attr='chain',
                    ctx=ast.Load()
                ),
                attr='from_iterable',
                ctx=ast.Load()
            ), args=[it], keywords=[]
        )
        return [_astgen.extend(it)]

    def _compile_document(self, element, ctx):
        """
        Compiles a document rooted in ``element`` to a Python AST. The
        resulting ast statements should be returned or yielded.

        ``register_call`` is a function used to record templates seen during
        compilation which may need to be compiled themselves.

        Calls the following hooks:

        * ``_compile_element`` compiles the non-directive parts (static &
          attribute generation & any other) of the element to AST
        * :samp:`_compile_directive_{name}` compiles the directive of the
          specified name to AST

        In either case, the current etree._Element is received as first
        parameter and the current body as second. The body *must* be returned,
        it can either be the original body (possibly modified in place) or a
        brand new list of AST nodes (containing the original body or not).
        """
        # stack of body items collected by subtrees
        bodies = [[]]
        skipto = None
        ignored = self._nondirectives_ignore()

        for event, el in etree.iterwalk(element, events=('start', 'end'),
                                        # ignore comments & processing instructions
                                        tag=etree.Element):
            # skip subtree to specified element
            if skipto is not None:
                if el is skipto:
                    skipto = None
                continue

            if event == 'start':
                if el.get("groups") and not self.user_has_groups(groups=el.get('groups')):
                    skipto = el
                    continue
                bodies.append([])

            if event != 'end':
                continue

            body = bodies.pop()
            # TODO: render_text/render_tail/render_attribute overload
            body = self._compile_element(el, body, ctx)
            directives = {
                att[2:]
                for att in el.attrib
                if att.startswith('t-')
                if not att.startswith('t-att')
                if att not in ignored
            }
            for name in reversed(self._directives_eval_order()):
                # skip directives not present on the element
                if name not in directives: continue

                directives.remove(name)
                mname = name.replace('-', '_')
                compile_handler = getattr(self, '_compile_directive_%s' % mname, None)
                interpret_handler = 'render_tag_%s' % mname
                if compile_handler:
                    if hasattr(self, interpret_handler):
                        _logger.warning(
                            "Directive '%s' is AOT-compiled. Dynamic "
                            "interpreter %s will ignored",
                            name, interpret_handler
                        )
                    body = compile_handler(el, body, ctx)
                elif hasattr(self, interpret_handler):
                    # output.append(self._runtime_trampoline(store(el), qwebcontext))
                    body = [_astgen.append(ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id='self', ctx=ast.Load()),
                            attr='_runtime_trampoline',
                            ctx=ast.Load()
                        ),
                        args=[
                            ctx.store_node(el),
                            ast.Name(id='qwebcontext', ctx=ast.Load()),
                            ast.Str(interpret_handler)
                        ],
                        keywords=[]
                    ))]
                else:
                    raise_qweb_exception(message="Unknown directive %s on %s" % (name, etree.tostring(el)))

            body = self._compile_tail(el, body, ctx)
            bodies[-1].extend(body)

        return bodies.pop()

    def _compile_text(self, el, body, ctx):
        if el.text is not None:
            body.insert(0, _astgen.append(ast.Str(unicode(el.text))))
        return body

    def _compile_tail(self, el, body, ctx):
        if el.tail is not None:
            body.append(_astgen.append(ast.Str(unicode(el.tail))))
        return body

    # assume cache will be invalidated by third party on write to ir.ui.view
    # or groups access rights changes, maybe could use declarative "clear
    # cache" spec so they can be duplicated without risking extra work?
    @openerp.tools.ormcache('self.env.uid', 'tmpl')
    def _get_template(self, tmpl, qwebcontext):
        element = self.get_template(tmpl, qwebcontext)
        element.attrib.pop("name", False)
        return self._compile(element)

    def render(self, cr, uid, id_or_xml_id, qwebcontext=None, loader=None, context=None):
        """ render(cr, uid, id_or_xml_id, qwebcontext=None, loader=None, context=None)

        Renders the template specified by the provided template name

        :param qwebcontext: context for rendering the template
        :type qwebcontext: dict or :class:`QWebContext` instance
        :param loader: if ``qwebcontext`` is a dict, loader set into the
                       context instantiated for rendering
        """
        # noinspection PyMethodFirstArgAssignment
        self = self.browse(cr, uid, [], context=context)
        if qwebcontext is None:
            qwebcontext = {}

        if not isinstance(qwebcontext, QWebContext):
            qwebcontext = QWebContext(cr, uid, qwebcontext, loader=loader, context=context)

        qwebcontext['__template__'] = id_or_xml_id
        stack = qwebcontext.get('__stack__', [])
        if stack:
            qwebcontext['__caller__'] = stack[-1]
        stack.append(id_or_xml_id)
        qwebcontext['__stack__'] = stack
        qwebcontext['xmlid'] = str(stack[0]) # Temporary fix

        template_function = self._get_template(id_or_xml_id, qwebcontext)
        result = template_function(self, qwebcontext)
        # is the encoding necessary?
        return u''.join(result).encode('utf-8')

    def _runtime_trampoline(self, element, qwebcontext, handler_name):
        """ Trampoline between AOT-compiled QWeb and runtime-implemented qweb
        directives. Reimplements part of render_node (and kinda duplicates
        _compile_element) to extract the g_att and t_att from the node.
        """
        template_attributes = {}
        generated_attributes = []
        for name, value in element.attrib.iteritems():
            name = str(name)
            if name == "groups":
                can_see = self.user_has_groups(groups=value)
                if not can_see:
                    return ''
            value = value.encode("utf8")
            if name.startswith("t-"):
                if name.startswith('t-att'):
                    if name.startswith("t-attf-"):
                        attrs = (name[7:], self.eval_format(value, qwebcontext))
                    elif name.startswith("t-att-"):
                        attrs = (name[6:], self.eval(value, qwebcontext))
                    else: # t-att=
                        attrs = self.eval_object(value, qwebcontext)

                    if isinstance(attrs, collections.Mapping):
                        attrs = attrs.iteritems()
                    else:
                        # assume tuple
                        attrs = [attrs]

                    for att, val in attrs:
                        if not val: continue
                        generated_attributes.append(_build_attribute(att, val))
                else:
                    template_attributes[name[2:]] = value
            else:
                generated_attributes.append(_build_attribute(name, value))
        res = getattr(self, handler_name)(
            element,
            template_attributes,
            ''.join(generated_attributes),
            qwebcontext
        )
        if isinstance(res, str):
            return res.decode('utf-8')
        return res

    def render_tag_call_assets(self, element, template_attributes, generated_attributes, qwebcontext):
        """ This special 't-call' tag can be used in order to aggregate/minify javascript and css assets"""
        if len(element):
            # An asset bundle is rendered in two differents contexts (when genereting html and
            # when generating the bundle itself) so they must be qwebcontext free
            # even '0' variable is forbidden
            template = qwebcontext.get('__template__')
            raise QWebException("t-call-assets cannot contain children nodes", template=template)
        xmlid = template_attributes['call-assets']
        cr, uid, context = [getattr(qwebcontext, attr) for attr in ('cr', 'uid', 'context')]
        bundle = AssetsBundle(xmlid, cr=cr, uid=uid, context=context, registry=self.pool)
        css = self.get_attr_bool(template_attributes.get('css'), default=True)
        js = self.get_attr_bool(template_attributes.get('js'), default=True)
        async = self.get_attr_bool(template_attributes.get('async'), default=False)
        return bundle.to_html(css=css, js=js, debug=bool(qwebcontext.get('debug')), async=async)

    def eval(self, expr, qwebcontext):
        try:
            return qwebcontext.safe_eval(expr)
        except Exception:
            template = qwebcontext.get('__template__')
            raise_qweb_exception(message="Could not evaluate expression %r" % expr, expression=expr, template=template)
    def eval_object(self, expr, qwebcontext):
        return self.eval(expr, qwebcontext)
    def eval_str(self, expr, qwebcontext):
        if expr == "0":
            return qwebcontext.get(0, '')
        val = self.eval(expr, qwebcontext)
        if isinstance(val, unicode):
            return val.encode("utf8")
        if val is False or val is None:
            return ''
        return str(val)
    def eval_format(self, expr, qwebcontext):
        expr, replacements = self._format_regex.subn(
            lambda m: self.eval_str(m.group(1) or m.group(2), qwebcontext),
            expr
        )
        if replacements:
            return expr
        try:
            return str(expr % qwebcontext)
        except Exception:
            template = qwebcontext.get('__template__')
            raise_qweb_exception(message="Format error for expression %r" % expr, expression=expr, template=template)

    def render_element(self, element, template_attributes, generated_attributes, qwebcontext, inner=None):
        # element: element
        # template_attributes: t-* attributes
        # generated_attributes: generated attributes
        # qwebcontext: values
        # inner: optional innerXml
        name = str(element.tag)
        if inner:
            g_inner = inner.encode('utf-8') if isinstance(inner, unicode) else inner
        else:
            g_inner = [] if element.text is None else [element.text.encode('utf-8')]

            if len(element):
                raise_qweb_exception(
                    message="Children nodes not supported anymore on "
                            "dynamically rendered directives",
                    node=element, template=qwebcontext.get('template')
                )
        inner = "".join(g_inner)
        if name == "t":
            return inner
        elif len(inner) or name not in self._void_elements:
            return "<%s%s>%s</%s>" % tuple(
                it if isinstance(it, str) else it.encode('utf-8')
                for it in (name, generated_attributes, inner, name)
            )
        else:
            return "<%s%s/>" % (name, generated_attributes)

    def render_tag_field(self, element, template_attributes, generated_attributes, qwebcontext):
        """ eg: <span t-record="browse_record(res.partner, 1)" t-field="phone">+1 555 555 8069</span>"""
        node_name = element.tag
        assert node_name not in ("table", "tbody", "thead", "tfoot", "tr", "td",
                                 "li", "ul", "ol", "dl", "dt", "dd"),\
            "RTE widgets do not work correctly on %r elements" % node_name
        assert node_name != 't',\
            "t-field can not be used on a t element, provide an actual HTML node"

        record, field_name = template_attributes["field"].rsplit('.', 1)
        record = self.eval_object(record, qwebcontext)
        assert hasattr(record, '_fields'), template_attributes['field']
        field = record._fields[field_name]
        foptions = self.eval_format(template_attributes.get('field-options') or '{}', qwebcontext)
        options = json.loads(foptions)

        field_type = get_field_type(field, options)

        converter = self.get_converter_for(field_type)

        return converter.to_html(qwebcontext.cr, qwebcontext.uid, field_name, record, options,
                                 element, template_attributes, generated_attributes, qwebcontext, context=qwebcontext.context)

    def get_converter_for(self, field_type):
        """ returns a :class:`~openerp.models.Model` used to render a
        ``t-field``.

        By default, tries to get the model named
        :samp:`ir.qweb.field.{field_type}`, falling back on ``ir.qweb.field``.

        :param str field_type: type or widget of field to render
        """
        return self.pool.get('ir.qweb.field.' + field_type, self.pool['ir.qweb.field'])

    def get_widget_for(self, widget):
        """ returns a :class:`~openerp.models.Model` used to render a
        ``t-esc``

        :param str widget: name of the widget to use, or ``None``
        """
        widget_model = ('ir.qweb.widget.' + widget) if widget else 'ir.qweb.widget'
        return self.pool.get(widget_model) or self.pool['ir.qweb.widget']

    def get_attr_bool(self, attr, default=False):
        if attr:
            attr = attr.lower()
            if attr in ('false', '0'):
                return False
            elif attr in ('true', '1'):
                return True
        return default

#--------------------------------------------------------------------
# QWeb Fields converters
#--------------------------------------------------------------------

class FieldConverter(osv.AbstractModel):
    """ Used to convert a t-field specification into an output HTML field.

    :meth:`~.to_html` is the entry point of this conversion from QWeb, it:

    * converts the record value to html using :meth:`~.record_to_html`
    * generates the metadata attributes (``data-oe-``) to set on the root
      result node
    * generates the root result node itself through :meth:`~.render_element`
    """
    _name = 'ir.qweb.field'

    def attributes(self, cr, uid, field_name, record, options,
                   source_element, g_att, t_att, qweb_context,
                   context=None):
        """ attributes(cr, uid, field_name, record, options, source_element, g_att, t_att, qweb_context, context=None)

        Generates the metadata attributes (prefixed by ``data-oe-`` for the
        root node of the field conversion. Attribute values are escaped by the
        parent.

        The default attributes are:

        * ``model``, the name of the record's model
        * ``id`` the id of the record to which the field belongs
        * ``field`` the name of the converted field
        * ``type`` the logical field type (widget, may not match the field's
          ``type``, may not be any Field subclass name)
        * ``translate``, a boolean flag (``0`` or ``1``) denoting whether the
          field is translatable
        * ``readonly``, has this attribute if the field is readonly
        * ``expression``, the original expression

        :returns: iterable of (attribute name, attribute value) pairs.
        """
        field = record._fields[field_name]
        field_type = get_field_type(field, options)
        data = [
            ('data-oe-model', record._name),
            ('data-oe-id', record.id),
            ('data-oe-field', field_name),
            ('data-oe-type', field_type),
            ('data-oe-expression', t_att['field']),
        ]
        if field.readonly:
            data.append(('data-oe-readonly', 1))
        return data

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        """ value_to_html(cr, uid, value, field, options=None, context=None)

        Converts a single value to its HTML version/output
        """
        if not value: return ''
        return value

    def record_to_html(self, cr, uid, field_name, record, options=None, context=None):
        """ record_to_html(cr, uid, field_name, record, options=None, context=None)

        Converts the specified field of the browse_record ``record`` to HTML
        """
        field = record._fields[field_name]
        return self.value_to_html(
            cr, uid, record[field_name], field, options=options, context=context)

    def to_html(self, cr, uid, field_name, record, options,
                source_element, t_att, g_att, qweb_context, context=None):
        """ to_html(cr, uid, field_name, record, options, source_element, t_att, g_att, qweb_context, context=None)

        Converts a ``t-field`` to its HTML output. A ``t-field`` may be
        extended by a ``t-field-options``, which is a JSON-serialized mapping
        of configuration values.

        A default configuration key is ``widget`` which can override the
        field's own ``_type``.
        """
        try:
            content = self.record_to_html(cr, uid, field_name, record, options, context=context)
            if options.get('html-escape', True):
                content = escape(content)
            elif hasattr(content, '__html__'):
                content = content.__html__()
        except Exception:
            _logger.warning("Could not get field %s for model %s",
                            field_name, record._name, exc_info=True)
            content = None

        inherit_branding = context and context.get('inherit_branding')
        if not inherit_branding and context and context.get('inherit_branding_auto'):
            inherit_branding = self.pool['ir.model.access'].check(cr, uid, record._name, 'write', False, context=context)

        if inherit_branding:
            # add branding attributes
            g_att += ''.join(
                _build_attribute(name, value)
                for name, value in self.attributes(
                    cr, uid, field_name, record, options,
                    source_element, g_att, t_att, qweb_context,
                    context=context)
            )

        return self.render_element(cr, uid, source_element, t_att, g_att,
                                   qweb_context, content)

    def qweb_object(self):
        return self.pool['ir.qweb']

    def render_element(self, cr, uid, source_element, t_att, g_att,
                       qweb_context, content):
        """ render_element(cr, uid, source_element, t_att, g_att, qweb_context, content)

        Final rendering hook, by default just calls ir.qweb's ``render_element``
        """
        return self.qweb_object().render_element(
            source_element, t_att, g_att, qweb_context, content or '')

    def user_lang(self, cr, uid, context):
        """ user_lang(cr, uid, context)

        Fetches the res.lang object corresponding to the language code stored
        in the user's context. Fallbacks to en_US if no lang is present in the
        context *or the language code is not valid*.

        :returns: res.lang browse_record
        """
        if context is None: context = {}

        lang_code = context.get('lang') or 'en_US'
        Lang = self.pool['res.lang']

        return Lang.browse(cr, uid, Lang._lang_get(cr, uid, lang_code), context=context)

class IntegerConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.integer'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        if context is None:
            context = {}

        lang_code = context.get('lang') or 'en_US'
        return self.pool['res.lang'].format(cr, uid, [lang_code], '%d', value, grouping=True)

class FloatConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.float'
    _inherit = 'ir.qweb.field'

    def precision(self, cr, uid, field, options=None, context=None):
        _, precision = field.digits or (None, None)
        return precision

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        if context is None:
            context = {}
        precision = self.precision(cr, uid, field, options=options, context=context)
        fmt = '%f' if precision is None else '%.{precision}f'

        lang_code = context.get('lang') or 'en_US'
        lang = self.pool['res.lang']
        formatted = lang.format(cr, uid, [lang_code], fmt.format(precision=precision), value, grouping=True)

        # %f does not strip trailing zeroes. %g does but its precision causes
        # it to switch to scientific notation starting at a million *and* to
        # strip decimals. So use %f and if no precision was specified manually
        # strip trailing 0.
        if precision is None:
            formatted = re.sub(r'(?:(0|\d+?)0+)$', r'\1', formatted)
        return formatted

class DateConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.date'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        if not value or len(value)<10: return ''
        lang = self.user_lang(cr, uid, context=context)
        locale = babel.Locale.parse(lang.code)

        if isinstance(value, basestring):
            value = datetime.datetime.strptime(
                value[:10], openerp.tools.DEFAULT_SERVER_DATE_FORMAT)

        if options and 'format' in options:
            pattern = options['format']
        else:
            strftime_pattern = lang.date_format
            pattern = openerp.tools.posix_to_ldml(strftime_pattern, locale=locale)

        return babel.dates.format_date(
            value, format=pattern,
            locale=locale)

class DateTimeConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.datetime'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        if not value: return ''
        lang = self.user_lang(cr, uid, context=context)
        locale = babel.Locale.parse(lang.code)

        if isinstance(value, basestring):
            value = datetime.datetime.strptime(
                value, openerp.tools.DEFAULT_SERVER_DATETIME_FORMAT)
        value = fields.datetime.context_timestamp(
            cr, uid, timestamp=value, context=context)

        if options and 'format' in options:
            pattern = options['format']
        else:
            strftime_pattern = (u"%s %s" % (lang.date_format, lang.time_format))
            pattern = openerp.tools.posix_to_ldml(strftime_pattern, locale=locale)

        if options and options.get('hide_seconds'):
            pattern = pattern.replace(":ss", "").replace(":s", "")

        return babel.dates.format_datetime(value, format=pattern, locale=locale)

class TextConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.text'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        """
        Escapes the value and converts newlines to br. This is bullshit.
        """
        if not value: return ''

        return nl2br(value, options=options)

class SelectionConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.selection'
    _inherit = 'ir.qweb.field'

    def record_to_html(self, cr, uid, field_name, record, options=None, context=None):
        value = record[field_name]
        if not value: return ''
        field = record._fields[field_name]
        selection = dict(field.get_description(record.env)['selection'])
        return self.value_to_html(
            cr, uid, selection[value], field, options=options)

class ManyToOneConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.many2one'
    _inherit = 'ir.qweb.field'

    def record_to_html(self, cr, uid, field_name, record, options=None, context=None):
        [read] = record.read([field_name])
        if not read[field_name]: return ''
        _, value = read[field_name]
        return nl2br(value, options=options)

class HTMLConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.html'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        return HTMLSafe(value or '')

class ImageConverter(osv.AbstractModel):
    """ ``image`` widget rendering, inserts a data:uri-using image tag in the
    document. May be overridden by e.g. the website module to generate links
    instead.

    .. todo:: what happens if different output need different converters? e.g.
              reports may need embedded images or FS links whereas website
              needs website-aware
    """
    _name = 'ir.qweb.field.image'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        try:
            image = Image.open(cStringIO.StringIO(value.decode('base64')))
            image.verify()
        except IOError:
            raise ValueError("Non-image binary fields can not be converted to HTML")
        except: # image.verify() throws "suitable exceptions", I have no idea what they are
            raise ValueError("Invalid image content")

        return HTMLSafe('<img src="data:%s;base64,%s">' % (Image.MIME[image.format], value))

class MonetaryConverter(osv.AbstractModel):
    """ ``monetary`` converter, has a mandatory option
    ``display_currency`` only if field is not of type Monetary.
    Otherwise, if we are in presence of a monetary field, the field definition must
    have a currency_field attribute set.

    The currency is used for formatting *and rounding* of the float value. It
    is assumed that the linked res_currency has a non-empty rounding value and
    res.currency's ``round`` method is used to perform rounding.

    .. note:: the monetary converter internally adds the qweb context to its
              options mapping, so that the context is available to callees.
              It's set under the ``_qweb_context`` key.
    """
    _name = 'ir.qweb.field.monetary'
    _inherit = 'ir.qweb.field'

    def to_html(self, cr, uid, field_name, record, options,
                source_element, t_att, g_att, qweb_context, context=None):
        options['_qweb_context'] = qweb_context
        return super(MonetaryConverter, self).to_html(
            cr, uid, field_name, record, options,
            source_element, t_att, g_att, qweb_context, context=context)

    def record_to_html(self, cr, uid, field_name, record, options, context=None):
        if context is None:
            context = {}
        Currency = self.pool['res.currency']
        cur_field = record._fields[field_name]
        display_currency = False
        #currency should be specified by monetary field
        if cur_field.type == 'monetary' and cur_field.currency_field:
            display_currency = record[cur_field.currency_field]
        #otherwise fall back to old method
        if not display_currency:
            display_currency = self.display_currency(cr, uid, options['display_currency'], options)

        # lang.format mandates a sprintf-style format. These formats are non-
        # minimal (they have a default fixed precision instead), and
        # lang.format will not set one by default. currency.round will not
        # provide one either. So we need to generate a precision value
        # (integer > 0) from the currency's rounding (a float generally < 1.0).
        fmt = "%.{0}f".format(display_currency.decimal_places)

        from_amount = record[field_name]

        if options.get('from_currency'):
            from_currency = self.display_currency(cr, uid, options['from_currency'], options)
            from_amount = Currency.compute(cr, uid, from_currency.id, display_currency.id, from_amount)

        lang_code = context.get('lang') or 'en_US'
        lang = self.pool['res.lang']
        formatted_amount = lang.format(cr, uid, [lang_code],
            fmt, Currency.round(cr, uid, display_currency, from_amount),
            grouping=True, monetary=True)

        pre = post = u''
        if display_currency.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'

        return HTMLSafe(u'{pre}<span class="oe_currency_value">{0}</span>{post}'.format(
            formatted_amount,
            pre=pre, post=post,
        ).format(
            symbol=display_currency.symbol,
        ))

    def display_currency(self, cr, uid, currency, options):
        return self.qweb_object().eval_object(
            currency, options['_qweb_context'])

TIMEDELTA_UNITS = (
    ('year',   3600 * 24 * 365),
    ('month',  3600 * 24 * 30),
    ('week',   3600 * 24 * 7),
    ('day',    3600 * 24),
    ('hour',   3600),
    ('minute', 60),
    ('second', 1)
)
class DurationConverter(osv.AbstractModel):
    """ ``duration`` converter, to display integral or fractional values as
    human-readable time spans (e.g. 1.5 as "1 hour 30 minutes").

    Can be used on any numerical field.

    Has a mandatory option ``unit`` which can be one of ``second``, ``minute``,
    ``hour``, ``day``, ``week`` or ``year``, used to interpret the numerical
    field value before converting it.

    Sub-second values will be ignored.
    """
    _name = 'ir.qweb.field.duration'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        units = dict(TIMEDELTA_UNITS)
        if value < 0:
            raise ValueError(_("Durations can't be negative"))
        if not options or options.get('unit') not in units:
            raise ValueError(_("A unit must be provided to duration widgets"))

        locale = babel.Locale.parse(
            self.user_lang(cr, uid, context=context).code)
        factor = units[options['unit']]

        sections = []
        r = value * factor
        for unit, secs_per_unit in TIMEDELTA_UNITS:
            v, r = divmod(r, secs_per_unit)
            if not v: continue
            section = babel.dates.format_timedelta(
                v*secs_per_unit, threshold=1, locale=locale)
            if section:
                sections.append(section)
        return ' '.join(sections)


class RelativeDatetimeConverter(osv.AbstractModel):
    _name = 'ir.qweb.field.relative'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        parse_format = openerp.tools.DEFAULT_SERVER_DATETIME_FORMAT
        locale = babel.Locale.parse(
            self.user_lang(cr, uid, context=context).code)

        if isinstance(value, basestring):
            value = datetime.datetime.strptime(value, parse_format)

        # value should be a naive datetime in UTC. So is fields.Datetime.now()
        reference = datetime.datetime.strptime(field.now(), parse_format)

        return babel.dates.format_timedelta(
            value - reference, add_direction=True, locale=locale)

class Contact(orm.AbstractModel):
    _name = 'ir.qweb.field.contact'
    _inherit = 'ir.qweb.field.many2one'

    def record_to_html(self, cr, uid, field_name, record, options=None, context=None):
        if context is None:
            context = {}

        if options is None:
            options = {}
        opf = options.get('fields') or ["name", "address", "phone", "mobile", "fax", "email"]

        value_rec = record[field_name]
        if not value_rec:
            return None
        value_rec = value_rec.sudo().with_context(show_address=True)
        value = value_rec.name_get()[0][1]

        val = {
            'name': value.split("\n")[0],
            'address': escape("\n".join(value.split("\n")[1:])).strip(),
            'phone': value_rec.phone,
            'mobile': value_rec.mobile,
            'fax': value_rec.fax,
            'city': value_rec.city,
            'country_id': value_rec.country_id.display_name,
            'website': value_rec.website,
            'email': value_rec.email,
            'fields': opf,
            'object': value_rec,
            'options': options
        }

        html = self.pool["ir.ui.view"].render(cr, uid, "base.contact", val, engine='ir.qweb', context=context).decode('utf8')

        return HTMLSafe(html)

class QwebView(orm.AbstractModel):
    _name = 'ir.qweb.field.qweb'
    _inherit = 'ir.qweb.field.many2one'

    def record_to_html(self, cr, uid, field_name, record, options=None, context=None):
        if not getattr(record, field_name):
            return None

        view = getattr(record, field_name)

        if view._model._name != "ir.ui.view":
            _logger.warning("%s.%s must be a 'ir.ui.view' model." % (record, field_name))
            return None

        ctx = (context or {}).copy()
        ctx['object'] = record
        html = view.render(ctx, engine='ir.qweb', context=ctx).decode('utf8')

        return HTMLSafe(html)

class QwebWidget(osv.AbstractModel):
    _name = 'ir.qweb.widget'

    def _format(self, inner, options, qwebcontext):
        return self.pool['ir.qweb'].eval_str(inner, qwebcontext)

    def format(self, inner, options, qwebcontext):
        return escape(self._format(inner, options, qwebcontext))

class QwebWidgetMonetary(osv.AbstractModel):
    _name = 'ir.qweb.widget.monetary'
    _inherit = 'ir.qweb.widget'

    def _format(self, inner, options, qwebcontext):
        inner = self.pool['ir.qweb'].eval(inner, qwebcontext)
        display = self.pool['ir.qweb'].eval_object(options['display_currency'], qwebcontext)
        precision = int(round(math.log10(display.rounding)))
        fmt = "%.{0}f".format(-precision if precision < 0 else 0)
        lang_code = qwebcontext.context.get('lang') or 'en_US'
        formatted_amount = self.pool['res.lang'].format(
            qwebcontext.cr, qwebcontext.uid, [lang_code], fmt, inner, grouping=True, monetary=True
        )
        pre = post = u''
        if display.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'

        return u'{pre}{0}{post}'.format(
            formatted_amount, pre=pre, post=post
        ).format(symbol=display.symbol,)

class HTMLSafe(object):
    """ HTMLSafe string wrapper, Werkzeug's escape() has special handling for
    objects with a ``__html__`` methods but AFAIK does not provide any such
    object.

    Wrapping a string in HTML will prevent its escaping
    """
    __slots__ = ['string']
    def __init__(self, string):
        self.string = string
    def __html__(self):
        return self.string
    def __str__(self):
        s = self.string
        if isinstance(s, unicode):
            return s.encode('utf-8')
        return s
    def __unicode__(self):
        s = self.string
        if isinstance(s, str):
            return s.decode('utf-8')
        return s

def nl2br(string, options=None):
    """ Converts newlines to HTML linebreaks in ``string``. Automatically
    escapes content unless options['html-escape'] is set to False, and returns
    the result wrapped in an HTMLSafe object.

    :param str string:
    :param dict options:
    :rtype: HTMLSafe
    """
    if options is None: options = {}

    if options.get('html-escape', True):
        string = escape(string)
    return HTMLSafe(string.replace('\n', '<br>\n'))

def get_field_type(field, options):
    """ Gets a t-field's effective type from the field definition and its options """
    return options.get('widget', field.type)

class AssetError(Exception):
    pass
class AssetNotFound(AssetError):
    pass

class AssetsBundle(object):
    rx_css_import = re.compile("(@import[^;{]+;?)", re.M)
    rx_preprocess_imports = re.compile("""(@import\s?['"]([^'"]+)['"](;?))""")
    rx_css_split = re.compile("\/\*\! ([a-f0-9-]+) \*\/")

    def __init__(self, xmlid, debug=False, cr=None, uid=None, context=None, registry=None):
        self.xmlid = xmlid
        self.cr = request.cr if cr is None else cr
        self.uid = request.uid if uid is None else uid
        self.context = request.context if context is None else context
        self.registry = request.registry if registry is None else registry
        self.javascripts = []
        self.stylesheets = []
        self.css_errors = []
        self.remains = []
        self._checksum = None

        context = self.context.copy()
        context['inherit_branding'] = False
        context['rendering_bundle'] = True
        self.html = self.registry['ir.ui.view'].render(self.cr, self.uid, xmlid, context=context)
        self.parse()

    def parse(self):
        fragments = html.fragments_fromstring(self.html)
        for el in fragments:
            if isinstance(el, basestring):
                self.remains.append(el)
            elif isinstance(el, html.HtmlElement):
                src = el.get('src', '')
                href = el.get('href', '')
                atype = el.get('type')
                media = el.get('media')
                if el.tag == 'style':
                    if atype == 'text/sass' or src.endswith('.sass'):
                        self.stylesheets.append(SassStylesheetAsset(self, inline=el.text, media=media))
                    elif atype == 'text/less' or src.endswith('.less'):
                        self.stylesheets.append(LessStylesheetAsset(self, inline=el.text, media=media))
                    else:
                        self.stylesheets.append(StylesheetAsset(self, inline=el.text, media=media))
                elif el.tag == 'link' and el.get('rel') == 'stylesheet' and self.can_aggregate(href):
                    if href.endswith('.sass') or atype == 'text/sass':
                        self.stylesheets.append(SassStylesheetAsset(self, url=href, media=media))
                    elif href.endswith('.less') or atype == 'text/less':
                        self.stylesheets.append(LessStylesheetAsset(self, url=href, media=media))
                    else:
                        self.stylesheets.append(StylesheetAsset(self, url=href, media=media))
                elif el.tag == 'script' and not src:
                    self.javascripts.append(JavascriptAsset(self, inline=el.text))
                elif el.tag == 'script' and self.can_aggregate(src):
                    self.javascripts.append(JavascriptAsset(self, url=src))
                else:
                    self.remains.append(html.tostring(el))
            else:
                try:
                    self.remains.append(html.tostring(el))
                except Exception:
                    # notYETimplementederror
                    raise NotImplementedError

    def can_aggregate(self, url):
        return not urlparse(url).netloc and not url.startswith(('/web/css', '/web/js'))

    def to_html(self, sep=None, css=True, js=True, debug=False, async=False):
        if sep is None:
            sep = '\n            '
        response = []
        if debug:
            if css and self.stylesheets:
                self.preprocess_css()
                if self.css_errors:
                    msg = '\n'.join(self.css_errors)
                    self.stylesheets.append(StylesheetAsset(self, inline=self.css_message(msg)))
                for style in self.stylesheets:
                    response.append(style.to_html())
            if js:
                for jscript in self.javascripts:
                    response.append(jscript.to_html())
        else:
            url_for = self.context.get('url_for', lambda url: url)
            if css and self.stylesheets:
                suffix = ''
                if request:
                    ua = request.httprequest.user_agent
                    if ua.browser == "msie" and int((ua.version or '0').split('.')[0]) < 10:
                        suffix = '.0'
                href = '/web/css%s/%s/%s' % (suffix, self.xmlid, self.version)
                response.append('<link href="%s" rel="stylesheet"/>' % url_for(href))
            if js:
                src = '/web/js/%s/%s' % (self.xmlid, self.version)
                response.append('<script %s type="text/javascript" src="%s"></script>' % (async and 'async="async"' or '', url_for(src)))
        response.extend(self.remains)
        return sep + sep.join(response)

    @func.lazy_property
    def last_modified(self):
        """Returns last modified date of linked files"""
        return max(itertools.chain(
            (asset.last_modified for asset in self.javascripts),
            (asset.last_modified for asset in self.stylesheets),
        ))

    @func.lazy_property
    def version(self):
        return self.checksum[0:7]

    @func.lazy_property
    def checksum(self):
        """
        Not really a full checksum.
        We compute a SHA1 on the rendered bundle + max linked files last_modified date
        """
        check = self.html + str(self.last_modified)
        return hashlib.sha1(check).hexdigest()

    def js(self):
        content = self.get_cache('js')
        if content is None:
            content = ';\n'.join(asset.minify() for asset in self.javascripts)
            self.set_cache('js', content)
        return content

    def css(self, page_number=None):
        """Generate css content from given bundle"""
        if page_number is not None:
            return self.css_page(page_number)

        content = self.get_cache('css')
        if content is None:
            content = self.preprocess_css()

            if self.css_errors:
                msg = '\n'.join(self.css_errors)
                content += self.css_message(msg)

            # move up all @import rules to the top
            matches = []
            def push(matchobj):
                matches.append(matchobj.group(0))
                return ''

            content = re.sub(self.rx_css_import, push, content)

            matches.append(content)
            content = u'\n'.join(matches)
            if not self.css_errors:
                self.set_cache('css', content)
            content = content.encode('utf-8')

        return content

    def css_page(self, page_number):
        content = self.get_cache('css.%d' % (page_number,))
        if page_number:
            return content
        if content is None:
            css = self.css().decode('utf-8')
            re_rules = '([^{]+\{(?:[^{}]|\{[^{}]*\})*\})'
            re_selectors = '()(?:\s*@media\s*[^{]*\{)?(?:\s*(?:[^,{]*(?:,|\{(?:[^}]*\}))))'
            css_url = '@import url(\'/web/css.%%d/%s/%s\');' % (self.xmlid, self.version)
            pages = [[]]
            page = pages[0]
            page_selectors = 0
            for rule in re.findall(re_rules, css):
                selectors = len(re.findall(re_selectors, rule))
                if page_selectors + selectors < MAX_CSS_RULES:
                    page_selectors += selectors
                    page.append(rule)
                else:
                    pages.append([rule])
                    page = pages[-1]
                    page_selectors = selectors
            if len(pages) == 1:
                pages = []
            for idx, page in enumerate(pages):
                self.set_cache("css.%d" % (idx+1), ''.join(page))
            content = '\n'.join(css_url % i for i in range(1,len(pages)+1))
            self.set_cache("css.0", content)
        if not content:
            return self.css()
        return content

    def get_cache(self, type):
        content = None
        domain = [('url', '=', '/web/%s/%s/%s' % (type, self.xmlid, self.version))]
        bundle = self.registry['ir.attachment'].search_read(self.cr, openerp.SUPERUSER_ID, domain, ['datas'], context=self.context)
        if bundle and bundle[0]['datas']:
            content = bundle[0]['datas'].decode('base64')
        return content

    def set_cache(self, type, content):
        ira = self.registry['ir.attachment']
        url = '/web/%s/%s/%s' % (type, self.xmlid, self.version)
        try:
            with self.cr.savepoint():
                ira.invalidate_bundle(self.cr, openerp.SUPERUSER_ID, type=type, xmlid=self.xmlid)
                ira.create(self.cr, openerp.SUPERUSER_ID, dict(
                    datas=content.encode('utf8').encode('base64'),
                    type='binary',
                    name=url,
                    url=url,
                ), context=self.context)
        except psycopg2.Error:
            pass

    def css_message(self, message):
        # '\A' == css content carriage return
        message = message.replace('\n', '\\A ').replace('"', '\\"')
        return """
            body:before {
                background: #ffc;
                width: 100%%;
                font-size: 14px;
                font-family: monospace;
                white-space: pre;
                content: "%s";
            }
        """ % message

    def preprocess_css(self):
        """
            Checks if the bundle contains any sass/less content, then compiles it to css.
            Returns the bundle's flat css.
        """
        for atype in (SassStylesheetAsset, LessStylesheetAsset):
            assets = [asset for asset in self.stylesheets if isinstance(asset, atype)]
            if assets:
                cmd = assets[0].get_command()
                source = '\n'.join([asset.get_source() for asset in assets])
                compiled = self.compile_css(cmd, source)

                fragments = self.rx_css_split.split(compiled)
                at_rules = fragments.pop(0)
                if at_rules:
                    # Sass and less moves @at-rules to the top in order to stay css 2.1 compatible
                    self.stylesheets.insert(0, StylesheetAsset(self, inline=at_rules))
                while fragments:
                    asset_id = fragments.pop(0)
                    asset = next(asset for asset in self.stylesheets if asset.id == asset_id)
                    asset._content = fragments.pop(0)

        return '\n'.join(asset.minify() for asset in self.stylesheets)

    def compile_css(self, cmd, source):
        """Sanitizes @import rules, remove duplicates @import rules, then compile"""
        imports = []
        def sanitize(matchobj):
            ref = matchobj.group(2)
            line = '@import "%s"%s' % (ref, matchobj.group(3))
            if '.' not in ref and line not in imports and not ref.startswith(('.', '/', '~')):
                imports.append(line)
                return line
            msg = "Local import '%s' is forbidden for security reasons." % ref
            _logger.warning(msg)
            self.css_errors.append(msg)
            return ''
        source = re.sub(self.rx_preprocess_imports, sanitize, source)

        try:
            compiler = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        except Exception:
            msg = "Could not execute command %r" % cmd[0]
            _logger.error(msg)
            self.css_errors.append(msg)
            return ''
        result = compiler.communicate(input=source.encode('utf-8'))
        if compiler.returncode:
            error = self.get_preprocessor_error(''.join(result), source=source)
            _logger.warning(error)
            self.css_errors.append(error)
            return ''
        compiled = result[0].strip().decode('utf8')
        return compiled

    def get_preprocessor_error(self, stderr, source=None):
        """Improve and remove sensitive information from sass/less compilator error messages"""
        error = stderr.split('Load paths')[0].replace('  Use --trace for backtrace.', '')
        if 'Cannot load compass' in error:
            error += "Maybe you should install the compass gem using this extra argument:\n\n" \
                     "    $ sudo gem install compass --pre\n"
        error += "This error occured while compiling the bundle '%s' containing:" % self.xmlid
        for asset in self.stylesheets:
            if isinstance(asset, PreprocessedCSS):
                error += '\n    - %s' % (asset.url if asset.url else '<inline sass>')
        return error

class WebAsset(object):
    html_url = '%s'

    def __init__(self, bundle, inline=None, url=None):
        self.id = str(uuid.uuid4())
        self.bundle = bundle
        self.inline = inline
        self.url = url
        self.cr = bundle.cr
        self.uid = bundle.uid
        self.registry = bundle.registry
        self.context = bundle.context
        self._content = None
        self._filename = None
        self._ir_attach = None
        name = '<inline asset>' if inline else url
        self.name = "%s defined in bundle '%s'" % (name, bundle.xmlid)
        if not inline and not url:
            raise Exception("An asset should either be inlined or url linked")

    def stat(self):
        if not (self.inline or self._filename or self._ir_attach):
            addon = filter(None, self.url.split('/'))[0]
            try:
                # Test url against modules static assets
                mpath = openerp.http.addons_manifest[addon]['addons_path']
                self._filename = mpath + self.url.replace('/', os.path.sep)
            except Exception:
                try:
                    # Test url against ir.attachments
                    fields = ['__last_update', 'datas', 'mimetype']
                    domain = [('type', '=', 'binary'), ('url', '=', self.url)]
                    ira = self.registry['ir.attachment']
                    attach = ira.search_read(self.cr, openerp.SUPERUSER_ID, domain, fields, context=self.context)
                    self._ir_attach = attach[0]
                except Exception:
                    raise AssetNotFound("Could not find %s" % self.name)

    def to_html(self):
        raise NotImplementedError()

    @func.lazy_property
    def last_modified(self):
        try:
            self.stat()
            if self._filename:
                return datetime.datetime.fromtimestamp(os.path.getmtime(self._filename))
            elif self._ir_attach:
                server_format = openerp.tools.misc.DEFAULT_SERVER_DATETIME_FORMAT
                last_update = self._ir_attach['__last_update']
                try:
                    return datetime.datetime.strptime(last_update, server_format + '.%f')
                except ValueError:
                    return datetime.datetime.strptime(last_update, server_format)
        except Exception:
            pass
        return datetime.datetime(1970, 1, 1)

    @property
    def content(self):
        if self._content is None:
            self._content = self.inline or self._fetch_content()
        return self._content

    def _fetch_content(self):
        """ Fetch content from file or database"""
        try:
            self.stat()
            if self._filename:
                with open(self._filename, 'rb') as fp:
                    return fp.read().decode('utf-8')
            else:
                return self._ir_attach['datas'].decode('base64')
        except UnicodeDecodeError:
            raise AssetError('%s is not utf-8 encoded.' % self.name)
        except IOError:
            raise AssetNotFound('File %s does not exist.' % self.name)
        except:
            raise AssetError('Could not get content for %s.' % self.name)

    def minify(self):
        return self.content

    def with_header(self, content=None):
        if content is None:
            content = self.content
        return '\n/* %s */\n%s' % (self.name, content)

class JavascriptAsset(WebAsset):
    def minify(self):
        return self.with_header(rjsmin(self.content))

    def _fetch_content(self):
        try:
            return super(JavascriptAsset, self)._fetch_content()
        except AssetError, e:
            return "console.error(%s);" % json.dumps(e.message)

    def to_html(self):
        if self.url:
            return '<script type="text/javascript" src="%s"></script>' % (self.html_url % self.url)
        else:
            return '<script type="text/javascript" charset="utf-8">%s</script>' % self.with_header()

class StylesheetAsset(WebAsset):
    rx_import = re.compile(r"""@import\s+('|")(?!'|"|/|https?://)""", re.U)
    rx_url = re.compile(r"""url\s*\(\s*('|"|)(?!'|"|/|https?://|data:)""", re.U)
    rx_sourceMap = re.compile(r'(/\*# sourceMappingURL=.*)', re.U)
    rx_charset = re.compile(r'(@charset "[^"]+";)', re.U)

    def __init__(self, *args, **kw):
        self.media = kw.pop('media', None)
        super(StylesheetAsset, self).__init__(*args, **kw)

    @property
    def content(self):
        content = super(StylesheetAsset, self).content
        if self.media:
            content = '@media %s { %s }' % (self.media, content)
        return content

    def _fetch_content(self):
        try:
            content = super(StylesheetAsset, self)._fetch_content()
            web_dir = os.path.dirname(self.url)

            if self.rx_import:
                content = self.rx_import.sub(
                    r"""@import \1%s/""" % (web_dir,),
                    content,
                )

            if self.rx_url:
                content = self.rx_url.sub(
                    r"url(\1%s/" % (web_dir,),
                    content,
                )

            if self.rx_charset:
                # remove charset declarations, we only support utf-8
                content = self.rx_charset.sub('', content)

            return content
        except AssetError, e:
            self.bundle.css_errors.append(e.message)
            return ''

    def minify(self):
        # remove existing sourcemaps, make no sense after re-mini
        content = self.rx_sourceMap.sub('', self.content)
        # comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.S)
        # space
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r' *([{}]) *', r'\1', content)
        return self.with_header(content)

    def to_html(self):
        media = (' media="%s"' % werkzeug.utils.escape(self.media)) if self.media else ''
        if self.url:
            href = self.html_url % self.url
            return '<link rel="stylesheet" href="%s" type="text/css"%s/>' % (href, media)
        else:
            return '<style type="text/css"%s>%s</style>' % (media, self.with_header())

class PreprocessedCSS(StylesheetAsset):
    html_url = '%s.css'
    rx_import = None

    def minify(self):
        return self.with_header()

    def to_html(self):
        if self.url:
            try:
                ira = self.registry['ir.attachment']
                url = self.html_url % self.url
                domain = [('type', '=', 'binary'), ('url', '=', url)]
                with self.cr.savepoint():
                    ira_id = ira.search(self.cr, openerp.SUPERUSER_ID, domain, context=self.context)
                    datas = self.content.encode('utf8').encode('base64')
                    if ira_id:
                        # TODO: update only if needed
                        ira.write(self.cr, openerp.SUPERUSER_ID, ira_id, {'datas': datas},
                                  context=self.context)
                    else:
                        ira.create(self.cr, openerp.SUPERUSER_ID, dict(
                            datas=datas,
                            mimetype='text/css',
                            type='binary',
                            name=url,
                            url=url,
                        ), context=self.context)
            except psycopg2.Error:
                pass
        return super(PreprocessedCSS, self).to_html()

    def get_source(self):
        content = self.inline or self._fetch_content()
        return "/*! %s */\n%s" % (self.id, content)

    def get_command(self):
        raise NotImplementedError

class SassStylesheetAsset(PreprocessedCSS):
    rx_indent = re.compile(r'^( +|\t+)', re.M)
    indent = None
    reindent = '    '

    def get_source(self):
        content = textwrap.dedent(self.inline or self._fetch_content())

        def fix_indent(m):
            # Indentation normalization
            ind = m.group()
            if self.indent is None:
                self.indent = ind
                if self.indent == self.reindent:
                    # Don't reindent the file if identation is the final one (reindent)
                    raise StopIteration()
            return ind.replace(self.indent, self.reindent)

        try:
            content = self.rx_indent.sub(fix_indent, content)
        except StopIteration:
            pass
        return "/*! %s */\n%s" % (self.id, content)

    def get_command(self):
        try:
            sass = misc.find_in_path('sass')
        except IOError:
            sass = 'sass'
        return [sass, '--stdin', '-t', 'compressed', '--unix-newlines', '--compass',
                '-r', 'bootstrap-sass']

class LessStylesheetAsset(PreprocessedCSS):
    def get_command(self):
        try:
            if os.name == 'nt':
                lessc = misc.find_in_path('lessc.cmd')
            else:
                lessc = misc.find_in_path('lessc')
        except IOError:
            lessc = 'lessc'
        webpath = openerp.http.addons_manifest['web']['addons_path']
        lesspath = os.path.join(webpath, 'web', 'static', 'lib', 'bootstrap', 'less')
        return [lessc, '-', '--clean-css', '--no-js', '--no-color', '--include-path=%s' % lesspath]

def rjsmin(script):
    """ Minify js with a clever regex.
    Taken from http://opensource.perlig.de/rjsmin
    Apache License, Version 2.0 """
    def subber(match):
        """ Substitution callback """
        groups = match.groups()
        return (
            groups[0] or
            groups[1] or
            groups[2] or
            groups[3] or
            (groups[4] and '\n') or
            (groups[5] and ' ') or
            (groups[6] and ' ') or
            (groups[7] and ' ') or
            ''
        )

    result = re.sub(
        r'([^\047"/\000-\040]+)|((?:(?:\047[^\047\\\r\n]*(?:\\(?:[^\r\n]|\r?'
        r'\n|\r)[^\047\\\r\n]*)*\047)|(?:"[^"\\\r\n]*(?:\\(?:[^\r\n]|\r?\n|'
        r'\r)[^"\\\r\n]*)*"))[^\047"/\000-\040]*)|(?:(?<=[(,=:\[!&|?{};\r\n]'
        r')(?:[\000-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/'
        r'))*((?:/(?![\r\n/*])[^/\\\[\r\n]*(?:(?:\\[^\r\n]|(?:\[[^\\\]\r\n]*'
        r'(?:\\[^\r\n][^\\\]\r\n]*)*\]))[^/\\\[\r\n]*)*/)[^\047"/\000-\040]*'
        r'))|(?:(?<=[\000-#%-,./:-@\[-^`{-~-]return)(?:[\000-\011\013\014\01'
        r'6-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))*((?:/(?![\r\n/*])[^/'
        r'\\\[\r\n]*(?:(?:\\[^\r\n]|(?:\[[^\\\]\r\n]*(?:\\[^\r\n][^\\\]\r\n]'
        r'*)*\]))[^/\\\[\r\n]*)*/)[^\047"/\000-\040]*))|(?<=[^\000-!#%&(*,./'
        r':-@\[\\^`{|~])(?:[\000-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/'
        r'*][^*]*\*+)*/))*(?:((?:(?://[^\r\n]*)?[\r\n]))(?:[\000-\011\013\01'
        r'4\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))*)+(?=[^\000-\040"#'
        r'%-\047)*,./:-@\\-^`|-~])|(?<=[^\000-#%-,./:-@\[-^`{-~-])((?:[\000-'
        r'\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)))+(?=[^'
        r'\000-#%-,./:-@\[-^`{-~-])|(?<=\+)((?:[\000-\011\013\014\016-\040]|'
        r'(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)))+(?=\+)|(?<=-)((?:[\000-\011\0'
        r'13\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)))+(?=-)|(?:[\0'
        r'00-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))+|(?:'
        r'(?:(?://[^\r\n]*)?[\r\n])(?:[\000-\011\013\014\016-\040]|(?:/\*[^*'
        r']*\*+(?:[^/*][^*]*\*+)*/))*)+', subber, '\n%s\n' % script
    ).strip()
    return result

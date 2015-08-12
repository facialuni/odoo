# -*- coding: utf-8 -*-
"""
Functions and helpers for AST generation from QWeb XML data
"""
import ast
import re
import __builtin__
import itertools

from openerp.tools import safe_eval

_FORMAT_REGEX = re.compile(
    '(?:'
        # ruby-style pattern
        '#\{(.+?)\}'
    ')|(?:'
        # jinja-style pattern
        '\{\{(.+?)\}\}'
    ')')

def base_module():
    """ module base supporting qweb template functions (provides basic
    imports and utilities)

    Currently provides:
    * collections
    * itertools
    * openerp.tools.html_escape as escape
    * unicodifier (empty string for a None or False, otherwise unicode string)
    """

    return ast.parse("""import collections
import itertools

from openerp.tools import html_escape as escape

def unicodifier(val):
    if val is None or val is False:
        return u''
    if isinstance(val, str):
        return val.decode('utf-8')
    return unicode(val)

def foreach_iterator(base_ctx, enum, name):
    ctx = base_ctx.copy()

    if isinstance(enum, int):
        enum = xrange(enum)

    size = None
    if isinstance(enum, collections.Sized):
        ctx["%s_size" % name] = size = len(enum)

    if isinstance(enum, collections.Mapping):
        enum = enum.iteritems()
    else:
        enum = itertools.izip(*itertools.tee(enum))

    value_key = '%s_value' % name
    index_key = '%s_index' % name
    first_key = '%s_first' % name
    last_key = '%s_last' % name
    parity_key = '%s_parity' % name
    even_key = '%s_even' % name
    odd_key = '%s_odd' % name
    for index, (item, value) in enumerate(enum):
        ctx[name] = item
        ctx[value_key] = value
        ctx[index_key] = index
        ctx[first_key] = index == 0
        if size is not None:
            ctx[last_key] = index + 1 == size
        if index % 2:
            ctx[parity_key] = 'odd'
            ctx[even_key] = False
            ctx[odd_key] = True
        else:
            ctx[parity_key] = 'even'
            ctx[even_key] = True
            ctx[odd_key] = False
        yield ctx

    # copy changed items back into source context (?)
    # FIXME: maybe QWebContext could provide a ChainMap-style clone?
    for k in base_ctx.keys():
        base_ctx[k] = ctx[k]
""")

def base_fn_def(body, name='fn', lineno=None):
    """ Generates a "qweb function" definition:

    * takes a single ``qwebcontext`` parameter
    * defines a local ``output`` list
    * returns ``u''.join(output)``

    The provided body should be a list of ast nodes, they will be injected
    between the initialization of ``body`` and its concatenation
    """
    fn = ast.FunctionDef(
        name=name,
        args=ast.arguments(args=[
            ast.Name('self', ast.Param()),
            ast.Name('qwebcontext', ast.Param())
        ], defaults=[], vararg=None, kwarg=None),
        body=[ast.Assign([ast.Name(id='output', ctx=ast.Store())],
                         ast.List(elts=[], ctx=ast.Load()))]
            + body
            + [ast.Return(ast.Name(id='output', ctx=ast.Load()))],
        decorator_list=[])
    if lineno is not None:
        fn.lineno = lineno
    return fn

def append(item, to='output'):
    assert isinstance(item, ast.expr)
    return ast.Expr(ast.Call(
        func=ast.Attribute(
            value=ast.Name(id=to, ctx=ast.Load()),
            attr='append',
            ctx=ast.Load()
        ), args=[item], keywords=[],
        starargs=None, kwargs=None
    ))
def extend(items, to='output'):
    return ast.Expr(ast.Call(
        func=ast.Attribute(
            value=ast.Name(id=to, ctx=ast.Load()),
            attr='extend',
            ctx=ast.Load()
        ), args=[items], keywords=[],
        starargs=None, kwargs=None
    ))


class Contextifier(ast.NodeTransformer):
    """ For user-provided template expressions, replaces any ``name`` by
    :sampe:`qwebcontext.eval_dict['{name}']` so all variable accesses are
    performed on the qwebcontext rather than in the "native" scope
    """

    # some people apparently put lambdas in template expressions. Turns out
    # the AST -> bytecode compiler does *not* appreciate parameters of lambdas
    # being converted from names to subscript expressions, and most likely the
    # reference to those parameters inside the lambda's body should probably
    # remain as-is. Because we're transforming an AST, the structure should
    # be lexical, so just store a set of "safe" parameter names and recurse
    # through the lambda using a new NodeTransformer
    def __init__(self, params=()):
        super(Contextifier, self).__init__()
        self._safe_names = tuple(params)

    def visit_Name(self, node):
        if node.id in self._safe_names:
            return node

        eval_ctx = ast.Attribute(
            value=ast.Name(id='qwebcontext', ctx=ast.Load()),
            attr='eval_dict',
            ctx=ast.Load()
        )
        return ast.copy_location(
            ast.Subscript(
                value=eval_ctx,
                slice=ast.Index(ast.Str(node.id)),
                ctx=ast.Load()),
            node
        )

    def visit_Lambda(self, node):
        args = node.args
        # assume we don't have any tuple parameter, just names
        names = [arg.id for arg in args.args]
        if args.vararg: names.append(args.vararg)
        if args.kwarg: names.append(args.kwarg)
        # remap defaults in case there's any
        return ast.copy_location(ast.Lambda(
            args=ast.arguments(
                args=args.args,
                defaults=map(self.visit, args.defaults),
                vararg=args.vararg,
                kwarg=args.kwarg,
            ),
            body=Contextifier(self._safe_names + tuple(names)).visit(node.body)
        ), node)

    # "lambda problem" also exists with comprehensions
    def _visit_comp(self, node):
        # CompExp(?, comprehension* generators)
        # comprehension = (expr target, expr iter, expr* ifs)

        # collect names in generators.target
        names = tuple(
            node.id
            for gen in node.generators
            for node in ast.walk(gen.target)
            if isinstance(node, ast.Name)
        )
        transformer = Contextifier(self._safe_names + names)
        # copy node
        newnode = ast.copy_location(type(node)(), node)
        # then visit the comp ignoring those names, transformation is
        # probably expensive but shouldn't be many comprehensions
        for field, value in ast.iter_fields(node):
            # map transformation of comprehensions
            if isinstance(value, list):
                setattr(newnode, field, map(transformer.visit, value))
            else: # set transformation of key/value/expr fields
                setattr(newnode, field, transformer.visit(value))
        return newnode
    visit_GeneratorExp = visit_ListComp = visit_SetComp = visit_DictComp = _visit_comp

def compile_strexpr(expr):
    if expr == "0":
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='qwebcontext', ctx=ast.Load()),
                attr='get',
                ctx=ast.Load()
            ),
            args=[ast.Num(0), ast.Str('')], keywords=[],
            starargs=None, kwargs=None
        )

    # ensure result is unicode
    return ast.Call(
        func=ast.Name(id='unicodifier', ctx=ast.Load()),
        args=[compile_expr(expr)], keywords=[],
        starargs=None, kwargs=None
    )

def compile_expr(expr):
    """ Compiles a purported Python expression to ast, verifies that it's safe
    (according to safe_eval's semantics) and alter its variable references to
    access qwebcontext data instead
    """
    # string must be stripped otherwise whitespace before the start for
    # formatting purpose are going to break parse/compile
    st = ast.parse(expr.strip(), mode='eval')
    safe_eval.assert_valid_codeobj(
        safe_eval._SAFE_OPCODES,
        compile(st, '<>', 'eval'), # could be expr, but eval *should* be fine
        expr
    )

    # ast.Expression().body -> expr
    return Contextifier().visit(st).body

def compile_format(f):
    """ Parses the provided format string and compiles it to a single
    expression ast, uses string concatenation via "+"
    """
    elts = []
    base_idx = 0
    for m in _FORMAT_REGEX.finditer(f):
        literal = f[base_idx:m.start()]
        if literal:
            elts.append(ast.Str(literal if isinstance(literal, unicode) else literal.decode('utf-8')))

        expr = m.group(1) or m.group(2)
        elts.append(compile_strexpr(expr))
        base_idx = m.end()
    # string past last regex match
    literal = f[base_idx:]
    if literal:
        elts.append(ast.Str(literal if isinstance(literal, unicode) else literal.decode('utf-8')))

    return reduce(lambda acc, it: ast.BinOp(
        left=acc,
        op=ast.Add(),
        right=it
    ), elts)

class CompileContext(object):
    def __init__(self):
        self._name_gen = itertools.count()
        self._functions = []
        self._nodes = []

    def call_body(self, body, args=('self', 'qwebcontext',), prefix='fn', lineno=None):
        """
        If ``body`` is non-empty, generates (and globally store) the
        corresponding function definition and returns the relevant ast.Call
        node.

        If ``body`` is empty, doesn't do anything and returns ``None``.
        """
        if not body:
            return None
        name = "%s_%s" % (prefix, next(self._name_gen))
        self._functions.append(base_fn_def(body, name=name, lineno=lineno))
        return ast.Call(
            func=ast.Name(id=name, ctx=ast.Load()),
            args=[ast.Name(id=arg, ctx=ast.Load()) for arg in args],
            keywords=[], starargs=None, kwargs=None
        )

    def store_node(self, node):
        """ Memoizes an elementtree node for use at runtime. The node will be
        available via a module-global ``nodes`` list

        :param etree._Element node:
        :returns: AST expression fetching the relevant node
        :rtype: ast.expr
        """
        idx = len(self._nodes)
        self._nodes.append(node)
        return ast.Subscript(
            value=ast.Name(id='nodes', ctx=ast.Load()),
            slice=ast.Index(ast.Num(idx)),
            ctx=ast.Load()
        )

def pp(node):
    PrettyPrinter().visit(node)

def pformat(node):
    s = []
    PrettyPrinter(s.append).visit(node)
    return ''.join(s)

import sys
class PrettyPrinter(ast.NodeVisitor):
    def __init__(self, p=sys.stdout.write):
        """
        :type p: (x: str) -> None
        """
        super(PrettyPrinter, self).__init__()
        self.level = 0
        self.p = p

    def _indent(self):
        self.p('    '*self.level)

    def visit_params(self, params, intersperse=', ', prev=False):
        for expr in params:
            if prev: self.p(intersperse)
            prev = True
            self.visit(expr)

    def visit_body(self, body):
        self.level += 1
        for stmt in body:
            self.visit(stmt)
        self.level -= 1

    def visit_Module(self, node):
        for stmt in node.body:
            self.visit(stmt)

    ## statements
    def visit_Import(self, node):
        # Import(alias* names)
        self._indent()
        self.p('import ')
        self.visit_params(node.names)
        self.p('\n')

    def visit_ImportFrom(self, node):
        # ImportFrom(identifier? module, alias* names, int? level)
        self._indent()
        self.p('from ')
        self.p('.'*(node.level or 0))
        self.p(node.module)
        self.p(' import ')
        self.visit_params(node.names)
        self.p('\n')

    def visit_FunctionDef(self, node):
        # FunctionDef(identifier name, arguments args, stmt* body, expr* decorator_list)
        self._indent()
        self.p("def {}(".format(node.name))
        self.visit(node.args)
        self.p('):\n')
        self.visit_body(node.body)
        self.p('\n')

    def visit_Return(self, node):
        # Return(expr? value)
        self._indent()
        self.p('return ')
        if node.value:
            self.visit(node.value)
        self.p('\n')

    def visit_Assign(self, node):
        # Assign(expr* targets, expr value)
        self._indent()
        self.visit_params(node.targets)
        self.p(' = ')
        self.visit(node.value)
        self.p('\n')

    def visit_If(self, node):
        # If(expr test, stmt* body, stmt* orelse)
        self._indent()
        self.p('if ')
        self.visit(node.test)
        self.p(':\n')
        self.visit_body(node.body)
        if node.orelse:
            self._indent()
            self.p('else:\n')
            self.visit_body(node.orelse)
        self.p('\n')

    def visit_For(self, node):
        # For(expr target, expr iter, stmt* body, stmt* orelse)
        self._indent()
        self.p('for ')
        self.visit(node.target)
        self.p(' in ')
        self.visit(node.iter)
        self.p(':\n')
        self.visit_body(node.body)
        if node.orelse:
            self._indent()
            self.p('else:\n')
            self.visit_body(node.orelse)
        self.p('\n')

    def visit_Expr(self, node):
        # Expr(expr value)
        self._indent()
        self.visit(node.value)
        self.p('\n')

    # expressions
    def visit_BinOp(self, node):
        # BinOp(expr left, operator op, expr right)
        self.visit(node.left)
        try:
            self.p(_operator[type(node.op)])
        except KeyError:
            raise Exception("Unknown operator %s" % node.op)
        self.visit(node.right)
    def visit_BoolOp(self, node):
        # BoolOp(boolop op, expr* values)
        self.p('(')
        self.visit_params(
            node.values,
            intersperse=' and ' if isinstance(node.op, ast.And) else ' or ')
        self.p(')')
    def visit_Compare(self, node):
        # Compare(expr left, cmpop* ops, expr* comparators)
        self.visit(node.left)
        for op, cmp in zip(node.ops, node.comparators):
            try:
                self.p(_cmpop[type(op)])
            except KeyError:
                raise Exception("Unknown comparison operator %s" % op)
            self.visit(cmp)
    def visit_UnaryOp(self, node):
        # UnaryOp(unaryop op, expr operand)
        assert isinstance(node.op, ast.Not), "unknown unary operator %s" % node.op
        self.p('not ')
        self.visit(node.operand)
    def visit_Call(self, node):
        # Call(expr func, expr* args, keyword* keywords, expr? starargs, expr? kwargs)
        self.visit(node.func)
        self.p('(')
        prev = bool(node.args)
        self.visit_params(node.args)
        if node.keywords:
            self.visit_params(node.keywords, prev=prev)
            prev = True
        if node.starargs:
            if prev: self.p(', ')
            self.visit(node.starargs)
            prev = True
        if node.kwargs:
            if prev: self.p(', ')
            self.visit(node.kwargs)
        self.p(')')
    def visit_Attribute(self, node):
        # Attribute(expr value, identifier attr, expr_context ctx)
        self.visit(node.value)
        self.p('.')
        self.p(node.attr)
    def visit_Subscript(self, node):
        # Subscript(expr value, slice slice, expr_context ctx)
        self.visit(node.value)
        self.p('[')
        self.visit(node.slice)
        self.p(']')
    def visit_Name(self, node):
        # Name(identifier id, expr_context ctx)
        self.p(node.id)
    def visit_Index(self, node):
        # Index(expr value)
        self.visit(node.value)
    def visit_GeneratorExp(self, node):
        # GeneratorExp(expr elt, comprehension* generators)
        # comprehension = (expr target, expr iter, expr* ifs)
        self.p('(')
        self.visit(node.elt)
        self.p(' ')
        self._visit_comprehension(node.generators)
        self.p(')')
    def visit_ListComp(self, node):
        # ListComp(expr elt, comprehension* generators)
        self.p('[')
        self.visit(node.elt)
        self.p(' ')
        self._visit_comprehension(node.generators)
        self.p(']')
    def visit_SetComp(self, node):
        # SetComp(expr elt, comprehension* generators)
        self.p('{')
        self.visit(node.elt)
        self.p(' ')
        self._visit_comprehension(node.generators)
        self.p('}')
    def visit_DictComp(self, node):
        # DictComp(expr key, expr value, comprehension* generators)
        self.p('{')
        self.visit(node.key)
        self.p(': ')
        self.visit(node.value)
        self.p(' ')
        self._visit_comprehension(node.generators)
        self.p('}')
    def _visit_comprehension(self, generators):
        for g in generators:
            self.p('for ')
            self.visit(g.target)
            self.p(' in ')
            self.visit(g.iter)
            self.p(' ')
            for test in g.ifs:
                self.p('if ')
                self.visit(test)
                self.p(' ')

    def visit_IfExp(self, node):
        # IfExp(expr test, expr body, expr orelse)
        self.visit(node.body)
        self.p(' if ')
        self.visit(node.test)
        self.p(' else ')
        self.visit(node.orelse)
    def visit_Slice(self, node):
        # Slice(expr? lower, expr? upper, expr? step)
        if node.lower:
            self.visit(node.lower)
        self.p(':')
        if node.upper:
            self.visit(node.upper)
        self.p(':')
        if node.step:
            self.visit(node.step)
    def visit_Yield(self, node):
        # Yield(expr? value)
        self.p('yield ')
        if node.value:
            self.visit(node.value)

    # literals
    def visit_Lambda(self, node):
        # Lambda(arguments args, expr body)
        self.p('lambda ')
        self.visit(node.args)
        self.p(': ')
        self.visit(node.body)
    def visit_List(self, node):
        # List(expr* elts, expr_context ctx)
        self.p('[')
        self.visit_params(node.elts)
        self.p(']')
    def visit_Tuple(self, node):
        # Tuple(expr* elts, expr_context ctx)
        self.p('(')
        self.visit_params(node.elts)
        self.p(')')
    def visit_Dict(self, node):
        # Dict(expr* keys, expr* values)
        prev = False
        self.p('{')
        for k, v in itertools.izip(node.keys, node.values):
            if prev: self.p(', ')
            prev = True
            self.visit(k)
            self.p(': ')
            self.visit(v)
        self.p('}')
    def visit_Str(self, node):
        self.p(repr(node.s))
    def visit_Num(self, node):
        self.p(repr(node.n))

    def visit_keyword(self, node):
        self.p(node.arg)
        self.p('=')
        self.visit(node.value)

    def visit_alias(self, node):
        self.p(node.name)
        if node.asname:
            self.p(' as ')
            self.p(node.asname)

    def visit_arguments(self, node):
        # arguments = (expr* args, identifier? vararg, identifier? kwarg, expr* defaults)
        nodefaults_count = len(node.args) - len(node.defaults)
        prev = bool(nodefaults_count)
        self.visit_params(node.args[:nodefaults_count])
        for (arg, default) in zip(node.args[nodefaults_count:], node.defaults):
            if prev: self.p(',')
            prev = True
            self.visit(arg)
            self.p('=')
            self.visit(default)
        if node.vararg:
            if prev: self.p(', ')
            self.p('*')
            self.p(node.vararg)
            prev = True
        if node.kwarg:
            if prev: self.p(', ')
            self.p('**')
            self.p(node.kwarg)

    def visit_int(self, node):
        self.p("[[INT {}]]".format(node))
    def visit_str(self, node):
        self.p("[[STR {}]]".format(node))

    def generic_visit(self, node):
        raise Exception("Unhandled node type %s (%s)" % (type(node), node))

_operator = {
    ast.Add: ' + ',
    ast.Sub: ' - ',
    ast.Mult: ' * ',
    ast.Div: ' / ',
    ast.Mod: ' % ',
    ast.Pow: ' ** ',
    ast.LShift: ' << ',
    ast.RShift: ' >> ',
    ast.BitOr: ' | ',
    ast.BitXor: ' ^ ',
    ast.BitAnd: ' & ',
    ast.FloorDiv: ' // ',
}
_cmpop = {
    ast.Eq: ' == ',
    ast.NotEq: ' != ',
    ast.Lt: ' < ',
    ast.LtE: ' <= ',
    ast.Gt: ' > ',
    ast.GtE: ' >= ',
    ast.Is: ' is ',
    ast.IsNot: ' is not ',
    ast.In: ' in ',
    ast.NotIn: ' not in ',
}

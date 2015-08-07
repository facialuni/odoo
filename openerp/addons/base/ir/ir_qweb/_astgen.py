# -*- coding: utf-8 -*-
"""
Functions and helpers for AST generation from QWeb XML data
"""
import ast
import re
import __builtin__

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

def base_fn_def(body, name='fn'):
    """ Generates a "qweb function" definition:

    * takes a single ``qwebcontext`` parameter
    * defines a local ``output`` list
    * returns ``u''.join(output)``

    The provided body should be a list of ast nodes, they will be injected
    between the initialization of ``body`` and its concatenation
    """
    return ast.FunctionDef(
        name=name,
        args=ast.arguments(args=[ast.Name('qwebcontext', ast.Param())], defaults=[]),
        body=[ast.Assign([ast.Name(id='output', ctx=ast.Store())],
                         ast.List(elts=[], ctx=ast.Load()))]
            + body
            + [ast.Return(ast.Name(id='output', ctx=ast.Load()))],
        decorator_list=[])

def append(item, to='output'):
    assert isinstance(item, ast.expr)
    return ast.Expr(ast.Call(
        func=ast.Attribute(
            value=ast.Name(id=to, ctx=ast.Load()),
            attr='append',
            ctx=ast.Load()
        ), args=[item], keywords=[]
    ))
def extend(items, to='output'):
    return ast.Expr(ast.Call(
        func=ast.Attribute(
            value=ast.Name(id=to, ctx=ast.Load()),
            attr='extend',
            ctx=ast.Load()
        ), args=[items], keywords=[]
    ))


class Contextifier(ast.NodeTransformer):
    """ For user-provided template expressions, replaces any ``name`` by
    :sampe:`qwebcontext.eval_dict['{name}']` so all variable accesses are
    performed on the qwebcontext rather than in the "native" scope
    """
    def visit_Name(self, node):
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

def compile_strexpr(expr):
    if expr == "0":
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='qwebcontext', ctx=ast.Load()),
                attr='get',
                ctx=ast.Load()
            ),
            args=[ast.Num(0), ast.Str('')], keywords=[]
        )

    # ensure result is unicode
    return ast.Call(
        func=ast.Name(id='unicodifier', ctx=ast.Load()),
        args=[compile_expr(expr)], keywords=[]
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
        self.to_compile = set()
    def register_template(self, name):
        self.to_compile.add(name)

def pp(node):
    PrettyPrinter().visit(node)

import sys
p = sys.stdout.write
class PrettyPrinter(ast.NodeVisitor):
    def __init__(self):
        super(PrettyPrinter, self).__init__()
        self.level = 0

    def _indent(self):
        sys.stdout.write('    '*self.level)

    def visit_params(self, params, intersperse=', '):
        for expr in params:
            self.visit(expr)
            if expr != params[-1]:
                p(intersperse)

    def visit_body(self, body):
        self.level += 1
        for stmt in body:
            self.visit(stmt)
        self.level -= 1

    ## statements
    def visit_FunctionDef(self, node):
        # FunctionDef(identifier name, arguments args, stmt* body, expr* decorator_list)
        self._indent()
        p("def {}(".format(node.name))
        self.visit_params(node.args.args)
        p('):\n')
        self.visit_body(node.body)
        p('\n')

    def visit_Return(self, node):
        # Return(expr? value)
        self._indent()
        p('return ')
        if node.value:
            self.visit(node.value)
        p('\n')

    def visit_Assign(self, node):
        # Assign(expr* targets, expr value)
        self._indent()
        self.visit_params(node.targets)
        p(' = ')
        self.visit(node.value)
        p('\n')

    def visit_If(self, node):
        # If(expr test, stmt* body, stmt* orelse)
        self._indent()
        p('if ')
        self.visit(node.test)
        p(':\n')
        self.visit_body(node.body)
        if node.orelse:
            p('else:\n')
            self.visit_body(node.orelse)
        p('\n')

    def visit_Expr(self, node):
        # Expr(expr value)
        self._indent()
        self.visit(node.value)
        p('\n')

    # expressions
    def visit_BinOp(self, node):
        # BinOp(expr left, operator op, expr right)
        self.visit(node.left)
        try:
            p(_operator[type(node.op)])
        except KeyError:
            raise Exception("Unknown operator %s" % node.op)
        self.visit(node.right)
    def visit_BoolOp(self, node):
        # BoolOp(boolop op, expr* values)
        p('(')
        self.visit_params(
            node.values,
            intersperse=' and ' if isinstance(node.op, ast.And) else ' or ')
        p(')')
    def visit_Compare(self, node):
        # Compare(expr left, cmpop* ops, expr* comparators)
        self.visit(node.left)
        for op, cmp in zip(node.ops, node.comparators):
            try:
                p(_cmpop[type(op)])
            except KeyError:
                raise Exception("Unknown comparison operator %s" % op)
            self.visit(cmp)
    def visit_UnaryOp(self, node):
        # UnaryOp(unaryop op, expr operand)
        assert isinstance(node.op, ast.Not), "unknown unary operator %s" % node.op
        p('not ')
        self.visit(node.operand)
    def visit_Call(self, node):
        # Call(expr func, expr* args, keyword* keywords, expr? starargs, expr? kwargs)
        self.visit(node.func)
        p('(')
        self.visit_params(node.args)
        if node.keywords:
            p(', ')
            self.visit_params(node.keywords)
        p(')')
    def visit_Attribute(self, node):
        # Attribute(expr value, identifier attr, expr_context ctx)
        self.visit(node.value)
        p('.')
        p(node.attr)
    def visit_Subscript(self, node):
        # Subscript(expr value, slice slice, expr_context ctx)
        self.visit(node.value)
        p('[')
        self.visit(node.slice)
        p(']')
    def visit_Name(self, node):
        # Name(identifier id, expr_context ctx)
        p(node.id)
    def visit_Index(self, node):
        # Index(expr value)
        self.visit(node.value)
    def visit_GeneratorExp(self, node):
        # GeneratorExp(expr elt, comprehension* generators)
        # comprehension = (expr target, expr iter, expr* ifs)
        p('(')
        self.visit(node.elt)
        p(' ')
        for g in node.generators:
            p('for ')
            self.visit(g.target)
            p(' in ')
            self.visit(g.iter)
            p(' ')
            for test in g.ifs:
                p('if ')
                self.visit(test)
                p(' ')
        p(')')
    def visit_IfExp(self, node):
        # IfExp(expr test, expr body, expr orelse)
        self.visit(node.body)
        p(' if ')
        self.visit(node.test)
        p(' else ')
        self.visit(node.orelse)
    def visit_Slice(self, node):
        # Slice(expr? lower, expr? upper, expr? step)
        if node.lower:
            self.visit(node.lower)
        p(':')
        if node.upper:
            self.visit(node.upper)
        p(':')
        if node.step:
            self.visit(node.step)

    # literals
    def visit_List(self, node):
        # List(expr* elts, expr_context ctx)
        p('[')
        self.visit_params(node.elts)
        p(']')
    def visit_Tuple(self, node):
        # Tuple(expr* elts, expr_context ctx)
        p('(')
        self.visit_params(node.elts)
        p(')')
    def visit_Str(self, node):
        p(repr(node.s))
    def visit_Num(self, node):
        p(repr(node.n))

    def visit_keyword(self, node):
        p(node.arg)
        p('=')
        self.visit(node.value)

    def visit_int(self, node):
        p("[[INT {}]]".format(node))
    def visit_str(self, node):
        p("[[STR {}]]".format(node))

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

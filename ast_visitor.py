from abc import abstractmethod, ABCMeta

from pycparser import c_ast as a
from utils import flatten

import logging


class AstVisitor(object):
    __metaclass__ = ABCMeta

    def __init__(self):
        self.methods = {
            a.ArrayDecl: self.visit_ArrayDecl,
            a.ArrayRef: self.visit_ArrayRef,
            a.Assignment: self.visit_Assignment,
            a.BinaryOp: self.visit_BinaryOp,
            a.Break: self.visit_Break,
            a.Case: self.visit_Case,
            a.Cast: self.visit_Cast,
            a.Compound: self.visit_Compound,
            a.CompoundLiteral: self.visit_CompoundLiteral,
            a.Constant: self.visit_Constant,
            a.Continue: self.visit_Continue,
            a.Decl: self.visit_Decl,
            a.DeclList: self.visit_DeclList,
            a.Default: self.visit_Default,
            a.DoWhile: self.visit_DoWhile,
            a.EllipsisParam: self.visit_EllipsisParam,
            a.EmptyStatement: self.visit_EmptyStatement,
            a.Enum: self.visit_Enum,
            a.Enumerator: self.visit_Enumerator,
            a.EnumeratorList: self.visit_EnumeratorList,
            a.ExprList: self.visit_ExprList,
            a.FileAST: self.visit_FileAST,
            a.For: self.visit_For,
            a.FuncCall: self.visit_FuncCall,
            a.FuncDecl: self.visit_FuncDecl,
            a.FuncDef: self.visit_FuncDef,
            a.Goto: self.visit_Goto,
            a.ID: self.visit_ID,
            a.IdentifierType: self.visit_IdentifierType,
            a.If: self.visit_If,
            a.InitList: self.visit_InitList,
            a.Label: self.visit_Label,
            a.NamedInitializer: self.visit_NamedInitializer,
            a.ParamList: self.visit_ParamList,
            a.PtrDecl: self.visit_PtrDecl,
            a.Return: self.visit_Return,
            a.Struct: self.visit_Struct,
            a.StructRef: self.visit_StructRef,
            a.Switch: self.visit_Switch,
            a.TernaryOp: self.visit_TernaryOp,
            a.TypeDecl: self.visit_TypeDecl,
            a.Typedef: self.visit_Typedef,
            a.Typename: self.visit_Typename,
            a.UnaryOp: self.visit_UnaryOp,
            a.Union: self.visit_Union,
            a.While: self.visit_While,
            a.Pragma: self.visit_Pragma
        }

    def visit(self, item):
        return self.methods[type(item)](item)

    @abstractmethod
    def visit_ArrayDecl(self, item):
        pass

    @abstractmethod
    def visit_ArrayRef(self, item):
        pass

    @abstractmethod
    def visit_Assignment(self, item):
        pass

    @abstractmethod
    def visit_BinaryOp(self, item):
        pass

    @abstractmethod
    def visit_Break(self, item):
        pass

    @abstractmethod
    def visit_Case(self, item):
        pass

    @abstractmethod
    def visit_Cast(self, item):
        pass

    @abstractmethod
    def visit_Compound(self, item):
        pass

    @abstractmethod
    def visit_CompoundLiteral(self, item):
        pass

    @abstractmethod
    def visit_Constant(self, item):
        pass

    @abstractmethod
    def visit_Continue(self, item):
        pass

    @abstractmethod
    def visit_Decl(self, item):
        pass

    @abstractmethod
    def visit_DeclList(self, item):
        pass

    @abstractmethod
    def visit_Default(self, item):
        pass

    @abstractmethod
    def visit_DoWhile(self, item):
        pass

    @abstractmethod
    def visit_EllipsisParam(self, item):
        pass

    @abstractmethod
    def visit_EmptyStatement(self, item):
        pass

    @abstractmethod
    def visit_Enum(self, item):
        pass

    @abstractmethod
    def visit_Enumerator(self, item):
        pass

    @abstractmethod
    def visit_EnumeratorList(self, item):
        pass

    @abstractmethod
    def visit_ExprList(self, item):
        pass

    @abstractmethod
    def visit_FileAST(self, item):
        pass

    @abstractmethod
    def visit_For(self, item):
        pass

    @abstractmethod
    def visit_FuncCall(self, item):
        pass

    @abstractmethod
    def visit_FuncDecl(self, item):
        pass

    @abstractmethod
    def visit_FuncDef(self, item):
        pass

    @abstractmethod
    def visit_Goto(self, item):
        pass

    @abstractmethod
    def visit_ID(self, item):
        pass

    @abstractmethod
    def visit_IdentifierType(self, item):
        pass

    @abstractmethod
    def visit_If(self, item):
        pass

    @abstractmethod
    def visit_InitList(self, item):
        pass

    @abstractmethod
    def visit_Label(self, item):
        pass

    @abstractmethod
    def visit_NamedInitializer(self, item):
        pass

    @abstractmethod
    def visit_ParamList(self, item):
        pass

    @abstractmethod
    def visit_PtrDecl(self, item):
        pass

    @abstractmethod
    def visit_Return(self, item):
        pass

    @abstractmethod
    def visit_Struct(self, item):
        pass

    @abstractmethod
    def visit_StructRef(self, item):
        pass

    @abstractmethod
    def visit_Switch(self, item):
        pass

    @abstractmethod
    def visit_TernaryOp(self, item):
        pass

    @abstractmethod
    def visit_TypeDecl(self, item):
        pass

    @abstractmethod
    def visit_Typedef(self, item):
        pass

    @abstractmethod
    def visit_Typename(self, item):
        pass

    @abstractmethod
    def visit_UnaryOp(self, item):
        pass

    @abstractmethod
    def visit_Union(self, item):
        pass

    @abstractmethod
    def visit_While(self, item):
        pass

    @abstractmethod
    def visit_Pragma(self, item):
        pass


class DfsVisitor(AstVisitor):

    def visit_default(self, item):
        return list()

    def visit(self, item):
        if item is None:
            return self.visit_default(item)
        else:
            return super().visit(item)

    def visit_ArrayDecl(self, item):
        a = self.visit(item.type)
        b = self.visit(item.dim)
        return a + b

    def visit_ArrayRef(self, item):
        a = self.visit(item.name)
        b = self.visit(item.subscript)
        return a + b

    def visit_Assignment(self, item):
        a = self.visit(item.left)
        b = self.visit(item.right)
        return a + b

    def visit_BinaryOp(self, item):
        a = self.visit(item.left)
        b = self.visit(item.right)
        return a + b

    def visit_Break(self, item):
        return self.visit_default(item)

    def visit_Case(self, item):
        a = self.visit(item.expr)
        b = flatten([self.visit(s) for s in item.stmts])
        return a + b

    def visit_Cast(self, item):
        a = self.visit(item.to_type)
        b = self.visit(item.expr)
        return a + b

    def visit_Compound(self, item):
        return flatten([self.visit(b) for b in item.block_items])

    def visit_CompoundLiteral(self, item):
        a = self.visit(item.type)
        b = self.visit(item.init)
        return a + b

    def visit_Constant(self, item):
        return self.visit_default(item)

    def visit_Continue(self, item):
        return self.visit_default(item)

    def visit_Decl(self, item):
        a = self.visit(item.type)
        b = self.visit(item.init)
        c = self.visit(item.bitsize)
        return a + b + c

    def visit_DeclList(self, item):
        return flatten([self.visit(d) for d in item.decls])

    def visit_Default(self, item):
        return flatten([self.visit(s) for s in item.stmts])

    def visit_DoWhile(self, item):
        a = self.visit(item.cond)
        b = self.visit(item.stmt)
        return a + b

    def visit_EllipsisParam(self, item):
        return self.visit_default(item)

    def visit_EmptyStatement(self, item):
        return self.visit_default(item)

    def visit_Enum(self, item):
        return self.visit(item.values)

    def visit_Enumerator(self, item):
        return self.visit(item.value)

    def visit_EnumeratorList(self, item):
        return flatten([self.visit(e) for e in item.enumerators])

    def visit_ExprList(self, item):
        return flatten([self.visit(e) for e in item.exprs])

    def visit_FileAST(self, item):
        return flatten([self.visit(e) for e in item.ext])

    def visit_For(self, item):
        return flatten([self.visit(i) for i in [item.init, item.cond, item.next, item.stmt]])

    def visit_FuncCall(self, item):
        a = self.visit(item.name)
        b = self.visit(item.args)
        return a + b

    def visit_FuncDecl(self, item):
        a = self.visit(item.args)
        b = self.visit(item.type)
        return a + b

    def visit_FuncDef(self, item):
        a = self.visit(item.decl)
        b = flatten([self.visit(p) for p in item.param_decls])
        c = self.visit(item.body)
        return a + b + c

    def visit_Goto(self, item):
        return self.visit_default(item)

    def visit_ID(self, item):
        return self.visit_default(item)

    def visit_IdentifierType(self, item):
        return self.visit_default(item)

    def visit_If(self, item):
        a = self.visit(item.cond)
        b = self.visit(item.iftrue)
        c = self.visit(item.iffalse)
        return a + b + c

    def visit_InitList(self, item):
        return flatten([self.visit(e) for e in item.exprs])

    def visit_Label(self, item):
        return self.visit(item.stmt)

    def visit_NamedInitializer(self, item):
        a = flatten([self.visit(n) for n in item.name])
        b = self.visit(item.expr)
        return a + b

    def visit_ParamList(self, item):
        return flatten([self.visit(p) for p in item.params])

    def visit_PtrDecl(self, item):
        return self.visit(item.type)

    def visit_Return(self, item):
        return self.visit(item.expr)

    def visit_Struct(self, item):
        return flatten([self.visit(d) for d in item.decls])

    def visit_StructRef(self, item):
        a = self.visit(item.name)
        b = self.visit(item.field)
        return a + b

    def visit_Switch(self, item):
        a = self.visit(item.cond)
        b = self.visit(item.stmt)
        return a + b

    def visit_TernaryOp(self, item):
        a = self.visit(item.cond)
        b = self.visit(item.iftrue)
        c = self.visit(item.iffalse)
        return a + b + c

    def visit_TypeDecl(self, item):
        return self.visit(item.type)

    def visit_Typedef(self, item):
        return self.visit(item.type)

    def visit_Typename(self, item):
        return self.visit(item.type)

    def visit_UnaryOp(self, item):
        return self.visit(item.expr)

    def visit_Union(self, item):
        return flatten([self.visit(d) for d in item.decls])

    def visit_While(self, item):
        a = self.visit(item.cond)
        b = self.visit(item.stmt)
        return a + b

    def visit_Pragma(self, item):
        return self.visit_default(item)


class NondetReplacer(DfsVisitor):

    searched_pattern = '__VERIFIER_nondet_'
    var_counter = 0

    def visit_default(self, item):
        return list(), item  # No change to AST

    # Hook
    def _get_nondet_init(self, var_name, var_type):
        return None

    # Hook
    def _get_nondet_marker(self, var_name, var_type):
        return None

    def __init__(self):
        super().__init__()
        self.types = dict()
        self.current_method = None

    def visit_FuncCall(self, node):
        statements_to_prepend = []
        nondet_var_name = '__iuv' + str(self.var_counter)
        self.var_counter += 1
        nondet_var_type = self.get_type(node)
        nondet_type_decl = a.TypeDecl(nondet_var_name, list(), nondet_var_type)
        nondet_init = self._get_nondet_init(nondet_var_name, nondet_var_type)
        nondet_var = a.Decl(nondet_var_name, list(), list(), list(), nondet_type_decl, nondet_init, None)
        statements_to_prepend.append(nondet_var)
        nondet_marker = self._get_nondet_marker(nondet_var_name, nondet_var_type)
        if nondet_marker is not None:
            statements_to_prepend.append(nondet_marker)
        return statements_to_prepend, a.ID(nondet_var_name)  # Replace __VERIFIER_nondet_X() with new nondet variable

    def matches(self, name):
        if type(name) is a.ID:
            return self.matches(name.name)
        elif type(name) is str:
            return name.startswith(self.searched_pattern)
        else:
            raise AssertionError('Unhandled type for matching name: ' + str(type(name)))

    def get_type(self, func_call_node):
        name = self.get_name(func_call_node)
        return self.types[name]

    def get_name(self, func_call_node):
        name = func_call_node.name.name
        return name

    def visit_TypeDecl(self, item):
        name = item.declname
        decl_type = item.type
        if name not in self.types:
            self.types[name] = decl_type
        else:
            logging.debug("Not adding (%s, %s) to type dict", name, decl_type)

        return list(), item

    def visit_Typedef(self, item):
        name = item.name
        decl_type = item.type
        if name not in self.types:
            self.types[name] = decl_type
        else:
            logging.debug("Not adding (%s, %s) to type dict", name, decl_type)

        return list(), item  # No need to go down further in the ast

    def visit_FuncDef(self, item):
        p, item.decl = self.visit(item.decl)
        ps, ns = p, []
        if item.param_decls:
            for d in item.param_decls:
                p, n = self.visit(d)
                ps += p
                ns += n
            item.param_decls = ns
        p, item.body = self.visit(item.body)
        return [], item

    def visit_ArrayDecl(self, item):
        p, n = self.visit(item.type)
        item.type = n
        q, n = self.visit(item.dim)
        item.dim = n
        return p + q, item

    def visit_ArrayRef(self, item):
        p, n = self.visit(item.name)
        item.name = n
        q, n = self.visit(item.subscript)
        item.subscript = n
        return p + q, item

    def visit_Assignment(self, item):
        p, l = self.visit(item.lvalue)
        item.lvalue = l
        q, r = self.visit(item.rvalue)
        item.rvalue = r
        return p + q, item

    def visit_BinaryOp(self, item):
        p, n = self.visit(item.left)
        item.left = n
        q, n = self.visit(item.right)
        item.right = n
        return p + q, item

    def visit_Case(self, item):
        p, n = self.visit(item.expr)
        item.expr = n
        for s in item.stmts:
            ns = []
            q, n = self.visit(s)
            p += q
            ns += n
        item.stmts = ns
        return p, item

    def visit_Cast(self, item):
        p, n = self.visit(item.to_type)
        item.to_type = n
        q, n = self.visit(item.expr)
        item.expr = n

        return p + q, item

    def visit_Compound(self, item):
        ps, ns = [], []
        for i in item.block_items:
            p, n = self.visit(i)
            ps += p
            ns.append(n)
        item.block_items = ps + ns
        return [], item

    def visit_CompoundLiteral(self, item):
        p, n = self.visit(item.type)
        item.type = n
        q, n = self.visit(item.init)
        item.init = n
        return p + q, item

    def visit_Decl(self, item):
        p, n = self.visit(item.type)
        item.type = n
        q, n = self.visit(item.init)
        item.init = n
        r, n = self.visit(item.bitsize)
        item.bitsize = n
        return p + q + r, item

    def visit_DeclList(self, item):
        ps, ns = [], []
        for d in item.decls:
            p, n = self.visit(d)
            ps += p
            ns += ns
        item.decls = ns
        return ps, item

    def visit_Default(self, item):
        ps, ns = [], []
        for d in item.stmts:
            p, n = self.visit(d)
            ps += p
            ns += ns
        item.decls = ns
        return ps, item

    def visit_DoWhile(self, item):
        p, n = self.visit(item.cond)
        item.cond = n
        q, n = self.visit(item.stmt)
        item.stmt = n
        return p + q, item

    def visit_Enum(self, item):
        p, n = self.visit(item.values)
        item.values = n
        return p, item

    def visit_Enumerator(self, item):
        p, n = self.visit(item.value)
        item.value = n
        return p, item

    def visit_EnumeratorList(self, item):
        ps, ns = [], []
        for e in item.enumerators:
            p, n = self.visit(e)
            ps += p
            ns += n
        item.enumerators = ns
        return ps, item

    def visit_ExprList(self, item):
        ps, ns = [], []
        for e in item.exprs:
            p, n = self.visit(e)
            ps += p
            ns += n
        item.exprs = ns
        return ps, item

    def visit_FileAST(self, item):
        ps, ns = [], []
        for e in item.ext:
            p, n = self.visit(e)
            ps += p
            ns.append(n)
        item.ext = ps + ns
        return [], item

    def visit_For(self, item):
        p, item.init = self.visit(item.init)
        q, item.cond = self.visit(item.cond)
        r, item.next = self.visit(item.next)
        s, item.stmt = self.visit(item.stmt)

        return p + q + r + s, item

    def visit_FuncDecl(self, item):
        p, item.args = self.visit(item.args)
        q, item.type = self.visit(item.type)
        return p + q, item

    def visit_If(self, item):
        p, item.cond = self.visit(item.cond)
        q, item.iftrue = self.visit(item.iftrue)
        r, item.iffalse = self.visit(item.iffalse)
        return p + q + r, item

    def visit_InitList(self, item):
        ps, ns = [], []
        for e in item.exprs:
            p, n = self.visit(e)
            ps += p
            ns.append(n)
        item.exprs = ns
        return ps, item

    def visit_Label(self, item):
        p, item.stmt = self.visit(item.stmt)
        return item

    def visit_NamedInitializer(self, item):
        ps, ns = [], []
        for i in item.name:
            p, n = self.visit(i)
            ps += p
            ns.append(n)
        item.name = ns
        return ps, item

    def visit_ParamList(self, item):
        # Skip params
        return [], item

    def visit_PtrDecl(self, item):
        p, item.type = self.visit(item.type)
        return p, item

    def visit_Return(self, item):
        p, item.expr = self.visit(item.expr)
        return p, item

    def visit_Struct(self, item):
        ps, ns = [], []
        for i in item.decls:
            p, n = self.visit(i)
            ps += p
            ns.append(n)
        item.decls = ns
        return ps, item

    def visit_StructRef(self, item):
        p, item.name = self.visit(item.name)
        q, item.field = self.visit(item.field)
        return p + q, item

    def visit_Switch(self, item):
        p, item.cond = self.visit(item.cond)
        q, item.stmt = self.visit(item.stmt)

        return p + q, item

    def visit_TernaryOp(self, item):
        p, item.cond = self.visit(item.cond)
        q, item.iftrue = self.visit(item.iftrue)
        r, item.iffalse = self.visit(item.iffalse)
        return p + q + r, item

    def visit_Typename(self, item):
        p, item.type = self.visit(item.type)
        return p, item

    def visit_UnaryOp(self, item):
        p, item.expr = self.visit(item.expr)
        return p, item

    def visit_Union(self, item):
        ps, ns = [], []
        for d in item.decls:
            p, n = self.visit(d)
            ps += p
            ns.append(n)
        item.decls = ns
        return ps, item

    def visit_While(self, item):
        p, item.cond = self.visit(item.cond)
        q, item.stmt = self.visit(item.stmt)
        return p + q, item

import re
from abc import abstractmethod, ABCMeta

from pycparser import c_ast as a


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

    def __init__(self):
        super().__init__()
        self.current_method = None

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
        a = self.visit(item.lvalue)
        b = self.visit(item.rvalue)
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
        if item.block_items:
            results = [self.visit(b) for b in item.block_items]
            return flatten(results)
        else:
            return []

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
        return flatten([
            self.visit(i) for i in [item.init, item.cond, item.next, item.stmt]
        ])

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
        assert self.current_method is None
        self.current_method = item
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


class NondetIdentifierCollector(DfsVisitor):

    __metaclass__ = ABCMeta

    def __init__(self, pattern):
        super().__init__()
        self.nondet_identifiers = dict()
        self.scope = list()
        self.pattern = re.compile(pattern)

    @abstractmethod
    def get_var_name_from_function(self, item):
        pass

    def visit_FuncCall(self, item):
        func_name = get_name(item)
        if self.pattern.match(func_name):
            relevant_var = self.get_var_name_from_function(item)

            self.nondet_identifiers[relevant_var] = {
                'line': item.coord.line,
                'origin file': item.coord.file,
                'scope': self.scope[-1]
            }
        # no need to visit item.args, we don't do nested klee_make_symbolic calls
        return []

    def visit_FuncDef(self, item):
        self.scope.append(get_name(item.decl))
        self.visit(item.body)
        self.scope = self.scope[:-1]

        return []


def get_name(node):
    if type(node) is a.FuncCall:
        name = node.name.name
    elif type(node) is a.FuncDecl:
        name = get_name(node.type)
    elif type(node) is a.PtrDecl:
        name = get_name(node.type)
    elif type(node) is a.Decl:
        name = get_name(node.type)
    elif type(node) is a.TypeDecl:
        name = node.declname
    elif type(node) is a.Struct:
        name = node.name
    else:
        raise AssertionError("Unhandled node type: " + str(type(node)))
    return name


def get_type(node):
    node_type = type(node)
    name = []
    if node_type is a.IdentifierType:
        name += node.names
    elif node_type is a.Union:
        name += ['union', node.name]
    elif node_type is a.EllipsisParam:
        name += ['...']
    elif node_type is a.Struct:
        name += ['struct ' + node.name]
    elif node_type is a.Enum:
        name += ['enum ' + node.name]
    elif node_type is a.TypeDecl:
        name += [get_type(node.type)]
    elif node_type is a.Typename:
        name += [get_type(node.type)]
    elif node_type is a.Decl:
        name += [get_type(node.type)]
    elif node_type is a.PtrDecl:
        if type(node.type) is a.FuncDecl:
            func_decl = node.type
            m_type = get_type(func_decl.type) + '(*{})('
            if func_decl.args:
                params = list()
                for param in func_decl.args.params:
                    params.append(get_type(param))
                m_type += ', '.join(params)
            m_type += ')'
            name += [m_type]
        else:
            name += [get_type(node.type), '*']
    elif node_type is a.ArrayDecl:
        a_type = get_type(node.type)
        name += [a_type, " {}[]"]
    elif node_type is a.FuncDecl:
        name += [get_type(node.type), node.declname + '()']
    else:
        raise AssertionError("Unhandled node type: " + str(node_type))
    try:
        # type quals can be 'const', 'volatile', 'static'
        if 'const' in node.quals and node_type is not a.Decl:
            name += ['const']
        if 'static' in node.quals:
            name = ['static'] + name
        if 'volatile' in node.quals:
            name = ['volatile'] + name
    except AttributeError:
        pass
    return ' '.join(name)


class FuncDefCollector(a.NodeVisitor):

    def __init__(self):
        self.func_defs = []

    def visit_FuncDef(self, node):
        self.func_defs.append(node.decl)


class FuncDeclCollector(a.NodeVisitor):

    def __init__(self):
        self.func_decls = []

    def visit_FuncDecl(self, node):
        self.func_decls.append(node)

    def visit_PtrDecl(self, node):
        pass  # Don't go deeper so we don't collect function pointer

    def visit_Typedef(self, node):
        pass  # Don't go deeper so we don't collect typedef functions

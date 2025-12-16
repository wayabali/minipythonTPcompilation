 
import re
import os
import sys
from anytree import Node, RenderTree
from anytree.exporter import DotExporter
 

TOKEN_SPEC = [
    ('NUMBER', r'\d+'),
    ('INT', r'int'),
    ('FLOAT', r'float'),
    ('BOOL', r'bool'), 
    ('STRING', r'string'),
    ('WHILE', r'while'),
    ('IF', r'if'),
    ('ELSE', r'else'),
    ('PRINT', r'print'),
    ('DEF', r'def'),
    ('RETURN', r'return'),
    ('ID', r'[A-Za-z_]\w*'),
    ('LT', r'<'),
    ('GT', r'>'),
    ('EQ', r'=='),
    ('NE', r'!='),
    ('LE', r'<='),
    ('GE', r'>='),
    ('COMMA', r','),
    ('SEMICOLON', r';'),
    ('PLUS', r'\+'),
    ('MINUS', r'-'),
    ('MULT', r'\*'),
    ('DIV', r'/'),
    ('EQUAL', r'='),
    ('LPAR', r'\('),
    ('RPAR', r'\)'),
    ('LBRACE', r'\{'),
    ('RBRACE', r'\}'),
    ('LBRACKET', r'\['),
    ('RBRACKET', r'\]'),
    ('SKIP', r'[ \t\n]+'),
    ('COMMENT', r'/\*.*?\*/')
]
TOKEN_REGEX = '|'.join(f'(?P<{n}>{p})' for n, p in TOKEN_SPEC)
 
 
# ---------------------------
# 2) Lexer
# ---------------------------
def lexer(code):
    tokens = [(m.lastgroup, m.group()) for m in re.finditer(TOKEN_REGEX, code, re.DOTALL)
              if m.lastgroup not in ['SKIP', 'COMMENT']]
    return tokens
 
 
# ---------------------------
# 3) Parser (returns ast, symbol_table)
# - Repr: AST as list of tuples (same style as ton code)
# ---------------------------
def parse(tokens):
    i = 0
    symbol_table = {}
    ast = []
    temp_counter = 0
    label_counter = 0
 
    def new_temp():
        nonlocal temp_counter
        temp_counter += 1
        return f"t{temp_counter}"
 
    def new_label():
        nonlocal label_counter
        label_counter += 1
        return f"L{label_counter}"
 
    def parse_expr(start_idx):
        nonlocal i
        i = start_idx
        if i >= len(tokens):
            raise Exception("Unexpected end in expression")
        left_tok, left_val = tokens[i]
        i += 1
 
        if left_tok == 'NUMBER':
            left = ('Const', int(left_val))
        elif left_tok == 'ID':
            left = ('Var', left_val)
        else:
            # fallback
            left = ('Var', left_val)
 
        if i < len(tokens) and tokens[i][0] in ['PLUS', 'MINUS', 'MULT', 'DIV']:
            op = tokens[i][1]
            i += 1
            if i >= len(tokens):
                raise Exception("Unexpected end after operator in expr")
            right_tok, right_val = tokens[i]
            i += 1
            if right_tok == 'NUMBER':
                right = ('Const', int(right_val))
            else:
                right = ('Var', right_val)
            return ('BinOp', op, left, right)
        return left
 
    def parse_condition(start_idx):
        nonlocal i
        i = start_idx
        if i >= len(tokens):
            raise Exception("Unexpected end in condition")
        left_tok, left_val = tokens[i]
        i += 1
        if left_tok == 'NUMBER':
            left = ('Const', int(left_val))
        else:
            left = ('Var', left_val)
 
        if i >= len(tokens):
            raise Exception("Missing operator in condition")
        op = tokens[i][1]
        i += 1
 
        if i >= len(tokens):
            raise Exception("Missing right side in condition")
        right_tok, right_val = tokens[i]
        i += 1
        if right_tok == 'NUMBER':
            right = ('Const', int(right_val))
        else:
            right = ('Var', right_val)
        return ('Condition', op, left, right)
 
    while i < len(tokens):
        tok, val = tokens[i]
 
        if tok in ['INT', 'FLOAT', 'BOOL', 'STRING']:
            var_type = val
            i += 1
            vars_list = []
            while i < len(tokens) and tokens[i][0] != 'SEMICOLON':
                if tokens[i][0] == 'ID':
                    vars_list.append(tokens[i][1])
                i += 1
            for v in vars_list:
                symbol_table[v] = var_type
            ast.append(('Decl', var_type, vars_list))
            if i < len(tokens) and tokens[i][0] == 'SEMICOLON':
                i += 1
 
        elif tok == 'ID':
            var_name = val
            i += 1
            if i < len(tokens) and tokens[i][0] == 'EQUAL':
                i += 1
                expr = parse_expr(i)
                ast.append(('Assign', var_name, expr))
                # advance to semicolon
                while i < len(tokens) and tokens[i][0] != 'SEMICOLON':
                    i += 1
                if i < len(tokens) and tokens[i][0] == 'SEMICOLON':
                    i += 1
            else:
                # unknown ID usage (ignore for now)
                i += 0
 
        elif tok == 'WHILE':
            i += 2  # skip 'while' and '('
            cond = parse_condition(i)
            # After parse_condition, i is after right expr token
            # skip ')' then '{'
            if i < len(tokens) and tokens[i][0] == 'RPAR':
                i += 1
            if i < len(tokens) and tokens[i][0] == 'LBRACE':
                i += 1
            start_body = i
            brace_count = 1
            while i < len(tokens) and brace_count > 0:
                if tokens[i][0] == 'LBRACE':
                    brace_count += 1
                elif tokens[i][0] == 'RBRACE':
                    brace_count -= 1
                i += 1
            end_body = i - 1
            ast.append(('While', cond, start_body, end_body))
 
        elif tok == 'IF':
            i += 2  # skip 'if' and '('
            cond = parse_condition(i)
            if i < len(tokens) and tokens[i][0] == 'RPAR':
                i += 1
            if i < len(tokens) and tokens[i][0] == 'LBRACE':
                i += 1
            body_start = i
            brace_count = 1
            while i < len(tokens) and brace_count > 0:
                if tokens[i][0] == 'LBRACE':
                    brace_count += 1
                elif tokens[i][0] == 'RBRACE':
                    brace_count -= 1
                i += 1
            body_end = i - 1
            ast.append(('If', cond, body_start, body_end))
 
        elif tok == 'PRINT':
            i += 2  # skip print and '('
            if i < len(tokens):
                var_name = tokens[i][1]
                i += 1
            else:
                raise Exception("print missing argument")
            # skip ')' and ';' if present
            if i < len(tokens) and tokens[i][0] == 'RPAR':
                i += 1
            if i < len(tokens) and tokens[i][0] == 'SEMICOLON':
                i += 1
            ast.append(('Print', var_name))
 
        else:
            i += 1
 
    return ast, symbol_table
 
 
# ---------------------------
# 4) Semantic check (simple)
# ---------------------------
def semantic_check(ast, symbol_table):
    new_ast = []
    for stmt in ast:
        if stmt[0] == 'Decl':
            new_ast.append(stmt)
        elif stmt[0] == 'Assign':
            var = stmt[1]
            if var not in symbol_table:
                raise Exception(f"Erreur sémantique : variable {var} non déclarée")
            new_ast.append(stmt)
        elif stmt[0] == 'Print':
            var = stmt[1]
            if var not in symbol_table:
                raise Exception(f"Erreur sémantique : variable {var} non déclarée")
            new_ast.append(stmt)
        elif stmt[0] in ['While', 'If']:
            new_ast.append(stmt)
        else:
            new_ast.append(stmt)
    return new_ast
 
 
# ---------------------------
# 5) Generate TAC (reuse logic)
# ---------------------------
temp_counter_global = 0
label_counter_global = 0
 
 
def new_temp_global():
    global temp_counter_global
    temp_counter_global += 1
    return f"t{temp_counter_global}"
 
 
def new_label_global():
    global label_counter_global
    label_counter_global += 1
    return f"L{label_counter_global}"
 
 
def generate_tac(ast, symbol_table):
    tac_code = []
    for var in symbol_table:
        tac_code.append(f"DECLARE {var}")
 
    for stmt in ast:
        if stmt[0] == 'Assign':
            var = stmt[1]
            expr = stmt[2]
            if expr[0] == 'Const':
                tac_code.append(f"LOAD {var}, {expr[1]}")
            elif expr[0] == 'Var':
                tac_code.append(f"LOAD {var}, {expr[1]}")
            elif expr[0] == 'BinOp':
                op_name = expr[1]
                left = expr[2]
                right = expr[3]
                temp = new_temp_global()
                left_val = left[1]
                right_val = right[1]
                if op_name == '+':
                    tac_code.append(f"ADD {temp}, {left_val}, {right_val}")
                elif op_name == '-':
                    tac_code.append(f"SUB {temp}, {left_val}, {right_val}")
                elif op_name == '*':
                    tac_code.append(f"MULT {temp}, {left_val}, {right_val}")
                elif op_name == '/':
                    tac_code.append(f"DIV {temp}, {left_val}, {right_val}")
                tac_code.append(f"STORE {var}, {temp}")
 
        elif stmt[0] == 'While':
            cond = stmt[1]
            start_label = new_label_global()
            end_label = new_label_global()
            tac_code.append(f"{start_label}:")
            left = cond[2][1] if cond[2][0] == 'Var' else cond[2][1]
            right = cond[3][1] if cond[3][0] == 'Var' else cond[3][1]
            temp_cond = new_temp_global()
            if cond[1] == '<':
                tac_code.append(f"LT {temp_cond}, {left}, {right}")
            elif cond[1] == '>':
                tac_code.append(f"GT {temp_cond}, {left}, {right}")
            elif cond[1] == '==':
                tac_code.append(f"EQ {temp_cond}, {left}, {right}")
            elif cond[1] == '!=':
                tac_code.append(f"NE {temp_cond}, {left}, {right}")
            tac_code.append(f"JMPF {end_label}, {temp_cond}")
            tac_code.append(f"# Corps du while (non développé)")
            tac_code.append(f"JMP {start_label}")
            tac_code.append(f"{end_label}:")
 
        elif stmt[0] == 'If':
            cond = stmt[1]
            end_label = new_label_global()
            left = cond[2][1] if cond[2][0] == 'Var' else cond[2][1]
            right = cond[3][1] if cond[3][0] == 'Var' else cond[3][1]
            temp_cond = new_temp_global()
            if cond[1] == '==':
                tac_code.append(f"EQ {temp_cond}, {left}, {right}")
            tac_code.append(f"JMPF {end_label}, {temp_cond}")
            tac_code.append(f"# Corps du if (non développé)")
            tac_code.append(f"{end_label}:")
 
        elif stmt[0] == 'Print':
            var = stmt[1]
            tac_code.append(f"PRINT {var}")
 
    return tac_code
 
 
# ---------------------------
# 6) Build anytree AST for visualization
# ---------------------------
def build_anytree(node, parent=None):
    if isinstance(node, tuple):
        n = Node(str(node[0]), parent=parent)
        for c in node[1:]:
            build_anytree(c, n)
        return n
    elif isinstance(node, list):
        n = Node("list", parent=parent)
        for item in node:
            build_anytree(item, n)
        return n
    else:
        Node(str(node), parent=parent)
        return parent
 
 
# ---------------------------
# 7) Execution (interpreter simple)
# ---------------------------
def execute(ast, symbol_table):
    runtime = {var: 0 for var in symbol_table.keys()}
 
    i = 0
    while i < len(ast):
        stmt = ast[i]
 
        if stmt[0] == 'Assign':
            var = stmt[1]
            val = stmt[2]
            if val[0] == 'Const':
                runtime[var] = val[1]
            elif val[0] == 'Var':
                runtime[var] = runtime.get(val[1], 0)
            elif val[0] == 'BinOp':
                op = val[1]
                left = val[2][1] if val[2][0] == 'Var' else val[2][1]
                right = val[3][1] if val[3][0] == 'Var' else val[3][1]
                left_val = runtime[left] if isinstance(left, str) else left
                right_val = runtime[right] if isinstance(right, str) else right
                if op == '+':
                    runtime[var] = left_val + right_val
                elif op == '-':
                    runtime[var] = left_val - right_val
                elif op == '*':
                    runtime[var] = left_val * right_val
                elif op == '/':
                    runtime[var] = left_val // right_val
 
        elif stmt[0] == 'While':
            cond = stmt[1]
            left = cond[2][1] if cond[2][0] == 'Var' else cond[2][1]
            right = cond[3][1] if cond[3][0] == 'Var' else cond[3][1]
            left_val = runtime[left] if isinstance(left, str) else left
            right_val = runtime[right] if isinstance(right, str) else right
            # simplified behaviour: we cannot execute body because AST stores body as indices.
            # this interpreter will skip while bodies (like original code) but will show how to extend.
            if cond[1] == '<' and left_val >= right_val:
                # skip body (nothing to execute here, because our AST didn't store inner statements)
                pass
            # a full implementation would parse body range and execute them repeatedly
 
        elif stmt[0] == 'Print':
            var = stmt[1]
            print(runtime.get(var, 0))
        i += 1
 
 
# ---------------------------
# 8) Top-level pipeline
# ---------------------------
def run_minipython_file(filename):
    if not os.path.isfile(filename):
        raise FileNotFoundError(f"Fichier introuvable: {filename}")
 
    with open(filename, "r", encoding="utf-8") as f:
        code = f.read()
 
    print("\n=== LEXICAL ===")
    toks = lexer(code)
    for t in toks:
        print(t)
 
    print("\n=== PARSING ===")
    ast, symtab = parse(toks)
    for node in ast:
        print(node)
 
    print("\n=== SEMANTIC ===")
    ast_sem = semantic_check(ast, symtab)
    for node in ast_sem:
        print(node)
 
    print("\n=== TAC ===")
    tac = generate_tac(ast_sem, symtab)
    for i, instr in enumerate(tac):
        print(instr)
 
    print("\n=== AST (console) ===")
    root = build_anytree(("Program", *ast_sem))
    for pre, fill, n in RenderTree(root):
        print(f"{pre}{n.name}")
 
    try:
        out = os.path.join(os.getcwd(), "ast_pythonpur.png")
        DotExporter(root).to_picture(out)
        print(f"\nAST exporté en image : {out}")
    except Exception as e:
        print("Export AST (image) failed:", e)
        print("Attempt to write .dot file...")
        try:
            with open("ast_pythonpur.dot", "w", encoding="utf-8") as f:
                for line in DotExporter(root):
                    f.write(line)
            print("DOT exported: ast_pythonpur.dot")
        except Exception as e2:
            print("DOT export also failed:", e2)
 
    print("\n=== EXÉCUTION ===")
    execute(ast_sem, symtab)
    print("\n=== Fin ===")
 
 

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python prgPythonPur_fixed.py <fichier1.minipython> [<fichier2> ...]")
        sys.exit(1)
   
    for filename in sys.argv[1:]:
        print(f"\n=== Processing {filename} ===")
        try:
            run_minipython_file(filename)
        except Exception as e:
            print(f"Erreur in {filename}:", e)
# fichier : prgPythonPur.py
from anytree import Node, RenderTree
from anytree.exporter import DotExporter
import re
 
# -------------------------------------------------
# 1. Code source MiniPython
# -------------------------------------------------
def get_code_from_user():
    print("Entrez votre code MiniPython (tapez 'FIN' sur une ligne vide pour terminer):")
    lines = []
    while True:
        line = input()
        if line.strip() == 'FIN':
            break
        lines.append(line)
    return '\n'.join(lines)
 
# Choix: code prédéfini ou saisie utilisateur
print("Choisissez une option:")
print("1. Utiliser le code prédéfini")
print("2. Saisir votre propre code")
choice = input("Votre choix (1 ou 2): ")
 
if choice == '2':
    code_source = get_code_from_user()
else:
    code_source = """
int x;
x = 0;
while (x < 3) {
    if (x == 1) {
        print(x);
    }
    x = x + 1;
}
"""
 
# -------------------------------------------------
# 2. Analyse lexicale
# -------------------------------------------------
token_specification = [
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
 
regex = '|'.join(f'(?P<{n}>{p})' for n, p in token_specification)
tokens = [(m.lastgroup, m.group()) for m in re.finditer(regex, code_source, re.DOTALL)
          if m.lastgroup not in ['SKIP', 'COMMENT']]
 
print("\n=== Phase lexicale ===")
for t in tokens:
    print(t)
 
# -------------------------------------------------
# 3. Analyse syntaxique & construction AST
# -------------------------------------------------
symbol_table = {}
ast = []
temp_counter = 0
label_counter = 0
 
def new_temp():
    global temp_counter
    temp_counter += 1
    return f"t{temp_counter}"
 
def new_label():
    global label_counter
    label_counter += 1
    return f"L{label_counter}"
 
i = 0
 
def parse_expr(start_idx):
    """Parse une expression arithmétique simple"""
    global i
    i = start_idx
    left_tok, left_val = tokens[i]
    i += 1
   
    if left_tok == 'NUMBER':
        left = ('Const', int(left_val))
    elif left_tok == 'ID':
        left = ('Var', left_val)
    else:
        return left
   
    if i < len(tokens) and tokens[i][0] in ['PLUS', 'MINUS', 'MULT', 'DIV']:
        op = tokens[i][1]
        i += 1
        right_tok, right_val = tokens[i]
        i += 1
        if right_tok == 'NUMBER':
            right = ('Const', int(right_val))
        else:
            right = ('Var', right_val)
        return ('BinOp', op, left, right)
   
    return left
 
def parse_condition(start_idx):
    """Parse une condition de comparaison"""
    global i
    i = start_idx
    left_tok, left_val = tokens[i]
    i += 1
   
    if left_tok == 'NUMBER':
        left = ('Const', int(left_val))
    else:
        left = ('Var', left_val)
   
    op = tokens[i][1]
    i += 1
   
    right_tok, right_val = tokens[i]
    i += 1
   
    if right_tok == 'NUMBER':
        right = ('Const', int(right_val))
    else:
        right = ('Var', right_val)
   
    return ('Condition', op, left, right)
 
i = 0
while i < len(tokens):
    tok, val = tokens[i]
   
    if tok in ['INT', 'FLOAT', 'BOOL', 'STRING']:  # Déclaration de variables
        var_type = val
        i += 1
        vars_list = []
        while tokens[i][0] != 'SEMICOLON':
            if tokens[i][0] == 'ID':
                vars_list.append(tokens[i][1])
            i += 1
       
        for v in vars_list:
            symbol_table[v] = var_type
        ast.append(('Decl(L-attribué)', var_type, vars_list))
        i += 1
   
    elif tok == 'ID':  # Assignation
        var_name = val
        i += 1
        if tokens[i][0] == 'EQUAL':
            i += 1
            expr = parse_expr(i)
            ast.append(('Assign(S-attribué)', var_name, expr))
            while i < len(tokens) and tokens[i][0] != 'SEMICOLON':
                i += 1
            i += 1
   
    elif tok == 'WHILE':  # Boucle while
        i += 2  # skip 'while' and '('
        cond = parse_condition(i)
        i += 1  # skip ')'
        i += 1  # skip '{'
       
        body = []
        brace_count = 1
        start_body = i
       
        while brace_count > 0:
            if tokens[i][0] == 'LBRACE':
                brace_count += 1
            elif tokens[i][0] == 'RBRACE':
                brace_count -= 1
            i += 1
       
        ast.append(('While', cond, start_body, i-1))
   
    elif tok == 'IF':  # Structure if
        i += 2  # skip 'if' and '('
        cond = parse_condition(i)
        i += 1  # skip ')'
        i += 1  # skip '{'
       
        body_start = i
        brace_count = 1
       
        while brace_count > 0:
            if tokens[i][0] == 'LBRACE':
                brace_count += 1
            elif tokens[i][0] == 'RBRACE':
                brace_count -= 1
            i += 1
       
        ast.append(('If', cond, body_start, i-1))
   
    elif tok == 'PRINT':
        i += 2  # skip 'print' and '('
        var_name = tokens[i][1]
        i += 3  # skip var, ')' and ';'
        ast.append(('Print(S-attribué)', var_name))
   
    else:
        i += 1
 
print("\n=== AST syntaxique brut ===")
for node in ast:
    print(node)
 
# -------------------------------------------------
# 4. Analyse sémantique simple
# -------------------------------------------------
def semantic_check(ast, symbol_table):
    new_ast = []
    for stmt in ast:
        if stmt[0].startswith('Decl'):
            new_ast.append(stmt)
        elif stmt[0].startswith('Assign'):
            var = stmt[1]
            if var not in symbol_table:
                raise Exception(f"Erreur sémantique : variable {var} non déclarée")
            new_ast.append(stmt)
        elif stmt[0].startswith('Print'):
            var = stmt[1]
            if var not in symbol_table:
                raise Exception(f"Erreur sémantique : variable {var} non déclarée")
            new_ast.append(stmt)
        elif stmt[0] in ['While', 'If']:
            new_ast.append(stmt)
    return new_ast
 
ast_semantic = semantic_check(ast, symbol_table)
print("\n=== AST après analyse sémantique ===")
for node in ast_semantic:
    print(node)
 
# -------------------------------------------------
# 5. Génération du code intermédiaire (TAC)
# -------------------------------------------------
def generate_tac(ast, symbol_table):
    tac_code = []
   
    for var in symbol_table:
        tac_code.append(f"DECLARE {var}")
   
    for stmt in ast:
        if stmt[0].startswith('Assign'):
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
               
                temp = new_temp()
               
                if left[0] == 'Const':
                    left_val = left[1]
                else:
                    left_val = left[1]
               
                if right[0] == 'Const':
                    right_val = right[1]
                else:
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
            start_label = new_label()
            end_label = new_label()
           
            tac_code.append(f"{start_label}:")
           
            left = cond[2][1] if cond[2][0] == 'Var' else cond[2][1]
            right = cond[3][1] if cond[3][0] == 'Var' else cond[3][1]
           
            temp_cond = new_temp()
            if cond[1] == '<':
                tac_code.append(f"LT {temp_cond}, {left}, {right}")
            elif cond[1] == '>':
                tac_code.append(f"GT {temp_cond}, {left}, {right}")
            elif cond[1] == '==':
                tac_code.append(f"EQ {temp_cond}, {left}, {right}")
            elif cond[1] == '!=':
                tac_code.append(f"NE {temp_cond}, {left}, {right}")
           
            tac_code.append(f"JMPF {end_label}, {temp_cond}")
            tac_code.append(f"# Corps du while")
            tac_code.append(f"JMP {start_label}")
            tac_code.append(f"{end_label}:")
       
        elif stmt[0] == 'If':
            cond = stmt[1]
            end_label = new_label()
           
            left = cond[2][1] if cond[2][0] == 'Var' else cond[2][1]
            right = cond[3][1] if cond[3][0] == 'Var' else cond[3][1]
           
            temp_cond = new_temp()
            if cond[1] == '==':
                tac_code.append(f"EQ {temp_cond}, {left}, {right}")
           
            tac_code.append(f"JMPF {end_label}, {temp_cond}")
            tac_code.append(f"# Corps du if")
            tac_code.append(f"{end_label}:")
       
        elif stmt[0].startswith('Print'):
            var = stmt[1]
            tac_code.append(f"PRINT {var}")
   
    return tac_code
 
tac = generate_tac(ast_semantic, symbol_table)
print("\n=== Code intermédiaire (TAC) ===")
for instruction in tac:
    print(instruction)
 
# -------------------------------------------------
# 6. Visualisation AST avec anytree
# -------------------------------------------------
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
 
root_node = build_anytree(("Program", *ast_semantic))
print("\n=== AST visuel console ===")
for pre, fill, node in RenderTree(root_node):
    print(f"{pre}{node.name}")
 
try:
    # Solution pour éviter l'erreur de permission Windows
    import os
    output_file = os.path.join(os.getcwd(), "ast_pythonpur.png")
    DotExporter(root_node).to_picture(output_file)
    print(f"\nAST exporté en image : {output_file}")
except Exception as e:
    print(f"\nErreur lors de l'export de l'image: {e}")
    print("Tentative d'export en format DOT...")
    try:
        # Alternative : sauvegarder en .dot
        with open("ast_pythonpur.dot", "w", encoding="utf-8") as f:
            for line in DotExporter(root_node):
                f.write(line)
        print("AST exporté en format DOT : ast_pythonpur.dot")
        print("Vous pouvez le convertir manuellement avec: dot -Tpng ast_pythonpur.dot -o ast_pythonpur.png")
    except Exception as e2:
        print(f"Erreur lors de l'export DOT: {e2}")
 
# -------------------------------------------------
# 7. Exécution MiniPython
# -------------------------------------------------
def execute(ast, symbol_table):
    runtime = {var: 0 for var in symbol_table.keys()}
   
    i = 0
    while i < len(ast):
        stmt = ast[i]
       
        if stmt[0].startswith('Assign'):
            var = stmt[1]
            val = stmt[2]
           
            if val[0] == 'Const':
                runtime[var] = val[1]
            elif val[0] == 'Var':
                runtime[var] = runtime[val[1]]
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
           
            if cond[1] == '<' and left_val >= right_val:
                # Skip while body
                i += 1
                continue
            elif cond[1] == '<' and left_val < right_val:
                # Execute body - simplified
                pass
       
        elif stmt[0].startswith('Print'):
            var = stmt[1]
            print(runtime[var])
       
        i += 1
 
print("\n=== Exécution MiniPython ===")
execute(ast_semantic, symbol_table)
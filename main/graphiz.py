from graphviz import Digraph
 
# Créer un graphe simple
dot = Digraph(comment='Test GraphViz')
dot.node('A', 'Racine')
dot.node('B', 'Enfant 1')
dot.node('C', 'Enfant 2')
dot.edge('A', 'B')
dot.edge('A', 'C')
 
# Sauvegarder et générer l'image
dot.render('test', format='png', cleanup=True)
print("✅ Image créée : test.png")
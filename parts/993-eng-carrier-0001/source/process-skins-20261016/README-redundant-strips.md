# Bandes de contact déjà contenues dans la feuille

Le chart 2 de la région gauche possède cinq contacts `upper` corrects sur son
bord inférieur. Les faces voisines et leurs parents concordent : il s’agit
d’une terrasse en trois dimensions, et non d’un rôle à inverser. Les cinq
quadrilatères proposés vers `+Z`, avec la pénétration de 0,2 mm déjà déclarée,
sont entièrement contenus dans le domaine libre de la feuille.

`redundant_strip_interfaces.py` conserve le constructeur incrémental 814 et les
opérations de 943. Pour une direction contraire au bord local, il prouve
rationnellement que le quadrilatère ENTIER est inclus dans le domaine source.
Seulement alors, il journalise `excluded_redundant_inside_source_domain` et
n’ajoute pas ses triangles. La feuille, les traces et leurs rôles restent
présents. L’union géométrique est identique puisque la bande est déjà dans D.
Une bande partiellement extérieure, traversant un trou ou non prouvée conserve
le refus. Sans ce cas, les cinq anciens témoins gardent exactement leur WKB et
leur reçu constructeur.

Le wrapper `continuous_redundant_interfaces.py` annonce explicitement le SHA du
nouveau constructeur comme autorité. Les anciens checkpoints conservent leur
autorité 943 ; ils doivent être réévalués par le chemin d’admission correspondant,
sans modifier leurs métadonnées. Les mêmes preuves de couverture, bande,
contacts, connexion en trois dimensions et exposition restent nécessaires.

Les entrées v6 conservent les arguments des entrées v5. Elles enregistrent aussi
D, les interfaces et leurs identités avant chaque appel d’infill d’une peau,
puis le résultat ou l’erreur dans `chart-progress/`. Ces journaux n’admettent
aucune géométrie. Ils permettent d’examiner un nouveau refus sans rejouer les
peaux qui le précèdent.

Le chart réel a passé l’infill natif, la réparation complète, la couverture et
la bande exactes, les contacts du domaine et de la composante, puis le remap.
Ce témoin ne remplace pas la génération et l’audit de toute la région. Les
preuves compactes et les SHA des reçus locaux sont dans
`combinatorial-evidence/redundant-results.json`.

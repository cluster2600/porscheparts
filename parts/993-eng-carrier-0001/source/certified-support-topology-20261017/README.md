# Retriangulation certifiée de trois régions des supports d’impression

Les copies corrigées **003, 009 et 010** conservent tous leurs sommets, ainsi
que les attributs `order` et `type`. Leurs triangles ont été reconstruits par
CGAL et contrôlés sur les fichiers réels.

| Région | Lignes de triangles changées | Coupes dégénérées avant → après | Couches strictes passées | Groupes connectés |
| --- | ---: | ---: | ---: | ---: |
| 003 | 39 | 205 → 0 | 1 034 / 1 034 | 147 / 147 |
| 009 | 49 | 2 879 → 0 | 1 034 / 1 034 | 22 / 22 |
| 010 | 290 | 1 185 → 0 | 1 034 / 1 034 | 30 / 30 |

Les méthodes natives restent identifiées séparément : 146 choix PMP pour
010 ; 48 choix PMP et une diagonale contrainte par `CGAL::Euler::split_face`
pour 003/009. Le résultat PMP historique de 49 cas, dont un conservait
l’ancienne diagonale, est conservé intégralement. Les certificats vérifient
les états successifs, les contours, les propriétaires des faces et la baisse
stricte du compteur de coupes dégénérées. Les bornes des peaux SKIN restent
quantifiées ; aucune identité universelle des surfaces 3D SKIN n’est annoncée.

Le [rejeu réel des 14 surfaces SKIN](evidence/replay-assessment.json) a passé
en 5,289 s sous le contrôleur borné. Il reproduit d’abord le remap original
et son reçu historique, puis les 320 lignes SKIN certifiées. Les triangles XYZ
reconstruits sont exactement égaux aux blocs candidats ; aucune ligne GRID
n’est modifiée par ce rejeu. Les contrôles du consumer sur les vrais fichiers
NPZ passent également. Le runtime et les entrées restent inchangés.

La fonction complète de chargement des supports et les six admissions de
l’assemblage ne sont pas exécutées par ce rejeu local. Les contacts et
l’exposition sur toutes les couches, puis l’assemblage des sept régions,
restent des étapes distinctes de la chaîne.

## Fichiers et utilisation

La [capsule](capsule/topology-manifest.json), SHA
`233d331592792eb2d667385db49b61d53fbe5416d162b71e2a11cf6c252cd544`,
conserve 67 fichiers : tableaux originaux/candidats/traces, certificats,
résultats natifs, contrôles stricts et helper de remap portable. Tous ses noms
sont locaux et plats. Les chemins historiques visibles dans les reçus sont
de la provenance ; le helper utilise les fichiers de la capsule.

L’[adaptateur privé](adapter/certified_support_consumer.py) reçoit le dossier
des sources runtime d’origine, ce manifeste et son SHA. Il conserve les six
contrôles de v6 et les quatre réemplois 2D existants. Il appelle les contrôles
originaux avant d’appliquer les faces certifiées, recalcule le graphe matériel
sur une dérivation nouvelle, puis lie ce graphe entier au reçu des contacts.
Le réemploi vérifie les vrais tableaux livrés et cette même liaison sans
recalculer le graphe.

Les 19 contrôles synthétiques de cet adaptateur se lancent sans environnement
AM, depuis la racine du dépôt :

```sh
python3 -I -B -m unittest discover \
  -s parts/993-eng-carrier-0001/source/certified-support-topology-20261017/adapter \
  -p selfcheck.py
```

Ils ne remplacent pas l’intégration réelle des sept régions. Les fichiers
dans `replay-source/` sont les sources et plans historiques byte-identiques
du calcul exécuté ; leurs sorties sont déjà occupées dans le workspace
producteur. Ce dossier ne les présente pas comme un nouveau lanceur autonome.
La recette finale doit fournir le snapshot runtime et un nouveau plan explicite.

Les [copies documentaires](copy-provenance.json), le [reçu de supervision](evidence/replay-supervision.json)
et la [collecte du vrai retour 0](evidence/replay-terminal-collection.json)
accompagnent les preuves locales. Aucun gros metadata régional ni runtime
n’est dupliqué ici.

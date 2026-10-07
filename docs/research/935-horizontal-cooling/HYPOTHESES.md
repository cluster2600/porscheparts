# Hypothèses de rétro-ingénierie du système horizontal 935

Décision du propriétaire, 7 octobre 2026 : avancer avec des hypothèses
explicites plutôt qu'attendre toutes les cotes. La cible reste d'abord le
montage historique 935, puis l'adaptation horizontale 993.

Une hypothèse comporte une justification, les calculs qui en dépendent et
un moyen de la rejeter. Le nominal sous hypothèses peut servir à préparer
des calculs et une CAO candidate. Il ne transforme pas une surface interpolée
en mesure et ne modifie pas les 17 interfaces indépendantes encore ouvertes.

| Identifiant | Hypothèse de travail | Confrontation prévue |
|---|---|---|
| H-SCALE | Réutiliser provisoirement 1 mm par unité des OBJ ; comparer 0,9 et 1,1 sans imposer un diamètre nominal. | Deux cotes indépendantes sur les mêmes pièces ; cohérence des portées et de l'empilage. Un alésage partiel supposé normalisé ne suffit pas à calibrer. |
| H-DRIVE | Courroie, arbre horizontal et renvoi d'angle vers l'arbre vertical ; denture conique comme premier candidat interne. | Architecture documentée par [Gunnar Racing](https://www.gunnarracing.com/team/lola/stage4.htm). Photographier un renvoi démonté ; relever axes, dentures, nombre de dents et rapports. Le type exact reste hypothétique. |
| H-RATIO | Comparer trois rapports totaux de vitesse rotor/moteur : 0,8, 1,0 et 1,2. | Mesurer simultanément les deux régimes et relever les diamètres primitifs/dentures. Ce sont des points d'exploration, pas des rapports Porsche publiés. |
| H-ROTOR | Utiliser neuf pales pour la première cinématique, à partir des neuf régions acquises. | Vérifier la répétition sur le tour entier, puis les pieds, extrémités et acquisitions du dos ; conserver les réparations localisées. |
| H-COUPLING | Prévoir un accouplement souple dans le chemin de couple ; ne pas le remplacer d'emblée par une liaison rigide. | Témoignage d'utilisation dans le [fil Rennlist](https://rennlist.com/forums/911-turbo-930-forum/94486-935-users-flat-fan.html). Localiser le composant sur une vue démontée et caractériser sa raideur/amortissement. |

Les références de roulements, leurs précharges et la lubrification deviennent
des variantes de conception à comparer lorsque les enveloppes et chemins
d'efforts sont ajustés. Aucune référence commerciale n'est présentée comme
la définition intérieure historique. Les inconnues du contrat restent nulles.

## Campagne cinématique

Le [calculateur existant](../../../twins/935-horizontal-cooling-system-f0/source/build_system_twin.py)
accepte désormais `purpose: hypothesis_screen`. Chaque entrée utilisée doit
référencer une source `kind: assumption`, avec `locator` et `rejection_test`.
Le statut des résultats est `hypothesis_calculation`. Les essais synthétiques
et les entrées mesurées conservent leurs contrôles antérieurs ; une hypothèse
ne peut pas être promue en preuve du spécimen.

Grille initiale exécutée : 3 régimes moteur (3 000, 6 000, 8 000 tr/min),
3 rapports totaux (0,8, 1,0, 1,2), 3 diamètres choisis (250, 275, 300 mm),
9 pales et glissement nul. **Ces diamètres ne sont ni des mesures des scans,
ni des cotes 935/993 sourcées, ni une calibration retenue.** La décomposition
« rapport de courroie variable, rapport d'engrenages égal à 1 » sert seulement
à factoriser le rapport total ; elle ne définit pas les poulies ou dentures.

Les 27 scénarios donnent 2 400–9 600 tr/min au rotor, 31,42–150,80 m/s
en périphérie et 360–1 440 Hz de passage des pales. Ces plages décrivent la
grille choisie ; elles n'établissent ni le régime admissible ni les
caractéristiques du ventilateur historique. Les incertitudes d'entrée nulles
signifient ici un point de scénario fixé, pas une certitude métrologique.
L'outil ne propage pas les incertitudes.

Reproduction minimale depuis la racine du dépôt, sans nouveau logiciel :

```python
from pathlib import Path
import importlib.util, itertools, json

study = Path('twins/935-horizontal-cooling-system-f0')
spec = importlib.util.spec_from_file_location('twin', study/'source/build_system_twin.py')
twin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(twin)
output = Path('work/935-hypotheses-new')
output.mkdir(mode=0o700)  # nouvelle destination ; ne pas remplacer un ancien lot
for rpm, ratio, diameter in itertools.product((3000, 6000, 8000), (0.8, 1.0, 1.2), (0.25, 0.275, 0.30)):
    case = json.loads((study/'operating-case.template.json').read_text())
    case.update(id=f'hypothesis-n{rpm}-r{ratio}-d{diameter}', purpose='hypothesis_screen')
    case['evidence'] = [{'id': 'H-KINEMATICS', 'kind': 'assumption',
        'locator': 'docs/research/935-horizontal-cooling/HYPOTHESES.md',
        'sha256': None, 'rejection_test': 'Compare calibrated geometry and independent tachometer measurements'}]
    values = dict(engine_rpm=rpm, belt_speed_ratio=ratio, belt_slip_fraction=0,
                  gear_speed_ratio=1, rotor_diameter=diameter, blade_count=9)
    for key, value in values.items():
        case['parameters'][key].update(value=value, uncertainty=0, evidence_ids=['H-KINEMATICS'])
    path = output/(case['id']+'.json')
    path.write_text(json.dumps(case, indent=2)+'\n')
    result = twin.build(path, output/case['id'])
    assert not result['manufacturing_release_allowed']
    assert result['models']['airflow']['values'] is None
```

Le débit, le couple aérodynamique, les températures, l'inertie et les efforts
de balourd restent sans résultat dans ce lot : leurs entrées ne sont pas
fournies. La CAO scannée n'est pas chargée par cette campagne cinématique.
Les questions de [recherche communautaire](COMMUNITY_RESEARCH.md) ciblent
les informations qui permettront de réduire les hypothèses.

La [campagne suivante](HYPOTHESIS_TESTS.md) exécute 160 scénarios d'inertie,
balourd, transmission, réseau d'air et thermique, plus un témoin centrifuge
CalculiX à trois maillages. Elle garde ses hypothèses distinctes des données
du spécimen.

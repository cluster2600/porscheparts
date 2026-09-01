# Ligne directrice titane

## Position du projet

Le matériau de référence pour LPBF est **Ti-6Al-4V Grade 5**. Le Grade 23 ELI est
réservé aux cas où ductilité ou ténacité justifient son coût. Le choix final doit
correspondre au procédé qualifié du fabricant, pas seulement à une désignation
commerciale de poudre.

## Quand le titane est pertinent

- Réduction de masse sur une pièce métallique complexe
- Corrosion problématique avec la matière d’origine
- Consolidation de plusieurs composants
- Conduits ou formes internes impossibles à usiner
- Petite série où l’outillage traditionnel domine le coût

## Quand il ne l’est pas

- Plaque, axe, entretoise ou bride simple facilement usinable
- Besoin important de conductivité thermique
- Pièce dont la flexion doit rester identique à une pièce acier
- Contact glissant non traité ou filetage répété exposé au grippage
- Environnement créant un couple galvanique non maîtrisé avec aluminium ou magnésium

## Le critère vaut au-delà du titane

La même grille décide de l'emploi de la fabrication additive en général. Elle
gagne sur trois familles de cas :

- **les passages internes inusinables** — le piston LPBF développé par Porsche
  avec MAHLE et TRUMPF porte un conduit de refroidissement fermé qu'aucune
  fonderie classique ne noyaute ;
- **les fonderies impossibles à noyauter autrement**, désormais accessibles par
  noyaux imprimés en sable, qui est de l'additif appliqué à l'outillage et non
  à la pièce ;
- **la consolidation**, quand un sous-ensemble de dizaines de pièces devient une
  seule.

Une pièce qui ne relève d'aucune de ces trois familles n'a rien à gagner à être
imprimée, quelle que soit sa matière. Le berceau moteur du 993 en est
l'illustration : lame monobloc, sans canal interne, sans sous-ensemble à
consolider — voir `parts/993-eng-carrier-0001/evidence/load-cases.md`.

Les noyaux imprimés méritent en revanche d'être gardés en tête pour ce projet :
ils ouvrent la petite série fondue sans modèle ni outillage, ce qui est le verrou
habituel de la reproduction de pièces classiques. La presse technique les décrit
d'ailleurs comme décisifs pour les « moteurs anciens dont les modèles de fonderie
n'existent plus ».

## Le coût réel d'une pièce métallique imprimée

Une pièce LPBF n'est pas finie quand elle sort de la machine. La chaîne
couramment décrite est : traitement thermique, **compression isostatique à chaud
pour refermer la porosité**, finition de surface, grenaillage et lissage
chimique — parce que la rugosité brute **dégrade la tenue en fatigue** — puis
**usinage des surfaces fonctionnelles** aux tolérances. Le contrôle ajoute
tomographie, essai de pression et scan laser après usinage.

Autrement dit, une pièce imprimée destinée à durer est aussi une pièce usinée.
Ce n'est pas un argument contre l'additif : c'est ce qui doit entrer dans la
comparaison de coût, et ce qui explique qu'une géométrie simple soit rarement
rentable à imprimer.

## Progression recommandée

Commencer par le polymère, pour les gabarits et les vérifications d'interface.
Passer ensuite aux noyaux de fonderie imprimés, qui restent dans un procédé
connu. N'aborder le métal qu'ensuite, chez un prestataire fournissant
documentation complète, tomographies et certificats de post-traitement.

C'est exactement l'ordre des phases 2 et 3 de ce projet.

## Dossier minimal du fabricant

- `STEP` maître et plan PDF avec révision
- Ti-6Al-4V et standard demandé
- Procédé LPBF et machine qualifiée
- Orientation proposée et stratégie de supports
- Surépaisseurs d’usinage
- Détensionnement et traitement thermique sous atmosphère maîtrisée
- HIP requis, optionnel ou non pertinent avec justification
- Zones à polir ou grenailler
- Filetages et alésages usinés
- Contrôle dimensionnel et non destructif
- Certificat matière, identification du lot et traçabilité du job

## Risques spécifiques

### Fatigue

Rugosité, pores, orientation et concentration de contraintes dominent souvent la
durée de vie. Une résistance statique élevée ne suffit pas. Pour une pièce cyclée,
prévoir surfaces critiques finies, rayons, HIP si pertinent et essais représentatifs.

### Déformation et anisotropie

Le modèle doit intégrer orientation, supports, détensionnement et usinage. Les
propriétés d’une éprouvette générique ne remplacent pas celles du couple
machine-poudre-paramètres utilisé.

### Grippage

Éviter les filetages titane-titane sollicités fréquemment. Prévoir inserts,
revêtements, lubrifiant compatible ou couple de matériaux adapté.

### Corrosion galvanique

Documenter rondelles isolantes, revêtement, mastic ou drainage lorsque le titane
est assemblé à l’aluminium ou au magnésium.

## Porte de libération

Une pièce titane ne peut atteindre `released` sans :

1. prototype ajusté ;
2. justification du choix titane ;
3. revue DfAM ;
4. traçabilité de fabrication ;
5. contrôle dimensionnel ;
6. inspection adaptée au risque ;
7. essai documenté ;
8. limites d’utilisation publiées.

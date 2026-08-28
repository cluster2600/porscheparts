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

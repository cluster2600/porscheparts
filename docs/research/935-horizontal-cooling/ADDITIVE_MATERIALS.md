# Aluminium, magnésium et titane pour les versions imprimées

Le 3 octobre 2026, le propriétaire a fixé trois familles candidates pour les
pièces améliorées des deux programmes : **aluminium, magnésium ou titane en
fabrication additive métallique**. Chaque pièce aura son propre choix matière
et procédé. La matière historique reste documentée dans [MATERIALS.md](MATERIALS.md).

## Trois candidats de départ

| Candidat | Procédé à étudier | Données disponibles et travail restant |
|---|---|---|
| Aluminium AlSi10Mg | Fusion laser sur lit de poudre, LPBF | Fiches industrielles EOS par machine et paramétrage. Base proposée pour la première étude imprimable du rotor, du support et du carter ; aucun choix final. |
| Magnésium WE43 | LPBF sur une installation et un procédé adaptés au magnésium | Impression démontrée dans des études expérimentales et poudre additive documentée. Identifier un atelier acceptant nos dimensions et fournissant des résultats sur son propre procédé. |
| Titane Ti-6Al-4V, Ti64 | LPBF | Fiches industrielles EOS disponibles. Comparer le rotor et les pièces de support avec une géométrie redimensionnée ; sa résistance ne garantit pas un gain de masse. |

Sources primaires : [EOS AlSi10Mg, données par procédé](https://www.eos.info/metal-solutions/data-sheets/all-processes-and-materials?id=eos-aluminium-alsi10mg),
[EOS Ti64, données par procédé](https://www.eos.info/metal-solutions/data-sheets/all-processes-and-materials?id=eos-titanium-ti64),
[Julmi et al., 2021, expériences LPBF WE43](https://pmc.ncbi.nlm.nih.gov/articles/PMC7918529/),
[Luxfer, poudre Elektron MAP+43, fiche 2018](https://luxfermagtech.com/wp-content/uploads/2020/03/Luxfer-Data-Sheets-Elektron-MAP43.pdf).
La fiche poudre prouve l'existence d'une offre décrite ; elle n'établit ni un
stock actuel, ni un prestataire, ni un procédé qualifié pour notre rotor. Les
éprouvettes de recherche ne qualifient pas un ventilateur tournant.

## Comparer la masse sans présumer du résultat

Les fiches EOS M 290 à couches de 30 µm donnent des densités moyennes au moins
égales à 2,67 g/cm³ pour l'AlSi10Mg et 4,4 g/cm³ pour le Ti64. La densité de
référence de l'alliage magnésium [WE43C / Elektron 43](https://www.luxfermeltechnologies.com/elektron-43/)
est d'environ 1,83 g/cm³ pour le produit corroyé ; ce n'est pas une mesure de
notre pièce imprimée. Les densités apparente et tassée de la poudre sont
distinctes de la densité du métal consolidé.

À volume égal, ces repères rendent le magnésium plus léger et le titane plus
lourd que l'aluminium. C'est une comparaison de densités, pas un gain annoncé
pour le système. Comparer ensuite deux niveaux : géométrie commune pour
isoler l'effet de matière ; géométries redimensionnées respectant les mêmes
charges, jeux, rigidité et critères de fatigue. La masse des inserts,
revêtements, fixations et roulements compte dans le bilan complet.

## Dossier d'impression et calculs par variante

Les études doivent lier chaque résultat à la géométrie, à l'alliage, à la
machine, au paramétrage, à l'orientation, à l'épaisseur de couche, aux supports,
à la poudre et aux traitements. Les fiches matière doivent porter sur le
procédé réellement utilisé. Une propriété du magnésium coulé ou de
l'aluminium 7075 usiné n'est pas une propriété de notre pièce LPBF.

Comparer masse, inertie, contraintes centrifuges, déformation des pales,
modes de vibration et fatigue, puis débit–pression–puissance pour chaque
géométrie. Le choix final doit intégrer températures, rugosité des pales,
retouches de portées et alésages, inspection, équilibrage et essais.

Pour les variantes titane, le dossier inclura explicitement nuance, procédé,
orientation, traitement thermique, usinage, inspection, hypothèses de fatigue
et isolation galvanique aux interfaces avec aluminium ou magnésium. Les
variantes magnésium doivent documenter leur protection de surface et les
interfaces entre métaux. Aucun fournisseur ni devis n'est encore retenu.

La voie aluminium est une recommandation de départ, motivée par la présence
de données industrielles et du scénario AlSi10Mg existant. La comparaison
reste ouverte au magnésium et au titane. Le
[rapport comparatif exécuté](../../../twins/fan-alloy-comparison-f0/README.md)
documente trois calculs centrifuges sur le modèle paramétrique 993 et le
blocage de la reconstruction volumique du scan 935. Aucune variante n'est
imprimée ou qualifiée sur le moteur.

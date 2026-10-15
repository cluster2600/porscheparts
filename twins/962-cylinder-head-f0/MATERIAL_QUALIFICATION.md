# Culasse à eau : données matière avant CHT et fatigue

**Aucune nuance ni recette n'est qualifiée pour notre culasse.** Le travail
compare CP1 et CuCrZr ; le choix dépend du transfert thermique **et** de la
tenue de l'ensemble sièges/guides/goujons à chaud. Une conductivité élevée
ne remplace pas ces contrôles.

## Vérification des sources le 12 octobre 2026

La [page Constellium actuelle](https://www.constellium.com/products/aluminium-powders/)
positionne CP1 (Al–Zr–Fe, AA8A61.50) pour la conductivité et HT1
(Al–Mn–Ni–Cu–Zr, AA8A81.50) pour la tenue à température et la résistance.
Cette distinction motive une comparaison si CP1 échoue à chaud ; la page ne
donne pas d'allowables pour notre culasse. La valeur CP1 de 187 W/m·K du
[dossier initial](README.md#matière--conductivité-et-tenue-à-chaud) reste une
mesure à température ambiante, pas une loi k(T).

La [fiche EOS CuCrZr](https://www.eos.info/var/assets/05-datasheet-images/Assets_MDS_Metal/EOS_CopperAlloy_CuCrZr/Material_DataSheet_EOS%20_Copper_CuCrZr_en.pdf?v=11),
pages PDF 5–7, sépare deux traitements pour M400-1, couches de 80 µm.
Le PDF téléchargé a la même empreinte que la référence initiale :
`274737eccc264b900ce8136bb5c3d786bea05378bccf2dd15dda70e53273f6c3`.

| Recette EOS M400-1 | Traitement publié | Rp0,2 vertical publié | Conductivité électrique publiée |
|---|---|---:|---:|
| Favorisant la conductivité | 550 °C, 3 h, atmosphère inerte | 230 MPa | 88 % IACS |
| Favorisant la traction | 490 °C, 1 h, atmosphère inerte | 495 MPa | 76 % IACS |

Ces résultats sur éprouvettes ne sont pas des limites de fatigue à chaud.
Ne pas attribuer 495 MPa et 88 % IACS à une même recette. L'IACS mesure
l'électricité : la fiche ne fournit pas une courbe de conductivité thermique
pour le calcul CHT. Les pages 9–10 décrivent un autre système M290 1 kW ;
ses données ne doivent pas être mélangées à celles du M400-1.

La paroi minimale de procédé annoncée sur la page 5 ne devient pas une
épaisseur de culasse résistant à la combustion. La conductivité de 340 W/m·K
citée dans le résumé de recherche initial ne qualifie pas davantage la
recette de notre fournisseur.

## Données à acquérir sur le procédé retenu

| Fonction | Données requises, encore absentes | Condition de comparaison |
|---|---|---|
| CHT | k(T), capacité thermique, densité, état de surface des canaux | Même lot/procédé, orientation et traitement ; domaine thermique défini par le calcul puis le banc |
| Contraintes thermiques | Dilatation, module et plasticité en fonction de T | Même état métallurgique et historique thermique que la pièce |
| Durée de vie | Fatigue thermomécanique, relaxation/fluage, dispersion et défauts | Cycle de température/pression moteur identifié, pas uniquement traction à froid |
| Sièges et guides | Emmanchement et pression de contact à chaud, dilatations des deux matériaux | Pièces fournisseurs exactes, tolérances et essais de maintien après cyclage |
| Eau et huile | Corrosion, compatibilité liquide, étanchéité et porosité | Liquide réel et températures retenues ; vieillissement et nettoyage du circuit |
| LPBF des canaux | Rugosité, dépowdering, résidus, dérive dimensionnelle et défauts CT | Coupons reprenant orientation, sections et jonctions du futur dessin |

Ne pas fixer maintenant une température de service du métal à partir de la
seule température du liquide. Les températures locales sont des résultats
CHT à corréler au banc. Pour les inserts CuCrZr dans CP1, ajouter résistance
thermique de contact, assemblage, dilatation différentielle et corrosion
galvanique ; aucun bénéfice multi-matériau n'est acquis.

## Comparaison à réaliser

Comparer CP1 et CuCrZr sur la **même géométrie et les mêmes conditions** avec
les lois propres à chaque recette. Conserver débit, perte de charge,
températures locales, masse et contraintes/fatigue comme résultats distincts.
Évaluer ensuite l'optimisation de canaux à débit ou puissance de pompage
comparables ; ne pas confondre gain matière et gain hydraulique.

Les coupons et épreuves sont à définir et approuver avec le motoriste et le
fabricant avant exécution. Aucun paramètre d'impression, pression d'épreuve,
durée de vie ou réduction d'épaisseur n'est autorisé par cette fiche.

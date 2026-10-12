# Exemples de turbomachines conçues avec PicoGK

Recherche du **10 octobre 2026** pour poursuivre le
[turbo bionique conceptuel à 39 composants](../assembly/README.md).
Deux projets publics fournissent du code proche de nos côtés froid et chaud :
**QUASAR Phy-CC** et **QUASAR Phy-CT**. Les modèles LEAP 71 complètent ces
références avec des roues téléchargeables et des turbopompes en développement.

Les sources examinées ne démontrent pas un **turbo automobile complet PicoGK,
fabriqué et essayé**. Cette conclusion porte sur cette recherche, pas sur
l'existence éventuelle d'autres prototypes. Une turbine, un compresseur ou
une turbopompe ne constituent pas à eux seuls un turbo automobile complet.

## Comparaison des exemples

| Exemple | Éléments utiles | Disponibilité et licence | Preuve disponible |
|---|---|---|---|
| [QUASAR Phy-CC](https://github.com/QU01/Quasar-Phy-CC) | Roue centrifuge, entrée, diffuseur, volute creuse et sortie tangentielle | C# PicoGK ; Apache-2.0 | Code et comparaisons numériques aux données publiées ; pas d'essai physique propre au projet établi |
| [QUASAR Phy-CT](https://github.com/QU01/Quasar-Phy-CT) | Roue de turbine radiale centripète, distributeur éventuel, volute, diffuseur et tronçon d'arbre | C# PicoGK ; Apache-2.0 | Code, provenance des cas de comparaison et limites déclarées ; pas de turbo automobile assemblé essayé établi |
| [Roues LEAP 71 à inducteur intégré](https://leap71.com/downloads/) | Trois roues de turbomachines ; intérêt visuel et géométrique | STL ; CC BY-SA 4.0 ; générateur absent de cette page | La galerie présente des roues imprimées ; aucune qualification en fonctionnement de ces trois fichiers établie |
| [Turbopompe LEAP 71 pour moteur méthane/LOX de 28 kN](https://www.linkedin.com/posts/leap71_we-are-making-progress-in-building-an-integrated-activity-7313126036693524481-oYCQ) | Pompe LOX, générateur de gaz, turbine et échappement | Développement Noyron ; code de conception propriétaire | Publication décrivant un travail en cours et des essais à chaud futurs |

## 1. QUASAR Phy-CC : référence pour le côté froid

Auteur : Quasar Solutions Lab, compte GitHub `QU01`. Version examinée :
`fd2b4f2066176265d77bfaa860bda7030578ffc6`.

Le [générateur principal](https://github.com/QU01/Quasar-Phy-CC/blob/fd2b4f2066176265d77bfaa860bda7030578ffc6/CompressorDesigner/src/CompressorDesigner/CentrifugalCompressor.cs)
sépare le rotor et le carter. Les sources décrivent notamment les pales
principales et secondaires, le passage méridien, le diffuseur sans aubes et
la volute. Ce sont les éléments à comparer avec notre géométrie actuelle.
Le [projet](https://github.com/QU01/Quasar-Phy-CC/blob/fd2b4f2066176265d77bfaa860bda7030578ffc6/CompressorDesigner/src/CompressorDesigner/CompressorDesigner.csproj)
cible .NET 9 pour Windows avec PicoGK 2.2.0. Notre assemblage utilise PicoGK
2.3.0 sur macOS : la compatibilité n'a pas été essayée.
La [licence Apache-2.0](https://github.com/QU01/Quasar-Phy-CC/blob/fd2b4f2066176265d77bfaa860bda7030578ffc6/LICENSE)
du code est vérifiée à cette révision.

Le [rapport numérique](https://github.com/QU01/Quasar-Phy-CC/blob/fd2b4f2066176265d77bfaa860bda7030578ffc6/validation/RESULTS.md)
compare un modèle moyen unidimensionnel au rotor Eckardt O : le rapport de
pression présente un écart de +0,22 %, tandis que le rendement présente
**+2,7 points**, en échec selon son propre seuil de 2 points. Le rapport
signale aussi une différence de longueur de diffuseur. Son cas interne
REF_PR5 est une référence de régression, pas une mesure indépendante.
Le [plan de validation](https://github.com/QU01/Quasar-Phy-CC/blob/fd2b4f2066176265d77bfaa860bda7030578ffc6/docs/VALIDATION.md)
place la réalisation d'un banc propre au projet parmi les objectifs à moyen terme.

## 2. QUASAR Phy-CT : référence pour le côté chaud

Même auteur. Version examinée : `fd9d78f6cccca0850273884e31faec7632810842`.
Le [générateur principal](https://github.com/QU01/Quasar-Phy-CT/blob/fd9d78f6cccca0850273884e31faec7632810842/RadialTurbineDesigner/src/RadialTurbineDesigner/RadialTurbine.cs)
et le [générateur de roue](https://github.com/QU01/Quasar-Phy-CT/blob/fd9d78f6cccca0850273884e31faec7632810842/RadialTurbineDesigner/src/RadialTurbineDesigner/RadialWheel.cs)
constituent des références directes pour notre turbine et sa volute.
La [licence du code est Apache-2.0](https://github.com/QU01/Quasar-Phy-CT/blob/fd9d78f6cccca0850273884e31faec7632810842/LICENSE).

Le [README de cette révision](https://github.com/QU01/Quasar-Phy-CT/blob/fd9d78f6cccca0850273884e31faec7632810842/README.md)
décrit des contrôles d'intersection sur l'assemblage complet à 360° et des
comparaisons à des données publiées. Nous ne les avons pas reproduits.
Les géométries CT-3 et CT-4 sont mises à l'échelle, pas indépendamment
mesurées ; l'export TurboGrid reste non vérifié et les pales STEP sont des
surfaces, pas des solides fermés. Le projet déconseille la calibration
avec les observations disponibles. Le tableau des cas comprend quatre
cas NASA et un cas Imperial College conditionnel, malgré une formulation
plus large dans son introduction.

Le [manifeste de données](https://github.com/QU01/Quasar-Phy-CT/blob/fd9d78f6cccca0850273884e31faec7632810842/validation/data/MANIFEST.json)
et le [cas CT-1 avec provenance](https://github.com/QU01/Quasar-Phy-CT/blob/fd9d78f6cccca0850273884e31faec7632810842/validation/data/ct1_tp1730.json)
méritent une revue avant toute reprise de paramètres. Ce projet ne fournit
pas notre corps central complet avec paliers, joints et wastegate.

## 3. LEAP 71 : roues disponibles et turbopompes en développement

[Voir l'illustration officielle des trois roues LEAP 71 à inducteur intégré](https://i0.wp.com/leap71.com/wp-content/uploads/2025/07/62BA1CA0-1871-4129-A387-7C3C7A34477C-1.jpg?resize=1080%2C608&ssl=1).

La [page de téléchargement](https://leap71.com/downloads/) propose trois
roues au format STL, avec une archive annoncée de 170 Mo. Elle relie ces
modèles à Noyron et PicoGK. La [galerie](https://leap71.com/gallery/)
présente des roues imprimées ; cela ne prouve pas les performances des
trois modèles téléchargeables. L'archive STL n'a pas été téléchargée ni inspectée.

La [publication sur la turbopompe de 28 kN](https://www.linkedin.com/posts/leap71_we-are-making-progress-in-building-an-integrated-activity-7313126036693524481-oYCQ)
montre une intégration plus avancée de composants, encore en développement.
La [description officielle de Noyron](https://leap71.com/Noyron/) précise sa
relation au noyau PicoGK. **L'ouverture du noyau géométrique ne donne pas
accès au modèle d'ingénierie Noyron, qui reste propriétaire.**

Les modèles téléchargeables sont proposés sous
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
L'illustration reste liée sur le site de LEAP 71 : aucune copie n'est intégrée
ici, car la portée de cette licence sur cette image de présentation n'est pas
établie. Cette illustration n'est pas une preuve de fabrication ou d'essai.

## Application à notre projet

1. Comparer les passages méridiens, angles de pales, diffuseur et loi de
   section de volute de Phy-CC à notre côté froid ; documenter les écarts
   avant d'adopter du code ou des paramètres.
2. Comparer le passage chaud et la loi de volute de Phy-CT ; examiner ses
   contrôles de l'assemblage complet. Un contrôle à 360° ne suffit pas à
   établir les jeux en rotation et à chaud.
3. Définir les conditions de service communes aux deux roues et relever
   les interfaces du corps central, paliers, joints et retenues. Les
   valeurs inconnues restent à `null` ; aucune valeur par défaut d'un
   exemple ne devient une cote mesurée de notre turbo.

La priorité proposée est **QUASAR pour étudier le code des deux côtés**, et
**LEAP 71 pour les exemples de formes et de fabrication**. Assembler deux
générateurs ne démontre ni leur appariement aérodynamique ni leur capacité
à partager le même arbre et le même régime.

## Périmètre de la recherche

Recherche ciblée sur PicoGK, turbocharger, compressor, turbine, impeller,
volute et LEAP 71 ; examen des pages officielles et de sources C# épinglées.
Les résultats relatifs au ventilateur de refroidissement Porsche de notre
propre projet ont été exclus des exemples indépendants de turbo.
Aucun code tiers n'a été exécuté, aucune simulation reproduite, et aucun
modèle externe n'a été intégré à l'assemblage. Ce dossier ajoute uniquement
de la documentation et des liens ; les sources et preuves
de géométrie existantes restent inchangées.

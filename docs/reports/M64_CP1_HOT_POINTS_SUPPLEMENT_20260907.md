# CP1 — complément ciblé : un point à chaud et des coefficients de dilatation

Recherche du 7 septembre 2026, indépendante du relevé précédent. Aucun paramètre
de solveur modifié, aucune courbe interpolée, aucune qualification matériau.

## 1. Un véritable point de traction à 200 °C

La présentation **Constellium / C-TEC, Formnext 2021, diapositive 9** distingue
explicitement le traitement **1 h à 400 °C** de l'essai **à 200 °C**. Procédé
indiqué : EOS M290, couches 60 µm, éprouvette verticale.

| Température d'essai | Limite élastique YS | Résistance UTS | Allongement |
|---|---:|---:|---:|
| 200 °C | **126 MPa** | **149 MPa** | **17,0 %** |

La même page donne une dilatation de **25,19 × 10⁻⁶ K⁻¹ sur 20–200 °C**,
mais ne rattache pas ce coefficient à un état de traitement précis. La table
et ses en-têtes ont été contrôlés visuellement dans le PDF rendu. Le document
public porte un marquage de confidentialité : aucun PDF ni image n'est ajouté
au dépôt, seulement ces faits et leur provenance.

Source primaire : [Shahani et Chehab, Constellium, Formnext 2021, p. 9](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/41170/2021-11-8_constellium_aheadd_formnext_final.a0a8c4307e76.pdf).

Les informations absentes restent absentes : norme de traction, décalage de
preuve de YS, vitesse de déformation, maintien à la température d'essai,
effectif, dispersion et état de surface. **126 MPa n'est pas automatiquement
Rp0,2, une contrainte admissible, ni la valeur du traitement 4 h.**

## 2. Une fiche fabricant plus récente avec trois intervalles thermiques

La fiche de procédé **EOS Aluminium Constellium CP1 / M290 / 60 µm**, affichée
à l'état du **04.09.2026**, identifie le jeu `AlCP1_060_M291`, niveau **TRL 3**,
plateau 125 °C et argon. Elle publie :

| Intervalle de température | Coefficient de dilatation publié |
|---|---:|
| 25–100 °C | **19 × 10⁻⁶ K⁻¹** |
| 25–200 °C | **21 × 10⁻⁶ K⁻¹** |
| 25–300 °C | **22 × 10⁻⁶ K⁻¹** |

Les propriétés de traction de cette fiche restent **à température ambiante**.
La section dilatation ne précise pas son état thermique, l'orientation, la
norme ou les incertitudes. La page HTML primaire a été archivée et hachée en
privé ; son lien de génération PDF a retourné HTTP 500.

Source primaire : [EOS, fiche CP1 M290 / 60 µm](https://www.eos.info/metal-solutions/data-sheets/aluminium/pds-eos-aluminium-constellium-cp1-eos-m-290-60um).

## Conséquences pour les futurs calculs M64

Le manque documentaire est réduit, pas résolu : le CP1 dispose maintenant dans
notre relevé d'**un point de traction explicitement à chaud** et de **quatre
coefficients sur intervalles**. Ils ne forment pas une loi matériau complète.

- Les valeurs de dilatation décrivent des intervalles, pas des valeurs
  instantanées d'α(T) à leurs bornes. Ne pas injecter leurs trois nombres comme
  une courbe différentielle dans un solveur.
- Les valeurs 2021 et EOS ne doivent pas être fusionnées : états non précisés,
  intervalles différents et valeurs sensiblement différentes.
- Aucune nouvelle loi **k(T)** ou **Cp(T)** vérifiée n'a été trouvée dans les
  documents retenus. Une conductivité électrique n'est pas substituée à une
  mesure thermique ; le vieillissement n'est pas assimilé à un essai à chaud.
- Les propriétés complémentaires à chaud et les données cycliques nécessaires
  au modèle mécanique restent manquantes. Le point à 200 °C ne justifie aucune
  extrapolation au point chaud de la future culasse turbo.

Les fiches Nikon `MDS_Aheadd CP1_2024-11.2_EN` et Velo3D du 16 février 2024
ont également été lues : elles détaillent des recettes et des essais ambiants,
mais n'ajoutent pas de loi à chaud à ce complément.
[Nikon](https://nikon-slm-solutions.com/wp-content/uploads/2024/11/mds5144.pdf),
[Velo3D](https://velo3d.com/wp-content/uploads/2025/04/Velo3D-Material-Datasheet-Aluminum-CP1.pdf).

Relevé machine, conditions et inconnues :
[cp1-hot-points-supplement-20260907.json](../../twins/m64-cylinder-head/cp1-hot-points-supplement-20260907.json).

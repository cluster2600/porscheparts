# Donnees de calcul d'ecoulement du 993 Turbo

Collecte etat au 30 aout 2026. Ce document prepare une simulation du circuit
d'air du 993 Turbo. Il ne declare ni une geometrie K16 exacte, ni une
performance mesuree, ni une piece fabricable.

## Conclusion de la collecte

Le dossier est suffisant pour lancer une etude exploratoire du debit moteur et
des pertes de charge d'un conduit cote froid. Il n'est pas suffisant pour
simuler fidelement la roue K16, calculer sa vitesse, predire le rendement ou
concevoir une roue de remplacement.

La lacune principale reste la meme apres la recherche en allemand et la
consultation de Porsche Fanatics : aucune carte compresseur/turbine K16
publique exploitable, aucun profil d'aube, aucun jeu interne, aucune courbe de
rendement et aucune mesure de perte de charge de l'echangeur n'ont ete trouves.

## Hierarchie des preuves

| Niveau | Source | Ce qu'elle permet d'affirmer | Ce qu'elle ne permet pas d'affirmer |
| --- | --- | --- | --- |
| A | [Porsche Christophorus](https://newsroom.porsche.com/christophorus/fr/2020/394/turbo-engines.html) | Architecture biturbo parallele, 3 600 cm3, 0,8 bar, 408 ch, 540 Nm | Carte K16, CAO, materiaux, pertes |
| A | [Porsche Austria PET, planche 107-45](https://www.porsche.at/media/Kwc_Basic_DownloadTag_Component/4740-45397-124814-downloadTag/default/f5000535/1729608718/kat017-d-911-98-katalog.pdf) | References, quantites, joints, colliers et interfaces a rechercher | Cotes de passage, tolerances, epaisseurs, CAO |
| B | [BorgWarner Performance Catalog](https://www.borgwarner.com/docs/default-source/iam/boosting-technologies/bw_turbo-performance-catalog.pdf) | Association K16-6735 + K16-6736, puissance catalogue et limites commerciales | Limite admissible d'une piece additive, carte aero |
| C | [FVD](https://www.fvd.net/de/shop/turbolader-k16-rechts-993-serie-99312301452-993123014dx~p239094), [Invasion Auto Products](https://www.invasionautoproducts.com/94pocark16tu.html), [TurboMaster](https://www.turbomaster.com/eng/turbo/borgwarner/5316-988-6735/) | References, dimensions et diametres declares par vendeurs | Mesure independante, profil de roue, tolerance |
| C | [elferclassic](https://www.elferclassic.de/technik/techdaten/993-turbo-95-98-techdat.php) | Points moteur et regime de reference | Debit d'admission reel et courbe de boost |
| derive | Calculs de ce document | Enveloppes de debit avec hypotheses explicites | Donnee Porsche mesuree |

Les fiches detaillees sont dans `catalog/sources/`. Les valeurs de masse et
d'encombrement retenues sont dans
`catalog/reference/993-declared-part-data.json` avec le statut `declared`.

## Identification du systeme

### Turbocompresseurs

- Porsche decrit deux petits turbocompresseurs en parallele, chacun alimentant
  un banc de cylindres, avec deux echangeurs air-air.
- Le catalogue BorgWarner identifie la paire d'origine comme **K16-6735 +
  K16-6736** pour le 911 Turbo 993 3.6. Il annonce 408 hp d'origine et une
  limite commerciale de turbo d'origine de 500 hp. La ligne d'upgrade annonce
  les K24 5324 988 7003/7004 et 555 hp.
- La documentation publique retrouvee identifie la famille **KKK / BorgWarner
  / 3K-Schwitzer**. Garrett n'est pas confirme par les sources consultees ; il
  ne faut pas renommer le turbo Garrett sans plaque signaletique ou source
  primaire.
- Une fiche fournisseur identifie le K16 droit comme BorgWarner
  `5316-988-6735`, Porsche `993 123 014 51/52`, CHRA `5316-710-0520` et modele
  `K16-2467GGA/8.88`. L'attribution gauche/droite du `6736` reste a confirmer
  sur une piece.

### Nomenclature de sous-ensembles recueillie

La page TurboMaster du `5316-988-6735` fournit des identifiants de catalogue
pour le CHRA et les sous-ensembles :

| Sous-ensemble | Reference publique |
| --- | --- |
| CHRA | `5316-710-0520` |
| Carter de palier | `5316-151-0002` |
| Back plate | `5314-151-5702` |
| Ecran thermique | `5316-165-2000` |
| Collier de poussee | `5314-127-0400` |
| Entretoise | `5314-127-0500` |
| Carter compresseur | `5324-101-5320` |
| Carter turbine | `5316-100-9050` |
| Roue turbine | `5316-120-5000` |
| Roue compresseur | `5324-123-2006` |
| Actionneur | `5825-110-4006` |
| A/R turbine declare | `8.00` |

Invasion Auto Products declare pour le K16 droit :

| Element | Valeur declaree | Limite |
| --- | ---: | --- |
| Roue turbine, inducer | 54,96 mm | Diametre fournisseur, profil inconnu |
| Roue turbine, exducer | 48,97 mm | Diametre fournisseur, profil inconnu |
| Roue turbine, trim | 6,45 | Convention fournisseur a confirmer |
| Roue turbine | 12 pales | Profil, epaisseur et angle inconnus |
| Roue compresseur, inducer | 40,6 mm | Diametre fournisseur, profil inconnu |
| Roue compresseur, exducer | 60,5 mm | Diametre fournisseur, profil inconnu |
| Roue compresseur | 6 + 6 pales, billet | Materiau et profil non documentes |
| Carter compresseur, angle alpha | 307,5 deg | Reference fournisseur seulement |
| Carter turbine, angle beta | 70 deg | Reference fournisseur seulement |
| Wastegate | 0,50 bar | Regime de reglage declare, pas loi de commande |
| Levee de tige | 4,20 mm | Mesure/protocole non fournis |

Ces nombres ne definissent pas une roue parametrique : une roue necessite les
surfaces completes, les angles locaux, les epaisseurs, le moyeu, les rayons,
les jeux et la loi de fabrication.

## Circuit d'air et interfaces OEM

Le chemin a modeliser en premier est :

```text
filtre / debitmetre HFM -> separation des bancs
    -> K16 gauche -> durite -> echangeur gauche ->
                                                     reunion -> papillon
    -> K16 droit  -> durite -> echangeur droit  ->     -> collecteur plastique
```

Le PET Porsche de la planche 107-45 confirme les references suivantes pour le
circuit de charge :

- echangeur : `993 110 330 53` ;
- conduits d'air : `993 110 340 53` et `993 110 340 54` ;
- supports : `993 110 110 50` et `993 110 110 52` ;
- sonde de temperature : `993 606 114 00` ;
- durite gauche : `993 110 633 56` ;
- durite droite : `993 110 632 56` ;
- O-rings : `30 x 3 mm`, reference `999 707 326 40` ;
- colliers : `60-80/12`, reference `999 512 648 02`, et `40-60/9`, reference
  `999 512 647 02` ;
- silentblocs : `930 113 430 00` ; douilles `993 110 111 50` ;
- vis et rondelles a retrouver avant toute CAO d'interface.

Le PET est la meilleure preuve de nomenclature, mais il ne donne pas le
diametre interieur, le rayon de courbure, l'epaisseur, la section de noyau ou
les entraxes complets. Les dimensions ci-dessous restent donc des enveloppes
de produits et des bornes de packaging.

## Dimensions et masses disponibles

| Objet | Dimensions / masse | Statut pour le jumeau |
| --- | --- | --- |
| K16 gauche complet, FVD | `280 x 190 x 210 mm`, `5,76 kg` | Declaration fournisseur, enveloppe seulement |
| K16 droit complet, FVD | `280 x 190 x 210 mm`, `5,60 kg` | Declaration fournisseur, enveloppe seulement |
| Durite pression droite FVD | `430 x 70 x 90 mm`, `0,42 kg` | Remplacement aftermarket |
| Durite pression gauche FVD | `430 x 70 x 115 mm`, `0,42 kg` | Remplacement aftermarket |
| Kit durites renforce FVD | raccord annonce `43/57 mm x 410 mm`; enveloppe `440 x 160 x 100 mm`, `1,08 kg` | Borne de raccordement, pression d'essai non fournie |
| Conduit d'air FVD `993 110 340 54` | `600 x 280 x 50 mm`, `0,9 kg` | Developpement FVD, pas geometrie OEM |
| Support renforce FVD | `255 x 80 x 23 mm`, `0,2 kg` | Upgrade aftermarket, pas qualification structurale |
| Noyau AKS DASIS `177020T` pour `993 110 330 53` | faisceau `260 x 270 x 60 mm`, `7,06 kg` | Noyau aftermarket, pas ensemble complet |
| Module TA Technix `05PO002` | deux modules de faisceau `260 x 260 x 100 mm`; raccords annonces 66 mm exterieur / 68 mm interieur; largeur max 860 mm, hauteur max 240 mm, entraxe 690 mm | Aftermarket, donnees heterogenes a ne pas assembler sans plan |
| Echangeur Motorsport FVD `FVD110330` | `870 x 410 x 190 mm`, `10,1 kg` | Upgrade avec modifications d'installation |
| Ecran thermique gauche FVD | `160 x 110 x 105 mm`, `0,23 kg` | Enveloppe produit, fixations inconnues |
| Sonde `993 606 114 00` FVD | `75 x 35 x 20 mm`, `0,02 kg` | Enveloppe produit, courbe electrique absente |

La masse d'un remplacement, d'un kit ou d'un noyau ne doit jamais etre
additionnee comme masse OEM. Les references source et la qualification sont
conservees dans le registre JSON.

## Forums germanophones

Les forums ont ete recherches separement des sources constructeur. Ils sont
utiles pour trouver des configurations, des pannes recurrentes et des donnees
a demander a un proprietaire, mais leurs messages ne sont pas des mesures
metrologiques par defaut.

| Forum | Information utile | Decision de modelisation |
| --- | --- | --- |
| [PFF, 408/430/450 ch](https://www.pff.de/thread/2651537-993-biturbo-408-430-450-ps-unterschiede/) | Retours indiquant K16 sur 408/430 et K24 sur 450/WLS II, avec modifications ECU/refroidissement | Recoupement de variante uniquement ; ne remplace pas la plaque du turbo ou le VIN |
| [Carpassion, pression affichee](https://www.carpassion.com/forum/thema/26748-ladedruckanzeige/) | Le combiné serait plafonne a 0,8 bar ; des voitures modifiees sont rapportees a 1,3-1,4 bar ; durites et colliers peuvent poser probleme | Le plafond est traite comme une limite d'affichage ; les pressions modifiees sont exclues du cas stock |
| [Motor-Talk, compilation 993 Turbo](https://www.motor-talk.de/forum/993-turbo-fragen-zum-kauf-t1226876.html) | Pistes sur WLS, K16/K24, limites supposees du refroidisseur et du debitmetre | Pistes d'achat/inspection, pas conditions aux limites |

Le signal commun le plus utile est la maintenance du circuit : verifier le
siege des durites, les colliers, les raccords et les fuites avant d'interpreter
une pression faible. Les forums ne fournissent toutefois ni section interne,
ni profil de raccord, ni carte K16, ni debit massique HFM reproductible. Les
valeurs de pression et de puissance de vehicules prepares ne doivent pas etre
injectees dans le jumeau stock.

## Preparateurs et fabricants de turbos

Les preparateurs publient parfois plus de details que les forums, mais il s'agit
de configurations proprietaires et de promesses de performance. Leur valeur
pour le jumeau est de montrer quelles variables ont effectivement ete modifiees
et quelles informations il faut demander.

| Preparateur | Configuration publiee | Donnee utile | Limite |
| --- | --- | --- | --- |
| [FVD](https://www.fvd.net/fr/shop/turbocompr-sport-k16-24-g-pour-993-fvd123013~p262679) | Hybride K16/24 | Inducer compresseur annonce 47,5 mm, carter CNC, backing plate modifie, turbine et palier renforces, equilibriage, adaptateurs d'huile/DME | 555 hp est une cible de kit ; pas de carte ni de profil complet |
| [Cargraphic](https://www.cargraphic.de/en/your-vehicle/for-porsche/for-911/for-993/for-turbo-turbo-s-36l/engine-upgrade-kits-porsche-993-turbo-s-36l/power-kit-2-for-porsche-993-turbo-36l/lkp93t300s2/) | K16/24 special + ECU + echappement + huile | 475 PS / 632 Nm annonces, essais revendiques sur banc RS-Tuning | Feuille de banc, boost, IAT et debit absents |
| [TTP](https://t-t-p.de/motortuning-porsche/) | K16 450 PS, K16 modifie 500 PS, K24 550 PS | Echangeur eau-air integre, refroidissement d'huile, ECU programmable, niveaux 450/580, 500/620 et 550/640 | Chiffres de preparation, sans carte ni protocole de banc |
| [Elferwelt](https://www.elferwelt.de/leistungen/porsche-993-turbo-gt2/) | K16/8055011W, kit 520-540 PS | Partie tournante allegee, optimisation des jeux, equilibriage statique/dynamique, injecteurs matches, DME CC460/OTP | La mention `80er CNC Druckseite` n'est pas une cote definie |
| [TTH](https://www.turbo-technik-hamburg.de/shop/porsche/911/993/436/porsche-911-993-gt2-wls-i-ii-turbo-s-3-6-t-k24-750ps) | K24 avec carter chaud 10 | Extended Tip, carter CNC, turbine retouchee, paliers/capsules renforces, equilibriage annonce jusqu'a 0,05 g | Offre K24 jusqu'a 750 PS avec moteur et logiciel adaptes ; pas K16 stock |
| [9ff](https://www.9ff.com/en/pages/993-konfigurator) | F64 twin turbo 550 avec 2x K24-24.80 | 550 hp / 700 Nm, echangeur eau, grosses conduites, injecteurs, pompe et carter renforces | Conversion complete ; aucune carte ou geometrie de roue |

Deux enseignements sont directement utiles :

1. Les hybrides K16/24 cherchent le compromis reponse bas regime / debit haut
   regime. Ils ne doivent pas etre utilises comme geometrie du K16 d'origine.
2. A partir des niveaux eleves, les preparateurs modifient simultanement
   turbo, echangeur, carburant, ECU, echappement et bas moteur. Il est donc
   impossible d'attribuer un gain de debit ou de temperature au turbo seul.

Les pages de preparateurs ne publient pas les donnees dont nous avons besoin
pour un modele aero : carte compresseur et turbine avec debit corrige, rapports
de pression et ilots de rendement, vitesse d'arbre, T1/T3, pertes de charge,
jeux et profils d'aubes. Une demande technique a leur adresser doit exiger ces
valeurs, les conditions d'essai, l'incertitude et l'autorisation d'utilisation
des donnees.

## Donnees publiques de banc

La recherche a trouve quelques points de banc, mais aucun dossier complet de
calibration. Le registre [`dyno-reference.json`](../simulation/993-turbo-dyno/dyno-reference.json)
conserve les valeurs publiees et leur contexte :

| Cas | Donnees rapportees | Usage retenu |
| --- | --- | --- |
| RUF Turbo R a base K16 | Couple en lb-ft de 2 000 a 6 000 tr/min ; pics annonces 506 hp a 5 500 et 460 hp a 6 000 | Courbe d'ancrage incomplete ; controle de coherence couple/puissance |
| Comparatif RS-Tuning/UMW | K24RS a 522 PS DIN contre K16 Stage 3 a 471 hp sur le meme moteur | Comparaison de niveau, sans points de courbe exploitables |
| Powerhaus K24 | 500 whp et 525 lb-ft a 5 000 tr/min, environ 1 bar rapporte | Point d'ancrage châssis ; puissance aux roues, pas vilebrequin |
| K16 reconstruits / DME Turbo S | 324 whp a 6 000 tr/min et 329 lb-ft a 4 600 tr/min, trois tirets rapportes | Ancrage châssis modifie, sans conversion vilebrequin |
| Cargraphic K16/24 | 475 PS a 6 090 tr/min et 632 Nm a 4 550 tr/min | Cible fabricant, feuille de banc absente |
| AP Car Design K26 | 610 PS et 920 Nm a 4 200 tr/min sur une conversion complete | Borne contextuelle hors K16/K24 |

Le script `scripts/model_turbo_dyno_0d.py` derive pour chaque point la puissance
du couple, le BMEP et une enveloppe de debit par turbo. Il compare aussi les
valeurs puissance/couple publiees au meme regime et signale les discordances.
La sortie est dans `simulation/993-turbo-dyno/derived-dyno-curves.json` et
reste au statut `reference_only` : elle ne fabrique ni carte compresseur ni
calibration CFD.

## Conditions moteur disponibles

| Parametre | Valeur | Nature |
| --- | ---: | --- |
| Cylindres | 6 | Donnee technique secondaire recoupee |
| Cylindree | 3 600 cm3 | Porsche / source technique |
| Alesage x course | `100 x 76,4 mm` | Compilation technique secondaire |
| Rapport volumetrique | `8,0:1` | Compilation technique secondaire |
| Puissance | `408 ch` a `5 750 tr/min` | Porsche |
| Couple | `540 Nm` a `4 500 tr/min` | Porsche |
| Limiteur | `6 720 +/- 20 tr/min` | Compilation technique secondaire |
| Suralimentation maximale publique | `0,8 bar` | Porsche ; pression et lieu de mesure a preciser |
| Mesure de charge | HFM / debitmetre massique | Identification fonctionnelle, calibration absente |
| Ventilateur | `1 210 l/s` a 5 750 tr/min | Refroidissement moteur, **pas debit d'admission** |

Le debit du ventilateur de refroidissement est explicitement exclu comme
condition d'entree du turbo. Il concerne l'air de refroidissement du moteur.

## Premiere enveloppe de debit calculee

Cette section est une derivee reproductible, pas une mesure. Hypotheses du
premier balayage :

- moteur quatre temps de `0,0036 m3` ;
- pression ambiante et entree compresseur : `1,013 bar abs` ;
- pression au collecteur : `0,8 bar` de boost, soit `1,813 bar abs` ;
- temperature apres echangeur : `50 degres C` ;
- rendement volumetrique balaye : `0,85` a `1,00` ;
- partage egal entre les deux bancs ;
- gaz parfait, `R = 287,05 J/(kg K)` ;
- aucune fuite et regime permanent.

La formule est :

```text
Vdot = Vd * N / (2 * 60)
rho = p / (R * T)
mdot_total = rho * Vdot * VE
mdot_banc = mdot_total / 2
```

Avec ces hypotheses, `rho = 1,9545 kg/m3`. Les valeurs obtenues sont :

| Regime | Debit volumique moteur | Debit total, VE 0,85-1,00 | Debit par K16, kg/s | Debit par K16, lb/min |
| ---: | ---: | ---: | ---: | ---: |
| 4 500 tr/min | `0,1350 m3/s` | `0,224-0,264 kg/s` | `0,112-0,132` | `14,8-17,5` |
| 5 750 tr/min | `0,1725 m3/s` | `0,287-0,337 kg/s` | `0,143-0,169` | `19,0-22,3` |
| 6 720 tr/min | `0,2016 m3/s` | `0,335-0,394 kg/s` | `0,168-0,197` | `22,2-26,1` |

Le debit massique est conserve dans le circuit, mais le debit volumique et la
density changent avant et apres le compresseur. La repartition 50/50 est une
hypothese de demarrage : les longueurs, pertes, wastegates et rendements gauche
et droit peuvent la rendre fausse.

Pour une premiere estimation du rapport de pression :

- sans perte entre compresseur et collecteur : `PR = 1,813 / 1,013 = 1,79` ;
- avec une perte provisoire de `0,05-0,20 bar` dans le circuit de charge :
  `PR` devient environ `1,84-1,99`.

La perte `0,05-0,20 bar` est une plage de sensibilite, pas une mesure Porsche.
Avec `T1 = 20 degres C`, un rendement compresseur suppose de `0,65-0,75` et
`gamma = 1,4`, la temperature de sortie compresseur calculee est environ
`91-117 degres C`. Avec une efficacite d'echangeur supposee de `0,60-0,75`, la
temperature apres echangeur serait environ `38-59 degres C`. Ces nombres ne
doivent pas remplacer une sonde avant/apres echangeur.

## Rapport avec le cas OpenFOAM actuel

Le cas
`simulation/993-k16-cold-side-baseline/` est un harnais de regression :

- diffuseur rectangulaire equivalent `50 -> 68 mm` sur `90 mm` ;
- densite imposee `1,2 kg/m3` ;
- vitesse imposee `40 m/s` ;
- debit derive `0,09425 kg/s` ;
- pas de roue, CHRA, wastegate, echangeur reel ou geometrie K16.

Ce debit est volontairement synthetique et se situe sous l'enveloppe
calculee par K16 dans les hypotheses ci-dessus. Il ne faut pas le remplacer
silencieusement : il sert a verifier la chaine OpenFOAM et les comparaisons
relatives. Le prochain cas physique devra imposer un debit par banc justifie et
une geometrie dont les sections sont connues.

Trois variantes de sensibilite sont maintenant materialisees dans
`simulation/993-turbo-variants/` : `K16-OEM`, `K16-24-HYBRID` et
`K24-REFERENCE`. Elles utilisent le meme debit derive de `0,156 kg/s` par
turbo, a densite constante, afin de comparer uniquement des enveloppes froides
synthetiques. Les vitesses d'entree changent avec la section. Le manifeste
attache les sources FVD, Cargraphic, TTP, TTH, Elferwelt et 9ff, mais les
objectifs de puissance des preparateurs restent des declarations hors solveur.
Les fichiers sont regenerables avec `make turbo-variants` et controles par
`make turbo-variants-check`.

## Ce qui manque avant un CFD calibre

### Geometrie

- scan ou CAO licencie du turbo droit et gauche ;
- plans de brides, axes, entraxes et datums communs ;
- diametres interieurs et rayons des durites OEM ;
- geometrie des boitiers d'echangeur, ailettes, densite de faisceau et volumes
  morts ;
- papillon, collecteur, repartiteur et sections d'admission ;
- profils complets des roues et diffuseurs.

### Fonctionnement

- courbe boost/regime et pression avant/apres chaque echangeur ;
- debit massique HFM et sa calibration ;
- temperature ambiante, temperature apres compresseur et apres echangeur ;
- efficacite compresseur/turbine et vitesse d'arbre ;
- pression d'entree turbine, temperature T3, contre-pression ;
- loi d'ouverture de wastegate et comportement transitoire ;
- limites surge/choke et donnees de fatigue.

### Validation

Le banc minimal devra mesurer simultanement debit massique, pression et
temperature avant/apres chaque K16 et chaque echangeur. Les points doivent etre
repetes, les instruments et incertitudes enregistres, puis compares au reseau
0D et au CFD 3D. Une photo, un eclate PET ou une fiche vendeur ne remplace pas
ce banc.

## Strategie de simulation

1. **Reseau 0D/1D** : balayer regime, VE, boost, temperature, rendement et
   perte de charge. Le [BorgWarner MatchBot](https://www.borgwarner.com/aftermarket/boosting-technologies/performance-turbochargers/matchbot)
   sert de reference pour les variables d'entree/sortie, mais ne fournit pas
   la carte K16 manquante.
2. **CFD cote froid** : calculer d'abord un conduit, un coude, un raccord ou un
   echangeur dont la geometrie est accessible et licenciee. Comparer perte de
   pression, uniformite de vitesse et separation.
3. **Thermique** : ajouter l'echangeur et son environnement avec des
   temperatures/coefficients mesures ou explicitement balayes.
4. **K16 complet** : seulement apres obtention d'une carte ou de points d'essai
   et d'une geometrie de roue autorisee. Une simulation sans carte produira une
   image ou une extrapolation, pas une prediction credible.
5. **Fabrication** : le turbo, la roue, l'arbre, le CHRA et le carter chaud
   restent bloques par la classe de securite du catalogue. Le premier objet
   doit rester un conduit ou adaptateur froid, non rotatif et non structurel.

## Sources enregistrees

- `SRC-PORSCHE-CHRISTOPHORUS-993-TURBO-DATA`
- `SRC-PORSCHE-AUSTRIA-993-107-45-PET`
- `SRC-PORSCHEFANATICS-993-TURBO-PET`
- `SRC-BORGWARNER-993-K16-PERFORMANCE-CATALOG`
- `SRC-BORGWARNER-MATCHBOT-993-INPUTS-OUTPUTS`
- `SRC-TURBOMAP-COMPRESSOR-MAP-METHODOLOGY`
- `SRC-TURBOMASTER-993-K16-6735-PARTS`
- `SRC-INVASIONAUTOPRODUCTS-993-K16-INTERNAL-DATA`
- `SRC-FVD-993-K16-OEM-DIMENSIONS`
- `SRC-ELFERCLASSIC-993-TURBO-TECHNICAL-DATA`
- `SRC-WS-AUTOTEILE-993-MAF-IDENTIFICATION`
- `SRC-PFF-993-BITURBO-VARIANT-FORUM`
- `SRC-CARPASSION-993-TURBO-BOOST-HOSE-FORUM`
- `SRC-MOTOR-TALK-993-TURBO-FORUM-TECHNICAL-LEADS`
- `SRC-FVD-993-K16-24-SPORT-TURBO-DATA`
- `SRC-CARGRAPHIC-993-K16-24-POWERKIT-DATA`
- `SRC-CARGRAPHIC-993-MOTORSPORT-INTERCOOLER-DATA`
- `SRC-TTP-993-TURBO-TUNING-STAGES`
- `SRC-ELFERWELT-993-K16-8055011W-KIT`
- `SRC-TTH-993-K24-750-TURBO-PROCESSING`
- `SRC-9FF-993-F64-K24-550-DATA`
- `SRC-RENNLIST-993-RUF-TURBO-R-ENGINE-DYNO`
- `SRC-RENNLIST-993-K16-K24-COMPARATIVE-ENGINE-DYNO`
- `SRC-RENNLIST-993-POWERHAUS-K24-DYNO`
- `SRC-RENNLIST-993-K16-CHASSIS-DYNO`
- `SRC-AP-CAR-DESIGN-993-K26-DYNO-REPORT`
- sources FVD, AKS DASIS et TA Technix des pieces adjacentes.

# Cas de charge — 993-ENG-CARRIER-0001

Document à remplir **avant** toute géométrie de remplacement. Aucune valeur n'est
pré-remplie : une hypothèse de charge inventée produirait un calcul qui rassure
sans rien prouver.

## 0. Masse et encombrement annoncés — piste à sourcer

| Donnée | Valeur | Lecture |
|---|---|---|
| Masse | 1,96 kg (4,3 lb) | vraisemblablement masse d'expédition, donc pièce plus légère |
| Encombrement | 600 × 50 × 50 mm | vraisemblablement le colis, donc **enveloppe maximale** de la pièce |

Ces deux valeurs ont la forme de données logistiques de revendeur, pas d'un
relevé sur pièce : des cotes de 60 × 5 × 5 cm sont des dimensions de carton, et
une masse d'expédition inclut l'emballage. Elles ne sont donc pas des mesures.

Comme **majorant**, elles restent la première information dimensionnelle du
dossier : la pièce tient dans 600 × 50 × 50 mm.

Recoupement de cohérence : 1,96 kg d'acier représentent environ 250 cm³ de
matière, soit 17 % du volume de cette enveloppe. Compatible avec une lame pliée
ou soudée — ce que le surnom allemand de la pièce, *Schwert*, suggère aussi.

## 1. Ce que la pièce reprend

### Masse du moteur — pesée, source communautaire nommée

Pesées au marbre de pesée par roue, attribuées à Steve Timmins (Instant G),
publiées sur forum. Méthode et périmètre déclarés, ce qui est rare : première
colonne moteur et admission seuls, seconde colonne complet prêt à tourner avec
volant léger, collecteurs et silencieux, sans climatisation.

| Moteur | Moteur + admission | Complet, prêt à tourner |
|---|---:|---:|
| 993 de 1995 (Carrera) | 150,1 kg | 186,9 kg |
| 993 Varioram | 159,2 kg | 195,9 kg |
| **993 GT2 Race** (biturbo) | **154,2 kg** | **195,0 kg** |
| 996 GT3 Cup 2003, pour comparaison | 185,1 kg | 217,7 kg |

Le moteur du Turbo n'est pas pesé ici ; le GT2 Race en est le plus proche, avec
un échappement de course qui compense turbos et échangeur.

### Contradiction ouverte sur la masse du Turbo

Une seconde valeur circule pour le moteur du 993 Turbo : **268 kg**. Elle ne
peut pas être vraie en même temps que la pesée, sous le même périmètre.

| Source | Périmètre déclaré | 993 atmosphérique | 993 Turbo |
|---|---|---:|---:|
| Pesée au marbre, méthode déclarée | moteur complet prêt à tourner, hors boîte | 186,9 kg | 195,0 kg (GT2 Race) |
| Chiffre en circulation, périmètre non déclaré | inconnu | 232 kg | 268 kg |
| Écart | | 45,1 kg | 73,0 kg |

Les deux écarts sont du même ordre de grandeur qu'une **boîte de vitesses de
911**. L'hypothèse la plus économique est donc que les valeurs de 232 et 268 kg
désignent un **ensemble moteur et boîte**, alors que les pesées portent sur le
moteur seul.

Elle reste une hypothèse. Trois autres explications tiennent debout : un moteur
Turbo de route avec climatisation, échangeurs et échappement de série, là où le
GT2 Race s'en passe ; des pleins comptés ou non ; ou simplement un chiffre repris
sans périmètre.

**Ce que ça change pour le calcul** : rien tant que ce n'est pas tranché, et
c'est précisément le point. Une masse dont on ignore le périmètre ne peut pas
devenir une charge. Si 268 kg inclut la boîte, une part importante repose sur le
support de boîte et non sur ce berceau — l'erreur irait dans le sens dangereux,
en surestimant puis en sous-estimant selon l'usage qu'on en fait.

**Retenir en attendant : environ 195 kg pour un groupe 993 biturbo complet hors
boîte, avec la contradiction signalée.**

Ce que cela ne dit pas encore :

- **la fraction reprise par ce berceau.** Le groupe est tenu par le support
  moteur, porté par le berceau, et par le support de boîte. La répartition entre
  les deux n'est pas connue ;
- la position du centre de gravité par rapport aux fixations ;
- le couple de réaction moteur en première, et son bras de levier.

Sans répartition, la masse pesée reste un majorant, pas une charge.

## 2. Facteurs dynamiques retenus

| Cas | Facteur | Justification et source |
|---|---:|---|
| Vertical, route dégradée | | |
| Freinage longitudinal | | |
| Accélération latérale | | |
| Choc / passage de nid-de-poule | | |
| Sollicitation cyclique de fatigue | | |

Un facteur retenu sans source est une hypothèse : le noter comme telle.

## 3. Interfaces et conditions aux limites

### Couples de serrage — table d'usine

Relevés dans le manuel d'atelier 993, groupe 10, table « Tightening torques:
Removing and installing the engine ». Le document n'est pas versé au dépôt ;
seules les valeurs, qui sont des faits, y sont reportées.

| Liaison | Filetage | Couple |
|---|---|---:|
| **Berceau moteur vers support moteur** | **M12** | **85 Nm (63 ft-lb)** |
| Support de boîte vers caisse | M12 | 46 Nm (34) |
| Traverse arrière vers panneaux latéraux | M12 × 1,5 | 120 Nm (88) |
| Traverse avant vers panneau latéral | M10 | 65 Nm (48) |
| Arbre de transmission vers bride | M10 | 81 Nm (60) |

Deux conclusions :

1. **Les 85 Nm communiqués sont confirmés par l'usine**, et la vis est bien une
   **M12** — la déduction faite à partir des tables de couple était juste.
2. **Le second chiffre communiqué, 45 à 50 Nm « berceau vers moteur », ne figure
   pas dans cette table.** La valeur voisine, 46 Nm, concerne le *support de
   boîte vers caisse*, une autre liaison. À ne pas reporter sur le berceau.

**La table ne donne aucun couple « berceau vers caisse ».** Vérifié dans les deux
volumes : la table du 911 Carrera indique « Engine carrier to engine mount », celle
du Carrera 4 « Engine to engine mount », même filetage et même valeur. Ni l'une ni
l'autre ne publie le serrage des fixations du berceau sur la caisse, et la
procédure de dépose se contente de « Unbolt engine mount (use long-reach socket) ».

Cette valeur est donc à chercher ailleurs dans le manuel, ou à relever sur
véhicule. C'est une entrée manquante du cas de charge, au même titre que la
répartition entre support moteur et support de boîte.

Autre exigence relevée dans la procédure de remontage, et qui compte pour une
pièce sollicitée en fatigue : **« Replace all fastening nuts »** — les écrous de
fixation sont à remplacer, pas à réutiliser.

Ce qu'ils contraignent une fois confirmés :

- **la précontrainte**, donc l'effort de serrage réellement appliqué au berceau,
  et la pression locale sous tête de vis ;
- **la taille de vis**. Aux valeurs de table usuelles à sec, 85 Nm est cohérent
  avec une M12 classe 8.8, et 45 à 50 Nm avec une M10 classe 8.8. C'est une
  déduction, pas un relevé : la classe réelle et le coefficient de frottement
  changent le résultat ;
- **la faisabilité titane**. Un berceau en Ti-6Al-4V devrait encaisser la même
  précontrainte avec un module presque deux fois plus faible, donc plus
  d'enfoncement local, et avec un risque de grippage que `docs/TITANIUM.md`
  impose déjà de traiter.

- Points de fixation à la caisse : nombre, diamètre, classe de vis, couple de serrage
- Supports moteur : type, raideur, précharge
- Conditions imposées dans le modèle EF (encastrement, appuis, contacts)
- Jeux et tolérances d'assemblage

## 4. Environnement

- Température au voisinage de l'échappement et du moteur : ____
- Vibrations : plage de fréquences d'excitation moteur ____
- Corrosion : sel, humidité, contact avec caisse acier
- Durée de vie visée : ____ km ou ____ heures

## 5. Critères d'acceptation

À définir avant de calculer, sinon le critère s'adapte au résultat :

- Contrainte admissible et coefficient de sécurité retenu : ____
- Déplacement maximal admissible aux interfaces : ____
- Première fréquence propre minimale : ____ Hz
- Tenue en fatigue : nombre de cycles et amplitude ____

## 6. Comparaison de procédés

| Procédé | Masse | Coût | Raideur | Fatigue | Risque | Verdict |
|---|---|---|---|---|---|---|
| Pièce d'origine (référence) | 1,96 kg annoncé | ~225-270 € neuf, non vérifié | référence | fissuration constatée sur la famille | connu | référence |
| Renfort rapporté sur pièce d'origine | + quelques centaines de g | 614 € annoncé, ou soudure atelier | augmentée | vise justement ce défaut | voilage au soudage constaté | **la piste utile** |
| **Usinage dans la masse, acier** | ≈ pièce d'origine | copeau élevé, matière peu chère | maîtrisée | **matière corroyée, le meilleur cas** | faible | **le plus probable** |
| Découpe laser plus pliage, bossages soudés | ≈ pièce d'origine | faible | maîtrisée | soudures là où la famille fissure | moyen | à éviter sur cette pièce |
| Forgeage | = pièce d'origine | outillage à amortir | = origine | = origine | faible | seulement en série |
| Aluminium usiné | plus léger | moyen | section à tripler | à qualifier | fluage, corrosion galvanique | écarté par le recoupement de densité |
| Ti-6Al-4V LPBF | ~1,51 kg à raideur égale | milliers d'euros | égale par croissance de section | à qualifier entièrement | grippage, couple galvanique, revue obligatoire | **gain 0,45 kg, soit 0,03 % du véhicule** |

### Pourquoi la fabrication additive métal ne convient pas à cette pièce

Quatre obstacles, dans l'ordre où ils bloquent.

**La taille.** La pièce fait 600 mm. Le volume de fabrication d'une machine LPBF
courante de type EOS M290 est de 250 × 250 × 325 mm : la pièce n'y entre pas,
même en diagonale. Il faudrait une machine grand format, du type 800 × 800 ×
600 mm, matériel rare dont le coût horaire n'a rien à voir.

**La géométrie n'appelle pas l'additif.** Une lame percée de trous
d'allègement, sans canal interne, sans consolidation de sous-ensemble, sans
forme impossible à usiner. `docs/TITANIUM.md` écarte déjà explicitement ce cas :
« plaque, axe, entretoise ou bride simple facilement usinable ».

**La fatigue, et c'est l'obstacle dirimant.** Le mode de défaillance constaté sur
la famille est la fissuration. Or l'état de surface brut de fabrication LPBF est
précisément l'endroit où s'amorcent les fissures : la littérature rapporte des
limites d'endurance de l'ordre de 25 % inférieures en brut de fabrication par
rapport à l'état usiné ou corroyé. La pièce d'origine est vraisemblablement
forgée, donc dans le meilleur état métallurgique possible. Remplacer du forgé par
du brut de fusion revient à reculer sur la seule propriété qui décide de la vie
de la pièce.

Le rattrapage existe — HIP, détensionnement, usinage de toutes les surfaces
fonctionnelles — mais sur une lame de 600 mm il faut alors tout reprendre, et le
coût dépasse celui d'un usinage direct.

**Le coût.** Une pièce d'origine neuve est à 1 788 USD. Une pièce LPBF de 2 kg
sur machine grand format, avec HIP et reprise d'usinage, coûterait
vraisemblablement davantage, pour une tenue en fatigue moins bien connue.

**Le contre-argument, et sa limite.** La presse technique documente des supports
et carters en aluminium ou titane optimisés en topologie, décrits comme « des
pièces qui se montent, se serrent et roulent », pas des maquettes. Le procédé
sait donc produire des pièces de structure secondaire qui tiennent.

La différence avec ce berceau tient en trois points : ces supports entrent dans
un volume de fabrication courant, ils ne mesurent pas 600 mm ; ils ne sont pas la
pièce dont la rupture laisse tomber le groupe motopropulseur ; et le même article
rappelle que la pièce imprimée qui dure est une pièce **HIP puis usinée sur ses
surfaces fonctionnelles**, ce qui ramène au coût que l'usinage direct évite.

### Là où l'additif reste pertinent sur ce dossier

- **Le prototype polymère de vérification d'interfaces**, déjà prévu, qui ne
  porte aucune charge.
- **Un renfort rapporté**, petit, complexe, optimisé en topologie, qui tient
  dans une machine courante et vise justement le mode de défaillance observé.
  C'est le seul emploi de l'additif métal qui se défende ici, et il reste soumis
  à revue d'ingénierie.
- **Les pièces d'habillage** issues de la liste courte de sélection, où
  l'impression polymère est exactement le bon procédé.

### Ce que la masse annoncée décide

À raideur de flexion égale, le titane ferait gagner environ **0,45 kg** sur cette
pièce — soit **0,03 % de la masse du véhicule**. C'est le prix total du concours.

Pour l'obtenir il faudrait : redessiner les sections, établir des cas de charge
complets, faire une revue d'ingénierie formelle, qualifier un procédé LPBF,
contrôler la pièce, gérer le grippage et le couple galvanique dans un
environnement dont la corrosion est documentée.

`docs/TITANIUM.md` tranche déjà ce cas dans sa liste « quand il ne l'est pas ».
**Sur ces chiffres, le titane n'est pas justifié sur cette pièce.**

Le mode de défaillance observé sur la famille n'est d'ailleurs pas la masse :
c'est la **fissuration**. La pièce utile n'est donc pas une pièce plus légère,
c'est une pièce plus endurante — ce que le marché traite déjà par un renfort à
614 €.

Rappel de `docs/TITANIUM.md` : le titane n'est pas pertinent pour « une pièce
dont la flexion doit rester identique à une pièce acier ». Le module du
Ti-6Al-4V est d'environ 114 GPa contre 210 GPa pour un acier : à géométrie
identique, la pièce serait presque deux fois plus souple. Un gain de masse ne
se constate qu'après avoir redessiné les sections pour retrouver la raideur.

## 7. Revue

- Calcul revu par : ____ (nom de rôle, compétence, date)
- Revue de fabricabilité prestataire : ____
- Plan de validation approuvé : oui / non
- Décision : poursuivre / arrêter / redéfinir

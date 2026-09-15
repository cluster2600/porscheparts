# Circuit d'huile de turbo, planche 202-16 — instruit, et écarté

Le triage titane du catalogue d'usine a fait remonter `oil pipe`, 21 références,
comme candidat additif sérieux. Ce document l'instruit. La conclusion est
**non** — deux fois, pour deux raisons indépendantes, et c'est la deuxième qui
est instructive.

## Ce que la planche établit

La planche `202-16 Turbocharger` du 993 Turbo identifie le circuit d'huile des
deux K16. Onze pièces de fluide ou de maintien, sans compter la visserie, les
joints et les o-rings de la même planche :

| position | références | désignation |
|---|---|---|
| 18 | `993 107 125 53`, `993 107 126 53` | `oil pipe`, paire gauche/droite |
| 20 | `993 107 339 53` | `oil pipe` |
| 21 | `993 107 338 53` | `oil pipe` |
| 19 | `993 107 311 53`, `993 107 312 52`, `993 107 312 54` | `vent line` |
| 9 | `993 107 127 51`, `993 107 128 51` | `oil collection container` |
| 22 | `993 107 005 52`, `993 107 005 53` | `bracket` |

Le catalogue **identifie, il ne cote pas** : ni dimension, ni matière, ni
interface. Et il n'établit pas **quelle paire est l'alimentation et quelle paire
est le retour**. Ce point corrige au passage une affirmation du dépôt : la fiche
`993-ENG-TURBO-OIL-RETURN-LINE-IN625-F0-0001` s'annonce « retour » sans que rien
ne l'établisse. La limite est désormais inscrite dans la fiche.

## Pourquoi c'est un très bon candidat additif

Onze pièces qui font un seul travail : amener l'huile à deux paliers, la
ramener, ventiler, et tenir l'ensemble. C'est la définition même de la
consolidation, la troisième famille de `TITANIUM.md`. S'y ajoutent des passages
internes, un routage contraint autour de pièces brûlantes, et une série qui ne
justifiera jamais un outillage. Sur le papier, c'est meilleur que l'embout.

## Première raison du refus : le mode de rupture est l'incendie

`SAFETY.md` définit `safety_critical` comme une rupture « susceptible de
provoquer perte de contrôle, **incendie** ou blessure ».

Une conduite d'huile de turbo qui lâche projette ou laisse couler de l'huile sur
un carter de turbine. L'huile moteur s'auto-enflamme vers 350 à 400 °C ; le
carter chaud d'un K16 est très au-dessus. Ce n'est pas un risque théorique,
c'est le scénario d'incendie de compartiment moteur le mieux connu sur ces
voitures.

La distinction alimentation/retour change l'intensité, pas la nature. Une
alimentation est à la pression d'huile moteur et **projette**. Un retour est un
drain par gravité, quasiment sans pression, et **coule**. Les deux aboutissent
au même endroit.

Aucune finesse de dessin ne supprime ce mode de rupture. La pièce reste
`prohibited_pending_engineering`, et le ferait même avec une géométrie parfaite.

## Seconde raison, et c'est la plus intéressante : le titane est le mauvais métal

Même en mettant l'incendie de côté, la grille du dépôt écarte le titane ici, et
sur un critère qu'on oublie facilement.

`TITANIUM.md` liste parmi les cas où le titane **n'est pas** pertinent :
« contact glissant non traité ou **filetage répété exposé au grippage** ».

Une conduite d'huile se démonte à l'entretien. Ses raccords — banjos, écrous
tournants — sont serrés et desserrés plusieurs fois dans la vie de la pièce. Le
titane grippe, contre lui-même comme contre l'acier, sans traitement de surface.
C'est exactement le cas d'exclusion.

Donc si cette pièce est un jour refabriquée en additif, **c'est en nickel ou en
acier**, pas en titane. Le meilleur candidat additif du triage n'est pas un
candidat titane. Les deux questions ne se confondent pas, et c'est la leçon à
retenir de cette instruction.

## Ce qui débloquerait la pièce

Pour la sortir de `prohibited_pending_engineering`, il faudrait, dans cet ordre :

1. l'attribution alimentation/retour de chaque référence, et la pression réelle
   de chaque branche ;
2. la mesure d'un exemplaire : longueur, diamètres, brides, interfaces, et les
   mouvements relatifs moteur/turbo que la conduite doit absorber ;
3. une carte matière chaude qualifiée, avec tenue au cyclage thermique et à
   l'huile ;
4. un essai de pression et d'étanchéité, puis un essai d'endurance en vibration
   à température ;
5. une revue d'ingénierie signée, au sens de `SAFETY.md`, portant explicitement
   sur le risque d'incendie.

C'est un programme, pas une impression. Il n'a rien à faire dans un premier
tirage métal.

## Conséquence pour la sélection en cours

L'embout d'échappement reste la première pièce titane. Il gagne moins sur la
consolidation que le circuit d'huile — mais il ne met le feu à rien, et ses
interfaces ne se démontent pas à chaque vidange.

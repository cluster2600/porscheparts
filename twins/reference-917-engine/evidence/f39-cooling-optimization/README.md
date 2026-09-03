# Refroidissement 917 F39 — optimisation paramétrique publiée

Le calcul balaye deux modèles indépendants dans leurs équations primaires : (A) une loi d'échelle ancrée sur le canal OpenFOAM F38 et (B) Gnielinski–Darcy avec efficacité d'ailette. Il ne s'agit ni d'une nouvelle CFD par candidat ni d'une CHT de culasse complète.

- combinaisons évaluées : 1728 ;
- combinaisons passant l'écran nominal : 35 ;
- candidat : 14 niveaux, ailettes 2.4 mm, jeu 3.5 mm, rayon de pied 4.0 mm, déflecteur `splitter12` ;
- `T_pont,max` nominale : 230.8 °C ;
- `Δp_max` nominale : 4.99 kPa ;
- écart relatif `h` : 3.0 % ;
- passages sans huile 1 200 W : 0 ;
- aire mouillée F39 : proxy extrapolé de la surface scan F37, pas mesurée sur un B-Rep accepté ;
- géométrie d'huile, carte matière à chaud, fan map, CHT complète et corrélation physique : non validées ;
- impression métal et démarrage moteur : interdits.

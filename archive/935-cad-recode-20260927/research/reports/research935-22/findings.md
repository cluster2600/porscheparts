Rapport brut OpenClaw — conclusions à contrôler.

Rapport de métrologie pour le scan Wolfe 935‑xtreme-cylinder‑head.obj  

**Fait 1** – Service de scanning 3D chez Wolfe Classics (https://www.wolfeclassics.com/services) : l’entreprise indique disposer du Creaform Handyscan 700 et de l’Einstar Vega, capables de scanner des pièces allant du petit composant à un véhicule complet, tarif à partir de 100 $ par item. Cela confirme l’existence de scanners « handheld » à résolution industrielle, mais ne précise pas la précision (résolution, tolérance).  

**Fait 2** – Atelier de Xtreme Cylinder Heads (https://www.xtremecylinderheads.com/ourshop) : l’atelier possède deux centres CNC Doosan 5700S (4 axes, 40 Outils) et un centre Rottler EM69P à 5 axes équipé d’un probe de numérisation Renishaw utilisé pour la digitisation des ports et des chambres ainsi que pour le rechargement de trous endommagés. Cette configuration permet une mesure très précise et l’usinage de surfaces complexes.  

**Applicabilité au scan** (cible 935‑xtreme‑cylinder‑head.obj)  
- *Confirmée* : les équipements décrits permettent de capturer la géométrie globale d’une tête de cylindre avec ailettes, comparable à la forme du scan.  
- *Hypothèse* : la résolution du Handyscan 700/Einstar Vega est suffisante pour reproduire les ailettes sans artefacts majeurs, mais la précision réelle doit être vérifiée contre des références connues.  
- *Inconnue* : l’échelle physique du modèle scan (mm ou inches) n’est pas indiquée ; aucune référence de dimension n’est disponible dans les pages consultées.  

**Conséquences concrètes pour la CAO**  
- Le maillage brut du scan peut être importé tel‑quel dans un logiciel CAD (SolidWorks, Fusion 360) et aligné à l’aide de marqueurs fiduciels virtuels placés sur les surfaces planes détectées.  
- La numérisation des ports via un probe virtuel inspirée du Rottler EM69P peut être simulée pour créer des surfaces de dégagement précises destinées à l’usinage ou au montage.  
- Sans échelle connue, toute opération d’usinage ou de réparation doit d’abord établir une calibration (ex. mesurer un calibre virtuel intégré au maillage ou ajouter un modèle de référence).  

**Inconnues persistantes**  
- L’échelle réelle du modèle, la texture de surface et les éventuelles distorsions dues à l’angle/éclairage restent non déterminées.  

Ce protocole minimal – nettoyage du maillage, ajout de points de référence, vérification de l’échelle – rend le scan exploitable pour une modélisation CAO fiable, sous réserve de confirmer la précision du scanner et l’échelle.
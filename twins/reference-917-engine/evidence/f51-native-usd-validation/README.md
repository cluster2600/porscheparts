# Preuves publiques expurgées F51

Ce répertoire publie uniquement des hashes, métriques et verdicts. Il ne
contient ni maître B-Rep, ni archive de tessellation, ni USD, ni coordonnée.

- `native-brep-usd-f51.json` relie les maîtres privés F50 aux USD privés 2V et
  4V par SHA-256;
- la conversion est directe B-Rep natif → tessellation OCCT → OpenUSD, sans
  intermédiaire STEP, transformation, proxy ou forme ovale;
- les contrôles OpenUSD et NVIDIA Asset Validator sont verts;
- le profil formel SimReady et le rendu OVRTX restent bloqués et toutes les
  portes de fabrication restent fermées.

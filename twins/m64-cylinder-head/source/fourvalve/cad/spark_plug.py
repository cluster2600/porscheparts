"""Enveloppe d'assemblage candidate ; ni CAO fournisseur, ni modèle thermique de bougie."""
from cadcommon import _cyl, _v, cq
from layout import plug_envelope_cylinders


def spark_plug(p, k):
    sections = plug_envelope_cylinders(p, k)
    # ponytail: enveloppe pleine sans filets ni cavité de nez ; plan fournisseur requis pour les résoudre.
    a, b, r = sections['hex']
    hexagon = cq.Workplane(cq.Plane(origin=_v(a), normal=_v(b - a))).polygon(
        6, 2 * r).extrude(p['plug_hex_height']).val()
    cylinders = [_cyl(*row) for name, row in sections.items() if name != 'hex']
    return hexagon.fuse(*cylinders).clean()

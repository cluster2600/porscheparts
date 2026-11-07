"""Preserve Gmsh's MSH2 structure while writing its live node values losslessly."""
from pathlib import Path
import numpy as np

def write_exact_msh(gmsh, output):
    output = Path(output)
    raw = output.with_name(output.stem + '-native16.msh')
    assert not raw.exists() and not output.exists()
    gmsh.option.setNumber('Mesh.PreserveNumberingMsh2', 1)
    gmsh.option.setNumber('Mesh.MshFileVersion', 2.2)
    gmsh.write(str(raw))
    tags, xyz, _ = gmsh.model.mesh.getNodes()
    order = np.argsort(tags)
    tags = np.asarray(tags)[order]
    xyz = np.asarray(xyz).reshape(-1, 3)[order]
    assert np.isfinite(xyz).all() and len(np.unique(tags)) == len(tags)
    seen = set()
    with raw.open() as src, output.open('x') as dst:
        for line in src:
            dst.write(line)
            if line.strip() != '$Nodes':
                continue
            count = next(src)
            dst.write(count)
            assert int(count) == len(tags)
            for _ in range(int(count)):
                row = next(src).split()
                tag = int(row[0])
                index = int(np.searchsorted(tags, tags.dtype.type(tag)))
                assert index < len(tags) and tags[index] == tag and tag not in seen
                seen.add(tag)
                point = xyz[index]
                assert [float(x) for x in row[1:]] == [float(format(x, '.16g')) for x in point]
                text = ' '.join(format(x, '.17g') for x in point)
                assert [float(x) for x in text.split()] == point.tolist()
                dst.write(f'{tag} {text}\n')
            assert next(src).strip() == '$EndNodes'
            dst.write('$EndNodes\n')
    assert len(seen) == len(tags)

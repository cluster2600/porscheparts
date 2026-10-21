"""Held explicit Gmsh4.1-binary writer; no mesh generation or optimization."""
import hashlib
import json
from pathlib import Path
import struct
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(output):
    import gmsh
    reference = Path(__file__).with_name('cube-reference.json')
    r = json.loads(reference.read_text())
    before = {'writer': sha(__file__), 'reference': sha(reference)}
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('Fresh owned mesh-writer output required; no retry')
    if gmsh.__version__ != '4.15.2' or sys.byteorder != 'little':
        raise ValueError('Recorded little-endian Gmsh4.15.2 required')
    if sha(sys.executable) != r['writer_runtime']['python_sha256'] or sha(gmsh.__file__) != r['writer_runtime']['gmsh_module_sha256'] or sha(gmsh.lib._name) != r['writer_runtime']['libgmsh_sha256']:
        raise ValueError('Recorded existing writer runtime identity changed')
    output.mkdir()
    gmsh.initialize([], readConfigFiles=False, run=False)
    try:
        gmsh.option.setNumber('General.Terminal', 1)
        gmsh.option.setNumber('General.NumThreads', 1)
        gmsh.option.setNumber('Mesh.MshFileVersion', 4.1)
        gmsh.option.setNumber('Mesh.Binary', 1)
        gmsh.option.setNumber('Mesh.SaveAll', 0)
        gmsh.model.add('normalized_imported_cube_software_witness')
        gmsh.model.addDiscreteEntity(2, 1)
        gmsh.model.addDiscreteEntity(3, 1, [1])
        tags = r['node_tags']; points = r['coordinates_mm']
        gmsh.model.mesh.addNodes(2, 1, tags[:8], [v for row in points[:8] for v in row])
        gmsh.model.mesh.addNodes(3, 1, tags[8:], points[8])
        gmsh.model.mesh.addElementsByType(1, 2, r['triangle_tags'], [v for row in r['outward_triangles_node_tags'] for v in row])
        gmsh.model.mesh.addElementsByType(1, 4, r['tetrahedron_tags'], [v for row in r['positive_tetrahedra_node_tags'] for v in row])
        gmsh.model.addPhysicalGroup(2, [1], 11); gmsh.model.setPhysicalName(2, 11, 'all_boundary')
        gmsh.model.addPhysicalGroup(3, [1], 21); gmsh.model.setPhysicalName(3, 21, 'solid')
        mesh = output / 'imported-cube.msh'; gmsh.write(str(mesh))
        with mesh.open('rb') as stream:
            if stream.readline() != b'$MeshFormat\n' or stream.readline() != b'4.1 1 8\n' or stream.read(4) != struct.pack('<i', 1):
                raise ValueError('Exact little-endian binary4.1/8-byte header required')
        gmsh.clear(); gmsh.open(str(mesh))
        got, xyz, _ = gmsh.model.mesh.getNodes()
        actual = {int(tag): tuple(float(v) for v in xyz[3*i:3*i+3]) for i, tag in enumerate(got)}
        if actual != dict(zip(tags, map(tuple, points))):
            raise ValueError('Full written node coordinates/tags differ')
        for dim, element_type, key, tag_key in [(2, 2, 'outward_triangles_node_tags', 'triangle_tags'), (3, 4, 'positive_tetrahedra_node_tags', 'tetrahedron_tags')]:
            types, elements, nodes = gmsh.model.mesh.getElements(dim)
            if list(types) != [element_type]: raise ValueError('Unexpected written element type')
            width = dim + 1
            actual = {int(tag): tuple(int(v) for v in nodes[0][width*i:width*i+width]) for i, tag in enumerate(elements[0])}
            if actual != dict(zip(r[tag_key], map(tuple, r[key]))): raise ValueError('Full ordered written connectivity differs')
        if gmsh.model.getPhysicalGroups() != [(2, 11), (3, 21)] or gmsh.model.getPhysicalName(2, 11) != 'all_boundary' or gmsh.model.getPhysicalName(3, 21) != 'solid':
            raise ValueError('Written physical boundary/domain identity differs')
    finally:
        gmsh.finalize()
    if before != {'writer': sha(__file__), 'reference': sha(reference)}: raise ValueError('Writer/reference drift')
    result = dict(status='explicit_mesh_written_and_full_gmsh_readback_only', mesh_sha256=sha(mesh), mesh_bytes=mesh.stat().st_size,
        source_sha256=before, gmsh_version=gmsh.__version__, mesh_generation_or_optimization_called=False,
        MOOSE_import_or_solve_run=False, head_or_physical_qualification=False)
    with (output / 'mesh-write-report.json').open('x') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')


if __name__ == '__main__':
    if len(sys.argv) != 2: raise SystemExit('Usage: make_mesh.py fresh-output-directory')
    main(sys.argv[1])

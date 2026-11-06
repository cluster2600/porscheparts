import cadquery as cq, trimesh, sys
s=cq.importers.importStep(sys.argv[1])
cq.exporters.export(s, sys.argv[2], tolerance=0.05, angularTolerance=0.2)
m=trimesh.load(sys.argv[2]); print(len(m.faces), m.is_watertight, m.volume)

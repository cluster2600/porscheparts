"""Render print/mockup.png: the engraved connecting rod mock-up, rod and cap as laid on the plate (cadsim image)."""
import pyvista as pv

pv.OFF_SCREEN = True
mesh = pv.read("parts/993-eng-connecting-rod-ti64-f0-0001/print/connecting_rod_f0_mockup.stl")
p = pv.Plotter(off_screen=True, window_size=(1600, 800), lighting="three lights")
p.set_background("white")
p.add_mesh(mesh, color="#e8e2d0", smooth_shading=False, specular=0.2)
p.add_mesh(mesh.extract_feature_edges(40), color="#5a5a5a", line_width=0.8)
p.view_vector((0.6, -1.2, 1.3), viewup=(0, 0, 1))
p.reset_camera()
p.camera.zoom(1.1)
p.screenshot("parts/993-eng-connecting-rod-ti64-f0-0001/print/mockup.png")

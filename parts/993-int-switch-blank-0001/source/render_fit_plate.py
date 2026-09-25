"""Render print/plate.png: the three fit-test blanks as laid on the build plate (cadsim image)."""
import pyvista as pv
pv.OFF_SCREEN=True
p=pv.Plotter(off_screen=True,window_size=(1500,800),lighting="three lights"); p.set_background("white")
for i in (1,2,3):
    m=pv.read(f"parts/993-int-switch-blank-0001/print/switch_blank_fit_{i}.stl").translate(((i-2)*30,0,0))
    p.add_mesh(m,color="#3a3d42",smooth_shading=False); p.add_mesh(m.extract_feature_edges(35),color="#9aa0a6",line_width=1)
p.view_vector((0.5,-1.3,1.5),viewup=(0,0,1)); p.reset_camera(); p.camera.zoom(1.25)
p.screenshot("parts/993-int-switch-blank-0001/print/plate.png")

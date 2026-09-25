"""Render the K16 display pair: wheels seated on the stand (print/display.png), in the cadsim image."""
import sys
import pyvista as pv

pv.OFF_SCREEN = True
C = "parts/993-eng-k16-compressor-wheel-al2139-f1-0001/print/"
T = "parts/993-eng-k16-turbine-wheel-in718-f0-0001/print/"
BASE_H, POCKET = 8.0, 2.0
stand = pv.read(C + "k16_display_stand.stl")
comp = pv.read(C + "k16_compressor_wheel_mockup.stl").translate((-38, 8, BASE_H - POCKET))
turb = pv.read(T + "k16_turbine_wheel_mockup.stl").translate((40, 8, BASE_H - POCKET))
out = sys.argv[1] if len(sys.argv) > 1 else C + "display.png"
p = pv.Plotter(off_screen=True, window_size=(1600, 900), lighting="three lights")
p.set_background("white")
for m, c in ((stand, "#2f3237"), (comp, "#c4c9cf"), (turb, "#9a8f7c")):
    p.add_mesh(m, color=c, smooth_shading=False, specular=0.3)
    p.add_mesh(m.extract_feature_edges(40), color="#50545a", line_width=0.6)
p.view_vector((0.15, -1.3, 0.9), viewup=(0, 0, 1))
p.reset_camera(); p.camera.zoom(1.25)
p.screenshot(out)

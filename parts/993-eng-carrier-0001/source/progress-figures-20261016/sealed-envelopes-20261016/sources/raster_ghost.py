"""Private visual adapter: unlit colours and framing from every real vertex."""
import numpy as np

def raster(vertices, faces, colors, elevation, azimuth, bounds=None, part_faces=None):
    from vispy import scene
    canvas = scene.SceneCanvas(show=False, size=(2000, 720), bgcolor="#f5f7f9")
    try:
        view = canvas.central_widget.add_view()
        view.camera = scene.cameras.TurntableCamera(fov=0, elevation=elevation, azimuth=azimuth)
        if part_faces is None:
            raise ValueError("The posed part triangle count is required")
        envelopes = scene.visuals.Mesh(vertices=vertices, faces=faces[part_faces:],
            face_colors=colors[part_faces:], shading=None, parent=view.scene)
        envelopes.set_gl_state('opaque', depth_test=True)
        envelopes.order = 0
        body_colors = colors[:part_faces].copy()
        body_colors[:, 3] = .18
        body = scene.visuals.Mesh(vertices=vertices, faces=faces[:part_faces],
            face_colors=body_colors, shading=None, parent=view.scene)
        body.set_gl_state('translucent', depth_test=True, depth_mask=False)
        body.order = 1
        box = np.array([vertices.min(0), vertices.max(0)]) if bounds is None else bounds
        view.camera.set_range(x=box[:, 0], y=box[:, 1], z=box[:, 2], margin=.035)
        # VisPy's default fit assumes XY extends horizontally, even after camera rotation.
        el, az = np.radians([elevation, azimuth])
        right = np.array([np.cos(az), np.sin(az), 0.])
        up = np.array([-np.sin(el)*np.sin(az), np.sin(el)*np.cos(az), np.cos(el)])
        projected = (vertices-box.mean(0)) @ np.stack([right, up], axis=1)
        extent = 2*np.abs(projected).max(0)
        view.camera.center = box.mean(0)
        view.camera.scale_factor = max(extent[1], extent[0]/(2000/720))*1.10
        pixels = canvas.render()
        occupied = np.any(pixels[:, :, :3] != [245, 247, 249], axis=2)
        y, x = np.nonzero(occupied)
        if not len(x):
            raise ValueError("Rendering is empty")
        return pixels[max(0,y.min()-30):min(len(pixels),y.max()+31),
                      max(0,x.min()-30):min(pixels.shape[1],x.max()+31)]
    finally:
        canvas.close()

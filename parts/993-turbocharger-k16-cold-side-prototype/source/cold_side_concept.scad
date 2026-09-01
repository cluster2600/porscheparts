// Parametric stationary cold-side diffuser concept for the 993 K16 study.
//
// This is an editable research geometry, not a reconstruction of a K16 turbo.
// It deliberately contains no rotor, blade, CHRA, bearing, wastegate or hot-side
// surface. Dimensions are design variables and are not inferred K16 measurements.

$fn = 96;

inlet_diameter_mm = 50;
outlet_diameter_mm = 68;
diffuser_length_mm = 90;
wall_thickness_mm = 4;
flange_thickness_mm = 8;
inlet_flange_diameter_mm = 74;
outlet_flange_diameter_mm = 92;
show_flow_domain = false;

assert(inlet_diameter_mm > 0, "inlet diameter must be positive");
assert(outlet_diameter_mm > inlet_diameter_mm, "outlet must be larger than inlet");
assert(diffuser_length_mm > 0, "diffuser length must be positive");
assert(wall_thickness_mm > 0 && wall_thickness_mm < inlet_diameter_mm / 2,
       "wall thickness must leave an inlet passage");

// A ring is used for the flanges so that the concept stays open to flow.
module ring(z_mm, height_mm, outer_diameter_mm, inner_diameter_mm) {
    translate([0, 0, z_mm])
        difference() {
            cylinder(h = height_mm, d = outer_diameter_mm);
            translate([0, 0, -0.1])
                cylinder(h = height_mm + 0.2, d = inner_diameter_mm);
        }
}

// Axisymmetric wall section. OpenSCAD rotates the radius/axial profile around Z.
module diffuser_shell() {
    rotate_extrude(angle = 360)
        polygon([
            [inlet_diameter_mm / 2, 0],
            [outlet_diameter_mm / 2, diffuser_length_mm],
            [outlet_diameter_mm / 2 + wall_thickness_mm, diffuser_length_mm],
            [inlet_diameter_mm / 2 + wall_thickness_mm, 0]
        ]);
}

// Solid fluid volume, useful as a reference while preparing a CFD mesh.
module flow_domain() {
    rotate_extrude(angle = 360)
        polygon([
            [0, 0],
            [inlet_diameter_mm / 2, 0],
            [outlet_diameter_mm / 2, diffuser_length_mm],
            [0, diffuser_length_mm]
        ]);
}

module cold_side_concept() {
    union() {
        diffuser_shell();
        // Overlap the end faces by 0.5 mm so the exported shell is one solid.
        ring(-flange_thickness_mm, flange_thickness_mm + 0.5,
             inlet_flange_diameter_mm, inlet_diameter_mm);
        ring(diffuser_length_mm - 0.5, flange_thickness_mm + 0.5,
             outlet_flange_diameter_mm, outlet_diameter_mm);
    }
}

if (show_flow_domain) {
    flow_domain();
} else {
    cold_side_concept();
}

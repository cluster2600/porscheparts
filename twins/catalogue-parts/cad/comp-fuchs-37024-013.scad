// Generated documentary F1 envelope proxy.
// Not manufacturing geometry, not dimensionally validated, not SimReady.
proxy_id = "COMP-FUCHS-37024.013";
$fn = 96;

rim_diameter_mm = 431.8;
rim_width_mm = 177.8;
centre_bore_mm = 71.58;

rotate([0, 90, 0])
difference() {
    cylinder(h = rim_width_mm, d = rim_diameter_mm, center = true);
    cylinder(h = rim_width_mm + 2, d = centre_bore_mm, center = true);
}

// Generated documentary F1 envelope proxy.
// Not manufacturing geometry, not dimensionally validated, not SimReady.
proxy_id = "COMP-FUCHS-37027.011";
$fn = 96;

rim_diameter_mm = 457.2;
rim_width_mm = 203.2;
centre_bore_mm = 71.5;

rotate([0, 90, 0])
difference() {
    cylinder(h = rim_width_mm, d = rim_diameter_mm, center = true);
    cylinder(h = rim_width_mm + 2, d = centre_bore_mm, center = true);
}

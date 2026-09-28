// PET-linked K16 F1 guides; not OEM, interface, aero or manufacturing geometry.
// Boxes are complete-unit supplier envelopes; diameter coupons are spatially unrelated.
$fn = 96;
envelope_mm = [280.000000, 190.000000, 210.000000];
coupon_thickness_mm = 2.000000; // visualization hypothesis only

module complete_unit_envelope() {
    cube(envelope_mm, center = true);
}

module diameter_coupon(diameter_mm) {
    cylinder(h = coupon_thickness_mm, d = diameter_mm, center = true);
}

// Left and right display offsets are not vehicle coordinates.
translate([-180.000000, 0, 0]) complete_unit_envelope();
translate([180.000000, 0, 0]) complete_unit_envelope();

// Right-side catalogue diameter coupons; never positioned inside either turbo.
// compressor_exducer: supplier-declared diameter
translate([-90.000000, -250.000000, 0]) 
    diameter_coupon(60.500000);
// compressor_inducer: supplier-declared diameter
translate([-30.000000, -250.000000, 0]) 
    diameter_coupon(40.600000);
// turbine_exducer: supplier-declared diameter
translate([30.000000, -250.000000, 0]) 
    diameter_coupon(48.970000);
// turbine_inducer: supplier-declared diameter
translate([90.000000, -250.000000, 0]) 
    diameter_coupon(54.960000);

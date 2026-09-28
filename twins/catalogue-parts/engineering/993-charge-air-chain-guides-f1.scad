// PET 107-45 charge-air F1 guides; not OEM shapes or interfaces.
// Component offsets and two aftermarket diameter coupons are display-only.
$fn = 96;
coupon_thickness_mm = 2.000000; // visualization hypothesis only

module envelope_guide(size_mm) { cube(size_mm, center = true); }
module diameter_coupon(diameter_mm) {
    cylinder(h = coupon_thickness_mm, d = diameter_mm, center = true);
}

// 993-INTERCOOLER-REPLACEMENT-AKS: aftermarket_core_only_not_complete_OEM_intercooler_envelope
993_intercooler_replacement_aks_mm = [260.000000, 270.000000, 60.000000];
translate([-520.000000, 0.000000, 0.000000])
    envelope_guide(993_intercooler_replacement_aks_mm);

// 993-INTERCOOLER-AIR-DUCT: supplier_replacement_product_bounding_box_not_OEM_surface
993_intercooler_air_duct_mm = [600.000000, 280.000000, 50.000000];
translate([520.000000, 0.000000, 0.000000])
    envelope_guide(993_intercooler_air_duct_mm);

// 993-INTERCOOLER-PRESSURE-HOSE-RIGHT: supplier_replacement_product_bounding_box_not_OEM_surface
993_intercooler_pressure_hose_right_mm = [430.000000, 70.000000, 90.000000];
translate([0.000000, 360.000000, 0.000000])
    envelope_guide(993_intercooler_pressure_hose_right_mm);

// 993-INTERCOOLER-PRESSURE-HOSE-LEFT: supplier_replacement_product_bounding_box_not_OEM_surface
993_intercooler_pressure_hose_left_mm = [430.000000, 70.000000, 115.000000];
translate([0.000000, -360.000000, 0.000000])
    envelope_guide(993_intercooler_pressure_hose_left_mm);

// 993-INTERCOOLER-TEMPERATURE-SENSOR: supplier_product_bounding_box_not_thread_or_probe_geometry
993_intercooler_temperature_sensor_mm = [75.000000, 35.000000, 20.000000];
translate([0.000000, 0.000000, 180.000000])
    envelope_guide(993_intercooler_temperature_sensor_mm);

// Aftermarket 43/57 mm coupons: no side, endpoint or OEM applicability assigned.
translate([-60.000000, -720.000000, 0])
    diameter_coupon(43.000000);
translate([60.000000, -720.000000, 0])
    diameter_coupon(57.000000);

// Generated PET-linked valve dimensional surrogates; not OEM geometry.
// Seat, guide clearance, keeper, neck, tolerances and hot geometry are unresolved.
$fn = 96;
face_thickness_mm = 2.500000; // hypothesis
neck_length_mm = 8.000000; // hypothesis

module valve_surrogate(head_d_mm, stem_d_mm, overall_length_mm) {
    union() {
        cylinder(h = face_thickness_mm, d = head_d_mm);
        translate([0, 0, face_thickness_mm])
            cylinder(h = neck_length_mm, d1 = head_d_mm, d2 = stem_d_mm);
        translate([0, 0, face_thickness_mm])
            cylinder(h = overall_length_mm - face_thickness_mm, d = stem_d_mm);
    }
}

// 993-carrera-exhaust-42_5-f1 — three_supplier_declared_overall_dimensions
translate([-60.000000, 0, 0])
    valve_surrogate(42.500000, 8.000000, 109.000000);

// 993-intake-49-f1 — partial_supplier_declaration_plus_length_hypothesis
translate([0.000000, 0, 0])
    valve_surrogate(49.000000, 8.000000, 109.000000);

// 993-turbo-exhaust-43_5-f1 — three_supplier_declared_overall_dimensions
translate([60.000000, 0, 0])
    valve_surrogate(43.500000, 8.000000, 108.900000);

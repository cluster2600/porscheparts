// 993 123 113 51 supplier-envelope guide; not an OEM heat-shield surface.
envelope_mm = [160.000000, 110.000000, 105.000000];
supplier_declared_mass_kg = 0.230000;

module supplier_envelope_guide() {
    cube(envelope_mm, center = true);
}

supplier_envelope_guide();

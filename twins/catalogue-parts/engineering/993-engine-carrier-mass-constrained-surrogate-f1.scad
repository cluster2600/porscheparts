// Generated mass-constrained structural surrogate, not OEM geometry.
// No interface coordinates, tolerances, fitment or manufacturing credit.
// The uniform square tube is one mathematical witness compatible with envelope and mass.

$fn = 48;
length_mm = 600.000000;
outer_mm = 50.000000;
wall_mm = 2.175319724;
inner_mm = outer_mm - 2 * wall_mm;

difference() {
    translate([-length_mm / 2, -outer_mm / 2, 0])
        cube([length_mm, outer_mm, outer_mm], center = false);
    translate([-length_mm / 2 - 1, -inner_mm / 2, wall_mm])
        cube([length_mm + 2, inner_mm, inner_mm], center = false);
}

// Generated documentary F1 envelope proxy.
// Not manufacturing geometry, not dimensionally validated, not SimReady.
proxy_id = "993-INTERCOOLER-AIR-DUCT";
$fn = 96;

length_mm = 600;
width_mm = 280;
height_mm = 50;

translate([-length_mm / 2, -width_mm / 2, 0])
    cube([length_mm, width_mm, height_mm], center = false);

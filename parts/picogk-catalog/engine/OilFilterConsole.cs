using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Oil filter console, mounting face at z = 0. A ribbed base plate with four
/// mounting pads carries the filter pedestal (seal land, recessed inlet
/// annulus, centre spigot). The two galleries are cast-style tubes merged into
/// the body: inlet port -> curved gallery -> opening in the filter annulus;
/// filter centre spigot -> curved gallery -> outlet port. Both galleries are
/// open at each end, so there is no trapped powder volume.
public sealed class OilFilterConsole : IPartGenerator
{
    public string Name => "oil_filter_console";

    public Voxels Build(Library lib, PartSpec s)
    {
        float L = s.P("body_length_mm") / 2f, W = s.P("body_width_mm") / 2f;
        float tPlate = s.P("base_plate_thickness_mm"), rPlate = s.P("base_plate_corner_radius_mm");
        float hPad = s.P("body_height_mm"), rPad = s.P("mount_pad_diameter_mm") / 2f;
        float rMount = s.P("mount_bore_diameter_mm") / 2f;
        float mx = s.P("mount_x_mm"), my = s.P("mount_y_mm");
        float cx = s.P("filter_pedestal_center_x_mm"), rPed = s.P("filter_pedestal_outer_diameter_mm") / 2f;
        float zPed = hPad + s.P("filter_pedestal_height_mm");
        float rSealO = s.P("filter_seal_land_outer_diameter_mm") / 2f, rSealI = s.P("filter_seal_land_inner_diameter_mm") / 2f;
        float hSeal = s.P("filter_seal_land_height_mm");
        float rSpig = s.P("filter_spigot_outer_diameter_mm") / 2f, rSpigBore = s.P("filter_spigot_bore_diameter_mm") / 2f;
        float hSpig = s.P("filter_spigot_height_mm");
        float annulusDepth = s.P("filter_inlet_annulus_depth_mm");
        float rPortBoss = s.P("external_port_boss_diameter_mm") / 2f, lPortBoss = s.P("external_port_boss_length_mm");
        float rGal = s.P("main_gallery_diameter_mm") / 2f, galWall = s.P("minimum_channel_wall_mm");
        float yIn = s.P("inlet_gallery_y_mm"), zIn = s.P("inlet_gallery_z_mm");
        float yOut = s.P("outlet_gallery_y_mm"), zOut = s.P("outlet_gallery_z_mm");
        float tRib = s.P("rib_thickness_mm") / 2f;

        float xEnd = L + lPortBoss / 2f;   // port faces
        float zSpigTop = zPed + hSpig;
        // Inlet: straight from the port, curve up into the pedestal, rise to the annulus.
        var inlet = new List<Vector3> { new(-xEnd - 1f, yIn, zIn), new(-L + 8f, yIn, zIn) };
        inlet.AddRange(Es.CubicPts(new Vector3(-L + 8f, yIn, zIn), new Vector3(cx - 20f, yIn, zIn),
                                   new Vector3(cx, yIn, zIn + 2f), new Vector3(cx, yIn, zIn + 17f), 12));
        inlet.Add(new Vector3(cx, yIn, zPed + 2f));
        // Outlet: down the spigot bore, curve out to the outlet port.
        var outlet = new List<Vector3>();
        outlet.AddRange(Es.CubicPts(new Vector3(cx, yOut, zPed - 12f), new Vector3(cx, yOut, zOut + 2f),
                                    new Vector3(cx + 14f, yOut, zOut), new Vector3(L - 6f, yOut, zOut), 12));
        outlet.Add(new Vector3(xEnd + 1f, yOut, zOut));
        var pads = new[] { new Vector2(-mx, -my), new Vector2(-mx, my), new Vector2(mx, -my), new Vector2(mx, my) };

        float F(Vector3 p)
        {
            float x = p.X, y = p.Y, z = p.Z;
            float plan = Es.Rect2(x, y, 0f, 0f, L, W, rPlate);
            float d = MathF.Max(Es.RoundEdge(plan, z - tPlate, 2f), -z);
            // Mounting pads and ribs running to the pedestal.
            float padD = float.MaxValue, rib = float.MaxValue, mounts = float.MaxValue;
            foreach (Vector2 m in pads)
            {
                float rm = Es.Len2(x - m.X, y - m.Y);
                padD = MathF.Min(padD, Es.RoundEdge(rm - rPad, z - hPad, 1.5f));
                mounts = MathF.Min(mounts, rm - rMount);
                float seg = Es.Seg2(x, y, m.X, m.Y, cx, 0f) - tRib;
                rib = MathF.Min(rib, Es.RoundEdge(seg, z - (hPad - 2f), tRib * 0.9f));
            }
            d = Es.SMin(d, MathF.Max(padD, -z), 3f);
            d = Es.SMin(d, MathF.Max(rib, -z), 3f);
            // Filter pedestal, seal land, spigot.
            float rp = Es.Len2(x - cx, y);
            float ped = MathF.Max(Es.RoundEdge(rp - rPed, z - zPed, 2.5f), -z);
            d = Es.SMin(d, ped, 6f);
            float seal = MathF.Max(MathF.Max(rp - rSealO, rSealI - rp), MathF.Max(zPed - 1f - z, z - (zPed + hSeal)));
            d = Es.SMin(d, seal, 0.5f);
            // Gallery tubes (cast-style bulges) and port bosses.
            float tubes = MathF.Min(Es.Tube(p, inlet, rGal + galWall), Es.Tube(p, outlet, rGal + galWall));
            tubes = MathF.Max(MathF.Max(tubes, -z), MathF.Max(MathF.Abs(x) - xEnd, z - (zPed - 2f)));
            float ports = MathF.Min(Es.Cyl(p, new Vector3(-xEnd, yIn, zIn), new Vector3(-xEnd + lPortBoss, yIn, zIn), rPortBoss),
                                    Es.Cyl(p, new Vector3(xEnd - lPortBoss, yOut, zOut), new Vector3(xEnd, yOut, zOut), rPortBoss));
            d = Es.SMin(d, MathF.Max(MathF.Min(tubes, ports), -z), 4f);
            // Recessed filter inlet annulus, then spigot standing in it.
            float annulus = MathF.Max(MathF.Max(rp - (rSealI - 2f), rSpig + 2f - rp), zPed - annulusDepth - z);
            d = Es.SMax(d, -annulus, 1f);
            float spig = Es.RoundEdge(rp - rSpig, MathF.Max(zPed - annulusDepth - 1f - z, z - zSpigTop), 1f);
            d = Es.SMin(d, spig, 1.5f);
            // Bores: galleries, spigot bore, mounting bores.
            float gal = MathF.Min(Es.Tube(p, inlet, rGal), Es.Tube(p, outlet, rGal));
            float spigBore = MathF.Max(rp - rSpigBore, zPed - 13f - z);
            float holes = MathF.Min(MathF.Min(gal, spigBore), mounts);
            return MathF.Max(d, -holes);
        }

        Sdf.Stage(s.PartId, "console field");
        return Sdf.Vox(lib, F, new Vector3(-xEnd - 1.5f, -W - 1.5f, -1.5f), new Vector3(xEnd + 1.5f, W + 1.5f, zSpigTop + 1.5f));
    }
}

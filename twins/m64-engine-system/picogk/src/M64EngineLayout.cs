// M64 (Porsche 993 Turbo) whole-engine layout scaffold — PicoGK 2.3.0 API.
// Statut : F1_envelope. Envelopes parametriques (poutres du reseau), aucune
// surface de conception. Cotes FACT_public cablees depuis les fiches sources du
// registre ; les cotes non publiques restent des parametres nommes (ASSUMPTION).
// Unites : mm. Export : STL + VDB.

using System;
using System.IO;
using System.Numerics;
using PicoGK;

namespace M64DigitalTwin
{
    public class LayoutParameters
    {
        // FACT_public — brochure 993 Turbo 1995
        // (SRC-PORSCHE-UK-993-TURBO-BROCHURE-1995)
        public float fBoreMm = 100.0f;
        public float fStrokeMm = 76.4f;

        // FACT_public — nomenclature 993
        // (SRC-PORSCHE-993-US-PARTS-GUIDE-ENGINE-CYLINDERS)
        public int nCylinders = 6;
        public int nHeadStudsPerHead = 12;          // goujons M8x22 par culasse
        public float fHeadJointOringDiaMm = 102.0f; // O-ring pied de cylindre

        // ASSUMPTION provisoires (ordre de grandeur uniquement) ; a promouvoir
        // via M64-ACQ-0002 (scan culasse) / M64-ACQ-0005 (scan ventilateur).
        public float fCylinderHeightMm = 170.0f;
        public float fCylinderWallMm = 8.0f;
        public float fHeadEnvelopeH = 160.0f;
        public float fFanEnvelopeDia = 420.0f;
        public float fTurboEnvelopeR = 130.0f;
        public float fSumpEnvelopeH = 170.0f;

        // ASSUMPTION : stations des paliers de cylindres (entraxe non public,
        // M64-ACQ-0004). Espacement provisoire = course + jeu.
        public float fBankStationX = 216.0f;
    }

    public static class EngineLayout
    {
        public static Lattice LayoutLattice(LayoutParameters P)
        {
            Lattice lat = new(Library.oLibrary());

            // Carter : poutre axiale le long du vilebrequin (axe X).
            lat.AddBeam(new Vector3(-550, 0, 0), new Vector3(550, 0, 0),
                        200.0f, 200.0f, false);

            // Culasses : une par palier, au-dessus du carter.
            foreach (float x in new[] { -P.fBankStationX, P.fBankStationX })
                lat.AddSphere(new Vector3(x, 0, 300), 180.0f);

            // Six cylindres : trois par palier (espacement = course + jeu, ASSUMPTION).
            float[] aY = { -(P.fStrokeMm + 10), 0, P.fStrokeMm + 10 };
            foreach (float x in new[] { -P.fBankStationX, P.fBankStationX })
                foreach (float y in aY)
                    lat.AddBeam(    new Vector3(x, y, 120),
                                    new Vector3(x, y, 120 + P.fCylinderHeightMm),
                                    P.fBoreMm / 2.0f + P.fCylinderWallMm,
                                    P.fBoreMm / 2.0f + P.fCylinderWallMm,
                                    false);

            // Ventilateur a l'avant (X negatif), disque axial (ASSUMPTION).
            lat.AddBeam(    new Vector3(-620, 0, 150),
                            new Vector3(-620 - 90, 0, 150),
                            P.fFanEnvelopeDia / 2.0f,
                            P.fFanEnvelopeDia / 2.0f,
                            false);

            // Turbos : un par palier, en retrait arriere lateral (ASSUMPTION).
            lat.AddSphere(new Vector3(-330, 190, -60), P.fTurboEnvelopeR);
            lat.AddSphere(new Vector3( 330, 190, -60), P.fTurboEnvelopeR);

            // Carter d'huile sec sous le carter (ASSUMPTION).
            lat.AddBeam(    new Vector3(0, 0, -200),
                            new Vector3(0, 0, -200 - P.fSumpEnvelopeH),
                            220.0f, 180.0f, false);

            return lat;
        }

        public static void Run()
        {
            try
            {
                LayoutParameters P = new();
                Library.Log("M64 layout scaffold (F1_envelope)\n");

                Lattice lat = LayoutLattice(P);
                Voxels voxLayout = new(lat);
                Mesh msh = new(voxLayout);

                string strOut = Environment.GetEnvironmentVariable("M64_OUT_DIR")
                                ?? "/build/picogk/out";
                Directory.CreateDirectory(strOut);

                msh.SaveToStlFile(Path.Combine(strOut, "m64-engine-layout.stl"));
                voxLayout.SaveToVdbFile(Path.Combine(strOut, "m64-engine-layout.vdb"));

                Library.Log("M64 layout exporte : " + strOut + "\n");
                Library.EndTask();
            }
            catch (Exception e)
            {
                Library.Log("ERREUR : " + e.Message + "\n");
                Library.EndTask();
                throw;
            }
        }

        public static void Main(string[] aArgs)
        {
            // 5 mm de voxel : suffisant pour des enveloppes, rapide a calculer.
            // Log dans le meme dossier que les exports (pas de repertoire
            // Documents dans le conteneur de calcul sans GUI).
            string strOut = Environment.GetEnvironmentVariable("M64_OUT_DIR")
                            ?? "/build/picogk/out";
            Directory.CreateDirectory(strOut);
            Library.Go(5.0f, Run,
                       strLogFilePath: Path.Combine(strOut, "m64-layout.log"),
                       bEndAppWithTask: true,
                       strWindowTitle: "M64 Engine Layout");
        }
    }
}

// SPDX-License-Identifier: GPL-3.0-or-later
// Positive, shared-face tetrahedra using OpenFOAM's own cell centres and face bases.
#include "argList.H"
#include "Time.H"
#include "fvMesh.H"
#include "OFstream.H"
#include <cmath>

using namespace Foam;

int main(int argc, char *argv[])
{
    argList::addOption("output", "file", "New Gmsh 2.2 output path");
    #include "setRootCase.H"
    #include "createTime.H"
    #include "createMesh.H"
    const fileName path(args.option("output"));
    if (isFile(path)) FatalErrorInFunction << "Output already exists" << exit(FatalError);
    const pointField& points = mesh.points();
    const vectorField& centres = mesh.cellCentres();
    const faceList& faces = mesh.faces();
    const labelList& base = mesh.tetBasePtIs();
    label nTets = 0, nBoundary = 0;
    forAll(faces, fi)
    {
        if (base[fi] < 0) FatalErrorInFunction << "No positive face basis: " << fi << exit(FatalError);
        nTets += (faces[fi].size() - 2) * (fi < mesh.nInternalFaces() ? 2 : 1);
        if (fi >= mesh.nInternalFaces()) nBoundary += faces[fi].size() - 2;
    }
    OFstream out(path); out.precision(17);
    out << "$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$PhysicalNames\n4\n"
        << "3 1 \"coolant\"\n2 101 \"inlet\"\n2 102 \"outlet\"\n2 103 \"walls\"\n$EndPhysicalNames\n"
        << "$Nodes\n" << points.size() + centres.size() << '\n';
    forAll(points, i) out << i + 1 << ' ' << points[i].x() << ' ' << points[i].y() << ' ' << points[i].z() << '\n';
    forAll(centres, i) out << points.size() + i + 1 << ' ' << centres[i].x() << ' ' << centres[i].y() << ' ' << centres[i].z() << '\n';
    out << "$EndNodes\n$Elements\n" << nTets + nBoundary << '\n';
    label element = 0;
    scalar totalVolume = 0, minimumVolume = GREAT;
    auto tetra = [&](label cell, label a, label b, label c)
    {
        const vector origin = centres[cell];
        const scalar volume = ((points[a] - origin) & ((points[b] - origin) ^ (points[c] - origin))) / 6;
        if (volume <= 0 || !std::isfinite(volume))
            FatalErrorInFunction << "Nonpositive native tetrahedron in cell " << cell << exit(FatalError);
        totalVolume += volume; minimumVolume = min(minimumVolume, volume);
        out << ++element << " 4 2 1 1 " << points.size() + cell + 1 << ' '
            << a + 1 << ' ' << b + 1 << ' ' << c + 1 << '\n';
    };
    forAll(faces, fi)
    {
        const face& f = faces[fi];
        const label a = f[base[fi]];
        for (label i = 1; i + 1 < f.size(); ++i)
        {
            const label b = f[(base[fi] + i) % f.size()], c = f[(base[fi] + i + 1) % f.size()];
            tetra(mesh.faceOwner()[fi], a, b, c);
            if (fi < mesh.nInternalFaces()) tetra(mesh.faceNeighbour()[fi], a, c, b);
        }
    }
    for (label fi = mesh.nInternalFaces(); fi < faces.size(); ++fi)
    {
        const face& f = faces[fi];
        const word name = mesh.boundaryMesh()[mesh.boundaryMesh().whichPatch(fi)].name();
        const label tag = name == "inlet" ? 101 : name == "outlet" ? 102 : name == "walls" ? 103 : -1;
        if (tag < 0) FatalErrorInFunction << "Unexpected patch " << name << exit(FatalError);
        for (label i = 1; i + 1 < f.size(); ++i)
            out << ++element << " 2 2 " << tag << ' ' << tag << ' ' << f[base[fi]] + 1 << ' '
                << f[(base[fi] + i) % f.size()] + 1 << ' ' << f[(base[fi] + i + 1) % f.size()] + 1 << '\n';
    }
    out << "$EndElements\n";
    const scalar parentVolume = sum(mesh.cellVolumes());
    const scalar relativeDifference = mag(totalVolume / parentVolume - 1);
    Info << "Native tetrahedra: " << nTets << "; minimum volume: " << minimumVolume
         << "; sum: " << totalVolume << "; parent: " << parentVolume
         << "; relative volume difference: " << relativeDifference << nl;
    if (relativeDifference > 1e-3)
        FatalErrorInFunction << "Representation volume error exceeds 0.1 percent" << exit(FatalError);
    Info << "End" << nl;
    return 0;
}

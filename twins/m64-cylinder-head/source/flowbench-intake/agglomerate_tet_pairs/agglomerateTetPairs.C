// SPDX-License-Identifier: GPL-3.0-or-later
// OpenFOAM 14 companion utility. No solver and no mesh-quality waiver.
// API references, revision 7b05503f98a85be88af930df48623b4d152bfc35:
// src/polyTopoChange/polyTopoChange/polyTopoChange.H (modifyFace/removeFace/
// removeCell/changeMesh); applications/utilities/mesh/advanced/removeFaces.
// Unlike removeFaces, never remove points or merge any retained faces.
#include "argList.H"
#include "Time.H"
#include "fvMesh.H"
#include "faceSet.H"
#include "polyTopoChange.H"
#include "polyTopoChangeMap.H"
#include "labelIOList.H"
#include "HashSet.H"
#include "ListOps.H"
#include "OSspecific.H"

using namespace Foam;

static void writeMap(const word& name, const labelList& values, const Time& runTime)
{
    labelIOList object
    (
        IOobject(name, "agglomerationMaps", runTime,
                 IOobject::NO_READ, IOobject::NO_WRITE, false),
        values
    );
    if (!object.write())
    {
        FatalErrorInFunction << "Cannot write " << name << exit(FatalError);
    }
}

int main(int argc, char *argv[])
{
    argList::noParallel();
    #include "addNoOverwriteOption.H"
    #include "addRegionOption.H"
    #include "addMeshOption.H"
    argList::validArgs.append("faceSet");
    #include "setRootCaseNoFunctionObjects.H"
    #include "createTimeNoFunctionObjects.H"
    #include "setNoOverwrite.H"
    #include "createSpecifiedMeshNoChangers.H"

    const fileName mapsPath(runTime.path()/"agglomerationMaps");
    if (isDir(mapsPath))
    {
        FatalErrorInFunction << "Use a fresh private case; agglomerationMaps exists"
            << exit(FatalError);
    }
    const word oldInstance(mesh.pointsInstance());
    forAll(mesh.poly().boundary(), patchi)
    {
        if (mesh.poly().boundary()[patchi].coupled())
        {
            FatalErrorInFunction << "Only serial uncoupled patches are supported"
                << exit(FatalError);
        }
    }
    faceSet requested(mesh, args[1]);
    labelList selected(requested.toc());
    sort(selected);
    if (selected.empty())
    {
        FatalErrorInFunction << "Nonempty internal faceSet required" << exit(FatalError);
    }

    const label oldNCells = mesh.nCells();
    const label oldNFaces = mesh.nFaces();
    const label oldNInternalFaces = mesh.nInternalFaces();
    const pointField oldPoints(mesh.points());
    labelList master(oldNCells);
    boolList used(oldNCells, false), removedFace(oldNFaces, false);
    forAll(master, celli) master[celli] = celli;

    // Validate the complete request before any topology action.
    forAll(selected, i)
    {
        const label facei = selected[i];
        if (facei < 0 || facei >= oldNInternalFaces)
        {
            FatalErrorInFunction << "Selected face is not strictly internal: "
                << facei << exit(FatalError);
        }
        const label own = mesh.faceOwner()[facei];
        const label nei = mesh.faceNeighbour()[facei];
        if (own == nei || used[own] || used[nei])
        {
            FatalErrorInFunction << "Pairs must be disjoint: " << facei << exit(FatalError);
        }
        for (label side = 0; side < 2; ++side)
        {
            const label celli = side == 0 ? own : nei;
            const cell& faces = mesh.cells()[celli];
            labelHashSet vertices;
            if (faces.size() != 4)
            {
                FatalErrorInFunction << "Input cell is not tetrahedral: "
                    << celli << exit(FatalError);
            }
            forAll(faces, j)
            {
                const face& f = mesh.faces()[faces[j]];
                if (f.size() != 3)
                {
                    FatalErrorInFunction << "Input tetra face is not triangular"
                        << exit(FatalError);
                }
                forAll(f, k) vertices.insert(f[k]);
            }
            if (vertices.size() != 4 || mesh.cellVolumes()[celli] <= 0)
            {
                FatalErrorInFunction << "Input tetra vertices/volume invalid"
                    << exit(FatalError);
            }
        }
        // Deleting a faceZone member or merging distinct cell memberships
        // would not preserve the meaning of those zones.
        forAll(mesh.faceZones(), zonei)
        {
            if (mesh.faceZones()[zonei].localIndex(facei) >= 0)
            {
                FatalErrorInFunction << "Cannot remove a faceZone member" << exit(FatalError);
            }
        }
        forAll(mesh.cellZones(), zonei)
        {
            const bool inOwn = mesh.cellZones()[zonei].localIndex(own) >= 0;
            const bool inNei = mesh.cellZones()[zonei].localIndex(nei) >= 0;
            if (inOwn != inNei)
            {
                FatalErrorInFunction << "Cannot merge different cellZone memberships"
                    << exit(FatalError);
            }
        }
        used[own] = used[nei] = true;
        master[max(own, nei)] = min(own, nei);
        removedFace[facei] = true;
    }

    polyTopoChange changes(mesh, true);
    forAll(selected, i) changes.removeFace(selected[i], -1);
    forAll(mesh.faces(), facei)
    {
        if (removedFace[facei]) continue;
        const label oldOwn = mesh.faceOwner()[facei];
        const label oldNei = facei < oldNInternalFaces ? mesh.faceNeighbour()[facei] : -1;
        const label own = master[oldOwn];
        const label nei = oldNei >= 0 ? master[oldNei] : -1;
        if (own == nei)
        {
            FatalErrorInFunction << "Unrequested face internal to one merged pair"
                << exit(FatalError);
        }
        if (own == oldOwn && nei == oldNei) continue;
        const label patchi = oldNei < 0 ? mesh.poly().boundary().whichPatch(facei) : -1;
        if (nei >= 0 && own > nei)
        {
            changes.modifyFace(mesh.faces()[facei].reverseFace(), facei,
                               nei, own, true, patchi);
        }
        else
        {
            changes.modifyFace(mesh.faces()[facei], facei, own, nei, false, patchi);
        }
    }
    forAll(master, celli)
    {
        if (master[celli] != celli) changes.removeCell(celli, master[celli]);
    }
    autoPtr<polyTopoChangeMap> map = changes.changeMesh(mesh, false, false, false);
    mesh.topoChange(map);

    if (mesh.nCells() != oldNCells - selected.size()
     || mesh.nFaces() != oldNFaces - selected.size()
     || mesh.nInternalFaces() != oldNInternalFaces - selected.size()
     || mesh.nPoints() != oldPoints.size()
     || map().pointMap().size() != mesh.nPoints()
     || map().faceMap().size() != mesh.nFaces()
     || map().cellMap().size() != mesh.nCells()
     || map().reverseCellMap().size() != oldNCells)
    {
        FatalErrorInFunction << "Unexpected topology counts after pair agglomeration"
            << exit(FatalError);
    }
    boolList seenPoint(oldPoints.size(), false), seenFace(oldNFaces, false);
    forAll(map().pointMap(), pointi)
    {
        const label old = map().pointMap()[pointi];
        if (old < 0 || old >= oldPoints.size() || seenPoint[old])
        {
            FatalErrorInFunction << "Point map is not a bijection" << exit(FatalError);
        }
        seenPoint[old] = true;
        for (direction d = 0; d < 3; ++d)
        {
            if (mesh.points()[pointi][d] != oldPoints[old][d])
            {
                FatalErrorInFunction << "Point coordinate changed" << exit(FatalError);
            }
        }
    }
    forAll(map().faceMap(), facei)
    {
        const label old = map().faceMap()[facei];
        if (old < 0 || old >= oldNFaces || removedFace[old] || seenFace[old])
        {
            FatalErrorInFunction << "Retained face map invalid" << exit(FatalError);
        }
        seenFace[old] = true;
    }
    labelList oldCellToNewCell(oldNCells);
    forAll(master, celli)
    {
        const label newCell = map().reverseCellMap()[master[celli]];
        if (newCell < 0 || newCell >= mesh.nCells() || map().cellMap()[newCell] != master[celli])
        {
            FatalErrorInFunction << "Resolved old-to-new cell map invalid" << exit(FatalError);
        }
        oldCellToNewCell[celli] = newCell;
    }

    if (!overwrite) runTime++;
    else mesh.setInstance(oldInstance);
    if (!mesh.write())
    {
        FatalErrorInFunction << "Mesh write failed" << exit(FatalError);
    }
    writeMap("m64PointMap", map().pointMap(), runTime);
    writeMap("m64FaceMap", map().faceMap(), runTime);
    writeMap("m64CellMap", map().cellMap(), runTime);
    writeMap("m64OldCellToNewCell", oldCellToNewCell, runTime);
    Info<< "Agglomerated " << selected.size() << " disjoint tetra pairs." << nl
        << "Maps: agglomerationMaps (first three new-to-old; last old-to-new)." << nl
        << "Existing topoSets are NOT remapped; use mapped mesh zones and exported maps." << nl
        << "No point movement or retained-face merging. Quality/convexity require independent review." << nl
        << "No CFD or manufacturing authorization." << endl;
    return 0;
}

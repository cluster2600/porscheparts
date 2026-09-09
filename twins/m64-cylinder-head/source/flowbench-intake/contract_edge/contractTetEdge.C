// SPDX-License-Identifier: GPL-3.0-or-later
// One directed tetra-edge contraction. Diagnostic only; no quality waiver.
// OpenFOAM Foundation 14, 7b05503f98a85be88af930df48623b4d152bfc35.
// Uses the polyTopoChange API already compiled in m64AgglomerateTetGroups.
// Unlike setting edgeCollapser::allowCellCollapse=true, explicitly reconnects
// the surviving coincident faces of every removed tetrahedron.
#include "argList.H"
#include "Time.H"
#include "fvMesh.H"
#include "polyTopoChange.H"
#include "polyTopoChangeMap.H"
#include "labelIOList.H"
#include "OSspecific.H"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <iterator>
#include <map>
#include <set>
#include <vector>

using namespace Foam;
using Key = std::array<label, 3>;
using Simplex = std::vector<label>;
using Complex = std::set<Simplex>;

static void demand(bool ok, const char* text)
{
    if (!ok) { FatalErrorInFunction << text << exit(FatalError); }
}
static Key key(const face& f)
{
    demand(f.size() == 3, "Affected face must be triangular");
    Key k{{f[0], f[1], f[2]}}; std::sort(k.begin(), k.end()); return k;
}
static bool cyclic(const face& a, const face& b)
{
    if (a.size() != b.size()) return false;
    forAll(a, shift)
    {
        bool same = true;
        forAll(a, i) same = same && a[i] == b[(i+shift)%b.size()];
        if (same) return true;
    }
    return false;
}
static void addLink(Complex& result, Simplex vertices)
{
    std::sort(vertices.begin(), vertices.end());
    for (unsigned mask=1; mask < (1u << vertices.size()); ++mask)
    {
        Simplex subset;
        for (unsigned i=0; i<vertices.size(); ++i)
            if (mask & (1u << i)) subset.push_back(vertices[i]);
        result.insert(subset);
    }
}
static void links(const Simplex& v, label A, label B,
                  Complex& la, Complex& lb, Complex& lab)
{
    bool a = std::find(v.begin(),v.end(),A) != v.end();
    bool b = std::find(v.begin(),v.end(),B) != v.end();
    Simplex withoutA, withoutB, withoutBoth;
    for (label p : v)
    {
        if (p != A) withoutA.push_back(p);
        if (p != B) withoutB.push_back(p);
        if (p != A && p != B) withoutBoth.push_back(p);
    }
    if (a) addLink(la,withoutA);
    if (b) addLink(lb,withoutB);
    if (a && b) addLink(lab,withoutBoth);
}
static void checkLink(const Complex& a, const Complex& b, const Complex& ab)
{
    Complex common;
    std::set_intersection(a.begin(),a.end(),b.begin(),b.end(),
                          std::inserter(common,common.end()));
    demand(common == ab, "Simplicial edge link condition failed");
}
static scalar side(const face& f, label opposite, const pointField& p)
{
    return ((p[f[1]]-p[f[0]]) ^ (p[f[2]]-p[f[0]]))
         & (p[opposite]-p[f[0]]);
}
static void writeMap(const word& name, const labelList& values, const Time& t)
{
    labelIOList object(IOobject(name,"contractionMaps",t,
        IOobject::NO_READ,IOobject::NO_WRITE,false),values);
    demand(object.write(), "Cannot write contraction map");
}
struct Plan
{
    face vertices;
    label owner, neighbour, patch;
    Plan(const face& f, label o, label n, label p)
    : vertices(f), owner(o), neighbour(n), patch(p) {}
};

int main(int argc, char *argv[])
{
    argList::noParallel();
    #include "addNoOverwriteOption.H"
    #include "addRegionOption.H"
    #include "addMeshOption.H"
    argList::validArgs.append("sourcePointA");
    argList::validArgs.append("targetPointB");
    argList::validArgs.append("maximumDistanceInMeshUnits");
    #include "setRootCaseNoFunctionObjects.H"
    #include "createTimeNoFunctionObjects.H"
    #include "setNoOverwrite.H"
    #include "createSpecifiedMeshNoChangers.H"
    const label A=args.argRead<label>(1), B=args.argRead<label>(2);
    const scalar limit=args.argRead<scalar>(3);
    const pointField points(mesh.points());
    const faceList sourceFaces(mesh.faces());
    const labelList sourceOwner(mesh.faceOwner()), sourceNeighbour(mesh.faceNeighbour());
    labelList sourcePatch(mesh.nFaces(),-1);
    for (label f=mesh.nInternalFaces();f<mesh.nFaces();++f)
        sourcePatch[f]=mesh.poly().boundary().whichPatch(f);
    wordList patchNames(mesh.poly().boundary().size()),patchTypes(patchNames.size());
    forAll(patchNames,p) {patchNames[p]=mesh.poly().boundary()[p].name(); patchTypes[p]=mesh.poly().boundary()[p].type();}
    const label nc=mesh.nCells(), nf=mesh.nFaces(), ni=mesh.nInternalFaces();
    const word oldInstance(mesh.pointsInstance());
    demand(!isDir(runTime.path()/"contractionMaps"), "Fresh case required");
    demand(A>=0 && B>=0 && A<points.size() && B<points.size() && A!=B,
           "Two distinct existing point labels required");
    demand(std::isfinite(limit) && limit>0, "Finite positive distance cap required");
    forAll(points,p) for (direction d=0;d<3;++d)
        demand(std::isfinite(points[p][d]), "Nonfinite source coordinate");
    const scalar distance=mag(points[A]-points[B]);
    demand(std::isfinite(distance) && distance<=limit, "Distance cap exceeded");
    forAll(mesh.poly().boundary(),p)
        demand(!mesh.poly().boundary()[p].coupled(), "Coupled patches unsupported");
    forAll(mesh.pointZones(),z) demand(mesh.pointZones()[z].empty(), "Point zones unsupported");
    forAll(mesh.faceZones(),z) demand(mesh.faceZones()[z].empty(), "Face zones unsupported");
    demand(mesh.cellZones().size()==1 && mesh.cellZones()[0].name()=="air",
           "Unique air cell zone required");
    demand(mesh.cellZones()[0].size()==nc, "Air zone must cover every source cell");
    boolList zoneSeen(nc,false);
    forAll(mesh.cellZones()[0],i)
    {
        label c=mesh.cellZones()[0][i];
        demand(c>=0 && c<nc && !zoneSeen[c], "Invalid air membership"); zoneSeen[c]=true;
    }

    boolList removedCell(nc,false), affectedCell(nc,false), removedFace(nf,false);
    std::map<label,Simplex> tets;
    Complex la,lb,lab,ba,bb,bab;
    label nRemovedCells=0;
    // Scan cell connectivity, not geometric proximity or old anatomical labels.
    forAll(mesh.cells(),c)
    {
        std::set<label> nodes;
        const cell& fs=mesh.cells()[c];
        forAll(fs,i) forAll(mesh.faces()[fs[i]],j) nodes.insert(mesh.faces()[fs[i]][j]);
        if (!nodes.count(A) && !nodes.count(B)) continue;
        demand(fs.size()==4 && nodes.size()==4, "Endpoint incident cell is not a tetrahedron");
        Simplex v(nodes.begin(),nodes.end());
        std::set<Key> actual, expected;
        for (unsigned omit=0;omit<4;++omit)
        {
            Key k; unsigned j=0;
            for (unsigned i=0;i<4;++i) if (i!=omit) k[j++]=v[i];
            expected.insert(k);
        }
        forAll(fs,i)
        {
            label fid=fs[i]; const face& f=mesh.faces()[fid]; actual.insert(key(f));
            label opposite=-1;
            for (label p:v) if (std::find(f.begin(),f.end(),p)==f.end()) opposite=p;
            demand(opposite>=0,"Invalid tetrahedron face");
            face outward=mesh.faceOwner()[fid]==c ? f : f.reverseFace();
            scalar d=side(outward,opposite,points);
            demand(std::isfinite(d) && d<0,"Source tetrahedron orientation invalid");
        }
        demand(actual==expected,"Incomplete or repeated tetrahedron faces");
        tets[c]=v; affectedCell[c]=true; links(v,A,B,la,lb,lab);
        if (nodes.count(A) && nodes.count(B)) {removedCell[c]=true; ++nRemovedCells;}
    }
    demand(nRemovedCells>0 && nRemovedCells<nc,"Existing edge with surviving domain required");
    checkLink(la,lb,lab);

    std::map<Key,std::vector<label>> groups;
    bool boundaryA=false,boundaryB=false,boundaryAB=false;
    forAll(mesh.faces(),f)
    {
        const face& original=mesh.faces()[f];
        bool hasA=false,hasB=false;
        forAll(original,i) {hasA |= original[i]==A; hasB |= original[i]==B;}
        if (!hasA && !hasB) continue;
        demand(original.size()==3,"Endpoint face must be triangular");
        if (f>=ni)
        {
            boundaryA |= hasA; boundaryB |= hasB; boundaryAB |= hasA && hasB;
            Simplex v(original.begin(),original.end()); links(v,A,B,ba,bb,bab);
        }
        if (hasA && hasB)
        {
            demand(removedCell[mesh.faceOwner()[f]] &&
                (f>=ni || removedCell[mesh.faceNeighbour()[f]]),
                "Degenerate face still bounds a live cell");
            removedFace[f]=true;
        }
        else
        {
            face mapped(original); forAll(mapped,i) if (mapped[i]==A) mapped[i]=B;
            groups[key(mapped)].push_back(f);
        }
    }
    demand(!(boundaryA && boundaryB) || boundaryAB,
           "Interior edge connecting two boundary points is unsupported");
    if (boundaryA && boundaryB) checkLink(ba,bb,bab);

    std::map<label,Plan> plans;
    labelList faceRepresentative(nf); forAll(faceRepresentative,f) faceRepresentative[f]=f;
    for (const auto& item:groups)
    {
        const std::vector<label>& ids=item.second;
        demand(ids.size()<=2,"More than two coincident source triangles");
        std::map<label,face> live;
        std::set<label> patches;
        std::vector<face> boundaryOrientations;
        unsigned boundaryRecords=0;
        for (label f:ids)
        {
            face mapped(mesh.faces()[f]); forAll(mapped,i) if (mapped[i]==A) mapped[i]=B;
            const label own=mesh.faceOwner()[f];
            if (!removedCell[own]) demand(live.emplace(own,mapped).second,"Repeated live cell on coincident face");
            if (f<ni)
            {
                label nei=mesh.faceNeighbour()[f];
                if (!removedCell[nei]) demand(live.emplace(nei,mapped.reverseFace()).second,"Repeated live neighbour");
            }
            else {patches.insert(mesh.poly().boundary().whichPatch(f)); ++boundaryRecords; boundaryOrientations.push_back(mapped);}
        }
        demand(live.size()==1 || live.size()==2,"Invalid number of surviving face incidences");
        label own=live.begin()->first, nei=-1, patch=-1;
        face oriented=live.begin()->second;
        if (live.size()==2)
        {
            auto next=std::next(live.begin()); nei=next->first;
            demand(patches.empty(),"Boundary/internal face pairing is ambiguous");
            demand(cyclic(oriented,next->second.reverseFace()),"Coincident faces have inconsistent orientation");
        }
        else
        {
            demand(patches.size()==1 && boundaryRecords==1,"Boundary patch provenance is ambiguous");
            demand(cyclic(oriented,boundaryOrientations.front()),"Transferred boundary orientation differs");
            patch=*patches.begin();
        }
        label representative=*std::min_element(ids.begin(),ids.end());
        plans.emplace(representative,Plan(oriented,own,nei,patch));
        for (label f:ids)
        {
            faceRepresentative[f]=representative;
            if (f!=representative) removedFace[f]=true;
        }
    }

    std::set<Simplex> survivingTets;
    for (const auto& item:tets)
    {
        label c=item.first; if (removedCell[c]) continue;
        Simplex v=item.second; for (label& p:v) if (p==A) p=B;
        std::sort(v.begin(),v.end());
        demand(std::adjacent_find(v.begin(),v.end())==v.end() && survivingTets.insert(v).second,
               "Duplicate or degenerate surviving tetrahedron");
        // Only A moves. Every oriented determinant is affine along A -> B;
        // Exact strict endpoint signs would protect the straight path. These
        // native binary64 evaluations are screens, not a rational certificate.
        for (unsigned omit=0;omit<4;++omit)
        {
            const cell& fs=mesh.cells()[c]; label sourceFace=fs[omit];
            face f=mesh.faceOwner()[sourceFace]==c ? mesh.faces()[sourceFace] : mesh.faces()[sourceFace].reverseFace();
            forAll(f,i) if (f[i]==A) f[i]=B;
            label opposite=-1; for (label p:v) if (std::find(f.begin(),f.end(),p)==f.end()) opposite=p;
            demand(opposite>=0,"Missing candidate opposite vertex");
            scalar d=side(f,opposite,points);
            demand(std::isfinite(d) && d<0,"Candidate inverts or flattens a surviving tetrahedron");
        }
    }

    boolList usedPoint(points.size(),false);
    labelList cellFaceCount(nc,0), patchFaceCount(mesh.poly().boundary().size(),0);
    std::map<std::array<label,2>,std::pair<label,label>> boundaryEdges;
    label nRemovedFaces=0, expectedInternal=0;
    forAll(mesh.faces(),fid)
    {
        if (removedFace[fid]) {++nRemovedFaces; continue;}
        auto it=plans.find(fid);
        face f=it==plans.end() ? mesh.faces()[fid] : it->second.vertices;
        label own=it==plans.end() ? mesh.faceOwner()[fid] : it->second.owner;
        label nei=it==plans.end() ? (fid<ni ? mesh.faceNeighbour()[fid] : -1) : it->second.neighbour;
        label patch=it==plans.end() ? (fid>=ni ? mesh.poly().boundary().whichPatch(fid) : -1) : it->second.patch;
        demand(own>=0 && !removedCell[own] && (nei<0 || (!removedCell[nei] && own!=nei)),
               "Retained face references a deleted cell");
        ++cellFaceCount[own]; if (nei>=0) {++cellFaceCount[nei]; ++expectedInternal;}
        else
        {
            demand(patch>=0,"Boundary face lost its patch"); ++patchFaceCount[patch];
            forAll(f,i)
            {
                label x=f[i],y=f[(i+1)%f.size()];
                std::array<label,2> k{{std::min(x,y),std::max(x,y)}};
                auto& count=boundaryEdges[k]; ++count.first; count.second += x<y ? 1 : -1;
            }
        }
        forAll(f,i) {demand(f[i]!=A,"Source point still referenced"); usedPoint[f[i]]=true;}
    }
    forAll(usedPoint,p) demand(p==A || usedPoint[p],"Contraction would orphan another point");
    forAll(cellFaceCount,c) demand(removedCell[c] ? cellFaceCount[c]==0 :
        (affectedCell[c] ? cellFaceCount[c]==4 : cellFaceCount[c]==mesh.cells()[c].size()),
        "Unexpected surviving cell boundary size");
    for (const auto& item:boundaryEdges)
        demand(item.second.first==2 && item.second.second==0,"Candidate exterior is not an oriented closed edge-manifold");
    forAll(patchFaceCount,p) demand(mesh.poly().boundary()[p].empty() || patchFaceCount[p]>0,
        "Contraction would erase an entire boundary patch");

    // No topology actions occur before every precondition above succeeds.
    polyTopoChange changes(mesh,true);
    forAll(removedFace,f) if (removedFace[f]) changes.removeFace(f,-1);
    for (const auto& item:plans)
    {
        const Plan& p=item.second;
        // No solver fields are loaded. flipFlux tracks orientation; point-label
        // substitution itself is not an orientation reversal.
        face oldMapped(mesh.faces()[item.first]); forAll(oldMapped,i) if (oldMapped[i]==A) oldMapped[i]=B;
        changes.modifyFace(p.vertices,item.first,p.owner,p.neighbour,
                           !cyclic(oldMapped,p.vertices),p.patch);
    }
    forAll(removedCell,c) if (removedCell[c]) changes.removeCell(c,-1);
    changes.removePoint(A,B);
    autoPtr<polyTopoChangeMap> map=changes.changeMesh(mesh,false,false,false);
    mesh.topoChange(map);
    demand(mesh.nPoints()==points.size()-1 && mesh.nCells()==nc-nRemovedCells &&
        mesh.nFaces()==nf-nRemovedFaces && mesh.nInternalFaces()==expectedInternal,
        "Unexpected native contraction counts");
    demand(map().pointMap().size()==mesh.nPoints() &&
        map().faceMap().size()==mesh.nFaces() && map().cellMap().size()==mesh.nCells(),
        "Native map sizes differ from mesh");
    labelList oldPointToNew(points.size(),-1),oldFaceToNew(nf,-1),oldCellToNew(nc,-1);
    forAll(map().pointMap(),p)
    {
        label old=map().pointMap()[p];
        demand(old>=0 && old<points.size() && old!=A && oldPointToNew[old]<0,"Invalid retained point map");
        oldPointToNew[old]=p;
        for (direction d=0;d<3;++d)
        {
            const scalar x=mesh.points()[p][d],y=points[old][d];
            demand(std::memcmp(&x,&y,sizeof(scalar))==0,"A retained coordinate changed bits");
        }
    }
    demand(oldPointToNew[B]>=0,"Target point disappeared"); oldPointToNew[A]=oldPointToNew[B];
    forAll(map().cellMap(),c)
    {
        label old=map().cellMap()[c];
        demand(old>=0 && old<nc && !removedCell[old] && oldCellToNew[old]<0,"Invalid retained cell map");
        oldCellToNew[old]=c;
    }
    forAll(map().faceMap(),f)
    {
        label old=map().faceMap()[f];
        demand(old>=0 && old<nf && !removedFace[old] && oldFaceToNew[old]<0,"Invalid retained face map");
        oldFaceToNew[old]=f;
        auto it=plans.find(old);
        face expected=it==plans.end() ? sourceFaces[old] : it->second.vertices;
        forAll(expected,i) expected[i]=oldPointToNew[expected[i]];
        demand(expected==mesh.faces()[f],"Native ordered face differs from plan");
        label own=it==plans.end() ? sourceOwner[old] : it->second.owner;
        label nei=it==plans.end() ? (old<ni ? sourceNeighbour[old] : -1) : it->second.neighbour;
        label patch=it==plans.end() ? sourcePatch[old] : it->second.patch;
        demand(mesh.faceOwner()[f]==oldCellToNew[own] &&
            (f<mesh.nInternalFaces() ? mesh.faceNeighbour()[f] : -1)==
            (nei<0 ? -1 : oldCellToNew[nei]),"Native face adjacency differs from plan");
        demand((f<mesh.nInternalFaces() ? -1 : mesh.poly().boundary().whichPatch(f))==patch,
               "Native face patch differs from plan");
    }
    forAll(faceRepresentative,f) if (faceRepresentative[f]!=f)
        oldFaceToNew[f]=oldFaceToNew[faceRepresentative[f]];
    demand(mesh.poly().boundary().size()==patchNames.size(),"Patch count changed");
    forAll(patchNames,p) demand(mesh.poly().boundary()[p].name()==patchNames[p] &&
        mesh.poly().boundary()[p].type()==patchTypes[p] &&
        mesh.poly().boundary()[p].size()==patchFaceCount[p],"Patch metadata or count changed");
    demand(mesh.cellZones().size()==1 && mesh.cellZones()[0].name()=="air" &&
        mesh.cellZones()[0].size()==mesh.nCells(),"Air zone changed");
    boolList seenAir(mesh.nCells(),false);
    forAll(mesh.cellZones()[0],i)
    {
        label c=mesh.cellZones()[0][i]; demand(c>=0 && c<mesh.nCells() && !seenAir[c],"Invalid mapped air zone"); seenAir[c]=true;
    }
    if (!overwrite) runTime++; else mesh.setInstance(oldInstance);
    demand(mesh.write(),"Candidate write failed");
    writeMap("m64PointMap",map().pointMap(),runTime);
    writeMap("m64FaceMap",map().faceMap(),runTime);
    writeMap("m64CellMap",map().cellMap(),runTime);
    writeMap("m64OldPointToNewPoint",oldPointToNew,runTime);
    writeMap("m64OldFaceToNewFace",oldFaceToNew,runTime);
    writeMap("m64OldCellToNewCell",oldCellToNew,runTime);
    Info<< "One directed edge contraction prepared: "<<A<<" -> "<<B
        <<"; distance "<<distance<<" <= "<<limit<<" in mesh coordinates."<<nl
        <<"Removed cells "<<nRemovedCells<<"; removed faces "<<nRemovedFaces<<nl
        <<"No solver; no quality, CAD-distance, CFD or manufacturing acceptance."<<endl;
    return 0;
}

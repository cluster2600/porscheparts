// Select disjoint internal-face merges; full checkMesh acceptance remains mandatory.
#include "argList.H"
#include "Time.H"
#include "polyMesh.H"
#include "cellSet.H"
#include "faceSet.H"
using namespace Foam;
int main(int argc, char *argv[]) {
    #include "setRootCase.H"
    #include "createTime.H"
    polyMesh mesh(IOobject(polyMesh::defaultRegion,runTime.name(),runTime,IOobject::MUST_READ));
    cellSet bad(mesh,"underdeterminedCells",IOobject::READ_IF_PRESENT);
    faceSet weights(mesh,"lowWeightFaces",IOobject::READ_IF_PRESENT);
    faceSet selected(mesh,"mergeSlivers",bad.size()+weights.size());
    labelHashSet occupied;
    forAllConstIter(cellSet,bad,it) {
        if(it.key()<0 || it.key()>=mesh.nCells()) FatalErrorInFunction << "Invalid cell index" << exit(FatalError);
        Info << "REFINE_MM " << 1000*mesh.cellCentres()[it.key()] << endl;
        if(occupied.found(it.key())) continue;
        const cell& faces=mesh.cells()[it.key()];
        label best=-1; scalar area=-1;
        forAll(faces,i) {
            label f=faces[i];
            if(f >= mesh.nInternalFaces()) continue;
            label other=mesh.faceOwner()[f]==it.key() ? mesh.faceNeighbour()[f] : mesh.faceOwner()[f];
            if(bad.found(other) || occupied.found(other)) continue;
            scalar a=mag(mesh.faceAreas()[f]);
            if(a>area) {area=a;best=f;}
        }
        if(best>=0) {
            selected.insert(best);occupied.insert(mesh.faceOwner()[best]);occupied.insert(mesh.faceNeighbour()[best]);
        } else Info << "No available pair for cell " << it.key() << endl;
    }
    forAllConstIter(faceSet,weights,it) {
        if(it.key()<0 || it.key()>=mesh.nInternalFaces()) FatalErrorInFunction << "Boundary face cannot be removed" << exit(FatalError);
        label f=it.key(),a=mesh.faceOwner()[f],b=mesh.faceNeighbour()[f];
        if(!occupied.found(a) && !occupied.found(b)) {
            selected.insert(f);occupied.insert(a);occupied.insert(b);
        }
    }
    Info << "Selected " << selected.size() << " internal faces" << endl;
    selected.write();
}

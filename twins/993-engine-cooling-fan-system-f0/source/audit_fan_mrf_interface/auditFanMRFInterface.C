// Fan-specific audit: rotation axis +Z, origin (0 0 0), actual rotorZone labels.
#include "argList.H"
#include "Time.H"
#include "polyMesh.H"
#include "cellZoneList.H"
#include "IOdictionary.H"
using namespace Foam;
int main(int argc, char *argv[]) {
    #include "setRootCase.H"
    #include "createTime.H"
    polyMesh mesh(IOobject(polyMesh::defaultRegion,runTime.name(),runTime,IOobject::MUST_READ));
    IOdictionary properties(IOobject("MRFProperties",runTime.constant(),mesh,IOobject::MUST_READ,IOobject::NO_WRITE));
    const dictionary& mrf=properties.subDict("MRF");
    const vector axis(mrf.lookup("axis")),origin(mrf.lookup("origin"));
    if(mag(axis-vector(0,0,1))>SMALL || mag(origin)>SMALL)
        FatalErrorInFunction << "This fan audit requires +Z and zero origin" << exit(FatalError);
    const word zoneName(mrf.lookup("cellZone"));
    boolList inside(mesh.nCells(),false);label count=0;
    forAll(mesh.cellZones(),z) if(mesh.cellZones()[z].name()==zoneName) {
        const labelList& cells=mesh.cellZones()[z];
        forAll(cells,i) {
            if(cells[i]<0 || cells[i]>=mesh.nCells()) FatalErrorInFunction << "Invalid zone label" << exit(FatalError);
            inside[cells[i]]=true; ++count;
        }
    }
    if(!count) FatalErrorInFunction << "Missing or empty rotorZone" << exit(FatalError);
    label faces=0;scalar area=0,absoluteFlux=0,maximum=0;
    for(label f=0;f<mesh.nInternalFaces();++f) {
        if(inside[mesh.faceOwner()[f]]==inside[mesh.faceNeighbour()[f]]) continue;
        const vector sf=mesh.faceAreas()[f];const scalar a=mag(sf);
        if(a<=0) FatalErrorInFunction << "Nonpositive interface area" << exit(FatalError);
        const scalar flux=mag((vector(0,0,1)^mesh.faceCentres()[f]) & sf);
        ++faces;area+=a;absoluteFlux+=flux;maximum=max(maximum,flux/a);
    }
    Info<<"MRF_AUDIT cells="<<count<<" totalCells="<<mesh.nCells()
        <<" interfaceFaces="<<faces<<" interfaceArea_m2="<<area
        <<" meanNormalSpeed_per_rad_s="<<(area>0?absoluteFlux/area:0)
        <<" maxNormalSpeed_per_rad_s="<<maximum<<endl;
    if(maximum>1e-8) {
        Info<<"MRF REJECTED: internal interface is not tangent to rotation"<<endl;
        return 2;
    }
}

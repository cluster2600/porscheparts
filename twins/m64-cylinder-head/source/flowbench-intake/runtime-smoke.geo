// Synthetic rectangular duct in mm, only for the OpenFOAM runtime pipeline.
// NOT a cylinder head, performance reference, or engine simulation.
SetFactory("OpenCASCADE");
Box(1) = {0, 0, 0, 100, 40, 40};
eps = 0.00001;
inlet[] = Surface In BoundingBox {-eps, -eps, -eps, eps, 40+eps, 40+eps};
outlet[] = Surface In BoundingBox {100-eps, -eps, -eps, 100+eps, 40+eps, 40+eps};
walls[] = Surface{:};
walls[] -= inlet[];
walls[] -= outlet[];
Physical Surface("inlet", 1) = {inlet[]};
Physical Surface("receiver_outlet", 2) = {outlet[]};
Physical Surface("walls", 3) = {walls[]};
Physical Volume("air", 100) = {1};
Mesh.MeshSizeMin = 8;
Mesh.MeshSizeMax = 8;
Mesh.Algorithm = 6;
Mesh.Algorithm3D = 1;
Mesh.MshFileVersion = 2.2;
Mesh.Binary = 0;
Mesh.SaveAll = 0;

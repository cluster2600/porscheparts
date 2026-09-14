// Structured synthetic duct ONLY for boundary-condition/runtime execution.
// Its success does not qualify a tetrahedral or dual mesh of the real head.
SetFactory("OpenCASCADE");
Rectangle(1) = {0, 0, 0, 40, 40};
Transfinite Curve{:} = 6;
Transfinite Surface{1};
Recombine Surface{1};
ext[] = Extrude {0, 0, 100} {Surface{1}; Layers{13}; Recombine;};
eps = 0.00001;
inlet[] = Surface In BoundingBox {-eps, -eps, -eps, 40+eps, 40+eps, eps};
outlet[] = Surface In BoundingBox {-eps, -eps, 100-eps, 40+eps, 40+eps, 100+eps};
walls[] = Surface{:};
walls[] -= inlet[];
walls[] -= outlet[];
Physical Surface("inlet", 1) = {inlet[]};
Physical Surface("receiver_outlet", 2) = {outlet[]};
Physical Surface("walls", 3) = {walls[]};
Physical Volume("air", 100) = {ext[1]};
Mesh.MshFileVersion = 2.2;
Mesh.Binary = 0;
Mesh.SaveAll = 0;

"""Composed vertex-map surface bound without summing disjoint contractions.

Every original triangle maps affinely under its final vertex representatives.
If each discarded degenerate image is covered by retained faces, the image of
all original triangles equals the final surface. Both directed surface
 distances are then bounded by the largest original vertex displacement.
"""
from fractions import Fraction as F


class VertexMap:
    def __init__(self, vertices):
        self.vertices=vertices
        self.clusters={}
        self.maximum=F(0)
        self.cache={}

    def point(self,index):
        if index not in self.cache:self.cache[index]=tuple(F(float(x))for x in self.vertices[index])
        return self.cache[index]

    def distance(self,original,representative):
        return sum(abs(a-b)for a,b in zip(self.point(original),self.point(representative)))

    def proposal(self,keep,remove):
        return max(self.maximum,max(self.distance(i,keep)for i in self.clusters.get(remove,(remove,))))

    def apply(self,keep,remove):
        bound=self.proposal(keep,remove)
        self.clusters[keep]=self.clusters.get(keep,(keep,))+self.clusters.pop(remove,(remove,))
        self.maximum=bound
        return bound

    def certificate(self):
        actual=max([F(0),*[self.distance(i,representative)for representative,originals in self.clusters.items()for i in originals]])
        if actual>self.maximum:raise ValueError('Composed vertex ancestry bound differs')
        return dict(method='Maximum original vertex L1 displacement under the composed representative map; affine images and redundant-image coverage prove both directed surface bounds',conservative_maximum_L1_mm=str(self.maximum),actual_final_vertex_maximum_L1_mm=str(actual),unchanged_vertices_map_identically=True,nontrivial_clusters=[dict(representative=int(k),original_vertices=list(map(int,v)))for k,v in sorted(self.clusters.items())])

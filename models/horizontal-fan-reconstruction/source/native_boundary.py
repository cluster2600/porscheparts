#!/usr/bin/env python3
"""Preserve all C3D10 boundary nodes through oriented linear subtriangles."""
import numpy as np


def boundary(elements, nodes):
    faces = {}
    for e in elements.values():
        center = np.mean([nodes[i] for i in e[:4]],axis=0)
        for inds in ((0,1,2,4,5,6),(0,3,1,7,8,4),(1,3,2,8,9,5),(2,3,0,9,7,6)):
            face = [e[i] for i in inds]
            key = tuple(sorted(face[:3]))
            if key in faces:
                del faces[key]
            else:
                p = np.array([nodes[i] for i in face[:3]])
                reverse = np.dot(np.cross(p[1]-p[0],p[2]-p[0]),p.mean(axis=0)-center)<0
                faces[key] = (face,reverse)
    triangles = []
    for (a,b,c,ab,bc,ca), reverse in faces.values():
        for tri in ((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)):
            triangles.append(tri[::-1] if reverse else tri)
    tags = sorted({v for tri in triangles for v in tri})
    index = {tag:i for i,tag in enumerate(tags)}
    return tags,np.array([[index[t] for t in tri] for tri in triangles],dtype=np.int32)

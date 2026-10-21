"""Write the exact finite prism-free software witness into a fresh folder."""
import argparse
from pathlib import Path
import numpy as np

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);args=p.parse_args()
    out=args.output.resolve();assert not out.exists();out.mkdir(parents=True)
    vertices=np.array([[0,0,10],[20,0,10],[0,20,10],[0,0,20],[20,0,20],[0,20,20]],dtype=np.float64)
    faces=np.array([[0,1,2],[3,4,5]],dtype=np.int64)
    np.savez_compressed(out/'roofs.npz',vertices=vertices,faces=faces,source_face_ids=np.array([41,42],dtype=np.int64))
    faces=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]],dtype=np.int64)
    for name,zlo,zhi in [('mask',-1,21),('part',8,12)]:
        vertices=np.array([[-1,-1,zlo],[21,-1,zlo],[21,21,zlo],[-1,21,zlo],[-1,-1,zhi],[21,-1,zhi],[21,21,zhi],[-1,21,zhi]],dtype=np.float64)
        np.savez_compressed(out/(name+'.npz'),vertices=vertices,faces=faces)

if __name__=='__main__':main()

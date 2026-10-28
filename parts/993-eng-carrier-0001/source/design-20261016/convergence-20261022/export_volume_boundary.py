"""Export the exact stored indexed skin of a volume without coordinate changes."""
import argparse
from pathlib import Path


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--volume',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    import numpy as np
    with np.load(a.volume,allow_pickle=False)as data:v=data['vertices'];faces=data['boundary'];ids,inverse=np.unique(faces,return_inverse=True);skin=v[ids];indexed=inverse.reshape(-1,3)
    with a.output.open('w')as stream:stream.write(f'{len(skin)} {len(indexed)}\n');np.savetxt(stream,skin,fmt='%.17g');np.savetxt(stream,indexed,fmt='%d')
    print('Complete boundary',len(skin),len(indexed))

if __name__=='__main__':main()

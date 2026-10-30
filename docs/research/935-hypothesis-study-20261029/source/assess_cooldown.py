"""Independently integrate native VTU temperatures and convective energy balance."""
import argparse
import base64
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zlib
import numpy as np

def array(item):
    typ={'Float32':'<f4','Float64':'<f8','Int32':'<i4','UInt32':'<u4','UInt8':'u1'}[item.attrib['type']]
    text=''.join((item.text or '').split())
    if item.attrib['format']=='ascii':data=np.fromstring(item.text,sep=' ',dtype=typ)
    else:
        first=np.frombuffer(base64.b64decode(text[:16]),dtype='<u4')
        n=int(first[0]);header_chars=4*((4*(3+n)+2)//3)
        header=np.frombuffer(base64.b64decode(text[:header_chars]),dtype='<u4')
        assert len(header)==3+n
        raw=base64.b64decode(text[header_chars:]);offset=0;blocks=[]
        for size in header[3:]:
            block=zlib.decompress(raw[offset:offset+int(size)]);offset+=int(size);blocks.append(block)
        data=np.frombuffer(b''.join(blocks),dtype=typ)
    components=int(item.attrib.get('NumberOfComponents',1))
    return data.reshape(-1,components) if components>1 else data

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('case',type=Path);p.add_argument('--volume-mm3',type=float,default=1100608);a=p.parse_args()
    rows=[]
    for path in sorted((a.case/'output').glob('cooldown.*.0.vtu'),key=lambda q:int(q.name.split('.')[1])):
        r=ET.parse(path).getroot();piece=r.find('.//Piece');x=array(piece.find('./Points/DataArray'))
        cell={q.attrib['Name']:array(q) for q in piece.findall('./Cells/DataArray')}
        assert np.all(cell['types']==12) and np.all(np.diff(np.r_[0,cell['offsets']])==8)
        conn=cell['connectivity'].reshape(-1,8)
        fields={q.attrib['Name']:array(q) for q in piece.findall('./PointData/DataArray')}
        for q in fields.values():assert np.isfinite(q).all()
        time=float(array(r.find('.//FieldData/DataArray'))[0])
        temp=fields['temperature'];xyz=x[conn];volume=np.prod(np.ptp(xyz,axis=1).astype(float),axis=1)
        assert abs(volume.sum()-a.volume_mm3*1e-9)/(a.volume_mm3*1e-9)<1e-5
        unique,inverse=np.unique(x,axis=0,return_inverse=True)
        local_faces=np.array([[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]])
        faces=conn[:,local_faces].reshape(-1,4)
        _,idx,count=np.unique(np.sort(inverse[faces],axis=1),axis=0,return_index=True,return_counts=True)
        assert count.max()==2
        boundary=faces[idx[count==1]];points=x[boundary]
        area=np.linalg.norm(np.cross(points[:,1]-points[:,0],points[:,3]-points[:,0]),axis=1).astype(float)
        energy=float(np.dot(volume,(temp[conn].mean(axis=1).astype(float)-500))*2670*900)
        loss=float(np.dot(area,temp[boundary].mean(axis=1).astype(float)-300)*20)
        displacement=fields['displacement']
        rows.append({'time_s':time,'temperature_K_range':[float(temp.min()),float(temp.max())],'mean_temperature_K':float(np.dot(volume,temp[conn].mean(axis=1))/volume.sum()),'thermal_energy_change_J':energy,'convective_loss_W':loss,'surface_area_m2':float(area.sum()),'volume_m3':float(volume.sum()),'displacement_mm_max':float(np.linalg.norm(displacement,axis=1).max()*1000),'native_scalar_stress_Pa_range':[float(fields['stress'].min()),float(fields['stress'].max())]})
    times=np.array([r['time_s'] for r in rows]);heat=np.array([r['convective_loss_W'] for r in rows])
    integrated=float(np.trapz(heat,times));change=rows[-1]['thermal_energy_change_J']-rows[0]['thermal_energy_change_J']
    report={'scope':'whole-envelope solid elastic cooldown only; no laser/deposition/porosity qualification','rows':rows,'integrated_convective_loss_J_trapezoidal':integrated,'energy_balance_relative':abs(change+integrated)/max(abs(change),integrated),'manufacturing_qualified':False}
    (a.case/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

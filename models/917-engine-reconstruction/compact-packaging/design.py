"""Lower charge roofs; retain every port of the accepted mechanical detail."""
from pathlib import Path
import importlib.util
p=Path(__file__).resolve().parent.parent/'mechanical-detail/design.py'
spec=importlib.util.spec_from_file_location('frozen_detail_design',p);prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)


def charge_path(bank):
    if bank not in (-1,1):raise ValueError('Invalid bank')
    a=prior.charge_path(bank)[0];b=[500,a[1]+bank*40,a[2]];d=[500,a[1]+bank*80,a[2]];c=[555,bank*490,260]
    return [a,b,d]+prior.curve(d,[555,bank*490,d[2]],c)[1:]+prior.curve(c,[555,bank*490,270],[430,bank*490,270])[1:]+[[-150,bank*490,270]]+prior.curve([-150,bank*490,270],[-150,bank*310,270],[-150,bank*310,295])[1:]+[[-100,bank*310,295]]


def bank_config(rows,cam_y,cam_z):
    result=[]
    for bank in (-1,1):
        heads=sorted((r for r in rows if r['family']=='individual_head' and r['bank']==bank),key=lambda r:r['matrix_mm'][0][3])
        if len(heads)!=6:raise ValueError('Six protected heads required per bank')
        matrix=[list(row) for row in heads[0]['matrix_mm']];matrix[0][3]=sum(r['matrix_mm'][0][3] for r in heads)/6
        sign=matrix[0][0];centres=sorted((r['matrix_mm'][0][3]-matrix[0][3])/sign for r in heads)
        if any(abs(centres[i]+centres[-1-i])>1e-6 for i in range(3)):raise ValueError('Asymmetric candidate bank')
        result.append({'bank':bank,'pose':matrix,'head_centres_local_x_mm':centres,'half_length_mm':max(centres)+58.17,
                       'cam_y_mm':cam_y,'cam_z_mm':cam_z,'bolt_x_mm':[-365,-263.5,-145.5,0,145.5,263.5,365],
                       'bolt_y_mm':85.13,'bolt_head_z_mm':78.13,'adapter_bottom_mm':66.13,'adapter_top_mm':74.13,
                       'lid_bottom_mm':74.63,'actual_alloy':None,'measured_interfaces':None})
    return result

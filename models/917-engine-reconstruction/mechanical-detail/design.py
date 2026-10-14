"""Fixed, editable mechanical hypotheses. None of these dimensions is a measured interface."""
import math


def cover_bolts(gears):
    circles=list({(y,z,r) for _,y,z,r in gears});result=[]
    for y,z,r in sorted(circles):
        for i in range(8):
            a=i*math.tau/8;p=[y+(r+6)*math.cos(a),z+(r+6)*math.sin(a)]
            if any(math.dist(p,[yy,zz])<rr+5 for yy,zz,rr in circles if (yy,zz,rr)!=(y,z,r)):continue
            if any(math.dist(p,q)<18 for q in result):continue
            result.append(p)
    if len(result)<12:raise ValueError('Insufficient clear cover bolt locations')
    return result


def pressure_rows(z_limit):
    return [-z_limit+8*i for i in range(int(2*z_limit/8)+1)]


def air_rows(z_limit):
    return [-z_limit+4+8*i for i in range(int(2*z_limit/8))]


def curve(a,b,c,count=24):
    return [[(1-t)**2*a[i]+2*t*(1-t)*b[i]+t*t*c[i] for i in range(3)] for t in [k/count for k in range(count+1)]]


def charge_path(bank):
    if bank not in (-1,1):raise ValueError('Invalid bank')
    terminal=[500,bank*382.25,-160-bank*49]
    # The frozen compressor outlet points along local +Y, transformed to bank*Y.
    a=terminal;b=[500,a[1]+bank*40,a[2]];d=[500,a[1]+bank*80,a[2]];c=[555,bank*490,260]
    return [a,b,d]+curve(d,[555,bank*490,d[2]],c)[1:]+curve(c,[555,bank*490,335],[430,bank*490,335])[1:]+[[-150,bank*490,335]]+curve([-150,bank*490,335],[-150,bank*310,335],[-150,bank*310,295])[1:]+[[-100,bank*310,295]]


def return_path(bank):
    return [[231,bank*310,295],[270,bank*310,295]]+curve([270,bank*310,295],[350,bank*310,295],[350,bank*310,155])[1:]

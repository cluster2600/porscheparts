"""Read only CCX2.21 global DISP dbi records and unchanged C3D10 geometry."""
import math
from pathlib import Path
import struct

VECTOR=struct.Struct('<i3d')
CELL=struct.Struct('<14i')


def read(path,nodes,cells,expected_times):
    coordinates=None;topology=None;frames={};header=None
    def payload(stream,size):
        value=stream.read(size)
        if len(value)!=size:raise ValueError('Truncated native double FRD record')
        return value
    with Path(path).open('rb')as stream:
        while line:=stream.readline():
            if line.startswith(b'    2C'):
                fields=line.split()
                if coordinates is not None or len(fields)!=3 or int(fields[1])!=len(nodes)or fields[2]!=b'3':raise ValueError('FRD coordinates are not full original binary64 records')
                coordinates={}
                for _ in nodes:
                    tag,*xyz=VECTOR.unpack(payload(stream,VECTOR.size))
                    if tag not in nodes or tag in coordinates or not all(map(math.isfinite,xyz)):raise ValueError('Invalid or duplicate FRD coordinate ID')
                    if struct.pack('<3d',*xyz)!=struct.pack('<3d',*nodes[tag]):raise ValueError('FRD coordinates differ from original INP binary64')
                    coordinates[tag]=tuple(xyz)
            elif line.startswith(b'    3C'):
                fields=line.split()
                if coordinates is None or topology is not None or len(fields)!=3 or int(fields[1])!=len(cells)or fields[2]!=b'2':raise ValueError('FRD topology header differs')
                topology=set()
                for _ in cells:
                    tag,kind,zero,material,*conn=CELL.unpack(payload(stream,CELL.size))
                    if tag not in cells or tag in topology or (kind,zero,material)!=(6,0,1)or tuple(conn)!=cells[tag]:raise ValueError('FRD C3D10 topology differs from original INP')
                    topology.add(tag)
            elif line.startswith(b'  100CL'):
                if coordinates is None or topology is None or len(line)!=76 or line[74:75]!=b'3':raise ValueError('Only native binary64 format3 is admitted')
                time=float(line[12:24]);count=int(line[24:36])
                if not math.isfinite(time)or time in frames or time not in expected_times or count!=len(nodes):raise ValueError('Invalid, repeated or incomplete FRD state')
                expected=[b' -4  DISP        4    1',b' -5  D1          1    2    1    0',b' -5  D2          1    2    2    0',b' -5  D3          1    2    3    0',b' -5  ALL         1    2    0    0    1ALL']
                for descriptor in expected:
                    if stream.readline().rstrip(b'\r\n')!=descriptor:raise ValueError('Only original global three-component DISP is admitted')
                rows=[];seen=set()
                for _ in nodes:
                    row=VECTOR.unpack(payload(stream,VECTOR.size));tag=row[0]
                    if tag not in nodes or tag in seen or not all(map(math.isfinite,row[1:])):raise ValueError('Nonfinite, duplicate or unexpected displacement ID')
                    seen.add(tag);rows.append(row)
                frames[time]=sorted(rows)
            elif line.strip()and not(line.startswith(b'    1')or line.strip()==b'9999'):
                raise ValueError('Unexpected native FRD header or trailing data')
    if coordinates is None or topology is None or sorted(frames)!=list(expected_times):raise ValueError('Native double FRD omits required geometry or states')
    return frames

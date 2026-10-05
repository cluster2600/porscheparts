#!/usr/bin/env python3
"""Require all32 finite native MPI checkpoint1040 files before analysis admission."""
import hashlib,json,re
from pathlib import Path
import numpy as np
from analyze_flow_balance import field_values
RANK_CELLS=[122709,167115,208232,182540]
RANK_FACES=[243383,351463,448842,385969]


def audit(case):
    files={}
    for rank,cells in enumerate(RANK_CELLS):
        directory=case/f'processor{rank}'/'1040'
        for name in ['p','U','k','omega','nut','phi','Uf']:
            path=directory/name;text=path.read_text();count=RANK_FACES[rank] if name in ['phi','Uf'] else cells;components=3 if name in ['U','Uf'] else 1
            declaration=re.search(r'internalField\s+nonuniform\s+List<(scalar|vector)>\s+(\d+)',text)
            if not declaration or int(declaration[2])!=count or declaration[1]!=('vector' if components==3 else 'scalar') or re.search(r'(?i)\b(?:nan|inf)\b',text):raise ValueError('Complete nonuniform finite native1040 field required')
            values=field_values(text,'internalField',count,components)
            if not np.isfinite(values).all():raise ValueError('Nonfinite native1040 field')
            files[str(path.relative_to(case))]={'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        path=directory/'uniform/time';text=path.read_text();data={}
        for key in ['value','name','index','deltaT','deltaT0']:
            found=re.search(r'\b'+key+r'\s+([^;]+);',text)
            if not found:raise ValueError('Native1040 time marker incomplete')
            data[key]=found[1].strip().strip('"')
        if data!={'value':'1040','name':'1040','index':'1040','deltaT':'1','deltaT0':'1'}:raise ValueError('Native1040 time/index differs')
        files[str(path.relative_to(case))]={'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    result={'status':'native1040_checkpoint_complete_finite','files':files,'all32_native_files_verified':len(files)==32,'physical_validation_established':False}
    (case/'native1040-checkpoint-verification.json').write_text(json.dumps(result,indent=2)+'\n');return result

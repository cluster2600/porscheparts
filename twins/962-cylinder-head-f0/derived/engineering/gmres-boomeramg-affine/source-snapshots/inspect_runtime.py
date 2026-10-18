"""Read only selected owned-runtime identities; never invoke a solver or write rootfs."""
import argparse
import hashlib
import json
from pathlib import Path

parser=argparse.ArgumentParser();parser.add_argument('--rootfs',type=Path,required=True);args=parser.parse_args()
files=['opt/moose/bin/moose-opt','opt/petsc/lib/libpetsc.so.3.25.2','opt/petsc/lib/libHYPRE-3.1.0.so',
       'opt/petsc/include/petscconf.h','environment']
result=dict(scope='read_only_metadata_no_MOOSE_or_solver_invocation',MOOSE_binary_invocations=0,
            shared_runtime_modified=False,files={})
for name in files:
    p=args.rootfs/name;data=p.read_bytes()
    result['files'][name]=dict(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
    if name.endswith('libpetsc.so.3.25.2'):
        result['selected_compiled_option_strings']={s:s.encode() in data for s in
            ['-ksp_view_mat','-ksp_view_pmat','-ksp_view_rhs','-ksp_view_solution','-ksp_view_final_residual','-pc_hypre_type','boomeramg']}
    if name.endswith('petscconf.h'):
        result['selected_compile_lines']=[line for line in data.decode().splitlines() if line.startswith((
            '#define PETSC_HAVE_HYPRE ','#define PETSC_USE_64BIT_INDICES ','#define PETSC_USE_REAL_DOUBLE '))]
result['reserved_output_exists']=(args.rootfs.parents[2]/'962-gmres-boomeramg-affine-001').exists()
print(json.dumps(result,indent=2))

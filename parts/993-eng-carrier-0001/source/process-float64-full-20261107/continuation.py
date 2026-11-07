"""Exact source-bound full-calendar prefix admission; partial leftovers refuse."""
from pathlib import Path
import hashlib,json,math

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def validate_calendar(indices,heights,h):
 if indices!=list(range(1034)) or len(heights)!=1034:raise ValueError('The complete current calendar must contain exactly indices 0 through 1033')
 if h!=0.06 or any(not math.isfinite(z) or z!=(i+.5)*h for i,z in zip(indices,heights)):raise ValueError('Current unshifted heights must match the declared parameter exactly')
 return True

def prefix_paths(rows):
 names={'context.json','mesh-bounds.json'}|{'checkpoint-%05d.json'%n for n in range(len(rows)+1)}
 for row in rows:
  i=row['layer'];names.update(['layer-%05d.receipt.json'%i,'layers/layer-%05d.npz'%i,'oracle/layer-%05d.npz'%i,'oracle/source-edges-%05d.npz'%i,'bounds/layer-%05d.json'%i])
 return names

def restore_prefix(root,context,indices,heights,marker,marker_sha,prior_terminal,terminal_sha,storage,audit):
 root=Path(root);prior_terminal=Path(prior_terminal)
 if sha(prior_terminal)!=terminal_sha:raise ValueError('Prior terminal identity differs')
 terminal=json.loads(prior_terminal.read_text())
 if terminal['contract_sha256']!=context['contract_sha256'] or not terminal['prepared_sources_unchanged'] or not terminal['child_reaped'] or not terminal['owned_group_cleanup']['group_absent'] or not terminal['owned_group_cleanup']['only_exact_owned_group_signaled']:raise ValueError('Prior exact source/process closure is incomplete')
 if terminal['reason'] not in ['finite_resource_or_observer_guard','worker_return_nonzero','complete']:raise ValueError('Prior terminal is not an admitted continuation state')
 rows=storage.restore(root,context,indices,heights,marker,marker_sha,audit)
 if len(rows)>=len(indices):raise ValueError('Completed full output must not be resumed')
 for row in rows:
  i=row['layer']
  if sha(root/'oracle'/('source-edges-%05d.npz'%i))!=row['source_edge_cycles_sha256']:raise ValueError('Source edge cycles differ')
  if sha(root/'bounds'/('layer-%05d.json'%i))!=row['arithmetic_bounds_sha256']:raise ValueError('Section arithmetic bound differs')
 if sha(root/'mesh-bounds.json')!=context['mesh_bounds_sha256']:raise ValueError('Geometry arithmetic bound differs')
 mesh=json.loads((root/'mesh-bounds.json').read_text())
 if mesh.get('contract_sha256')!=context['contract_sha256']:raise ValueError('Geometry arithmetic contract differs')
 actual=set()
 for p in root.rglob('*'):
  if p.is_symlink():raise ValueError('Symlink continuation entry refused')
  if p.is_file() and p.relative_to(root).as_posix()!='.DS_Store':actual.add(p.relative_to(root).as_posix())
 if actual!=prefix_paths(rows):raise ValueError('Unaccounted partial or missing scientific outputs refuse continuation')
 return rows

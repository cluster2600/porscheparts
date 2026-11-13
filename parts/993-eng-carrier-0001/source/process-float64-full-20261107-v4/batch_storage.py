"""Exclusive per-layer receipts and hash-bound prefix resume for bounded AM batches."""
from pathlib import Path
import hashlib,json
import numpy as np

def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def canonical(data):return json.dumps(data,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def context_sha(context):return hashlib.sha256(canonical(context)).hexdigest()
def write_json(path,data):
 with Path(path).open('x') as f:json.dump(data,f,indent=2,allow_nan=False);f.write('\n')
def create(root,context):
 root=Path(root);root.mkdir(mode=0o700,exist_ok=False);(root/'layers').mkdir();(root/'oracle').mkdir();write_json(root/'context.json',context)
def publish(root,context,index,z,result,oracle_rings,oracle_area,cache,core,audit):
 root=Path(root);raw=root/'layers'/('layer-%05d.npz'%index);oracle=root/'oracle'/('layer-%05d.npz'%index);receipt=root/('layer-%05d.receipt.json'%index)
 assert json.loads((root/'context.json').read_text())==context,'Publication context differs'
 assert not raw.exists() and not oracle.exists() and not receipt.exists(),'Existing raw/receipt must never be overwritten'
 row=cache.write_layer(root,index,z,result);points,offsets=core.packed_paths(oracle_rings)
 with oracle.open('xb') as f:np.savez_compressed(f,points_mm=points,offsets=offsets,area_mm2=np.asarray(oracle_area),z_mm=np.asarray(z))
 domain=audit.section_domain(oracle_rings);assert abs(domain.area-oracle_area)<=audit.AREA_RELATIVE_TOLERANCE*max(1.,abs(oracle_area)),'Independent ring domain differs from oracle area'
 with np.load(raw,allow_pickle=False) as data:
  native=audit.layer_check(data,row['part_area_mm2']);contours=audit.paths(data['part_scan_contour_points_mm'],data['part_scan_contour_offsets']);pieces=[np.stack((p[:-1],p[1:]),axis=1) for p in contours];segments=np.concatenate(pieces) if pieces else np.empty((0,2,2));independent_hatch=audit.segments_check(data['part_hatch_segments_mm'],domain);independent_contour=audit.segments_check(segments,domain)
 error=float(row['part_area_mm2']-oracle_area);area_ok=abs(error)<=audit.AREA_RELATIVE_TOLERANCE*max(1.,abs(oracle_area));passed=native['passed'] and independent_hatch['passed'] and independent_contour['passed'] and area_ok
 value=dict(status='layer_complete_native_and_independent_domain_audits_passed' if passed else 'layer_rejected_retained_not_admitted',context_sha256=context_sha(context),layer=index,z_mm=z,row=row,raw_sha256=sha(raw),raw_bytes=raw.stat().st_size,oracle_sha256=sha(oracle),oracle_area_mm2=oracle_area,area_difference_mm2=error,area_pass=area_ok,native_audit=native,independent_hatch_audit=independent_hatch,independent_contour_audit=independent_contour)
 write_json(receipt,value);assert passed,'Layer rejected; raw arrays and refusal receipt retained'
 return dict(layer=index,z_mm=z,receipt_path=str(receipt),receipt_sha256=sha(receipt),raw_sha256=value['raw_sha256'],oracle_sha256=value['oracle_sha256'])
def checkpoint(root,context,indices,heights,rows):
 assert [r['layer'] for r in rows]==list(indices[:len(rows)]) and [r['z_mm'] for r in rows]==list(heights[:len(rows)])
 path=Path(root)/('checkpoint-%05d.json'%len(rows));value=dict(status='bounded_batch_complete' if len(rows)==len(indices) else 'bounded_batch_admitted_prefix_only',context_sha256=context_sha(context),indices=list(indices),heights=list(heights),rows=rows,all_layers_complete=len(rows)==len(indices));write_json(path,value);return path,sha(path)
def restore(root,context,indices,heights,marker,expected_sha,audit):
 root=Path(root);marker=Path(marker);assert marker.parent==root and sha(marker)==expected_sha,'Resume marker changed'
 value=json.loads(marker.read_text());assert value['context_sha256']==context_sha(context) and json.loads((root/'context.json').read_text())==context,'Resume source/pose/runtime/parameter context differs'
 assert value['indices']==list(indices) and value['heights']==list(heights),'Resume calendar differs'
 rows=value['rows'];assert [r['layer'] for r in rows]==list(indices[:len(rows)]) and [r['z_mm'] for r in rows]==list(heights[:len(rows)])
 for item in rows:
  i=item['layer'];path=root/('layer-%05d.receipt.json'%i);assert str(path)==item['receipt_path'] and sha(path)==item['receipt_sha256'];record=json.loads(path.read_text());assert record['status']=='layer_complete_native_and_independent_domain_audits_passed' and record['context_sha256']==context_sha(context) and record['z_mm']==item['z_mm'] and record['layer']==i
  raw=root/'layers'/('layer-%05d.npz'%i);oracle=root/'oracle'/('layer-%05d.npz'%i);assert sha(raw)==record['raw_sha256']==item['raw_sha256'] and sha(oracle)==record['oracle_sha256']==item['oracle_sha256']
  if 'source_edge_cycles_sha256' in item:assert sha(root/'oracle'/('source-edges-%05d.npz'%i))==item['source_edge_cycles_sha256'],'Source edge-cycle evidence changed'
  with np.load(oracle,allow_pickle=False) as data:rings=audit.paths(data['points_mm'],data['offsets']);area=float(data['area_mm2']);assert float(data['z_mm'])==item['z_mm']
  domain=audit.section_domain(rings);assert abs(domain.area-area)<=audit.AREA_RELATIVE_TOLERANCE*max(1.,abs(area))
  with np.load(raw,allow_pickle=False) as data:
   assert float(data['z_mm'])==item['z_mm'] and audit.layer_check(data,record['row']['part_area_mm2'])['passed'];assert audit.segments_check(data['part_hatch_segments_mm'],domain)['passed'];contours=audit.paths(data['part_scan_contour_points_mm'],data['part_scan_contour_offsets']);parts=[np.stack((p[:-1],p[1:]),axis=1) for p in contours];assert audit.segments_check(np.concatenate(parts) if parts else np.empty((0,2,2)),domain)['passed']
 return rows

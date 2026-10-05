#!/usr/bin/env python3
"""Offline-only D3 budget, actual isolation gate, ownership and partial-evidence tests."""
import copy,hashlib,json,os,shutil,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from d3_guards import LABELS,IMAGE,validate_plan,check_complete20,container_command,inspect_limits,phase_deadline,active_native_jobs,archive_private,verify_manifest
from build_d3_capsule import SOURCES
from launch_d3 import launch
from run_d3 import native_command,run
from audit_d3_checkpoint import audit
from analyze_d3 import prerequisites
ROOT=Path(__file__).resolve().parents[1]


def fixture_capsule(output):
    output.mkdir()
    for name in SOURCES:
        dest=output/'source'/name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(ROOT/'source'/name,dest)
    dest=output/'configs/diagnostic-plan.json';dest.parent.mkdir();shutil.copyfile(ROOT/'parameters/D3-prepared-relaxation-protocol.json',dest)
    files={str(f.relative_to(output)):{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in output.rglob('*') if f.is_file()}
    (output/'capsule-manifest.json').write_text(json.dumps({'new_solver_launched':False,'files':files,'offline_fixture_no_native_execution':True}))


def inspection(uid,gid):
    return {'HostConfig':{'NanoCpus':4000000000,'CpusetCpus':'0,2,4,5','Memory':5*1024**3,'MemorySwap':5*1024**3,
              'NetworkMode':'none','PidsLimit':256,'CapDrop':['ALL'],'SecurityOpt':['no-new-privileges'],'Privileged':False},
            'Config':{'User':str(uid)+':'+str(gid)},'Image':IMAGE,
            'Mounts':[{'Destination':name,'RW':False} for name in ['/prepared','/previous','/selections.npz','/capsule']]+[{'Destination':'/run','RW':True}]}


class Guards(unittest.TestCase):
    def test_smooth_pressure_or_promoted_flags_cannot_override_failed_residual(self):
        numerical=['initial_time_matches_frozen_continuation','residual_p','residual_U','residual_turbulence','mass_balance','flow_stability','torque_stability','declared_flow_direction','complete_finite_fields','finite_measurements']
        station=['common_flow_CV','common_pressure_std','between_windows_common_flow','between_windows_torque','between_windows_pressure','core_pressure_checkpoint_RMS','core_velocity_checkpoint_RMS']
        reports={label:{'original_numerical_checks':dict.fromkeys(numerical,True),'stationarity_checks':dict.fromkeys(station,True),
                 'all_original_numerical_checks_pass':True,'all_additional_stationarity_checks_pass':True,'pressure_std_Pa':0} for label in LABELS}
        self.assertTrue(prerequisites(reports));reports['candidate005']['original_numerical_checks']['residual_p']=False
        self.assertFalse(prerequisites(reports))
        reports['candidate005']['original_numerical_checks']={}
        with self.assertRaises(ValueError):prerequisites(reports)

    def test_original_exact_pair_budget_and_no_more_iterations(self):
        p=json.loads((ROOT/'parameters/D3-prepared-relaxation-protocol.json').read_text());validate_plan(p)
        for key,value in [('target_iteration',1060),('new_iterations_per_case',40),('solver_count_max',3),('cases_run_sequentially',False)]:
            wrong=copy.deepcopy(p);wrong[key]=value
            with self.assertRaises(ValueError):validate_plan(wrong)
        for key,value in [('aggregate_wall_cap_seconds',600),('CPU_max',6),('RAM_and_swap_limit_bytes',6*1024**3)]:
            wrong=copy.deepcopy(p);wrong['budget_requires_resource_coordination_before_launch'][key]=value
            with self.assertRaises(ValueError):validate_plan(wrong)
        wrong=copy.deepcopy(p);wrong['cases']['candidate005']['native_MPI_seed_files'].pop(next(iter(wrong['cases']['candidate005']['native_MPI_seed_files'])))
        with self.assertRaises(ValueError):validate_plan(wrong)
        wrong=copy.deepcopy(p);wrong['original_numerical_acceptance_all_required']['maximum_initial_residual_p']=.1
        with self.assertRaises(ValueError):validate_plan(wrong)
        wrong=copy.deepcopy(p);wrong['additional_stationarity_screen']['last_window_common_pressure_std_Pa_max']=20
        with self.assertRaises(ValueError):validate_plan(wrong)

    def test_complete20_rejects_fractional_time_partial_tail_and_duplicate(self):
        log=''.join(f'Time = {n}\nExecutionTime = {n} s  ClockTime = {n} s\n' for n in range(1021,1041))+'End\n'
        self.assertEqual(check_complete20(log),list(range(1021,1041)))
        for bad in [log.replace('Time = 1021','Time = 1021.5'),log.replace('ExecutionTime = 1040 s  ClockTime = 1040 s',''),log.replace('End','Time = 1041\nEnd'),log.replace('End',''),log+'FOAM FATAL']:
            with self.assertRaises(ValueError):check_complete20(bad)

    def test_shared_deadline_cannot_reset_after_budget_consumption(self):
        self.assertEqual(phase_deadline(360,90,150,now=125),210)
        self.assertEqual(phase_deadline(360,90,150,now=175),210)
        with self.assertRaises(TimeoutError):phase_deadline(360,90,150,now=210)

    def test_command_has_only_owned_image_and_readonly_sources(self):
        args=container_command('fan-d3-fixture',Path('/p'),Path('/v'),Path('/s'),Path('/c'),Path('/o'),1000,1000,'OFFLINE_FIXTURE',360)
        self.assertIn('--pull=never',args);self.assertIn(IMAGE,args);self.assertIn('python3 -B',args[-1])
        mounts=[args[i+1] for i,a in enumerate(args) if a=='--mount']
        self.assertEqual(len(mounts),5);self.assertEqual(sum(a.endswith(',readonly') for a in mounts),4)
        self.assertNotIn('decomposePar',' '.join(args));self.assertNotIn('docker pull',' '.join(args))
        with self.assertRaises(ValueError):container_command('foreign',Path('/p'),Path('/v'),Path('/s'),Path('/c'),Path('/o'),1000,1000,'fixture',360)

    def test_actual_extra_mount_privilege_or_wrong_caps_rejects(self):
        good=inspection(1000,1000);inspect_limits(good,1000,1000)
        for key in ['RAM','swap','network','source','extra_mount','privileged','image']:
            bad=copy.deepcopy(good)
            if key=='RAM':bad['HostConfig']['Memory']=6*1024**3
            elif key=='swap':bad['HostConfig']['MemorySwap']=6*1024**3
            elif key=='network':bad['HostConfig']['NetworkMode']='bridge'
            elif key=='source':bad['Mounts'][0]['RW']=True
            elif key=='extra_mount':bad['Mounts'].append({'Destination':'/foreign','RW':True})
            elif key=='privileged':bad['HostConfig']['Privileged']=True
            else:bad['Image']='other'
            with self.assertRaises(ValueError):inspect_limits(bad,1000,1000)

    def test_support_ccx_process_blocks_overlap_without_reading_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for pid,value in [('11',b'/usr/bin/ccx\0private-argument'),('12',b'/usr/bin/python3\0control-service')]:
                directory=root/pid;directory.mkdir();(directory/'cmdline').write_bytes(value);(directory/'comm').write_text('ccx' if pid=='11' else 'python3')
            self.assertEqual(active_native_jobs(root),['11'])

    def test_real_capsule_import_help_leaves_frozen_inventory_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            capsule=Path(tmp)/'capsule';fixture_capsule(capsule);before={str(p.relative_to(capsule)) for p in capsule.rglob('*') if p.is_file()}
            for name in ['launch_d3.py','build_d3_capsule.py','analyze_d3.py']:
                subprocess.run([sys.executable,'-B',str(capsule/'source'/name),'--help'],stdout=subprocess.DEVNULL,check=True)
            subprocess.run([sys.executable,'-B','-c','import run_d3, audit_d3_checkpoint'],cwd=capsule/'source',check=True)
            self.assertEqual(before,{str(p.relative_to(capsule)) for p in capsule.rglob('*') if p.is_file()})

    def test_partial_archive_is_not_verified_and_original_files_remain(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);file=root/'control015/processor0/1040/p';file.parent.mkdir(parents=True);file.write_text('offline synthetic partial field')
            with self.assertRaises(TimeoutError):archive_private(root,time.monotonic()-1)
            self.assertTrue(file.exists());self.assertFalse((root/'native-evidence-manifest.json').exists())

    def test_owned_sleep_fixture_is_terminated_on_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);start=time.monotonic()
            with self.assertRaises(subprocess.TimeoutExpired):native_command([sys.executable,'-c','import time; time.sleep(5)'],root,root/'fixture.log',start+3.3,4)
            self.assertLess(time.monotonic()-start,2)


class Checkpoints(unittest.TestCase):
    def fixture(self,root):
        for rank in range(4):
            directory=root/f'processor{rank}/1040';directory.mkdir(parents=True)
            for name in ['p','U','k','omega','nut','phi','Uf']:
                vector=name in ['U','Uf'];(directory/name).write_text('internalField nonuniform List<'+('vector' if vector else 'scalar')+'>\n1\n(\n'+('(1 0 0)' if vector else '1')+'\n);\n')
            (directory/'uniform').mkdir();(directory/'uniform/time').write_text('value 1040; name "1040"; index 1040; deltaT 1; deltaT0 1;')

    def test_all32_files_and_time_marker_required(self):
        with tempfile.TemporaryDirectory() as tmp,patch('audit_d3_checkpoint.RANK_CELLS',[1]*4),patch('audit_d3_checkpoint.RANK_FACES',[1]*4):
            root=Path(tmp);self.fixture(root);self.assertEqual(len(audit(root)['files']),32)
            (root/'processor3/1040/Uf').unlink()
            with self.assertRaises(FileNotFoundError):audit(root)

    def test_nonfinite_boundary_or_wrong_saved_time_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp,patch('audit_d3_checkpoint.RANK_CELLS',[1]*4),patch('audit_d3_checkpoint.RANK_FACES',[1]*4):
            root=Path(tmp);self.fixture(root);p=root/'processor0/1040/p';original=p.read_text();p.write_text(original+'\nvalue uniform nan;')
            with self.assertRaises(ValueError):audit(root)
            p.write_text(original);(root/'processor0/1040/uniform/time').write_text('value 1040; name "1040"; index 1020; deltaT 1; deltaT0 1;')
            with self.assertRaises(ValueError):audit(root)


class SupervisorFixtures(unittest.TestCase):
    def simulate(self,mode):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);capsule=root/'capsule';fixture_capsule(capsule)
            capsule_sha256=hashlib.sha256((capsule/'capsule-manifest.json').read_bytes()).hexdigest()
            prepared=root/'prepared';prepared.mkdir();previous=root/'previous';previous.mkdir();selection=root/'selections.npz';selection.write_bytes(b'offline fixture')
            output=root/'output';calls=[];active=[False];real_read=Path.read_text
            def read(path,*args,**kwargs):
                if str(path)=='/proc/meminfo':return 'MemAvailable: 8000000 kB\n'
                if str(path).startswith('/sys/devices/system/cpu/'):return '0' if path.name=='physical_package_id' else path.parent.parent.name
                return real_read(path,*args,**kwargs)
            def docker(args,**kwargs):
                calls.append(args)
                if args[1]=='inspect':
                    data=inspection(os.getuid(),os.getgid())
                    if mode=='bad_isolation':data['HostConfig']['MemorySwap']=6*1024**3
                    return subprocess.CompletedProcess(args,0,json.dumps([data]),'')
                if args[1] in ['stop','kill']:active[0]=False
                if args[1]=='ps':
                    own=any('name=^/fan-d3-' in a for a in args)
                    value='owned-fixture' if own and active[0] else ''
                    if '--filter' not in args:value='existing-control-service pinned-image\n'+('fan-support-S2 support-image\n' if mode=='support_active' else '')
                    return subprocess.CompletedProcess(args,0,value,'')
                return subprocess.CompletedProcess(args,0,'[]','')
            class FakeProcess:
                def __init__(self,args,**kwargs):
                    calls.append(args);active[0]=True;self.code=None
                    if mode in ['success','bad_isolation','partial']:
                        (output/'execution-receipt.json').write_text(json.dumps({'status':'completed_two_fixed20_no_retry','completed_solver_arms':list(LABELS) if mode!='partial' else [LABELS[0]],'offline_fixture_only':True}))
                        (output/'native-evidence-manifest.json').write_text(json.dumps({'all_members_verified':True,'offline_fixture_only':True}))
                def wait(self,timeout=None):
                    if mode=='timeout' and self.code is None:raise subprocess.TimeoutExpired('offline-fixture',timeout)
                    self.code=0 if self.code is None else self.code;active[0]=False;return self.code
                def poll(self):return self.code
                def terminate(self):self.code=130
                def kill(self):self.code=137
            with patch('launch_d3.sys.platform','linux'),patch('launch_d3.platform.machine',return_value='x86_64'),patch('launch_d3.os.cpu_count',return_value=12),patch('launch_d3.os.getloadavg',return_value=(1,1,1)),patch.object(Path,'read_text',read),patch('launch_d3.active_native_jobs',return_value=[]),patch('launch_d3.subprocess.run',side_effect=docker),patch('launch_d3.subprocess.Popen',FakeProcess):
                if mode in ['support_active','bad_pin']:
                    with self.assertRaises(ValueError):launch(prepared,previous,selection,capsule,output,'OFFLINE_FIXTURE_ONLY',capsule_sha256 if mode!='bad_pin' else '0'*64)
                    self.assertFalse(output.exists());return None,None,calls,False
                code=launch(prepared,previous,selection,capsule,output,'OFFLINE_FIXTURE_ONLY',capsule_sha256)
            return code,json.loads((output/'launcher-receipt.json').read_text()),calls,(output/'isolation-admitted.json').exists()

    def test_success_has_one_container_two_arms_global360_and_release(self):
        code,receipt,calls,gate=self.simulate('success');self.assertEqual(code,0);self.assertTrue(gate)
        self.assertEqual(sum(c[1]=='run' for c in calls),1);self.assertEqual(receipt['global_wall_cap_seconds'],360)
        self.assertFalse(receipt['owned_container_remaining']);self.assertTrue(receipt['service_name_image_inventory_unchanged'])

    def test_support_container_blocks_before_any_run_or_reservation(self):
        _,_,calls,_=self.simulate('support_active');self.assertFalse(any(c[1]=='run' for c in calls))

    def test_untrusted_capsule_pin_blocks_before_any_container(self):
        _,_,calls,_=self.simulate('bad_pin');self.assertEqual(calls,[])

    def test_bad_isolation_cannot_write_admission_or_stop_foreign_container(self):
        code,receipt,calls,gate=self.simulate('bad_isolation');self.assertNotEqual(code,0);self.assertFalse(gate)
        stopped=[c[-1] for c in calls if c[1] in ['stop','kill']];self.assertEqual(stopped,[receipt['container_name']]);self.assertTrue(all(n.startswith('fan-d3-') for n in stopped))

    def test_timeout_or_partial_is_never_retried_or_admitted(self):
        for mode in ['timeout','partial']:
            code,receipt,calls,_=self.simulate(mode);self.assertNotEqual(code,0)
            self.assertEqual(sum(c[1]=='run' for c in calls),1);self.assertFalse(receipt['owned_container_remaining'])
            self.assertEqual(receipt['status'],'failed_or_partial_no_retry')


class RuntimeFixtures(unittest.TestCase):
    def simulate(self,partial):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);capsule=root/'capsule';fixture_capsule(capsule);output=root/'output';output.mkdir()
            from d2_completion_guards import digest_file as real_digest
            manifest_identity=real_digest(capsule/'capsule-manifest.json',time.monotonic()+5)
            deadline=time.monotonic()+360
            (output/'isolation-admitted.json').write_text(json.dumps({'actual_isolation_verified':True,'aggregate_deadline_monotonic':deadline,'capsule_manifest_sha256':manifest_identity['sha256']}))
            plan=json.loads((ROOT/'parameters/D3-prepared-relaxation-protocol.json').read_text());calls=[]
            def copied(*args):
                for label in LABELS:(output/label).mkdir()
                return plan,{}
            def digest(path,limit):
                for label in LABELS:
                    if label in path.parts:
                        name=str(path.relative_to(output/label))
                        if name in plan['cases'][label]['native_MPI_seed_files']:return plan['cases'][label]['native_MPI_seed_files'][name]
                return real_digest(path,limit)
            def native(args,cwd,log,finish,cap):
                calls.append({'args':args,'finish':finish,'cap':cap})
                self.assertLessEqual(finish,deadline)
                if 'foamRun' in args:
                    steps=range(1021,1040 if partial and cwd.name==LABELS[0] else 1041)
                    text=''.join(f'Time = {n}\nExecutionTime = 1 s  ClockTime = 1 s\n' for n in steps)
                    if partial and cwd.name==LABELS[0]:text+='Time = 1040\n'
                    else:text+='End\n'
                    log.write_text(text)
                else:log.write_text('offline fixture command, no solver executed\n')
                return {'args':args,'exit_status':0,'wall_seconds':0}
            real_isdir=Path.is_dir
            def isdir(path):return True if str(path)=='/opt/openfoam13' else real_isdir(path)
            with patch.dict(os.environ,{'FAN_D3_DEADLINE':str(deadline),'FAN_D3_RELEASE':'OFFLINE_FIXTURE_ONLY'}),patch('run_d3.sys.platform','linux'),patch('run_d3.os.nice'),patch.object(Path,'is_dir',isdir),patch('run_d3.copy_inputs',side_effect=copied),patch('run_d3.digest_file',side_effect=digest),patch('run_d3.native_command',side_effect=native):
                code=run(root/'prepared',root/'previous',root/'selections.npz',capsule,output)
            return code,json.loads((output/'execution-receipt.json').read_text()),json.loads((output/'native-evidence-manifest.json').read_text()),calls

    def test_two_sequential_fixed20_arms_then_shared_reconstruction_analysis_and_archive(self):
        code,receipt,archive,calls=self.simulate(False);self.assertEqual(code,0)
        solvers=[c for c in calls if 'foamRun' in c['args']];self.assertEqual(len(solvers),2)
        self.assertEqual([Path(c['args'][-1]).name for c in solvers],list(LABELS))
        self.assertEqual([c['cap'] for c in calls],[90,90,40,40,45])
        self.assertEqual(calls[2]['finish'],calls[3]['finish']);self.assertEqual(receipt['completed_solver_arms'],list(LABELS))
        self.assertTrue(archive['all_members_verified']);self.assertIn('control015/log.foamRun',archive['members']);self.assertIn('candidate005/log.foamRun',archive['members'])

    def test_incomplete_control_archived_without_candidate_retry_or_reconstruction(self):
        code,receipt,archive,calls=self.simulate(True);self.assertEqual(code,2)
        self.assertEqual(len(calls),1);self.assertEqual(receipt['completed_solver_arms'],[])
        self.assertEqual(receipt['status'],'failed_or_partial_no_retry');self.assertTrue(archive['all_members_verified'])
        self.assertIn('control015/log.foamRun',archive['members']);self.assertNotIn('candidate005/log.foamRun',archive['members'])


if __name__=='__main__':unittest.main()

#!/usr/bin/env python3
"""Offline fixtures only: bounded supervisor, isolation, custody and no replay."""
import copy,json,os,subprocess,tempfile,time,unittest
import sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
from d2_completion_guards import (IMAGE,remaining,validate_plan,check_complete20,container_command,
                                  inspect_limits,merge_native_rows,archive_private)
from build_d2_completion_capsule import build
from launch_d2_completion import launch
ROOT=Path(__file__).resolve().parents[1]


def inspection(uid,gid):
    return {'HostConfig':{'NanoCpus':4000000000,'CpusetCpus':'0,2,4,5','Memory':5*1024**3,
             'MemorySwap':5*1024**3,'NetworkMode':'none','PidsLimit':256,'CapDrop':['ALL'],
             'SecurityOpt':['no-new-privileges']},'Config':{'User':str(uid)+':'+str(gid)},
             'Image':IMAGE,'Mounts':[{'Destination':p,'RW':False} for p in ['/prepared','/previous','/selections.npz','/capsule']]+[{'Destination':'/run','RW':True}]}


class Guards(unittest.TestCase):
    def test_descriptive_domain_bands_cannot_override_failed_pressure_gate(self):
        from verify_d2_completion import validate_completed
        result=json.loads((ROOT/'results/cfd/D2-completed-pair-analysis.json').read_text())
        summary=json.loads((ROOT/'results/cfd/D2-extended1020-flow-summary.json').read_text())
        self.assertTrue(all(result['last20_comparison']['domain_checks_descriptive_even_when_inconclusive'].values()))
        validate_completed(result,summary)
        for key,value in [('status','bulk_observables_within_declared_single_extension_bands'),('both_cases_numerical_and_stationarity_admitted',True)]:
            promoted=copy.deepcopy(result);promoted[key]=value
            with self.assertRaises(ValueError):validate_completed(promoted,summary)

    def test_exact20_complete_log_and_no_partial_or_extra_step(self):
        text=''.join(f'Time = {n}\nExecutionTime = {n} s  ClockTime = {n} s\n' for n in range(1001,1021))+'End\n'
        self.assertEqual(check_complete20(text),list(range(1001,1021)))
        for bad in [text.replace('ExecutionTime = 1020 s  ClockTime = 1020 s',''),text.replace('End','Time = 1021\nEnd'),text.replace('End',''),text+'FOAM FATAL']:
            with self.assertRaises(ValueError):check_complete20(bad)

    def test_frozen_plan_and_no_new_deadline_after_exhaustion(self):
        plan=json.loads((ROOT/'parameters/D2-restart1000-protocol.json').read_text());validate_plan(plan)
        for key,value in [('new_cases',['current','extended']),('new_iterations',40),('target_iteration',1040)]:
            altered=copy.deepcopy(plan);altered[key]=value
            with self.assertRaises(ValueError):validate_plan(altered)
        altered=copy.deepcopy(plan);altered['budget_proposed_not_authorized_or_started']['aggregate_wall_cap_seconds']=300
        with self.assertRaises(ValueError):validate_plan(altered)
        self.assertEqual(remaining(240,45,100),95)
        with self.assertRaises(TimeoutError):remaining(240,45,200)

    def test_only_existing_image_sources_readonly_and_single_runner(self):
        cmd=container_command('fan-d2-completion-fixture',Path('/p'),Path('/old'),Path('/s'),Path('/c'),Path('/o'),1000,1000,'fixture-not-native',240)
        self.assertIn('--pull=never',cmd);self.assertIn(IMAGE,cmd);self.assertNotIn('launch_d2.py',' '.join(cmd))
        mounts=[cmd[i+1] for i,x in enumerate(cmd) if x=='--mount']
        self.assertEqual(sum(x.endswith(',readonly') for x in mounts),4)
        self.assertTrue(all(word not in ' '.join(cmd) for word in ['decomposePar','regrid','docker pull']))
        self.assertIn('python3 -B',cmd[-1])
        with self.assertRaises(ValueError):container_command('foreign',Path('/p'),Path('/old'),Path('/s'),Path('/c'),Path('/o'),1000,1000,'fixture',240)

    def test_actual_isolation_required_before_admission(self):
        good=inspection(1000,1000);inspect_limits(good,1000,1000)
        for change in ['memory','network','source_RW','image','capabilities']:
            bad=copy.deepcopy(good)
            if change=='memory':bad['HostConfig']['MemorySwap']=6*1024**3
            elif change=='network':bad['HostConfig']['NetworkMode']='bridge'
            elif change=='source_RW':bad['Mounts'][0]['RW']=True
            elif change=='image':bad['Image']='changed'
            else:bad['HostConfig']['CapDrop']=[]
            with self.assertRaises(ValueError):inspect_limits(bad,1000,1000)

    def test_derived_table_keeps_native_lines_and_checks_duplicate1000(self):
        old=''.join(f'{n} 2.5\n' for n in range(960,1001))
        new=''.join(f'{n} 2.5\n' for n in range(1000,1021))
        parse=lambda text:np.asarray([list(map(float,line.split())) for line in text.splitlines() if not line.startswith('#')])
        merged=merge_native_rows(old,new,parse)
        self.assertEqual(parse(merged)[:,0].tolist(),list(range(960,1021)))
        self.assertIn('Derived view',merged)
        with self.assertRaises(ValueError):merge_native_rows(old,new.replace('1000 2.5','1000 3.0'),parse)
        with self.assertRaises(ValueError):merge_native_rows(old,new.replace('1020 2.5\n',''),parse)

    def test_archive_includes_native_processor_fields_and_verified_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);field=root/'extended/processor2/1020/p';field.parent.mkdir(parents=True);field.write_text('synthetic fixture field, no CFD')
            record=archive_private(root,time.monotonic()+5)
            self.assertIn('extended/processor2/1020/p',record['members']);self.assertTrue(record['all_members_verified'])
            self.assertTrue((root/'native-evidence.tar.gz').exists())

    def test_archive_timeout_preserves_native_files_and_never_labels_partial_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);field=root/'native-field-fixture';field.write_text('synthetic fixture')
            with self.assertRaises(TimeoutError):archive_private(root,time.monotonic()-1)
            self.assertTrue(field.exists());self.assertFalse((root/'native-evidence.tar.gz').exists())
            self.assertFalse((root/'native-evidence-manifest.json').exists())

    def test_real_help_import_cannot_add_bytecode_to_frozen_capsule(self):
        with tempfile.TemporaryDirectory() as tmp:
            capsule=Path(tmp)/'capsule';build(ROOT,capsule)
            before={str(p.relative_to(capsule)) for p in capsule.rglob('*') if p.is_file()}
            subprocess.run([sys.executable,'-B',str(capsule/'source/launch_d2_completion.py'),'--help'],stdout=subprocess.DEVNULL,check=True)
            after={str(p.relative_to(capsule)) for p in capsule.rglob('*') if p.is_file()}
            self.assertEqual(before,after)


class SupervisorFixtures(unittest.TestCase):
    def simulate(self,mode):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);capsule=root/'capsule';build(ROOT,capsule)
            prepared=root/'prepared';prepared.mkdir();previous=root/'previous';previous.mkdir();selections=root/'selections.npz';selections.write_bytes(b'fixture')
            output=root/'output';calls=[];active=[False];real_read=Path.read_text;real_iter=Path.iterdir
            def read(path,*args,**kwargs):
                if str(path)=='/proc/meminfo':return 'MemAvailable: 8000000 kB\n'
                if str(path).startswith('/sys/devices/system/cpu/'):
                    return '0' if path.name=='physical_package_id' else path.parent.parent.name
                return real_read(path,*args,**kwargs)
            def directories(path):return iter([]) if str(path)=='/proc' else real_iter(path)
            def docker(args,**kwargs):
                calls.append(args)
                if args[1]=='inspect':
                    data=inspection(os.getuid(),os.getgid())
                    if mode=='bad_isolation':data['HostConfig']['MemorySwap']=6*1024**3
                    return subprocess.CompletedProcess(args,0,json.dumps([data]),'')
                if args[1] in ['stop','kill']:active[0]=False
                if args[1]=='ps':
                    value='owned-fixture' if any('name=^/fan-d2-completion-' in a for a in args) and active[0] else ''
                    if '--filter' not in args:value='existing-control-plane unchanged-image\n'
                    return subprocess.CompletedProcess(args,0,value,'')
                return subprocess.CompletedProcess(args,0,'[]','')
            class FakeProcess:
                def __init__(self,args,**kwargs):
                    calls.append(args);active[0]=True;self.code=None
                    if mode=='success':
                        (output/'execution-receipt.json').write_text(json.dumps({'status':'completed_exact20_no_retry','offline_fixture':True}))
                        (output/'native-evidence-manifest.json').write_text(json.dumps({'all_members_verified':True,'offline_fixture':True}))
                def wait(self,timeout=None):
                    if mode=='timeout' and self.code is None:raise subprocess.TimeoutExpired('fixture',timeout)
                    self.code=0;active[0]=False;return 0
                def poll(self):return self.code
                def terminate(self):self.code=130
                def kill(self):self.code=137
            with patch('launch_d2_completion.sys.platform','linux'),patch('launch_d2_completion.os.cpu_count',return_value=12),patch('launch_d2_completion.os.getloadavg',return_value=(1,1,1)),patch.object(Path,'read_text',read),patch.object(Path,'iterdir',directories),patch('launch_d2_completion.subprocess.run',side_effect=docker),patch('launch_d2_completion.subprocess.Popen',FakeProcess):
                code=launch(prepared,previous,selections,capsule,output,'OFFLINE_FIXTURE_NOT_NATIVE')
            return code,json.loads((output/'launcher-receipt.json').read_text()),calls,(output/'isolation-admitted.json').exists()

    def test_success_fixture_has_one_owned_container_and_no_control_replay(self):
        code,receipt,calls,gate=self.simulate('success')
        self.assertEqual(code,0);self.assertTrue(gate);self.assertFalse(receipt['current_control_replayed'])
        self.assertEqual(sum(len(c)>1 and c[1]=='run' for c in calls),1)
        self.assertEqual(receipt['global_wall_cap_seconds'],240)
        self.assertTrue(receipt['services_unchanged']);self.assertFalse(receipt['owned_container_remaining'])

    def test_bad_isolation_never_admits_and_stops_only_its_owned_name(self):
        code,receipt,calls,gate=self.simulate('bad_isolation')
        self.assertNotEqual(code,0);self.assertFalse(gate)
        stops=[c for c in calls if len(c)>1 and c[1] in ['stop','kill']]
        self.assertTrue(stops);self.assertTrue(all(c[-1]==receipt['container_name'] for c in stops))
        self.assertFalse(receipt['owned_container_remaining'])

    def test_timeout_releases_owned_container_without_retry(self):
        code,receipt,calls,gate=self.simulate('timeout')
        self.assertEqual(code,124);self.assertTrue(gate);self.assertTrue(receipt['no_retry_or_further_continuation'])
        self.assertEqual(sum(len(c)>1 and c[1]=='run' for c in calls),1)
        self.assertFalse(receipt['owned_container_remaining']);self.assertTrue(receipt['services_unchanged'])


if __name__=='__main__':unittest.main()

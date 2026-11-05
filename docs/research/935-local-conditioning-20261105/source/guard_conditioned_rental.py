"""Guard one receipt-bound mesh rental, including network and terminal accounting."""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import time


def excess(row,config,now):
    def above(value,ceiling):
        return (isinstance(value,bool) or not isinstance(value,(int,float))
                or not math.isfinite(value) or value<0 or value>ceiling)
    return (now>=config["deadline_epoch"] or above(row.get("dph_total"),config["hourly_ceiling_usd"])
            or any(above(row.get(key),config["network_ceiling_usd_per_gb"])
                   for key in ("inet_up_cost_usd_per_gb","inet_down_cost_usd_per_gb")))


def controls(helper):
    result=helper.controls()
    config={"deadline_epoch":100,"hourly_ceiling_usd":.4,"network_ceiling_usd_per_gb":.006}
    row={"id":123,"dph_total":.33,"inet_up_cost_usd_per_gb":.0059,"inet_down_cost_usd_per_gb":.0059}
    assert not excess(row,config,99) and excess(row,config,100)
    assert excess(row|{"dph_total":.41},config,99)
    assert excess(row|{"inet_up_cost_usd_per_gb":.007},config,99)
    assert excess({"id":123},config,99)
    for value in (None,float("nan"),-1,True,"0.1"):
        assert excess(row|{"dph_total":value},config,99)
    higher=config|{"network_ceiling_usd_per_gb":.014}
    assert not excess(row|{"inet_up_cost_usd_per_gb":.0131},higher,99)
    assert excess(row|{"inet_up_cost_usd_per_gb":.015},higher,99)
    result.update(deadline_rate_and_network_controls=True,missing_rate_refused=True,network_budget_composition_checked=True)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--helper",type=Path,required=True);p.add_argument("--self-test",action="store_true")
    a=p.parse_args();config=json.loads(a.manifest.read_text());root=a.manifest.parent
    spec=importlib.util.spec_from_file_location("retained_rental_identity",a.helper)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    tested=controls(helper)
    if a.self_test:print(json.dumps(tested));return
    assert not (root/"guard-armed.json").exists() and not (root/"guard-terminal.json").exists()
    assert time.time()<config["deadline_epoch"]<=time.time()+3600
    assert config["attempt_budget_usd"]<=1.5 and config["hourly_ceiling_usd"]<=.4
    assert config["network_ceiling_usd_per_gb"]<=.014 and config["network_allowance_gb"]<=20
    assert config["hourly_ceiling_usd"]+config["network_allowance_gb"]*config["network_ceiling_usd_per_gb"]<=config["attempt_budget_usd"]
    def call(*args):
        x=subprocess.run([config["wrapper"],*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=30)
        if x.returncode:raise RuntimeError("Approved wrapper failed: "+args[0])
        return json.loads(x.stdout)
    def terminal(data):
        with (root/"guard-terminal.json").open("x") as stream:stream.write(json.dumps(data,indent=2)+'\n')
    with (root/"guard-armed.json").open("x") as stream:
        stream.write(json.dumps({"armed_epoch":time.time(),"deadline_epoch":config["deadline_epoch"],"controls":tested,
                                 "scope":"Only the task launch receipt ID; never foreign resources"},indent=2)+'\n')
    owned=None;seen=False;absent=0
    while True:
        try:
            receipt=root/"launch-receipt.json"
            if not receipt.exists():
                if time.time()>=config["deadline_epoch"]:
                    terminal({"instance_id":None,"owned_id_unknown":True,"absence_verified":False,"deadline_reached":True});return
                if (root/"cancel-before-creation.json").exists():
                    rows=call("instances")
                    ids={row["id"] for row in rows}
                    if ids.issubset(set(config["prelaunch_instance_ids"])):
                        terminal({"instance_id":None,"creation_cancelled":True,"absence_verified":True,"confirmed_at_epoch":time.time()});return
                time.sleep(2);continue
            owned=helper.target(json.loads(receipt.read_text()))
            if owned in config["prelaunch_instance_ids"]:
                terminal({"instance_id":owned,"foreign_preexisting_receipt_refused":True,"absence_verified":False})
                return
            row=helper.select(call("instances"),owned)
            if row is None:
                absent+=1
                if seen or absent>=12:
                    terminal({"instance_id":owned,"absence_verified":True,"deadline_reached":time.time()>=config["deadline_epoch"],"confirmed_at_epoch":time.time()});return
            else:
                seen=True;absent=0
                if excess(row,config,time.time()) and helper.select(call("instances"),owned) is not None:
                    call("destroy",str(owned),"--confirm")
        except (OSError,ValueError,TypeError,RuntimeError,subprocess.TimeoutExpired):
            with (root/"guard-errors.jsonl").open("a") as stream:
                stream.write(json.dumps({"epoch":time.time(),"owned_instance_id":owned,"state":"observation_or_cleanup_failed_retrying"})+'\n')
        time.sleep(10)


if __name__=="__main__":main()

"""Bounded VM discovery; embedded into the existing OpenBao Vast wrapper.

Reuses its authentication and request boundary without changing secret access.
"""

CAD_RECODE_VM_GPUS = ("RTX PRO 6000 WS", "RTX PRO 6000 Blackwell Max-Q", "RTX PRO 6000 S")
CAD_RECODE_VM_IMAGE = "docker.io/vastai/kvm:@vastai-automatic-tag"
CAD_RECODE_VM_TEMPLATE = "fc393e1a4058a2f2b88e0c0e1a92e540"
CAD_RECODE_VM_LABEL = "3dprinting993-cad-recode-vm-20260926"
CAD_RECODE_VM_STATE = Path.home() / "projects/3dprinting993/work/cad-recode-935-fresh/vm-session.json"
CAD_RECODE_VM_GUARD = "com.3dprinting993.cad-recode-vm-expiry"


def cad_recode_vm_status(api_key):
    state = json.loads(CAD_RECODE_VM_STATE.read_text())
    instance_id = state["instance_id"]
    result = vast_request(api_key, f"/api/v0/instances/{instance_id}/")["instances"]
    if result.get("label") != CAD_RECODE_VM_LABEL:
        raise SafeError("Unexpected CAD VM identity")
    return {k: result.get(k) for k in ("id", "vm", "is_vm", "actual_status", "cur_state",
            "vm_state", "ssh_host", "ssh_port", "ports", "public_ipaddr", "status_msg")}


def expire_cad_recode_vm(api_key):
    if not CAD_RECODE_VM_STATE.exists():
        return {"status": "not_started"}
    state = json.loads(CAD_RECODE_VM_STATE.read_text())
    if state.get("label") != CAD_RECODE_VM_LABEL or type(state.get("deadline_epoch")) is not int:
        raise SafeError("Invalid CAD VM expiry state")
    if time.time() < state["deadline_epoch"]:
        return {"status": "within_deadline"}
    matches = list_instances(api_key, label=CAD_RECODE_VM_LABEL)
    for item in matches:
        destroy_instance_verified(api_key, item["id"], expected_label=CAD_RECODE_VM_LABEL)
    return {"status": "expired_verified_absent"}


def launch_cad_recode_vm(api_key, offer_id):
    offer_id = positive_id(offer_id, "CAD VM offer id")
    with simready_launch_lock():
        if CAD_RECODE_VM_STATE.exists() or list_instances(api_key):
            raise SafeError("CAD VM launch requires a fresh session and no existing instances")
        guard = subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/{CAD_RECODE_VM_GUARD}"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        if guard.returncode:
            raise SafeError("CAD VM expiry LaunchAgent must be installed first")
        offers = get_cad_recode_vm_offers(api_key)["offers"]
        selected = [o for o in offers if o["id"] == offer_id]
        if len(selected) != 1:
            raise SafeError("Selected CAD VM offer is unavailable or outside fixed limits")
        if picogk_account_balance(api_key)["conservative_available_usd"] < 15:
            raise SafeError("CAD VM requires at least USD 15 available; no automatic recharge")
        ensure_local_ssh_registered(api_key)
        state = {"label": CAD_RECODE_VM_LABEL, "offer_id": offer_id,
                 "image": CAD_RECODE_VM_IMAGE, "deadline_epoch": int(time.time()) + 10800,
                 "dph_total": selected[0]["dph_total"], "status": "creating"}
        with CAD_RECODE_VM_STATE.open("x") as f:
            json.dump(state, f, indent=2)
        try:
            result = vast_request(api_key, f"/api/v0/asks/{offer_id}/", method="PUT", payload={
                "client_id": "me", "template_hash_id": CAD_RECODE_VM_TEMPLATE, "disk": 500,
                "label": CAD_RECODE_VM_LABEL, "vm": True,
                "onstart": "#!/bin/bash\nshutdown -h +180\n", "cancel_unavail": True})
            instance_id = result.get("new_contract")
            if type(instance_id) is not int or instance_id <= 0:
                raise SafeError("CAD VM creation did not return an exact instance ID")
            state.update(instance_id=instance_id, status="created")
            CAD_RECODE_VM_STATE.write_text(json.dumps(state, indent=2))
            return state
        except BaseException:
            # Never retry an uncertain creation; reconcile the dedicated label.
            for item in list_instances(api_key, label=CAD_RECODE_VM_LABEL):
                destroy_instance_verified(api_key, item["id"], expected_label=CAD_RECODE_VM_LABEL)
            raise


def cad_recode_vm_query():
    query = heavy_offer_query()
    query.update({
        "gpu_name": {"in": list(CAD_RECODE_VM_GPUS)},
        "gpu_frac": {"gt": 0, "lte": 1},
        "vms_enabled": {"eq": True},
        "gpu_ram": {"gte": 95000},
        "cpu_cores_effective": {"gte": 32},
        "dph_total": {"lte": 2.50},
        "inet_down_cost": {"lte": 0.05},
        "inet_up_cost": {"lte": 0.05},
    })
    return query


def cad_recode_vm_eligible(offer):
    return (
        offer.get("gpu_name") in CAD_RECODE_VM_GPUS
        and (fraction := finite_number(offer.get("gpu_frac"))) is not None and 0 < fraction <= 1
        and heavy_offer_eligible(dict(offer, gpu_name=HEAVY_GPU_NAME, gpu_frac=1))
        and offer.get("vms_enabled") in (True, 1)
        and (finite_number(offer.get("gpu_ram")) or 0) >= 95000
        and (finite_number(offer.get("cpu_cores_effective")) or 0) >= 32
        and all((n := finite_number(offer.get(k))) is not None and 0 <= n <= 0.05
                for k in ("inet_up_cost", "inet_down_cost"))
    )


def get_cad_recode_vm_offers(api_key):
    result = vast_request(api_key, "/api/v0/bundles", method="POST",
                          payload=cad_recode_vm_query())
    offers = result.get("offers")
    if not isinstance(offers, list):
        raise SafeError("Vast VM search returned an invalid result")
    eligible = sorted(
        [dict(safe_offer(o), vms_enabled=True) for o in offers
         if isinstance(o, dict) and cad_recode_vm_eligible(o)],
        key=lambda o: o["dph_total"],
    )
    return {"provider_offer_count": len(offers), "offers": eligible,
            "query": cad_recode_vm_query()}


def cad_recode_vm_alternative_query():
    query = cad_recode_vm_query()
    query.update({"gpu_name": {"in": [*CAD_RECODE_VM_GPUS, "L40S", "RTX 6000Ada"]},
                  "gpu_frac": {"gt": 0, "lte": 1},
                  "gpu_ram": {"gte": 45000}, "cpu_cores_effective": {"gte": 12},
                  "cpu_ram": {"gte": 64000}, "disk_space": {"gte": 300},
                  "allocated_storage": 300, "order": [["dph_total", "asc"]]})
    return query


def cad_recode_vm_alternative_eligible(o):
    q = cad_recode_vm_alternative_query()
    # gpu_frac is the share of host GPUs, not the fraction of one GPU's VRAM.
    return (
        type(o.get("id")) is int and o["id"] > 0
        and o.get("gpu_name") in q["gpu_name"]["in"]
        and finite_number(o.get("num_gpus")) == 1
        and (f := finite_number(o.get("gpu_frac"))) is not None and 0 < f <= 1
        and o.get("vms_enabled") in (True, 1)
        and (o.get("verified") is True or o.get("verification") == "verified")
        and o.get("rentable") in (True, 1) and o.get("rented") in (False, 0)
        and all((n := finite_number(o.get(k))) is not None and n >= q[k]["gte"]
                for k in ("gpu_ram", "cpu_cores_effective", "cpu_ram", "disk_space"))
        and (r := finite_number(o.get("reliability", o.get("reliability2")))) is not None and r >= .99
        and (p := finite_number(o.get("dph_total"))) is not None and 0 < p <= 2.5
        and all((n := finite_number(o.get(k))) is not None and 0 <= n <= .05
                for k in ("inet_up_cost", "inet_down_cost"))
    )


def get_cad_recode_vm_alternatives(api_key):
    query = cad_recode_vm_alternative_query()
    result = vast_request(api_key, "/api/v0/bundles", method="POST", payload=query)
    offers = result.get("offers")
    if not isinstance(offers, list):
        raise SafeError("Vast VM alternatives search returned an invalid result")
    return {"provider_offer_count": len(offers), "query": query,
            "offers": sorted([dict(safe_offer(o), vms_enabled=True) for o in offers
                              if isinstance(o, dict) and cad_recode_vm_alternative_eligible(o)],
                             key=lambda o: o["dph_total"])}

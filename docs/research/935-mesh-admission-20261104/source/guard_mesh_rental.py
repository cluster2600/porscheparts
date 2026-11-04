"""Guard one receipt-bound mesh rental through the approved OpenBao wrapper."""
import argparse
import json
from pathlib import Path
import subprocess
import time


def target(receipt):
    value = receipt.get('instance_id')
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError('Invalid owned instance ID')
    if receipt.get('label') != '3dprinting993-mesh-cfd':
        raise ValueError('Unexpected launch receipt label')
    return value


def select(inventory, instance_id):
    if not isinstance(inventory, list):
        raise ValueError('Invalid instance inventory')
    matches = [row for row in inventory if row.get('id') == instance_id]
    if len(matches) > 1:
        raise ValueError('Ambiguous instance inventory')
    return matches[0] if matches else None


def controls():
    receipt = {'instance_id': 123, 'label': '3dprinting993-mesh-cfd'}
    assert target(receipt) == 123
    assert select([{'id': 999}, {'id': 123}], 123) == {'id': 123}
    assert select([{'id': 999}], 123) is None
    for altered in [dict(receipt, instance_id=True), dict(receipt, instance_id=-1),
                    dict(receipt, label='unrelated')]:
        try:
            target(altered)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid target accepted')
    try:
        select([{'id': 123}, {'id': 123}], 123)
    except ValueError:
        pass
    else:
        raise AssertionError('Duplicate target accepted')
    return {'positive_receipt_target': True, 'foreign_instance_not_selected': True,
            'invalid_ids_and_label_refused': True, 'duplicate_target_refused': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.manifest.read_text())
    root = args.manifest.parent
    if (root/'guard-armed.json').exists() or (root/'guard-terminal.json').exists():
        raise SystemExit('Existing guard output refused')
    wrapper = config['wrapper']
    deadline = config['deadline_epoch']
    if not time.time() < deadline <= time.time()+3600:
        raise SystemExit('Guard deadline outside one-hour bound')
    if config['attempt_budget_usd'] > 1.5 or config['hourly_ceiling_usd'] > .4:
        raise SystemExit('Guard financial bound refused')

    def call(*operation):
        process = subprocess.run([wrapper, *operation], capture_output=True, text=True, timeout=30)
        if process.returncode:
            raise RuntimeError('Approved wrapper operation failed: '+operation[0])
        return json.loads(process.stdout)

    (root/'guard-armed.json').write_text(json.dumps({'armed_epoch': time.time(), 'deadline_epoch': deadline,
        'scope': 'Only the instance ID in this task launch receipt; no label-wide destruction',
        'controls': controls()}, indent=2)+'\n')
    owned = None
    seen = False
    absent = 0
    while True:
        try:
            receipt_path = root/'launch-receipt.json'
            if not receipt_path.exists():
                time.sleep(5)
                continue
            receipt = json.loads(receipt_path.read_text())
            owned = target(receipt)
            row = select(call('instances'), owned)
            if row is None:
                absent += 1
                if seen or absent >= 12:
                    (root/'guard-terminal.json').write_text(json.dumps({'instance_id': owned,
                        'absence_verified': True, 'deadline_reached': time.time() >= deadline,
                        'confirmed_at_epoch': time.time()}, indent=2)+'\n')
                    return
            else:
                seen = True
                absent = 0
                price = row.get('dph_total')
                over_price = isinstance(price, (int, float)) and price > config['hourly_ceiling_usd']
                over_network = any(isinstance(row.get(name), (int, float)) and row[name] > .005
                                   for name in ('inet_up_cost_usd_per_gb', 'inet_down_cost_usd_per_gb'))
                if time.time() >= deadline or over_price or over_network:
                    # Fresh inventory matching and receipt binding avoid touching other rentals.
                    if select(call('instances'), owned) is not None:
                        call('destroy', str(owned), '--confirm')
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
            # Keep the guard alive across transient observation/provider failures.
            with (root/'guard-errors.jsonl').open('a') as stream:
                stream.write(json.dumps({'epoch': time.time(), 'owned_instance_id': owned,
                                         'state': 'observation_or_cleanup_failed_retrying'})+'\n')
        time.sleep(10)


if __name__ == '__main__':
    main()

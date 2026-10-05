#!/usr/bin/env python3
"""Independent interface admission; study CAD cannot manufacture its own evidence."""


def evaluate(contract, proposal):
    missing=[]
    if not contract.get('catalogue_variant_id'):missing.append('catalogue_variant_id')
    measurements=contract.get('physical_measurements',{})
    for interface,features in contract['required_interfaces'].items():
        for feature in features:
            key=interface+'.'+feature;record=measurements.get(key)
            if not isinstance(record,dict) or record.get('origin')!='physical_measurement':
                missing.append(key);continue
            if record.get('value') is None or any(not record.get(name) for name in contract['measurement_requirements']):
                missing.append(key)
    if not contract.get('manufacturing_acceptance'):missing.append('manufacturing_acceptance')
    if not contract.get('engineering_release'):missing.append('engineering_release')
    ready=not missing
    claimed=any(proposal.get(key,False) for key in ['functional_interfaces_verified','manufacturing_authorized','physical_validation_established','functional_completion_allowed'])
    if claimed and not ready:raise ValueError('Functional claim contradicts independent interface contract')
    return {'status':'physical_interfaces_complete' if ready else 'study_only_physical_interfaces_missing',
            'missing_evidence':missing,'functional_completion_allowed':ready,
            'study_geometry_may_be_reviewed':not claimed,'physical_measurements_used':len(measurements)}

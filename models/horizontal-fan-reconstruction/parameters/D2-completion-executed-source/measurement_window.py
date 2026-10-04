"""Require complete native telemetry separately from field checkpoint cadence."""
import re


def require_measurement_window(residual_iterations,inlet,outlet,force,n):
    if not isinstance(n,int) or n<=0:
        raise ValueError('A positive integer measurement window is required')
    if min(len(inlet),len(outlet),len(force),len(residual_iterations))<n:
        raise ValueError('Insufficient native samples for the frozen measurement window')
    expected=[float(v) for v in residual_iterations[-n:]]
    if expected!=list(range(int(expected[-1])-n+1,int(expected[-1])+1)):
        raise ValueError('The frozen solver window must contain consecutive iterations')
    if not all([float(row[0]) for row in values[-n:]]==expected for values in [inlet,outlet,force]):
        raise ValueError('Every measurement must match each actual iteration of the frozen window')


def configure_measurement_cadence(text,checkpoint_interval):
    match=re.search(r'\bfunctions\s*\{',text)
    if not match:raise ValueError('Measurement functions block required')
    prefix,n=re.subn(r'\bwriteInterval\s+[0-9]+','writeInterval '+str(checkpoint_interval),text[:match.start()])
    if n!=1:raise ValueError('Exactly one top-level checkpoint interval required')
    functions=text[match.start():]
    for name in ['inletFlow','outletFlow','rotorForces']:
        block=re.search(r'\b'+name+r'\s*\{([^{}]*)\}',functions)
        if not block or not re.search(r'\bwriteControl\s+timeStep\s*;',block[1]):
            raise ValueError('Per-iteration writer required: '+name)
        fixed,count=re.subn(r'\bwriteInterval\s+[0-9]+','writeInterval 1',block[0])
        if count!=1:raise ValueError('Exactly one measurement interval required: '+name)
        functions=functions[:block.start()]+fixed+functions[block.end():]
    return prefix+functions

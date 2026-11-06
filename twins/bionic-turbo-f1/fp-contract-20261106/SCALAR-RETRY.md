# Reject the first launcher attempt

The first scalar attempt passed the input filename as a positional shell
argument while sourcing OpenFOAM's bashrc. That setup script consumed the
argument and attempted to source the data file, producing `value: command not
found` before the utility ran. Its numerical output is not an accepted trial.
Preserve every first-attempt result and reject unexpected setup diagnostics.

Before retrying, save the input filename in a shell variable and remove it from
the positional arguments, then source the standard setup with no arguments.
Use a new private output directory. Keep the same eleven inputs, precision,
expected criteria, runtime, source pins and resource limits. No threshold or
case changes are made. The independent reader must reject the first attempt.

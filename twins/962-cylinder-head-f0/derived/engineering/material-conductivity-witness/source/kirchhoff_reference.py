"""Strict measured-range Kirchhoff oracle; stdlib only, no native-output parser."""
from decimal import Decimal, localcontext

D = Decimal
TEMPERATURES_C = tuple(map(D, ('23', '150', '200', '250')))
K_W_MM_K = {
    'Z': tuple(map(D, ('.1629', '.1636', '.1654', '.1605'))),
    'XY': tuple(map(D, ('.1546', '.1544', '.1549', '.1522'))),
}
LENGTH_MM = D('10')
AREA_MM2 = D('2')


def number(value):
    if isinstance(value, bool):
        raise ValueError('Finite scalar required')
    try:
        answer = D(str(value))
    except Exception as exc:
        raise ValueError('Finite scalar required') from exc
    if not answer.is_finite():
        raise ValueError('Finite scalar required')
    return answer


def column(direction):
    if direction not in K_W_MM_K:
        raise ValueError('Only separate Z and XY measured columns are defined')
    return K_W_MM_K[direction]


def conductivity(direction, temperature_C):
    t = number(temperature_C)
    values = column(direction)
    if not TEMPERATURES_C[0] <= t <= TEMPERATURES_C[-1]:
        raise ValueError('Measured23..250C range only; no extension or clamping')
    with localcontext() as context:
        context.prec = 60
        for i, (lo, hi) in enumerate(zip(TEMPERATURES_C, TEMPERATURES_C[1:])):
            if t <= hi:
                return values[i] + (values[i+1]-values[i])*(t-lo)/(hi-lo)
    raise ValueError('Uncovered measured temperature')


def primitive(direction, temperature_C):
    """Integral from23C toT of k(T)dT, in W/mm; exact decimal segment data."""
    t = number(temperature_C)
    values = column(direction)
    if not TEMPERATURES_C[0] <= t <= TEMPERATURES_C[-1]:
        raise ValueError('Measured23..250C range only; no extension or clamping')
    with localcontext() as context:
        context.prec = 60
        total = D(0)
        for i, (lo, hi) in enumerate(zip(TEMPERATURES_C, TEMPERATURES_C[1:])):
            if t <= lo:
                break
            dt = min(t, hi)-lo
            slope = (values[i+1]-values[i])/(hi-lo)
            total += values[i]*dt+slope*dt*dt/2
        return total


def temperature(direction, z_mm):
    """Continuum solution of d/dz(k(T)dT/dz)=0; independent of any mesh."""
    z = number(z_mm)
    values = column(direction)
    if not 0 <= z <= LENGTH_MM:
        raise ValueError('Declared0..10mm bar only; no profile extrapolation')
    with localcontext() as context:
        context.prec = 60
        target = primitive(direction, TEMPERATURES_C[-1])*z/LENGTH_MM
        for t in TEMPERATURES_C:
            if target == primitive(direction, t):
                return t
        for i, (lo, hi) in enumerate(zip(TEMPERATURES_C, TEMPERATURES_C[1:])):
            lower, upper = primitive(direction, lo), primitive(direction, hi)
            if lower < target < upper:
                s = target-lower
                slope = (values[i+1]-values[i])/(hi-lo)
                discriminant = values[i]*values[i]+2*slope*s
                if discriminant <= 0:
                    raise ValueError('Invalid positive-conductivity reference')
                dt = 2*s/(values[i]+discriminant.sqrt())
                answer = lo+dt
                if not lo < answer < hi:
                    raise ValueError('Reference inversion left its measured segment')
                return answer
    raise ValueError('Uncovered Kirchhoff coordinate')


def axial_flux_density(direction):
    """Signed q_z=-k*dT/dz in W/mm2; heat flows toward the cold z=0 end."""
    return -primitive(direction, TEMPERATURES_C[-1])/LENGTH_MM


def gauss2_average(direction, cold_temperature_C, hot_temperature_C):
    """k average for one linear axial FE cell at its declared2Gauss points."""
    lo, hi = number(cold_temperature_C), number(hot_temperature_C)
    conductivity(direction, lo)
    conductivity(direction, hi)
    with localcontext() as context:
        context.prec = 60
        middle, half = (lo+hi)/2, (hi-lo)/2
        point = half/D(3).sqrt()
        return (conductivity(direction, middle-point)+conductivity(direction, middle+point))/2

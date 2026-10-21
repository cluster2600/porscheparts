"""Reproduce the documented CalculiX2.21 plcopy.f limit before known-result checks."""
import numpy as np


def effective_curve(raw):
    """Rows are stress, plastic strain; retain the input curve unchanged."""
    raw=np.asarray(raw,dtype=float)
    assert raw.ndim==2 and raw.shape[1]==2 and np.isfinite(raw).all()
    assert np.all(np.diff(raw[:,1])>0)
    if len(raw)<=200:
        return raw.copy()
    # Official plcopy.f lines54–65: 199 equal intervals, upper endpoint−1e−10.
    start,end=raw[0,1],raw[-1,1]-1e-10
    strain=start+np.arange(200)*(end-start)/199
    return np.column_stack((np.interp(strain,raw[:,1],raw[:,0]),strain))


def maximum_interpolation_difference(raw,effective):
    """The difference of two linear interpolants attains extrema at union knots."""
    knots=np.unique(np.r_[raw[:,1],effective[:,1]])
    knots=knots[(knots>=effective[0,1])&(knots<=effective[-1,1])]
    error=np.abs(np.interp(knots,raw[:,1],raw[:,0])-np.interp(knots,effective[:,1],effective[:,0]))
    index=int(error.argmax())
    return float(error[index]),float(knots[index])

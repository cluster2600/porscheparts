"""Preserve exhaustive best-valid edge choice while delaying expensive checks."""
import math

def choose(rows,evaluate):
    rows=list(rows)
    assert len({row[2] for row in rows})==len(rows),'Duplicate edge key'
    for score,length,key in rows:
        assert math.isfinite(score) and score>=0 and math.isfinite(length) and length>0
        assert type(key) is int and key>=0
    for row in sorted(rows,key=lambda x:(x[0],x[1],-x[2]),reverse=True):
        proof=evaluate(row[2])
        if proof is not None:
            return row,proof
    return None

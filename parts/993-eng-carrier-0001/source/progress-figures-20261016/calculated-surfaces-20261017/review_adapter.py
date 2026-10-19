"""Bind this rendering to the independently reviewed three local checkpoints."""

SUPPORTS = {
    3: 'cba69543b45d599f4d5298e66889872f1c78f6bf2a6788899af4ebacdb93dd35',
    9: '607dfadf95edff7738ae11e6e3c1560f13e73a416844bebd01d49034e1a6c943',
    10: 'cdd21de198227d6facef7789b98751659ed85d1c3ce666a219c2ccf795c18d91',
}

def verify(review, checkpoints):
    if (review.get('status') != 'three_region_checkpoint_identity_review_passed_no_global_admission'
            or review.get('global_admission') is not False):
        raise ValueError('The independent local review was not passed in its declared scope')
    rows = review.get('rows', [])
    if [r.get('source_index') for r in rows] != [3, 9, 10]:
        raise ValueError('The review must bind all three regions in order')
    for row in rows:
        index = row['source_index']
        if (row.get('checkpoint_sha256') != checkpoints[index]
                or row.get('support_npz_sha256') != SUPPORTS[index]
                or row.get('local_checkpoint_pass') is not True):
            raise ValueError('A locally reviewed checkpoint or real surface differs')

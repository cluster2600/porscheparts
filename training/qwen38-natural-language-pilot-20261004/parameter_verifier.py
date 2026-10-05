"""Strict spacer parameters and pure owner-intent grading, without builder permission.

This module parses no requests, evaluates no expressions and reads no gold files.
The grader supplies its independently reviewed expected response in memory; this
function cannot authenticate that review or authorize any geometry execution.
"""
import json
import math
from decimal import Decimal, InvalidOperation

MAX_JSON_BYTES = 8192
FIELDS = ('outer_diameter_mm', 'inner_diameter_mm', 'thickness_mm')
VARIANTS = ((40, 20, 3), (45, 20, 3))
REASONS = {'needs_clarification': ('missing_dimension', 'conflicting_request', 'unsupported_request'),
           'rejected': ('out_of_scope', 'unsupported_unit')}


class VerificationError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise VerificationError(message)


def keys(value, expected, label):
    require(type(value) is dict and set(value) == set(expected), 'Unknown or missing fields: ' + label)


def finite_number(value):
    require(type(value) in (int, float, Decimal), 'Finite numeric dimension required; no bool or expression')
    if type(value) is float:
        require(math.isfinite(value), 'Nonfinite dimension')
    try:
        result = value if type(value) is Decimal else Decimal(str(value))
    except (InvalidOperation, ValueError, OverflowError) as error:
        raise VerificationError('Invalid numeric dimension') from error
    require(result.is_finite(), 'Nonfinite dimension')
    return result


def strict_loads(raw):
    require(type(raw) in (str, bytes), 'JSON text or UTF-8 bytes required')
    try:
        data = raw.encode('utf-8') if type(raw) is str else raw
        require(len(data) <= MAX_JSON_BYTES and not data.startswith(b'\xef\xbb\xbf'), 'Oversized JSON or BOM')
        def pairs(entries):
            result = {}
            for key, value in entries:
                require(key not in result, 'Duplicate JSON key: ' + key)
                result[key] = value
            return result
        def constant(value):
            raise VerificationError('Nonstandard JSON number: ' + value)
        value = json.loads(data.decode('utf-8'), object_pairs_hook=pairs,
                           parse_float=Decimal, parse_constant=constant)
    except (InvalidOperation, ValueError, UnicodeError, RecursionError) as error:
        if isinstance(error, VerificationError):
            raise
        raise VerificationError('Invalid strict JSON') from error
    require(type(value) is dict, 'JSON object required')
    return value


def validate_response(response):
    """Validate shape/numbers only; never assert association with a request."""
    keys(response, ('schema_version', 'status', 'parameters', 'reason'), 'response')
    require(type(response['schema_version']) is int and response['schema_version'] == 1, 'Only integer schema version1')
    status = response['status']
    require(type(status) is str and status in ('proposal', *REASONS), 'Unknown status')
    if status != 'proposal':
        require(response['parameters'] is None and type(response['reason']) is str and
                response['reason'] in REASONS[status], 'Nonproposal requires null parameters and a status-specific reason')
        return {'schema_version': 1, 'status': status, 'parameters': None, 'reason': response['reason']}
    require(response['reason'] is None, 'Proposal reason must be null')
    params = response['parameters']
    keys(params, (*FIELDS, 'unit'), 'parameters')
    require(type(params['unit']) is str and params['unit'] == 'mm', 'Only canonical mm; no inferred conversion')
    values = tuple(finite_number(params[field]) for field in FIELDS)
    require(values[0] > values[1] > 0 and values[2] > 0, 'OD > ID > 0 and thickness > 0 required')
    require(values in VARIANTS, 'Only the exact40/20/3 or45/20/3 mm discrete tuple')
    return {'schema_version': 1, 'status': 'proposal',
            'parameters': dict(zip(FIELDS, map(int, values)), unit='mm'), 'reason': None}


def validate_json(raw):
    return validate_response(strict_loads(raw))


def compare_expected_intent(response, expected_response, acceptable_nonproposal_reasons=None):
    """Pure grading against a caller-owned expected response; no file/gold access.

    Optional alternative reasons must be a nonempty distinct list of codes for
    the expected nonproposal status. Their prior review is the caller's duty.
    A semantic match is necessary evidence, never a builder authorization.
    """
    candidate = validate_response(response)
    expected = validate_response(expected_response)
    if expected['status'] == 'proposal':
        require(acceptable_nonproposal_reasons is None, 'Alternative reasons apply only to nonproposals')
        reason_match = candidate['reason'] is None
    else:
        accepted = [expected['reason']] if acceptable_nonproposal_reasons is None else acceptable_nonproposal_reasons
        require(type(accepted) is list and accepted and all(type(code) is str and code in REASONS[expected['status']] for code in accepted),
                'Pre-reviewed reasons must be a nonempty status-specific list')
        require(len(set(accepted)) == len(accepted), 'Duplicate accepted reason')
        reason_match = candidate['reason'] in accepted
    status_match = candidate['status'] == expected['status']
    parameters_match = candidate['parameters'] == expected['parameters']
    return {'semantic_match': status_match and parameters_match and reason_match,
            'status_match': status_match, 'parameters_match': parameters_match, 'reason_match': reason_match,
            'expected_review_authenticated': False, 'builder_execution_authorized': False,
            'geometry_runtime': 'CLOSED'}

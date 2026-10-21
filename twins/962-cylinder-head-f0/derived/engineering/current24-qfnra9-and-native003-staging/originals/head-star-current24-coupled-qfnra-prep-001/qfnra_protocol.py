"""HELD/UNRUN pure QF_NRA reply projection and same-model word mapping.

No transport, subprocess, solver import, file IO, fallback or execution authority.
Only protocol and rounding GIVEN a retained model are deterministic.
"""
from fractions import Fraction
import hashlib
import json
import struct

CAP = 32 * 1024**2
MAX_POSITIVE_WORD = 0x7fefffffffffffff


class ProtocolRefusal(ValueError):
    pass


class MappingRefusal(ValueError):
    def __init__(self, message, events):
        super().__init__(message)
        self.events = list(events)


def need(value, message):
    if not value:
        raise ProtocolRefusal(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def symbol(component, node, axis):
    need(type(component) is int and component > 0 and type(node) is int and node > 0,
         'Positive component/node IDs required')
    need(type(axis) is int and 0 <= axis < 3, 'Exact axis0..2 required')
    return 'c%03d_n%d_%s' % (component, node, 'xyz'[axis])


def parse_sexpr(text):
    """One complete response; iterative, bounded by full input bytes, never eval."""
    need(type(text) is str and len(text.encode('utf-8')) <= CAP,
         'Complete response must fit32MiB')
    roots = []
    stack = []
    i = 0
    while i < len(text):
        c = text[i]
        if c in ' \r\n\t':
            i += 1
            continue
        if c == '(':
            row = []
            (stack[-1] if stack else roots).append(row)
            stack.append(row)
            i += 1
            continue
        if c == ')':
            need(bool(stack), 'Unexpected closing parenthesis')
            stack.pop()
            i += 1
            continue
        if c == '"':
            i += 1
            out = []
            while True:
                need(i < len(text), 'Unterminated SMT string')
                if text[i] == '"':
                    if i + 1 < len(text) and text[i + 1] == '"':
                        out.append('"')
                        i += 2
                        continue
                    i += 1
                    break
                need(ord(text[i]) >= 32 or text[i] in '\r\n\t', 'Control byte in string')
                out.append(text[i])
                i += 1
            token = {'SMT_string': ''.join(out)}
        else:
            start = i
            while i < len(text) and text[i] not in '() \r\n\t':
                need(text[i].isascii() and ord(text[i]) >= 33
                     and text[i] not in ';"|\\', 'Unsupported reply token')
                i += 1
            token = text[start:i]
            need(bool(token), 'Empty token')
        (stack[-1] if stack else roots).append(token)
    need(not stack and len(roots) == 1, 'Exactly one complete response required')
    root = roots[0]
    if isinstance(root, list) and root and root[0] == 'error':
        raise ProtocolRefusal('Solver error response: ' + canonical(root))
    return root


def rational_value(term):
    """Exact finite numeral forms only; '?' decimal and nonconstant division refuse."""
    if type(term) is str:
        if term.isascii() and term.isdigit():
            return Fraction(int(term))
        if term.count('.') == 1:
            a, b = term.split('.')
            if a.isascii() and b.isascii() and a.isdigit() and b.isdigit():
                return Fraction(int(a + b), 10**len(b))
        raise ProtocolRefusal('Unsupported exact numeral')
    need(type(term) is list and bool(term), 'Exact numeral expression required')
    if term[0] == '-' and len(term) == 2:
        return -rational_value(term[1])
    if term[0] == '/' and len(term) == 3:
        a, b = rational_value(term[1]), rational_value(term[2])
        need(b != 0, 'Constant division by zero refuses')
        return a / b
    raise ProtocolRefusal('Unsupported exact numeral expression')


def model_value(term):
    """Algebraic root terms remain solver-owned syntax, never decimal approximations."""
    try:
        q = rational_value(term)
    except ProtocolRefusal:
        q = None
    if q is not None:
        return dict(kind='rational', numerator=str(q.numerator), denominator=str(q.denominator))
    need(type(term) is list and len(term) == 3 and term[0] == 'root-obj'
         and type(term[2]) is str and term[2].isascii() and term[2].isdigit(),
         'Unsupported model value; no approximate fallback')
    def polynomial(node):
        if node == 'x':
            return
        try:
            rational_value(node)
            return
        except ProtocolRefusal:
            pass
        need(type(node) is list and bool(node), 'Root polynomial syntax required')
        if node[0] in ('+', '*') and len(node) >= 3:
            for child in node[1:]:
                polynomial(child)
        elif node[0] == '-' and len(node) in (2, 3):
            for child in node[1:]:
                polynomial(child)
        elif node[0] == '^' and len(node) == 3:
            need(type(node[2]) is str and node[2].isascii() and node[2].isdigit(),
                 'Nonnegative integer polynomial exponent required')
            polynomial(node[1])
        else:
            raise ProtocolRefusal('Unsupported root polynomial syntax')
    polynomial(term[1])
    return dict(kind='solver_algebraic_root_term', term=term,
                root_index_interpretation='Uninterpreted solver-owned syntax; no root theorem claimed')


def parse_status(text):
    status = parse_sexpr(text)
    need(type(status) is str and status in ('sat', 'unsat', 'unknown'), 'Exact solver status required')
    return status


def parse_projection(text, expected_symbols, status):
    need(status == 'sat', 'Only SAT permits a candidate projection')
    need(type(expected_symbols) is list and expected_symbols
         and len(expected_symbols) == len(set(expected_symbols)), 'Unique ordered symbols required')
    rows = parse_sexpr(text)
    need(type(rows) is list and len(rows) == len(expected_symbols), 'Full model projection required')
    out = []
    for row, name in zip(rows, expected_symbols):
        need(type(row) is list and len(row) == 2 and row[0] == name,
             'Ordered model symbol association changed')
        out.append(dict(symbol=name, value=model_value(row[1]), raw_term=row[1]))
    return out


def normalized_term(term):
    try:
        q = rational_value(term)
        return ['exact_rational', str(q.numerator), str(q.denominator)]
    except ProtocolRefusal:
        pass
    if type(term) is str:
        need(term and all(c.isascii() and (c.isalnum() or c == '_') for c in term),
             'Unsupported queried symbol')
        return term
    need(type(term) is list and term and term[0] in ('<', '<=', '=', '>', '>=', '-'),
         'Unsupported Boolean query expression')
    need(len(term) == (2 if term[0] == '-' else 3), 'Exact query arity required')
    return [term[0]] + [normalized_term(x) for x in term[1:]]


def parse_boolean(text, expected_term, status):
    need(status == 'sat', 'Only retained SAT model queries allowed')
    rows = parse_sexpr(text)
    need(type(rows) is list and len(rows) == 1 and type(rows[0]) is list and len(rows[0]) == 2,
         'One complete Boolean get-value pair required')
    need(normalized_term(rows[0][0]) == normalized_term(parse_sexpr(expected_term)),
         'Returned query term does not match request')
    need(type(rows[0][1]) is str and rows[0][1] in ('true', 'false'), 'Exact Boolean response required')
    return rows[0][1] == 'true'


def snapshot_id(projection):
    return hashlib.sha256(canonical(projection).encode()).hexdigest()


def positive_word_value(word):
    need(type(word) is int and 0 <= word <= MAX_POSITIVE_WORD, 'Finite nonnegative word required')
    exponent = (word >> 52) & 2047
    mantissa = word & ((1 << 52) - 1)
    if exponent:
        mantissa += 1 << 52
    shift = exponent - 1023 - 52 if exponent else -1074
    return Fraction(mantissa << shift) if shift >= 0 else Fraction(mantissa, 1 << -shift)


def smt_rational(value):
    need(type(value) in (int, Fraction), 'Exact rational constant required')
    q = Fraction(value)
    number = str(abs(q.numerator))
    if q.numerator < 0:
        number = '(- ' + number + ')'
    return number if q.denominator == 1 else '(/ ' + number + ' ' + str(q.denominator) + ')'


def nearest_binary64(coordinate, scale, retained_model_id, oracle):
    """One model coordinate -> one word, through a pure same-model callback.

    Callback receives {model_id,term,command}; returns a real bool. No transport
    exists here. External code must keep the same SAT session and retain replies.
    """
    need(type(coordinate) is dict and set(coordinate) == {'component_ID', 'node_tag', 'axis', 'symbol'},
         'Exact coordinate association required')
    name = symbol(coordinate['component_ID'], coordinate['node_tag'], coordinate['axis'])
    need(coordinate['symbol'] == name, 'Coordinate symbol mismatch')
    need(type(scale) is int and scale > 0 and scale & (scale - 1) == 0, 'Positive power-of-two scale required')
    need(type(retained_model_id) is str and len(retained_model_id) == 64
         and all(c in '0123456789abcdef' for c in retained_model_id), 'Retained model identity required')
    need(callable(oracle), 'Explicit callback required; no fallback')
    events = []
    def ask(operator, left, right):
        term = '(' + operator + ' ' + left + ' ' + right + ')'
        request = dict(model_id=retained_model_id, term=term, command='(get-value (' + term + '))')
        event = dict(request=request, value=None)
        events.append(event)
        try:
            answer = oracle(request)
        except Exception as exc:
            event['error'] = repr(exc)
            raise MappingRefusal('Same-model callback failed', events) from exc
        if type(answer) is not bool:
            event['error'] = 'Callback returned a non-Boolean'
            raise MappingRefusal('Same-model callback must return bool', events)
        event['value'] = answer
        return answer
    def threshold(q):
        return smt_rational(scale * q)
    if ask('=', name, '0'):
        return dict(coordinate=coordinate, word_u64=0, word_le_hex='0000000000000000',
                    rule='Exact zero -> canonical+0', model_id=retained_model_id, events=events)
    negative = ask('<', name, '0')
    magnitude = '(- ' + name + ')' if negative else name
    if not ask('<=', magnitude, threshold(positive_word_value(MAX_POSITIVE_WORD))):
        raise MappingRefusal('Model coordinate outside finite-word range; no fallback', events)
    lo, hi = 0, MAX_POSITIVE_WORD
    decisions = 0
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if ask('<=', threshold(positive_word_value(mid)), magnitude):
            lo = mid
        else:
            hi = mid - 1
        decisions += 1
    need(decisions <= 63, 'Finite-word rank bound violated')
    lower = positive_word_value(lo)
    if ask('=', magnitude, threshold(lower)):
        chosen = lo
        bracket = dict(lower_word=lo, exact_representable=True)
    else:
        if lo == MAX_POSITIVE_WORD:
            raise MappingRefusal('Inconsistent model range/equality replies', events)
        upper = positive_word_value(lo + 1)
        if not ask('<', magnitude, threshold(upper)):
            raise MappingRefusal('Inconsistent final adjacent-word bracket', events)
        midpoint = (lower + upper) / 2
        if ask('<', magnitude, threshold(midpoint)):
            chosen = lo
            relation = 'below_midpoint'
        elif ask('=', magnitude, threshold(midpoint)):
            chosen = lo if lo & 1 == 0 else lo + 1
            relation = 'tie_to_even'
        else:
            chosen = lo + 1
            relation = 'above_midpoint'
        bracket = dict(lower_word=lo, upper_word=lo + 1,
            lower_rational=[str(lower.numerator), str(lower.denominator)],
            upper_rational=[str(upper.numerator), str(upper.denominator)],
            midpoint_rational=[str(midpoint.numerator), str(midpoint.denominator)], relation=relation)
    word = chosen | (1 << 63 if negative else 0)
    return dict(coordinate=coordinate, word_u64=word, word_le_hex=struct.pack('<Q', word).hex(),
                bracket=bracket, rank_decisions=decisions, model_id=retained_model_id, events=events,
                real_model_feasibility_implies_rounded_gate=False, application_authorized=False)

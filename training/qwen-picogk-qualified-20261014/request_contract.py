"""Request-derived quantities for the existing six bounded PicoGK recipes."""
from decimal import Decimal, InvalidOperation
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('qualified_legacy_course', HERE.parent/'qwen-picogk-robustness-20261013/run.py')
course = importlib.util.module_from_spec(spec)
spec.loader.exec_module(course)
pilot = course.pilot
FIELDS = {
    'cylinder': (('length', 'length'), ('outer', 'radius')),
    'pipe': (('length', 'length'), ('outer', 'radius'), ('inner', 'radius')),
    'washer': (('thickness', 'length'), ('outer', 'radius'), ('bore', 'radius')),
    'bcc': (('cell_side', 'length'), ('beam', 'diameter')),
    'thread': (('length', 'length'), ('outer', 'radius'), ('core', 'radius'), ('pitch', 'length')),
}
UNITS = {'mm': Decimal(1), 'cm': Decimal(10), 'm': Decimal(1000)}
LANGUAGES = ('en', 'fr', 'de', 'ja', 'zh')


def normalize(request):
    if not isinstance(request, dict) or set(request) != {'recipe', 'language', 'interface_status', 'fields'}:
        raise ValueError('Request requires recipe, language, interface_status and fields')
    language, status, fields = request['language'], request['interface_status'], request['fields']
    if any(type(request[key]) is not str for key in ('recipe', 'language', 'interface_status')):
        raise ValueError('Recipe, language and interface status must be strings')
    if language not in LANGUAGES or status not in ('synthetic', 'missing', 'unverified') or not isinstance(fields, dict):
        raise ValueError('Unsupported language, interface status or fields')
    if status != 'synthetic':
        return {'recipe': 'needs_measurement', 'parameters_mm': [], 'missing': ['measured_interfaces']}
    recipe = request['recipe']
    if recipe not in FIELDS or set(fields) != {name for name, _ in FIELDS[recipe]}:
        raise ValueError('Provide every named recipe field without extras')
    values = []
    for name, target in FIELDS[recipe]:
        field = fields[name]
        if not isinstance(field, dict) or set(field) != {'value', 'unit', 'quantity'}:
            raise ValueError('Each field requires value, unit and quantity')
        if type(field['unit']) is not str or field['unit'] not in UNITS or type(field['value']) not in (str, int, float):
            raise ValueError('Unsupported unit or value')
        text = str(field['value']).strip()
        pattern = r'[0-9]+(?:[.,][0-9]+)?' if language in ('fr', 'de') else r'[0-9]+(?:\.[0-9]+)?'
        if len(text) > 64 or not re.fullmatch(pattern, text):
            raise ValueError('Use an explicit decimal without grouping or inferred units')
        try:
            number = Decimal(text.replace(',', '.')) * UNITS[field['unit']]
        except InvalidOperation as error:
            raise ValueError('Invalid decimal') from error
        quantity = field['quantity']
        if type(quantity) is not str: raise ValueError('Quantity must be a string')
        if target == 'length':
            if quantity != 'length': raise ValueError('Length field has a radial quantity')
        elif quantity not in ('radius', 'diameter'):
            raise ValueError('Specify radius or diameter explicitly')
        elif target != quantity:
            number = number / 2 if target == 'radius' else number * 2
        if not number.is_finite(): raise ValueError('Nonfinite quantity')
        values.append(float(number))
    return pilot.parse(json.dumps({'recipe': recipe, 'parameters_mm': values, 'missing': []}, allow_nan=False))


def canonical(request):
    plan = normalize(request)
    if plan['recipe'] == 'needs_measurement':
        return 'Original Porsche mounting interfaces are missing or unverified. Return needs_measurement; invent no dimensions.'
    names = ', '.join(name for name, _ in FIELDS[plan['recipe']])
    return (f"Synthetic {plan['recipe']}. Named fields in order: {names}. "
            f"parameters_mm={json.dumps(plan['parameters_mm'], separators=(',', ':'))}. "
            'These values already use the ordered recipe quantities in millimeters. Preserve them exactly; do not halve radii.')


def accepted(response, finish, request):
    plan = course.ask.accepted(response, finish)
    if not pilot.matches(plan, normalize(request)):
        raise ValueError('Model proposal differs from the independent request contract')
    return plan

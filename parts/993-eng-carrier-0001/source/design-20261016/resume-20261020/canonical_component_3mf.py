"""Preserve source coordinates as exact decimal numbers in a component 3MF."""
from decimal import Decimal
from fractions import Fraction
import hashlib
import io
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

CORE='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
IDENTITY=[1,0,0,0,1,0,0,0,1,0,0,0]


def exact_decimal(value):
    value=float(value)
    if not math.isfinite(value):raise ValueError('Nonfinite vertex coordinate')
    return format(Decimal.from_float(value),'f')


def identity_transform(text):
    return text is None or [Fraction(x) for x in text.split()]==IDENTITY


def canonicalize(raw_archive,output,source_coordinates):
    output=Path(output)
    if output.exists():raise ValueError('Preserve the existing archive')
    with zipfile.ZipFile(raw_archive) as source:
        model_name='3D/3dmodel.model'
        raw_model=source.read(model_name)
        namespaces=dict(value for _,value in ET.iterparse(io.BytesIO(raw_model),events=('start-ns',)))
        for prefix,uri in namespaces.items():ET.register_namespace(prefix,uri)
        model=ET.fromstring(raw_model)
        if model.tag!='{'+CORE+'}model' or model.get('unit','millimeter')!='millimeter':
            raise ValueError('Millimetre Core 3MF model required')
        objects={int(obj.get('id')):obj for obj in model.findall('./{'+CORE+'}resources/{'+CORE+'}object')}
        coordinate_count=0
        for resource_id,coordinates in source_coordinates.items():
            vertices=objects[resource_id].findall('./{'+CORE+'}mesh/{'+CORE+'}vertices/{'+CORE+'}vertex')
            if len(vertices)!=len(coordinates):raise ValueError('Source vertex count differs')
            for vertex,point in zip(vertices,coordinates):
                for axis,value in zip(['x','y','z'],point):
                    vertex.set(axis,exact_decimal(value));coordinate_count+=1
        items=model.findall('./{'+CORE+'}build/{'+CORE+'}item')
        if len(items)!=1 or not identity_transform(items[0].get('transform')):
            raise ValueError('One identity-transform build item required')
        component_object=objects[int(items[0].get('objectid'))]
        components=component_object.findall('./{'+CORE+'}components/{'+CORE+'}component')
        ids=[int(c.get('objectid')) for c in components]
        if ids!=list(source_coordinates) or not all(identity_transform(c.get('transform')) for c in components):
            raise ValueError('Complete identity component graph required')
        ET.register_namespace('',CORE)
        encoded=ET.tostring(model,encoding='utf-8',xml_declaration=True)
        for prefix in model.get('requiredextensions','').split():
            if prefix not in namespaces:raise ValueError('Unbound required extension prefix')
            if ('xmlns:'+prefix+'=').encode() not in encoded:
                model.set('xmlns:'+prefix,namespaces[prefix])
        encoded=ET.tostring(model,encoding='utf-8',xml_declaration=True)
        with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as target:
            for item in source.infolist():
                entry=zipfile.ZipInfo(item.filename,date_time=(1980,1,1,0,0,0))
                entry.compress_type=zipfile.ZIP_DEFLATED
                target.writestr(entry,encoded if item.filename==model_name else source.read(item.filename))
    return dict(unit='millimeter',build_item_count=1,component_resource_ids=ids,
                all_build_and_component_transforms_identity=True,
                exact_decimal_coordinate_count=coordinate_count,
                raw_archive_sha256=hashlib.sha256(Path(raw_archive).read_bytes()).hexdigest(),
                canonical_archive_sha256=hashlib.sha256(output.read_bytes()).hexdigest())

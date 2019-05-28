import json
from copy import deepcopy
from decimal import Decimal

import dateutil

from toll_booth.obj.data_objects import SensitiveData
from toll_booth.obj.data_objects.stored_data import S3StoredData


def _set_object_property_value(data_type, obj_value):
    if data_type == 'N':
        return Decimal(obj_value)
    if data_type == 'S':
        return str(obj_value)
    if data_type == 'B':
        return obj_value == 'True'
    if data_type == 'DT':
        return dateutil.parser.parse(obj_value)
    raise NotImplementedError(f'do not understand how to parse {obj_value} with data_type: {data_type}')


class GqlResolver(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    @staticmethod
    def object_hook(obj):
        if '__typename' not in obj:
            return obj
        alg_class = obj['__typename']
        obj_value = deepcopy(obj)
        del (obj_value['__typename'])
        if alg_class == 'ObjectProperty':
            return {obj_value['property_name']: obj_value['property_value']}
        if alg_class == 'LocalPropertyValue':
            data_type = obj_value['data_type']
            return _set_object_property_value(data_type, obj_value['property_value'])
        if alg_class == 'SensitivePropertyValue':
            pointer = obj_value['pointer']
            data_type = obj_value['sensitive_data_type']
            sensitive_data = SensitiveData.from_insensitive(pointer)
            return _set_object_property_value(data_type, sensitive_data)
        if alg_class == 'StoredPropertyValue':
            data_type = obj_value['stored_data_type']
            storage_class = obj_value['storage_class']
            storage_uri = obj_value['storage_uri']
            if storage_class == 's3':
                s3_data = S3StoredData(data_type, storage_class, storage_uri)
                return _set_object_property_value(data_type, s3_data.retrieve())
        return obj


class GqlDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    @staticmethod
    def object_hook(obj):
        if '__typename' not in obj:
            return obj
        alg_class = obj['__typename']
        obj_value = deepcopy(obj)
        del (obj_value['__typename'])
        if alg_class == 'ObjectProperty':
            object_property = obj_value['property_value']
            object_property['property_name'] = obj_value['property_name']
            return object_property
        return obj

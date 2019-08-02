from datetime import datetime
from decimal import Decimal
from typing import Union

import dateutil


def set_property_data_type(data_type: str, property_value: str, **kwargs) -> Union[None, Decimal, str, bool, datetime]:
    if not property_value:
        return None
    if property_value == '':
        return None
    if data_type == 'N':
        return Decimal(property_value)
    if data_type == 'S':
        return str(property_value)
    if data_type == 'DT':
        return dateutil.parser.parse(property_value)
    if data_type == 'B':
        return property_value == 'True'
    raise NotImplementedError(
        f'data type {data_type} is unknown to the system')

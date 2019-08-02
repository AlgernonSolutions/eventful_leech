import json
from datetime import datetime
from decimal import Decimal


class FireHoseEncoder(json.JSONEncoder):
    @classmethod
    def default(cls, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super(FireHoseEncoder, cls()).default(obj)

import os
from typing import Union, Dict, Any

from aws_xray_sdk.core import xray_recorder

from toll_booth.obj.schemata.schema import Schema


@xray_recorder.capture()
def leech(object_type: str,
          extracted_data: Dict[str, Any],
          **kwargs) -> Dict[str, Union[str, Any]]:
    """Entry method for this block, formats data and redirects to generate_source_vertex

    Args:
        object_type:
        extracted_data:
        kwargs:
    Returns:

    """
    bucket_name = os.environ['STORAGE_BUCKET_NAME']
    schema = Schema.retrieve(bucket_name)
    schema_entry = schema[object_type]
    return {
        'schema': schema,
        'schema_entry': schema_entry,
        'extracted_data': extracted_data
    }

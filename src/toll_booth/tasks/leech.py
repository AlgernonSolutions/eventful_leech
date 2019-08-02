import os
from typing import Dict, Any, List

from aws_xray_sdk.core import xray_recorder

from toll_booth.obj.aio import AioMaster
from toll_booth.obj.schemata.schema import Schema


# @xray_recorder.capture()
def leech(object_type: str,
          identifier: str,
          id_value: int,
          extracted_data: Dict[str, Any],
          **kwargs) -> List[Dict]:
    """Entry method for this block, formats data and redirects to generate_source_vertex

    Args:
        object_type:
        id_value:
        identifier:
        extracted_data:
        kwargs:
    Returns:

    """
    bucket_name = os.environ['STORAGE_BUCKET_NAME']
    progress_table_name = os.environ['PROGRESS_TABLE_NAME']
    schema = Schema.retrieve(bucket_name)
    aio_kwargs = {
        'identifier': identifier,
        'id_value': id_value,
        'source_object_type': object_type,
        'extracted_data': extracted_data,
        'schema': schema,
        'num_potential_workers': kwargs.get('num_potential_workers', 5),
        'num_identified_workers': kwargs.get('num_identified_workers', 5),
        'progress_table_name': progress_table_name
    }
    aio_master = AioMaster(**aio_kwargs)
    results = aio_master.work()
    return [{x: y.for_gql for x, y in a.items()} for a in results]

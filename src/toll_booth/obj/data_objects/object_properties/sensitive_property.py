import hashlib
import logging
import os

import boto3

from toll_booth.obj.utils import set_property_data_type


class SensitivePropertyValue:
    """
        data that is HIPAA relevant does not get stored directly onto the public graph, instead it is stored into
            a separate table and referenced by pointer
    """
    def __init__(self, source_internal_id, property_name, sensitive_value):
        """SensitiveData is any information that might be considered relevant to HIPAA

            Any data possibly relevant to HIPAA is not stored directly into the graph or index
            Instead, an opaque pointer is generated and used in place of the data
            The sensitive data itself is stored in a separate location, where it can be retrieved by authorized persons

        Args:
            source_internal_id:
            property_name:
            sensitive_value:
        """
        self._source_internal_id = source_internal_id
        self._property_name = property_name
        self._sensitive_value = sensitive_value

    @classmethod
    def from_insensitive_pointer(cls, pointer):
        """ retrieves a value from the remote table per the pointer

        Args:
            pointer:

        Returns:

        """
        sensitive_table_name = os.environ['SENSITIVE_TABLE']
        resource = boto3.resource('dynamodb')
        table = resource.Table(sensitive_table_name)
        results = table.get_item(Key={'insensitive': pointer})
        returned_item = results.get('Item')
        if returned_item is None:
            raise RuntimeError(f'sensitive value cannot be found: {pointer}')
        sensitive_value = returned_item['sensitive_entry']
        return set_property_data_type('S', sensitive_value)

    @property
    def sensitive_value(self):
        return self._sensitive_value

    def _create_pointer(self):
        """ generates opaque pointer

        Returns:

        """
        pointer_string = ''.join([self._property_name, self._source_internal_id])
        return hashlib.sha3_512(pointer_string.encode('utf-8')).hexdigest()

    def store(self):
        """Push a sensitive value to remote storage

        Args:

        Returns: None

        Raises:
            ClientError: the update operation could not take place

        """
        import boto3
        from botocore.exceptions import ClientError
        sensitive_table_name = os.environ['SENSITIVE_TABLE']
        resource = boto3.resource('dynamodb')
        table = resource.Table(sensitive_table_name)
        pointer = self._create_pointer()
        try:
            table.update_item(
                Key={'insensitive': pointer},
                UpdateExpression='SET sensitive_entry = if_not_exists(sensitive_entry, :s)',
                ExpressionAttributeValues={':s': self._sensitive_value},
                ReturnValues='NONE'
            )
            return pointer
        except ClientError as e:
            logging.error(f'failed to update a sensitive data entry: {e}')
            raise e

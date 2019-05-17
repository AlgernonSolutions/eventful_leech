import pytest

from toll_booth.obj.data_objects import IdentifierStem
from toll_booth.obj.data_objects.stored_data import S3StoredData


@pytest.mark.stored_s3
class TestStoredS3Data:
    @pytest.mark.usefixtures('dev_s3_stored_data')
    def test_get_retrieve(self):
        test_object = IdentifierStem('vertex', 'MockVertex', {'id_source': 'Algernon'})
        stored_data = S3StoredData.store(
            test_object,
            data_type='IdentifierStem',
            bucket_name='algernonsolutions-gentlemen-dev',
            object_key='test/identifier-stem')
        retrieved_object = stored_data.retrieve()
        assert retrieved_object == test_object

import os

import pytest

from toll_booth.obj.regulators import ObjectRegulator


@pytest.mark.object_regulator
@pytest.mark.usefixtures('dev_s3_stored_data')
class TestObjectRegulator:
    def test_object_regulator(self, object_regulator_event):
        os.environ['ENCOUNTER_BUCKET'] = 'algernonsolutions-gentlemen-dev'
        event, schema_entry = object_regulator_event
        regulator = ObjectRegulator(schema_entry)
        potential_vertex = regulator.create_potential_vertex_data(event['source'])
        assert potential_vertex

import pytest

from toll_booth import format_fire_hosed_extractions


class TestFireHoseExtractionHandler:
    @pytest.mark.fire_hose_extraction_handler
    def test_fire_hose_extraction_handler(self, fire_hose_event, mock_context):
        results = format_fire_hosed_extractions(fire_hose_event, mock_context)
        assert results

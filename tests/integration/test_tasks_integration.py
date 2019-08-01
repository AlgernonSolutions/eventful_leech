import pytest

from toll_booth.tasks import leech


@pytest.mark.tasks_integration
@pytest.mark.usefixtures('integration_environment')
class TestTasks:
    @pytest.mark.aio
    def test_aio(self, aio_event, mock_context):
        results = leech(aio_event, mock_context)
        assert results

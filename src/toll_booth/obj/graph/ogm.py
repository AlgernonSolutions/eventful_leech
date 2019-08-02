from toll_booth.obj.graph.generators import create_vertex_command_from_scalar, create_edge_command_from_scalar
from toll_booth.obj.graph.trident_driver import TridentDriver
from toll_booth.obj.data_objects.graph_objects import VertexData, EdgeData


class Ogm:
    def __init__(self, trident_driver=None):
        if not trident_driver:
            trident_driver = TridentDriver()
        self._trident_driver = trident_driver

    def graph_vertex(self, vertex_scalar: VertexData):
        command = create_vertex_command_from_scalar(vertex_scalar)
        try:
            self._trident_driver.execute(command)
            return {
                'status': 'succeeded',
                'operation': 'graph_vertex',
                'details': {
                    'message': '',
                    'command': command
                }
            }
        except Exception as e:
            return {
                'status': 'failed',
                'operation': 'graph_vertex',
                'details': {
                    'message': e.args,
                    'command': command
                }
            }

    def graph_edge(self, edge_scalar: EdgeData):
        command = create_edge_command_from_scalar(edge_scalar)
        try:
            self._trident_driver.execute(command)
            return {
                'status': 'succeeded',
                'operation': 'graph_edge',
                'details': {
                    'message': '',
                    'command': command
                }
            }
        except Exception as e:
            return {
                'status': 'failed',
                'operation': 'graph_edge',
                'details': {
                    'message': e.args,
                    'command': command
                }
            }

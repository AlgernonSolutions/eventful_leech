import logging

from aws_xray_sdk.core import xray_recorder

from toll_booth.obj.graph.ogm import Ogm


@xray_recorder.capture()
def push_graph(leech, **kwargs):
    logging.info(f'received a call to the graph_handler: {leech}, {kwargs}')
    graph_results = {}
    ogm = Ogm()
    logging.info(f'created ogm: {ogm}')
    edge = leech.get('edge')
    other_vertex = leech.get('other_vertex')
    source_vertex = leech['source_vertex']
    graph_results['source_vertex'] = ogm.graph_vertex(source_vertex)
    if other_vertex:
        graph_results['other_vertex'] = ogm.graph_vertex(other_vertex)
    if edge:
        graph_results['edge'] = ogm.graph_edge(edge)
    return graph_results

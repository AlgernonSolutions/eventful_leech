import logging

from toll_booth.obj.graph.ogm import Ogm


def graph_handler(source_vertex, **kwargs):
    logging.info(f'received a call to the graph_handler: {source_vertex}, {kwargs}')
    graph_results = {}
    ogm = Ogm()
    logging.info(f'created ogm: {ogm}')
    edge = kwargs.get('edge')
    other_vertex = kwargs.get('other_vertex')
    graph_results['source_vertex'] = ogm.graph_vertex(source_vertex)
    if other_vertex:
        graph_results['other_vertex'] = ogm.graph_vertex(other_vertex)
    if edge:
        graph_results['edge'] = ogm.graph_edge(edge)
    return graph_results

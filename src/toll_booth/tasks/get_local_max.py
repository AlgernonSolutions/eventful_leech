import os

from toll_booth.obj.index.elastic_driver import ElasticDriver


def get_local_max(id_source, object_type):
    elastic_host = os.environ['ELASTIC_HOST']
    driver = ElasticDriver.generate(elastic_host)
    max_value = driver.get_max_id_value(id_source, object_type)
    return max_value

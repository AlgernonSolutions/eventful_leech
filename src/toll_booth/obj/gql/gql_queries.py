SEARCH_FOR_EXISTING_VERTEXES = '''
    query find_vertexes($object_type: String!, $object_properties: [InputLocalProperty]!, $token: ID) {
        find_vertexes(object_type: $object_type, object_properties: $object_properties, token: $token){
            vertexes{
                internal_id
                id_value{
                    property_name
                    __typename
                    property_value{
                        __typename
                        ... on LocalPropertyValue{
                            data_type
                            property_value
                        }
                        ... on SensitivePropertyValue{
                            sensitive_data_type: data_type
                            pointer
                        }
                        ... on StoredPropertyValue{
                            storage_class
                            stored_data_type: data_type
                            storage_uri
                        }
                    }
                }
                identifier_stem{
                    property_name
                    __typename
                    property_value{
                        __typename
                        ... on LocalPropertyValue{
                            data_type
                            property_value
                        }
                        ... on SensitivePropertyValue{
                            sensitive_data_type: data_type
                            pointer
                        }
                        ... on StoredPropertyValue{
                            storage_class
                            stored_data_type: data_type
                            storage_uri
                        }
                    }
                }
                vertex_type
                vertex_properties{
                    property_name
                    __typename
                    property_value{
                        __typename
                        ... on LocalPropertyValue{
                            data_type
                            property_value
                        }
                        ... on SensitivePropertyValue{
                            sensitive_data_type: data_type
                            pointer
                        }
                        ... on StoredPropertyValue{
                            storage_class
                            stored_data_type: data_type
                            storage_uri
                        }
                    }
                }
            }
            token
        }
    }
'''

LIST_EXISTING_VERTEXES = """
query list_vertexes($identifier_stem: String!, $object_type: String!, $object_properties: [InputLocalProperty]!, $token: ID) {
  list_vertexes(identifier_stem:$identifier_stem, object_type: $object_type, object_properties: $object_properties, token: $token){
    vertexes{
          internal_id
          id_value{
              property_name
              __typename
              property_value{
                  __typename
                  ... on LocalPropertyValue{
                      data_type
                      property_value
                  }
                  ... on SensitivePropertyValue{
                      sensitive_data_type: data_type
                      pointer
                  }
                  ... on StoredPropertyValue{
                      storage_class
                      stored_data_type: data_type
                      storage_uri
                  }
              }
          }
          identifier_stem{
              property_name
              __typename
              property_value{
                  __typename
                  ... on LocalPropertyValue{
                      data_type
                      property_value
                  }
                  ... on SensitivePropertyValue{
                      sensitive_data_type: data_type
                      pointer
                  }
                  ... on StoredPropertyValue{
                      storage_class
                      stored_data_type: data_type
                      storage_uri
                  }
              }
          }
          vertex_type
          vertex_properties{
              property_name
              __typename
              property_value{
                  __typename
                  ... on LocalPropertyValue{
                      data_type
                      property_value
                  }
                  ... on SensitivePropertyValue{
                      sensitive_data_type: data_type
                      pointer
                  }
                  ... on StoredPropertyValue{
                      storage_class
                      stored_data_type: data_type
                      storage_uri
                  }
              }
          }
        }
    		token
      }
  }
"""

GRAPH_VERTEX = '''
    mutation graphVertex($input_vertex: InputVertex!) {
        addVertex(vertex: $input_vertex)
    }
'''
GRAPH_CLUSTER = '''
    mutation graphCluster($source_vertex: InputVertex!, $target_vertex: InputVertex!, $potential_edge: InputEdge!){
        add_source: addVertex(vertex: $source_vertex)
        add_other: addVertex(vertex: $target_vertex)
        add_edge: addEdge(edge: $potential_edge)
    }
'''

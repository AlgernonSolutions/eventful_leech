SEARCH_FOR_EXISTING_VERTEXES = '''
            query find_vertexes($object_type: String!, $object_properties: [InputLocalProperty]!) {
                find_vertexes(object_type: $object_type, object_properties: $object_properties){
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
            }
        '''
GRAPH_VERTEX = '''
    mutation graphVertex($input_vertex: InputVertex!) {
        addVertex(vertex: $input_vertex)
    }
'''
GRAPH_CLUSTER = '''
    mutation graphCluster($source_vertex: InputVertex!, $target_vertex: InputVertex!, #potential_edge: InputEdge!){
        addVertex(vertex: $source_vertex)
        addVertex(vertex: $target_vertex)
        addEdge(edge: $potential_edge)
    }
'''
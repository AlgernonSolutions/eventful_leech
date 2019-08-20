import json
from datetime import datetime

import dateutil


def _derive_object_properties(object_properties) -> str:
    property_commands = []
    for entry in object_properties:
        property_commands.append(_derive_property_value(entry))
    return f".{'.'.join(property_commands)}"


def _derive_property_value(object_property) -> str:
    property_name = object_property['property_name']
    stored_property_value = _derive_property_map(object_property)
    return f"property('{property_name}', {stored_property_value})"


def _derive_property_map(object_property) -> str:
    if 'pointer' in object_property:
        pointer = object_property['pointer']
        return f"'#SENSITIVE#{pointer}'"
    if 'storage_uri' in object_property:
        storage_class = object_property['storage_class']
        storage_uri = object_property['storage_uri']
        return f"'#STORED@{storage_class}#{storage_uri}'"
    return _derive_local_property_value(object_property)


def _derive_sensitive_property_map(object_property) -> str:
    property_value = f"'#SENSITIVE#{object_property.property_value}'"
    return property_value


def _derive_stored_property_map(object_property) -> str:
    property_value = f"'#STORED#{object_property.property_value}'"
    return property_value


def _derive_local_property_value(object_property) -> str:
    property_value = object_property['property_value']
    property_data_type = object_property['data_type']
    if property_data_type == 'S':
        property_value = json.dumps(property_value)
    if property_data_type == 'DT':
        try:
            datetime_value = dateutil.parser.parse(property_value)
        except ValueError:
            datetime_value = datetime.fromisoformat(property_value)
        iso_format = datetime_value.isoformat(sep='T')
        property_value = f"datetime('{iso_format}')"
    return property_value


def create_edge_command(internal_id: str,
                        edge_label: str,
                        id_value,
                        identifier,
                        source_vertex_internal_id: str,
                        target_vertex_internal_id: str,
                        edge_properties=None) -> str:
    import re
    collected_properties = []
    for property_type, type_properties in edge_properties.items():
        collected_properties.extend(type_properties)
    collected_properties.append(id_value)
    collected_properties.append(identifier)
    command = f"g" \
        f".E('{internal_id}')" \
        f".fold()" \
        f".coalesce(unfold()," \
        f" addE('{edge_label}').from(g.V('{source_vertex_internal_id}')).to(g.V('{target_vertex_internal_id}'))" \
        f".property(id, '{internal_id}')" \
        f"{_derive_object_properties(collected_properties)})"
    command = re.sub(r'\s+', ' ', command)
    return command


def create_vertex_command(internal_id: str,
                          vertex_type: str,
                          id_value,
                          identifier,
                          vertex_properties) -> str:
    import re
    collected_properties = []
    for property_type, type_properties in vertex_properties.items():
        collected_properties.extend(type_properties)
    collected_properties.append(id_value)
    collected_properties.append(identifier)
    command = f"g" \
        f".V('{internal_id}')" \
        f".fold()" \
        f".coalesce(unfold()," \
        f" addV('{vertex_type}')" \
        f".property(id, '{internal_id}')" \
        f"{_derive_object_properties(collected_properties)})"
    command = re.sub(r'\s+', ' ', command)
    return command


def create_vertex_command_from_scalar(vertex_data):
    return create_vertex_command(**vertex_data)


def create_edge_command_from_scalar(edge_data):
    return create_edge_command(**edge_data)

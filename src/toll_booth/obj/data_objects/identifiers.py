from algernon import AlgObject


class InternalId:
    def __init__(self, internal_id):
        self._internal_id = internal_id

    @property
    def id_value(self):
        import hashlib

        return hashlib.md5(self._internal_id.encode('utf-8')).hexdigest()

    def __str__(self):
        return self.id_value


class IdentifierStem(AlgObject):
    def __init__(self, graph_type, object_type, identifiers=None):
        if not identifiers:
            identifiers = []
        self._graph_type = graph_type
        self._object_type = object_type
        self._identifiers = identifiers

    @classmethod
    def from_raw(cls, identifier_stem):
        if isinstance(identifier_stem, IdentifierStem):
            return identifier_stem
        pieces = identifier_stem.split('#')
        graph_type = pieces[1]
        object_type = pieces[2]
        identifiers = []
        if len(pieces) > 2:
            identifiers = pieces[3:]
        return cls(graph_type, object_type, identifiers)

    @classmethod
    def for_stub(cls, stub_vertex):
        identifier_stem = stub_vertex.identifier
        try:
            identifier_stem = IdentifierStem.from_raw(identifier_stem)
            return identifier_stem
        except AttributeError:
            pass
        object_type = getattr(stub_vertex, 'object_type', 'UNKNOWN')
        paired_identifiers = {}
        for property_field in identifier_stem:
            property_value = stub_vertex.object_properties.get(property_field, None)
            if hasattr(property_value, 'is_missing'):
                property_value = None
            paired_identifiers[property_field] = property_value
        if not stub_vertex.is_properties_complete:
            object_type = object_type + '::stub'
        return cls('vertex', object_type, paired_identifiers)

    @classmethod
    def parse_json(cls, json_dict):
        return cls(
            json_dict['graph_type'], json_dict['object_type'],
            json_dict.get('paired_identifiers')
        )

    @property
    def object_type(self):
        return self._object_type

    @property
    def is_edge(self):
        return self._graph_type == 'edge'

    def __str__(self):
        if not self._identifiers:
            return f'#{self._graph_type}#{self._object_type}#'
        return f'''#{self._graph_type}#{self._object_type}#{"#".join(self._identifiers)}#'''


class MissingObjectProperty(AlgObject):
    @classmethod
    def is_missing(cls):
        return True

    @classmethod
    def parse_json(cls, json_dict):
        return cls()

class EmptyIndexException(Exception):
    def __init__(self, index_name):
        self._index_name = index_name

    @property
    def index_name(self):
        return self._index_name


class UniqueIndexViolationException(Exception):
    def __init__(self, index_name, indexed_object):
        self._index_name = index_name
        self._indexed_object = indexed_object

    @property
    def index_name(self):
        return self._index_name

    @property
    def indexed_object(self):
        return self._indexed_object


class MissingIndexException(Exception):
    def __init__(self, index_name):
        self._index_name = index_name


class MissingIndexedPropertyException(Exception):
    def __init__(self, index_name, indexed_fields, missing_fields):
        self._index_name = index_name
        self._indexed_fields = indexed_fields
        self._missing_fields = missing_fields


class AttemptedStubIndexException(Exception):
    def __init__(self, index_name, stub_object):
        self._index_name = index_name
        self._stub_object = stub_object

from typing import Dict, List

from algernon import AlgObject


class SnapshotHeader(AlgObject):
    def __init__(self, snapshot_type: str, capture_timestamp: float, snapshot_parameters: Dict = None):
        if not snapshot_parameters:
            snapshot_parameters = {}
        self._snapshot_type = snapshot_type
        self._capture_timestamp = capture_timestamp
        self._snapshot_parameters = snapshot_parameters

    @classmethod
    def parse_json(cls, json_dict):
        return cls(json_dict['snapshot_type'], json_dict['capture_timestamp'], json_dict.get('snapshot_parameters'))

    @property
    def snapshot_type(self):
        return self._snapshot_type

    @property
    def capture_timestamp(self):
        return self._capture_timestamp

    @property
    def snapshot_parameters(self):
        return self._snapshot_parameters


class Snapshot(AlgObject):
    def __init__(self, snapshot_header: SnapshotHeader, snapshot_items: List = None):
        if not snapshot_items:
            snapshot_items = []
        self._snapshot_header = snapshot_header
        self._snapshot_items = snapshot_items

    @classmethod
    def parse_json(cls, json_dict):
        return cls(json_dict['snapshot_header'], json_dict['snapshot_items'])

    @property
    def snapshot_header(self):
        return self._snapshot_header

    @property
    def snapshot_items(self):
        return self._snapshot_items

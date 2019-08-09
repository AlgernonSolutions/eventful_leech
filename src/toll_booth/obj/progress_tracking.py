from datetime import datetime

import boto3


class Overseer:
    def __init__(self, table_name, identifier, id_value):
        self._table_name = table_name
        self._identifier = identifier
        self._id_value = id_value

    @property
    def progress_key(self):
        return {
            'identifier': self._identifier,
            'id_value': int(self._id_value)
        }

    def mark_stage_completed(self, stage_name, stage_results=None):
        if not stage_results:
            stage_results = {}
        dynamo = boto3.resource('dynamodb')
        table = dynamo.Table(self._table_name)
        update_entry = {
            'completed_at': datetime.now().isoformat(),
            'stage_results': stage_results
        }
        table.update_item(
            Key=self.progress_key,
            UpdateExpression='SET #sn=:ue',
            ExpressionAttributeNames={
                '#sn': stage_name
            },
            ExpressionAttributeValues={
                ':ue': update_entry
            }
        )


class MigrationStep:
    def __init__(self, step_name, completed_at, **kwargs):
        self._step_name = step_name
        self._completed_at = completed_at
        self._stage_results = kwargs.get('stage_results', [])

    @property
    def step_name(self):
        return self._step_name

    @property
    def completed_at(self):
        try:
            return datetime.fromisoformat(self._completed_at)
        except ValueError:
            trimmed = self._completed_at[:-1]
            return datetime.fromisoformat(trimmed)

    @property
    def stage_results(self):
        return self._stage_results

    def __str__(self):
        return self._step_name


class MigrationProgress:
    def __init__(self, identifier, id_value, steps):
        self._identifier = identifier
        self._id_value = id_value
        self._steps = steps

    @classmethod
    def from_dynamo_entry(cls, dynamo_entry):
        disregard = ['identifier', 'id_value', 'started', 'migration_status']
        steps = [MigrationStep(x, **y) for x, y in dynamo_entry.items() if x not in disregard]
        return cls(dynamo_entry['identifier'], dynamo_entry['id_value'], steps)

    @property
    def identifier(self):
        return self._identifier

    @property
    def id_value(self):
        return self._id_value

    @property
    def steps(self):
        return self._steps

    @property
    def most_recent_step(self):
        ordered_steps = sorted(self._steps, key=lambda x: x.completed_at, reverse=True)
        for ordered_step in ordered_steps:
            return ordered_step

    @property
    def last_activity_time(self):
        return self.most_recent_step.completed_at

    def has_completed_step(self, step_name):
        return step_name in [str(x) for x in self._steps]

    def __str__(self):
        return f'{self._identifier}#{self._id_value}'

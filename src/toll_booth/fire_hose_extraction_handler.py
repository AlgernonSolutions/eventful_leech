import base64

import rapidjson


def _format_record(object_type, record_payload):
    if object_type == 'Encounter':
        return _format_encounter_record(record_payload)
    raise RuntimeError(f'do not know how to manage {record_payload} for object_type: {object_type}')


def _format_encounter_record(record_payload):
    extracted_data = record_payload.get('extracted_data', {})
    source_data = extracted_data.get('source', {})
    patient_data = extracted_data.get('patient_data', [{}])
    standard_record = {
        'object_type': record_payload.get('object_type'),
        'identifier': record_payload.get('identifier'),
        'id_value': record_payload.get('id_value'),
        'extracted_data': {
            'source': {
                'id_source': source_data.get('id_source'),
                'encounter_id': source_data.get('encounter_id'),
                'provider_id': source_data.get('provider_id'),
                'patient_id': source_data.get('patient_id'),
                'encounter_type': source_data.get('encounter_type'),
                'encounter_datetime_in': source_data.get('encounter_datetime_in'),
                'encounter_datetime_out': source_data.get('encounter_datetime_out'),
                'documentation': source_data.get('documentation')
            },
            'patient_data': [
                {
                    'last_name': x.get('last_name'),
                    'first_name': x.get('first_name'),
                    'dob': x.get('dob')
                } for x in patient_data
            ]
        }
    }
    return rapidjson.dumps(standard_record)


def format_fire_hosed_extractions(event, context):
    output = []

    for record in event['records']:
        record_id = record['recordId']
        original_payload = base64.b64decode(record['data'])
        try:
            record_payload = rapidjson.loads(original_payload)
            object_type = record_payload['object_type']
            payload = _format_record(object_type, record_payload)
            payload = f'{payload}\n'

            output_record = {
                'recordId': record_id,
                'result': 'Ok',
                'data': base64.b64encode(payload.encode())
            }
        except (rapidjson.JSONDecodeError, KeyError, RuntimeError):
            output_record = {
                'recordId': record_id,
                'result': 'ProcessingFailed',
                'data': base64.b64encode(original_payload)
            }
        output.append(output_record)
    return {'records': output}

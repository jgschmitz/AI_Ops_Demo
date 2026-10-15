"""STEP 2: Introduce a reproducible failure with a MongoDB update pipeline.
App equivalent: inject(). Only synthetic batches in the selected run are updated.
"""
from common import arguments, command, database, incident, now, record
from fixtures import IMPACTED


def inject(db, run):
    incident(db, run, ['Healthy', 'Investigating'])
    result = db.telemetry.update_many(
        {'run_id': run, 'minute': {'$gte': 45, '$lt': 60}, 'program_id': {'$in': IMPACTED}},
        [{'$set': {
            'failed': {'$toInt': {'$multiply': ['$attempted', 0.72]}},
            'backlog': {'$multiply': [{'$subtract': ['$minute', 44]}, 210]},
            'latency_ms': 2400, 'deployment': 'REL-241', 'error_code': 'MISSING_RECIPIENT',
            'message': 'Splunk: ValueError Missing contact.emailAddress; Adobe delivery rejected'}}])
    if result.matched_count != 90:
        raise ValueError('Expected 90 fixture batches. Complete step 01 before continuing.')
    db.incidents.update_one({'_id': run}, {'$set': {
        'state': 'Investigating', 'release': 'REL-241'}})
    db.incidents.update_one({'_id': run, 'detected_at': {'$exists': False}},
                            {'$set': {'detected_at': now()}})
    record(db, run, 'Detect', f'Injected shared release failure in {result.matched_count} batches')
    print(f'{result.matched_count} matching batches / six programs. State: Investigating.')


@command
def main():
    args = arguments(__doc__).parse_args()
    inject(database(), args.run)


if __name__ == '__main__':
    main()

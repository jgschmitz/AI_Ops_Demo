"""STEP 3: Correlate errors in Atlas and attach inspectable code/payload evidence.
App equivalent: the evidence-building portion of investigate(). Extension:
uses a server-side aggregation instead of loading every batch into Python.
"""
import difflib
from common import arguments, command, database, incident, now, record, show
from fixtures import BEFORE, AFTER, SAMPLE


def correlation_pipeline(run):
    return [
        {'$match': {'run_id': run, 'failed': {'$gt': 0}}},
        {'$group': {'_id': {'release': '$deployment', 'error': '$error_code'},
                    'programs': {'$addToSet': '$program'},
                    'failed_messages': {'$sum': '$failed'},
                    'batches': {'$sum': 1}, 'first_seen': {'$min': '$timestamp'}}},
        {'$sort': {'failed_messages': -1}},
    ]


def correlate(db, run):
    incident(db, run, ['Investigating'])
    pipeline = correlation_pipeline(run)
    print('Pipeline executed by Atlas:')
    show(pipeline)
    groups = list(db.telemetry.aggregate(pipeline))
    if not groups:
        raise ValueError('No failed batches. Run step 02 first.')
    # This fixture has one shared defect. Do not silently merge unrelated errors.
    if len(groups) != 1:
        raise ValueError('Multiple error/release groups found. This example expects one injected defect.')
    group = groups[0]
    samples = list(db.telemetry.find({'run_id': run, 'failed': {'$gt': 0}}, {'_id': 0})
                   .sort([('minute', 1), ('program_id', 1)]).limit(6))
    evidence = dict(log_samples=samples, failed_messages=group['failed_messages'],
        affected_programs=sorted(group['programs']), release=group['_id']['release'],
        error_code=group['_id']['error'], correlation_groups=groups,
        code_diff=''.join(difflib.unified_diff(BEFORE.splitlines(True), AFTER.splitlines(True),
                        fromfile='adapter_v2.4.0.py', tofile='adapter_v2.4.1.py')),
        sample_payload=SAMPLE)
    db.incidents.update_one({'_id': run}, {'$set': {'evidence': evidence, 'correlated_at': now()}})
    record(db, run, 'Correlate', f"{len(group['programs'])} programs share one release/error; {group['failed_messages']} failed messages")
    show(evidence)
    return evidence


@command
def main():
    args = arguments(__doc__).parse_args()
    correlate(database(), args.run)


if __name__ == '__main__':
    main()

"""STEP 1: Model operational batches as documents, create indexes, and seed Atlas.
App equivalent: fixture() + initialize(). Does not reset existing scenarios.
"""
from pymongo import UpdateOne
from common import arguments, command, database, now, record
from fixtures import fixture


def seed(db, run):
    # Same access pattern and unique key as the workbench.
    db.telemetry.create_index([('run_id', 1), ('minute', 1), ('program_id', 1)], unique=True)
    db.activity.create_index([('run_id', 1), ('timestamp', 1)])
    existing = db.incidents.find_one({'_id': run})
    if existing and existing.get('state') != 'Healthy':
        raise ValueError('This run has progressed. Choose a fresh --run ID; seeding will not reset its history.')
    db.incidents.update_one({'_id': run}, {'$setOnInsert': {
        'state': 'Healthy', 'created_at': now()}}, upsert=True)
    # Preserve the timestamp anchor and existing records on retries.
    anchor = db.incidents.find_one({'_id': run})['created_at']
    from datetime import timedelta
    docs = fixture()
    for doc in docs:
        doc.update(run_id=run, timestamp=anchor-timedelta(minutes=60-doc['minute']))
        doc['_id'] = f"{run}:{doc['minute']}:{doc['program_id']}"
    result = db.telemetry.bulk_write([UpdateOne({'_id': d['_id']}, {'$setOnInsert': d}, upsert=True)
                                      for d in docs])
    record(db, run, 'Monitor', f'Seed requested: {len(docs)} batches; {result.upserted_count} inserted')
    print(f'{run}: {result.upserted_count} new batches; 24 programs, 8 LOBs, 60 minutes. Existing batches preserved.')


@command
def main():
    args = arguments(__doc__).parse_args()
    seed(database(), args.run)


if __name__ == '__main__':
    main()

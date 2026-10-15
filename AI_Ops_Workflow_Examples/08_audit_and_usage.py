"""STEP 8: Read the persisted timeline and aggregate provider usage in Atlas.
App equivalent: Agent activity. Extension: server-side current health aggregation.
"""
from common import arguments, command, database, incident, show


def usage_pipeline(run):
    return [
        {'$match': {'run_id': run, 'provider': {'$ne': 'workflow'}}},
        {'$group': {'_id': {'provider': '$provider', 'model': '$model'},
            'tokens': {'$sum': '$tokens'}, 'recorded_calls': {'$sum': 1}}},
        {'$sort': {'_id.provider': 1, '_id.model': 1}},
    ]


def audit(db, run):
    doc = incident(db, run)
    print('Incident state:', doc['state'])
    latest = db.telemetry.find_one({'run_id': run}, sort=[('minute', -1)])
    if latest:
        health = list(db.telemetry.aggregate([
            {'$match': {'run_id': run, 'minute': latest['minute']}},
            {'$group': {'_id': None, 'attempted': {'$sum': '$attempted'},
                'failed': {'$sum': '$failed'}, 'backlog': {'$sum': '$backlog'}}},
        ]))[0]
        health['delivery_success_percent'] = round(100*(1-health['failed']/health['attempted']), 2)
        print('Latest batch health (Atlas aggregation):')
        show(health)
    print('Timeline:')
    show(list(db.activity.find({'run_id': run}, {'_id': 0}).sort('timestamp', 1)))
    print('Usage aggregation pipeline:')
    show(usage_pipeline(run))
    show(list(db.activity.aggregate(usage_pipeline(run))))
    print('Tokens are provider-reported totals when available. No prices, budget limits or hidden API retries are counted here.')


@command
def main():
    args = arguments(__doc__).parse_args()
    audit(database(), args.run)


if __name__ == '__main__':
    main()

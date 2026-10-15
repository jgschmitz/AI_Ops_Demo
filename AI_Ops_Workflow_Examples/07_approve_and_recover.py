"""STEP 7: Explicit approval, a real fixture canary, and a simulated recovery.
App equivalent: recover(). No live deploy, Adobe replay or model-generated code.
Run without --approve to inspect the plan; --approve performs synthetic writes.
"""
from datetime import timedelta
from pymongo import UpdateOne
from common import arguments, command, database, incident, now, record, show
from fixtures import BEFORE, AFTER, SAMPLE, PROGRAMS


def canary():
    # Only execute the two bundled, trusted fixture functions.
    old, new = {}, {}
    exec(BEFORE, {'__builtins__': {'ValueError': ValueError}}, old)
    exec(AFTER, {'__builtins__': {'ValueError': ValueError}}, new)
    try:
        new['build_delivery'](SAMPLE)
    except ValueError:
        pass
    else:
        raise ValueError('New adapter unexpectedly passed; fixture no longer reproduces the defect.')
    result = old['build_delivery'](SAMPLE)
    if result['recipient'] != SAMPLE['contact']['email']:
        raise ValueError('Previous adapter canary failed; recovery stopped.')
    return result


def recover(db, run, approve=False, operator='demo-operator'):
    doc = incident(db, run, ['Awaiting approval', 'Recovered'])
    if doc['state'] == 'Recovered':
        print('Already recovered. No additional replay or recovery batch written.')
        return
    if not doc.get('analysis'):
        raise ValueError('Run step 06 first.')
    print('Plan: validate previous adapter; append healthy minute-60 batches; mark synthetic replay complete.')
    if not approve:
        print('Preview only. Rerun with --approve --operator YOUR_NAME to approve this simulation.')
        return
    if not operator.strip():
        raise ValueError('Provide a nonempty --operator label.')
    show({'canary': canary(), 'simulation': True})
    original = list(db.telemetry.find({'run_id': run, 'minute': {'$lt': 60}}))
    if len(original) != 1440:
        raise ValueError('Expected 1,440 original batches. Recovery stopped.')
    total = sum(row['failed'] for row in original)
    end = max(row['timestamp'] for row in original)
    healthy = [dict(_id=f"{run}:60:{p['id']}", run_id=run, minute=60,
        timestamp=end+timedelta(minutes=1), program_id=p['id'], program=p['program'], lob=p['lob'],
        attempted=250, failed=0, backlog=0, latency_ms=92, source='Recovery simulator',
        deployment='REL-240', error_code='', message='Synthetic canary and replay completed') for p in PROGRAMS]
    # Stable batch IDs make a retry after partial execution safe for this sequential demo.
    db.telemetry.bulk_write([UpdateOne({'_id': row['_id']}, {'$setOnInsert': row}, upsert=True)
                             for row in healthy])
    record(db, run, 'Recover', f'Approval label={operator}; fixture canary passed; simulated replay count={total}. Original errors retained.')
    db.incidents.update_one({'_id': run}, {'$set': {'state': 'Recovered',
        'approved_at': now(), 'approved_by': operator, 'replayed_simulated': total}})
    print(f'Recovered (simulated): {total:,} messages marked replayed; 24 healthy batches added.')
    print('The operator label is demo metadata, not an authenticated identity.')


@command
def main():
    parser = arguments(__doc__)
    parser.add_argument('--approve', action='store_true')
    parser.add_argument('--operator', default='demo-operator')
    args = parser.parse_args()
    recover(database(), args.run, args.approve, args.operator)


if __name__ == '__main__':
    main()

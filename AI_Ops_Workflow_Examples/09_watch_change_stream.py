"""BONUS: Observe incident state changes without polling. Not in the current app.
Start this BEFORE steps 01-07 in another terminal. Filtered to one run ID.
This is an observer, not a correlation worker or durable event-processing system.
"""
import time
from common import arguments, command, database, show


@command
def main():
    parser = arguments(__doc__)
    parser.add_argument('--seconds', type=int, default=120, help='Stop after this many seconds.')
    args = parser.parse_args()
    if args.seconds < 1:
        raise ValueError('--seconds must be positive.')
    db = database()
    # Create the collection if needed so it can be watched before the scenario exists.
    if 'incidents' not in db.list_collection_names():
        db.create_collection('incidents')
    pipeline = [{'$match': {'operationType': {'$in': ['insert', 'update', 'replace']},
                            'documentKey._id': args.run}}]
    print(f'Watching incidents for {args.run}. Run the workflow in a second terminal.', flush=True)
    deadline = time.monotonic()+args.seconds
    with db.incidents.watch(pipeline, full_document='updateLookup', max_await_time_ms=1000) as stream:
        while time.monotonic() < deadline:
            event = stream.try_next()
            if event is not None:
                show({'operation': event['operationType'], 'run_id': event['documentKey']['_id'],
                      'changed_fields': event.get('updateDescription', {}).get('updatedFields', {}),
                      'current_state': (event.get('fullDocument') or {}).get('state')})
    print('Watch complete. This example does not persist resume tokens or replay past events.')


if __name__ == '__main__':
    main()

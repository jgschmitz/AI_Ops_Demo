"""Small connection, CLI and provider helpers. Workflow logic lives in the scripts."""
import argparse
import json
from functools import wraps
from datetime import datetime, timezone

import requests
from pymongo import MongoClient
import config


def now():
    return datetime.now(timezone.utc)


def arguments(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--run', default='examples-demo-001', help='Explicit scenario ID; use the same ID for every step.')
    return parser


def database():
    if not config.ATLAS_URI:
        raise ValueError('Fill ATLAS_URI in config.py first.')
    client = MongoClient(config.ATLAS_URI, serverSelectionTimeoutMS=8000,
                         socketTimeoutMS=60000, tz_aware=True)
    client.admin.command('ping')
    return client[config.DATABASE]


def incident(db, run, states=None):
    doc = db.incidents.find_one({'_id': run})
    if not doc:
        raise ValueError('Scenario not found. Run 01_seed_telemetry.py with this --run ID.')
    if states and doc.get('state') not in states:
        raise ValueError(f"State is {doc.get('state')}; expected one of {states}. Use a new --run to restart.")
    return doc


def record(db, run, stage, detail, tokens=0, provider='workflow', model=''):
    db.activity.insert_one(dict(run_id=run, timestamp=now(), stage=stage, detail=detail,
                                tokens=int(tokens or 0), provider=provider, model=model))


def show(value):
    print(json.dumps(value, default=str, indent=2))


def voyage(endpoint, payload):
    if not config.VOYAGE_API_KEY:
        raise ValueError('Fill VOYAGE_API_KEY in config.py first.')
    response = requests.post('https://api.voyageai.com/v1/' + endpoint,
        headers={'Authorization': 'Bearer ' + config.VOYAGE_API_KEY}, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def embed(db, run, texts, kind):
    payload = voyage('embeddings', {'model': config.VOYAGE_MODEL, 'input': texts,
        'input_type': kind, 'output_dimension': config.DIMENSIONS})
    items = sorted(payload['data'], key=lambda item: item['index'])
    if [item['index'] for item in items] != list(range(len(texts))):
        raise ValueError('Embedding response indices do not match the requested inputs.')
    vectors = [item['embedding'] for item in items]
    if any(len(vector) != config.DIMENSIONS for vector in vectors):
        raise ValueError('Embedding dimensions do not match config.py.')
    record(db, run, 'Embed', f'Embedded {len(texts)} {kind} inputs',
           payload.get('usage', {}).get('total_tokens', 0), 'Voyage', config.VOYAGE_MODEL)
    return vectors


def signature():
    return f'{config.VOYAGE_MODEL}:{config.DIMENSIONS}'


def command(fn):
    """Keep credential-bearing connection exceptions out of customer-facing output."""
    @wraps(fn)
    def wrapped():
        try:
            fn()
        except KeyboardInterrupt:
            print('\nStopped.')
        except ValueError as error:
            raise SystemExit(str(error)) from None
        except requests.HTTPError as error:
            raise SystemExit(f'Provider HTTP {error.response.status_code}. Check key, model access and quota.') from None
        except Exception as error:
            raise SystemExit(f'{type(error).__name__}: step failed. Check network, credentials, permissions and prerequisite steps. No credentials printed.') from None
    return wrapped

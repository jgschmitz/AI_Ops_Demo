"""STEP 4: Embed the shared knowledge corpus and create a vector index once.
App equivalent: build_knowledge() + index_status(). --status makes no API calls.
"""
from pymongo import ReplaceOne
from pymongo.operations import SearchIndexModel
import config
from common import arguments, command, database, embed, incident, show, signature
from fixtures import KNOWLEDGE


def definition():
    return {'fields': [
        {'type': 'vector', 'path': 'embedding', 'numDimensions': config.DIMENSIONS, 'similarity': 'cosine'},
        {'type': 'filter', 'path': 'signature'},
    ]}


def status(db):
    found = list(db.knowledge.list_search_indexes(name=config.VECTOR_INDEX))
    if not found:
        return 'Not created'
    current = found[0]
    actual = current.get('latestDefinition', current.get('definition'))
    if actual and actual.get('fields') != definition()['fields']:
        raise ValueError('Existing index has different settings. Use a new VECTOR_INDEX name in config.py.')
    return 'Queryable' if current.get('queryable') else current.get('status', 'Building')


def prepare(db, run):
    incident(db, run)
    pending = [(key, title, text) for key, title, text in KNOWLEDGE
        if not db.knowledge.find_one({'_id': key, 'signature': signature(), 'title': title, 'text': text})]
    if pending:
        vectors = embed(db, run, [title+'\n'+text for _, title, text in pending], 'document')
        db.knowledge.bulk_write([ReplaceOne({'_id': key}, dict(_id=key, title=title, text=text,
            embedding=vector, signature=signature()), upsert=True)
            for (key, title, text), vector in zip(pending, vectors)])
    print(f'Embedded {len(pending)} new/changed documents; unchanged documents reused.')
    current = status(db)
    if current == 'Not created':
        print('Creating index with definition:')
        show(definition())
        db.knowledge.create_search_index(SearchIndexModel(name=config.VECTOR_INDEX,
            type='vectorSearch', definition=definition()))
        current = 'Building'
    print(f'{config.VECTOR_INDEX}: {current}. Run this script with --status until Queryable.')


@command
def main():
    parser = arguments(__doc__)
    parser.add_argument('--status', action='store_true', help='Only inspect index status; no embedding calls.')
    args = parser.parse_args()
    db = database()
    if args.status:
        print(status(db))
    else:
        prepare(db, args.run)


if __name__ == '__main__':
    main()

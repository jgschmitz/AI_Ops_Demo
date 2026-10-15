"""STEP 5: Query embeddings -> Atlas Vector Search -> optional Voyage reranking.
App equivalent: retrieve(). Saves retrieved runbooks into the incident evidence.
"""
import importlib
import config
from common import arguments, command, database, embed, incident, now, record, show, signature, voyage


def retrieve(db, run, rerank=False):
    doc = incident(db, run, ['Investigating'])
    evidence = doc.get('evidence', {})
    if not evidence.get('code_diff'):
        raise ValueError('Run step 03 to assemble the incident evidence first.')
    if importlib.import_module('04_embed_and_index').status(db) != 'Queryable':
        raise ValueError('Run step 04, then check --status until Queryable.')
    query = f"{evidence['error_code']} contact.emailAddress validation failures after Adobe adapter {evidence['release']} deployment; reporting backlog"
    vector = embed(db, run, [query], 'query')[0]
    pipeline = [
        {'$vectorSearch': {'index': config.VECTOR_INDEX, 'path': 'embedding',
            'queryVector': vector, 'numCandidates': 80, 'limit': 5,
            'filter': {'signature': signature()}}},
        {'$project': {'title': 1, 'text': 1, 'score': {'$meta': 'vectorSearchScore'}}},
    ]
    print(f'Atlas $vectorSearch: {config.DIMENSIONS} dimensions, 80 candidates, top 5, signature filter.')
    hits = list(db.knowledge.aggregate(pipeline))
    if not hits:
        raise ValueError('No indexed knowledge found. Allow indexing to catch up and retry.')
    if rerank:
        result = voyage('rerank', {'model': config.RERANK_MODEL, 'query': query,
            'documents': [hit['text'] for hit in hits], 'top_k': min(3, len(hits))})
        hits = [dict(hits[item['index']], rerank_score=item['relevance_score']) for item in result['data']]
        record(db, run, 'Rerank', 'Reranked retrieved knowledge',
            result.get('usage', {}).get('total_tokens', 0), 'Voyage', config.RERANK_MODEL)
    db.incidents.update_one({'_id': run}, {'$set': {
        'evidence.runbooks': hits, 'retrieval_query': query, 'retrieved_at': now()}})
    record(db, run, 'Retrieve', 'Evidence: '+', '.join(hit['_id'] for hit in hits))
    show(hits)
    print('Retrieval relevance scores are not diagnosis confidence percentages.')
    return hits


@command
def main():
    parser = arguments(__doc__)
    parser.add_argument('--rerank', action='store_true', help='Make an additional Voyage reranking call.')
    args = parser.parse_args()
    retrieve(database(), args.run, args.rerank)


if __name__ == '__main__':
    main()

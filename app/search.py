from flask import current_app

def add_to_index(index, model):
    if not current_app.elasticsearch:
        return

    payload = {}
    for field in model.__searchable__:
        payload[field] = getattr(model, field)

    current_app.elasticsearch.index(
        index=index,
        id=model.id,
        document=payload
    )

def remove_from_index(index, model):
    if not current_app.elasticsearch:
        return

    current_app.elasticsearch.delete(
        index=index,
        id=model.id
    )


def before_commit(session):
    session.info['search_add'] = list(session.new)
    session.info['search_update'] = list(session.dirty)
    session.info['search_delete'] = list(session.deleted)


def after_commit(session):
    for obj in session.info.get('search_add', []):
        if hasattr(obj, '__searchable__'):
            add_to_index('posts', obj)

    for obj in session.info.get('search_update', []):
        if hasattr(obj, '__searchable__'):
            add_to_index('posts', obj)

    for obj in session.info.get('search_delete', []):
        if hasattr(obj, '__searchable__'):
            remove_from_index('posts', obj)

    session.info['search_add'] = []
    session.info['search_update'] = []
    session.info['search_delete'] = []


def after_rollback(session):
    session.info.pop('search_add', None)
    session.info.pop('search_update', None)
    session.info.pop('search_delete', None)


def query_index(index, query, page, per_page):
    if not current_app.elasticsearch:
        return [], 0

    search = current_app.elasticsearch.search(
        index=index,
        query={'multi_match': {'query': query, 'fields': ['*']}},
        from_=(page - 1) * per_page,
        size=per_page
    )

    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    return ids, search['hits']['total']['value']

class SearchableMixin:
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return [], 0
        import sqlalchemy as sa
        from app import db
        when = [(v, i) for i, v in enumerate(ids)]
        query = sa.select(cls).where(cls.id.in_(ids)).order_by(
            db.case(*when, value=cls.id))
        return db.session.scalars(query).all(), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        from app import db
        import sqlalchemy as sa
        for obj in db.session.scalars(sa.select(cls)):
            add_to_index(cls.__tablename__, obj)
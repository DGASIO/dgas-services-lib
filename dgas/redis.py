import aioredis
from dgas.config import config

_global_connection = None

def get_redis_connection():
    assert _global_connection is not None, "redis not prepared before use"
    return _global_connection

def set_redis_connection(connection):
    global _global_connection
    _global_connection = connection

async def prepare_redis(config=None):
    if config is None:
        return await _prepare_global_redis()
    else:
        db = config.get('db', None)
        return await aioredis.create_redis_pool(
            config['url'],
            password=config.get('password', None),
            db=int(db) if db else None)

async def _prepare_global_redis():
    global _global_connection
    if _global_connection is None:
        db = config['redis'].get('db', None)
        _global_connection = await aioredis.create_redis_pool(
            config['redis']['url'],
            password=config['redis'].get('password', None),
            db=int(db) if db else None)
    return _global_connection

class RedisMixin:

    @property
    def redis(self):
        return get_redis_connection()

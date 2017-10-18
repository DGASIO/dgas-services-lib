import asyncio
import testing.postgresql
import signal
from dgas.config import config
from dgas.database import prepare_database, set_database_pool
from dgas.log import log

POSTGRESQL_FACTORY = testing.postgresql.PostgresqlFactory(cache_initialized_db=True, auto_start=False)
    #postgres_args="-h 127.0.0.1 -F -c logging_collector=on -c log_directory=/tmp/log -c log_filename=postgresql-%Y-%m-%d_%H%M%S.log -c log_statement=all")

def requires_database(func=None):
    """Used to ensure all database connections are returned to the pool
    before finishing the test"""
    def wrap(fn):

        async def wrapper(self, *args, **kwargs):

            psql = POSTGRESQL_FACTORY()
            # this fixes a regression in the testing.commons library that causes
            # the setup method to be called multiple times when `cache_initialize_db`
            # is used without an init_handler
            psql.setup()
            psql.start()

            config['database'] = psql.dsn()
            config['database']['ssl'] = '0'
            set_database_pool(None)
            self.pool = await prepare_database()

            try:
                f = fn(self, *args, **kwargs)
                if asyncio.iscoroutine(f):
                    await f

                # wait for all the connections to be released
                if hasattr(self.pool, '_con_count'):
                    # pre 0.10.0
                    con_count = lambda: self.pool._con_count
                elif hasattr(self.pool, '_holders'):
                    # post 0.10.0
                    con_count = lambda: len(self.pool._holders)
                else:
                    raise Exception("Don't know how to get connection pool count")
                err_count = 0
                while con_count() != self.pool._queue.qsize():
                    # if there are connections still in use, there should be some
                    # other things awaiting to be run. this simply pass control back
                    # to the ioloop to continue execution, looping until all the
                    # connections are released.
                    err_count += 1
                    if err_count > 5:
                        log.warning("database connections still unreleased")
                    await asyncio.sleep(0.1)
            finally:
                await self.pool.close()
                set_database_pool(None)
                psql.stop(_signal=signal.SIGKILL)
                del config['database']

        return wrapper

    if func is not None:
        return wrap(func)
    else:
        return wrap

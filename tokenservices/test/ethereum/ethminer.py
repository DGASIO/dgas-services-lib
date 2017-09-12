import os
import signal
import subprocess

from testing.common.database import (
    Database, DatabaseFactory, get_path_of
)

class EthMiner(Database):

    DEFAULT_SETTINGS = dict(auto_start=2,
                            base_dir=None,
                            ethminer_cmd=None,
                            jsonrpc_url=None,
                            home=None,
                            copy_data_from=None,
                            debug=None)

    subdirectories = ['data', 'tmp']

    def initialize(self):
        self.ethminer = self.settings.get('ethminer_cmd')
        if self.ethminer is None:
            self.ethminer = get_path_of('ethminer')

        self.jsonrpc_url = self.settings.get('jsonrpc_url') or 'http://127.0.0.1:8545'
        self.home = self.settings.get('home') or os.path.expanduser("~")
        self.debug = self.settings.get('debug') or False

    def prestart(self):
        if not os.path.exists(os.path.join(self.home, '.ethash')):
            raise Exception("Missing {}. run `HOME={} {} -D 0` to initialise ethminer before tests can be run".format(
                os.path.join(self.home, '.ethash'), self.home, self.ethminer))

    def start(self):
        if self.child_process:
            return  # already started

        self.prestart()

        logger = open(os.path.join(self.base_dir, '%s.log' % self.name), 'wt')
        try:
            command = self.get_server_commandline()
            flags = 0
            if os.name == 'nt':
                flags |= subprocess.CREATE_NEW_PROCESS_GROUP
            custom_env = os.environ.copy()
            custom_env["HOME"] = self.home
            kwargs = {'env': custom_env, 'creationflags': flags}
            if not self.debug:
                kwargs.update({'stdout': logger, 'stderr': logger})
            self.child_process = subprocess.Popen(command, **kwargs)
        except Exception as exc:
            raise RuntimeError('failed to launch %s: %r' % (self.name, exc))
        else:
            try:
                self.wait_booting()
                self.poststart()
            except:
                self.stop()
                raise
        finally:
            logger.close()

    def pause(self):
        """stops ethminer, without calling the cleanup"""
        self.terminate(signal.SIGTERM)

    def get_server_commandline(self):
        return [self.ethminer,
                '-F', self.jsonrpc_url, '-t', '1', '--no-precompute']

    def is_server_available(self):
        return True

class EthMinerFactory(DatabaseFactory):
    target_class = EthMiner

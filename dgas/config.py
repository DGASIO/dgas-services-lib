import os
import tornado.options
import configparser
import urllib.parse

# extra tornado config options
tornado.options.define("config", default="config.ini", help="configuration file")
tornado.options.define("port", default=8888, help="port to listen on")

_UNSET = object()

class Config(configparser.ConfigParser):

    def set_from_os_environ(self, section, key, os_key, default=_UNSET):
        if os_key in os.environ:
            value = os.environ[os_key]
        elif default is _UNSET:
            return
        else:
            value = default
        if not self.has_section(section):
            self.add_section(section)
        self.set(section, key, value)

    def _push(self):
        """Used in conjunction with _pop for testing to reset the configuration
        after each test"""
        if not hasattr(self, '_config_stack'):
            self._config_stack = []
        clone = Config()
        clone.read_dict(self)
        self._config_stack.append(clone)
        return self

    def _pop(self):
        if not hasattr(self, '_config_stack') or len(self._config_stack) == 0:
            raise Exception("Config Stack Underflow")
        clone = self._config_stack.pop()
        for section in self.sections():
            self.remove_section(section)
        self.read_dict(clone)
        return self

def setup_config():

    config = Config()

    if os.path.exists(tornado.options.options.config):
        config.read(tornado.options.options.config)

    if 'CONFIG' in os.environ:
        config.read(os.environ['CONFIG'])

    # verify config and set default values
    if 'general' not in config:
        config['general'] = {'debug': 'false'}
    elif 'debug' not in config['general']:
        config['debug'] = 'false'

    if 'DATABASE_URL' in os.environ:
        if 'PGSQL_STUNNEL_ENABLED' in os.environ and os.environ['PGSQL_STUNNEL_ENABLED'] == '1':
            p = urllib.parse.urlparse(os.environ['DATABASE_URL'])
            config['database'] = {
                'host': '/tmp/.s.PGSQL.6101',
                'database': p.path[1:]
            }
            if p.username:
                config['database']['user'] = p.username
            if p.password:
                config['database']['password'] = p.password
        else:
            config['database'] = {'dsn': os.environ['DATABASE_URL']}

    config.set_from_os_environ('database', 'max_size', 'MAX_DATABASE_CONNECTIONS')
    config.set_from_os_environ('database', 'min_size', 'MIN_DATABASE_CONNECTIONS')
    config.set_from_os_environ('redis', 'url', 'REDIS_URL')

    config.set_from_os_environ('s3', 'aws_access_key_id', 'AWS_ACCESS_KEY_ID')
    config.set_from_os_environ('s3', 'aws_secret_access_key', 'AWS_SECRET_ACCESS_KEY')
    config.set_from_os_environ('s3', 'bucket_name', 'AWS_BUCKET_NAME')
    config.set_from_os_environ('s3', 'region_name', 'AWS_REGION')

    config.set_from_os_environ('executor', 'max_workers', 'EXECUTOR_MAX_WORKERS')

    config.set_from_os_environ('general', 'cookie_secret', 'COOKIE_SECRET')

    if 'ENFORCE_HTTPS' in os.environ:
        mode = os.environ['ENFORCE_HTTPS']
        if mode not in ['reject', 'redirect']:
            mode = 'redirect'
        config['general']['enforce_https'] = mode

    config.set_from_os_environ('mixpanel', 'token', 'MIXPANEL_TOKEN')

    config.set_from_os_environ('logging', 'slack_webhook_url', 'SLACK_LOG_URL')
    if 'logging' in config and 'slack_webhook_url' in config['logging']:
        if 'SLACK_LOG_USERNAME' in os.environ:
            config['logging']['slack_log_username'] = os.environ['SLACK_LOG_USERNAME']
        if 'SLACK_LOG_LEVEL' in os.environ:
            config['logging']['slack_log_level'] = os.environ['SLACK_LOG_LEVEL']

    config.set_from_os_environ('logging', 'level', 'LOG_LEVEL', 'INFO')

    return config

tornado.options.parse_command_line()
config = setup_config()

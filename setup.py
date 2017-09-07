from setuptools import setup

setup(
    name='token-services',
    version='0.0.1',
    author='Tristan King',
    author_email='mars.king@gmail.com',
    packages=['tokenservices'],
    url='http://raneeli.com:dgasio/dgasio/dgas-services-lib',
    description='',
    long_description=open('README.md').read(),
    setup_requires=['pytest-runner'],
    install_requires=[
        'regex',
        'tornado==4.4.2',
        'ethereum',
    ],
    dependency_links=[
    ],
    tests_require=[
        'pytest',
        'requests',
        'testing.common.database',
        'testing.postgresql',
        'testing.redis',
        'asyncpg',
        'redis'
    ]
)

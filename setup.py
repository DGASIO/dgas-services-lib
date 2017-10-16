from setuptools import setup

setup(
    name='dgas-services',
    version='0.0.1',
    author='Tristan King',
    author_email='mars.king@gmail.com',
    packages=['dgas'],
    url='http://raneeli.com:dgasio/dgasio/dgas-services-lib',
    description='',
    long_description=open('README.md').read(),
    setup_requires=['pytest-runner'],
    install_requires=[
        'regex',
        'tornado==5.0.0'
    ],
    dependency_links=[
    ],
    extras_require={
        'ethereum': [
            'ethereum==2.3.0',
            'secp256k1'
        ]
    },
    tests_require=[
        'pytest',
        'requests',
        'testing.common.database',
        'testing.postgresql',
        'testing.redis',
        'asyncpg',
        'mixpanel==4.3.2',
        'redis',
        'msgpack-python',
        'aioredis==1.0.0',
        'botocore==1.8.21',
        'boto3==1.5.7',
        'aiobotocore==0.6.0',
        'moto[server]==1.2.0'
    ]
)

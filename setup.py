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
        'asyncpg==0.0.1',
        'dgasio==0.0.1'
    ],
    dependency_links=[
        'http://raneeli.com:dgasio/dgasio/asyncpg/tarball/master#egg=asyncpg-0.0.1',
        #'http://raneeli.com:dgasio/dgasio/dgasbrowser-python/tarball/master#egg=dgasio-0.0.1'
        'git+ssh://git@raneeli.com:dgasio/dgasio/dgasbrowser-python.git#egg=dgasio-0.0.1'
    ],
    tests_require=[
        'pytest'
    ]
)

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
    install_requires=[
        'asyncpg'
    ],
    dependency_links=['http://raneeli.com:dgasio/dgasio/asyncpg/tarball/master#egg=asyncpg']
)

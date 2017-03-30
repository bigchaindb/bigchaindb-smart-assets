#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('CHANGELOG.rst') as changelog_file:
    changelog = changelog_file.read()

install_requires = [
]

tests_require = [
    'tox>=2.3.1',
    'coverage>=4.1',
    'flake8>=2.6.0',
    'pytest>=3.0.1',
    'pytest-cov',
    'pytest-env',
    'pytest-sugar',
    'pytest-xdist',
    'responses',
]

dev_require = [
    'ipdb',
    'ipython',
]

docs_require = [
    'Sphinx>=1.3.5',
    'sphinx-autobuild',
    'sphinxcontrib-napoleon>=0.4.4',
    'sphinx_rtd_theme',
    'sphinxcontrib-httpdomain',
    'matplotlib',
]

setup(
    name='bigchaindb_consensus_composition',
    version='0.0.1',
    description="Composition consensus plugin for BigchainDB",
    long_description=readme + '\n\n' + changelog,
    author="BigchainDB",
    author_email='dev@bigchaindb.com',
    url='https://github.com/ascribe/bigchaindb-consensus-plugin-composition',
    packages=[
        'bigchaindb_consensus_composition',
    ],
    # Replace `PLUGIN_NAME` with a unique, unambiguous name to identify your
    # rules. You can also add multiple entry_points for different rules sets.
    entry_points={
        'bigchaindb.consensus': [
            'consensus_asset_composition=bigchaindb_consensus_composition.consensus:AssetCompositionConsensusRules'
        ]
    },
    package_dir={'bigchaindb_consensus_composition':
                 'bigchaindb_consensus_composition'},
    include_package_data=True,
    install_requires=install_requires,
    license="Apache Software License 2.0",
    zip_safe=False,
    keywords='bigchaindb_consensus_composition',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    extras_require={
        'test': tests_require,
        'dev': dev_require + tests_require + docs_require,
        'docs': docs_require,
    },
)

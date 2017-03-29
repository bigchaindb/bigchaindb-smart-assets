from pytest import fixture


@fixture
def plugin():
    return 'bigchaindb_consensus_composition.consensus:AssetCompositionConsensusRules'


@fixture
def plugin_local():
    import os
    plugin_path = 'bigchaindb_consensus_composition/consensus.py:AssetCompositionConsensusRules'
    return '{}/{}'.format(os.getcwd().split('/tests')[0], plugin_path)


from bigchaindb.common import crypto
from bigchaindb.common.exceptions import ValidationError
import pytest

TX_ENDPOINT = '/api/v1/transactions/'


def post_tx(b, client, tx):
    class Response():
        status_code = None

    response = Response()
    try:
        b.validate_transaction(tx)
        response.status_code = 202
    except ValidationError:
        response.status_code = 400

    if response.status_code == 202:
        mine(b, [tx])
    return response


def mine(b, tx_list):
    block = b.create_block(tx_list)
    b.write_block(block)

    # vote the block valid
    vote = b.vote(block.id, b.get_last_voted_block().id, True)
    b.write_vote(vote)

    return block, vote


def create_simple_tx(user_pub, user_priv, asset=None, metadata=None):
    from bigchaindb.models import Transaction
    create_tx = Transaction.create([user_pub], [([user_pub], 1)], asset=asset, metadata=metadata)
    create_tx = create_tx.sign([user_priv])
    return create_tx


def transfer_simple_tx(user_pub, user_priv, input_tx, metadata=None):
    from bigchaindb.models import Transaction

    asset_id = input_tx.id if input_tx.operation == 'CREATE' else input_tx.asset['id']

    transfer_tx = Transaction.transfer(input_tx.to_inputs(),
                                       [([user_pub], 1)],
                                       asset_id=asset_id,
                                       metadata=metadata)
    transfer_tx = transfer_tx.sign([user_priv])

    return transfer_tx


@pytest.mark.bdb
@pytest.mark.usefixtures('inputs')
def test_consensus_load(b):
    alice_priv, alice_pub = crypto.generate_key_pair()

    create_a = create_simple_tx(
        alice_pub, alice_priv,
        asset={
            'type': 'mix',
            'data': {
                'material': 'secret sauce'
            }
        })
    response = post_tx(b, None, create_a)
    assert response.status_code == 202


@pytest.mark.bdb
@pytest.mark.usefixtures('inputs')
def test_consensus_rules(b):
    alice_priv, alice_pub = crypto.generate_key_pair()

    create_a = create_simple_tx(
        alice_pub, alice_priv,
        asset={
            'type': 'composition',
            'policy': [
                {
                    'condition': {
                        'expr': '%0 EQ {}'.format('"INIT"'),
                        'locals': ['transaction.metadata["state"]']
                    },
                    'rule': {
                        'expr': '%0 EQ %1',
                        'locals': ['transaction.inputs[:].amount', 'transaction.outputs[:].amount']
                    }
                },
                {
                    'condition': {
                        'expr': '%0 EQ {}'.format(alice_pub),
                        'locals': ['transaction.metadata']
                    },
                    'rule': {
                        'expr': '%0 EQ 1',
                        'locals': ['transaction.outputs[:].amount']
                    }
                },
            ]
        },
        metadata={
            'state': "INIT"
        })
    response = post_tx(b, None, create_a)
    assert response.status_code == 202


@pytest.mark.bdb
@pytest.mark.usefixtures('inputs')
def test_consensus_rules_frontend(b):
    alice_priv, alice_pub = crypto.generate_key_pair()

    create_a = create_simple_tx(
        alice_pub, alice_priv,
        asset={
            'type': 'composition',
            'policy': [
                {
                    'condition': {
                        'expr': "'INIT' EQ 'INIT'",
                        'locals': []
                    },
                    'rule': {
                        'expr': "'0' EQ '0'",
                        'locals': []
                    }
                },
            ]
        },
        metadata={
            'state': "INIT"
        })
    response = post_tx(b, None, create_a)
    assert response.status_code == 202


@pytest.mark.bdb
@pytest.mark.usefixtures('inputs')
def test_consensus_rules_recipe(b):
    brand_priv, brand_pub = crypto.generate_key_pair()
    sicpa_priv, sicpa_pub = crypto.generate_key_pair()
    clarion_priv, clarion_pub = crypto.generate_key_pair()

    # recipe stages:
    # 1) PUBLISH RECIPE
    #    - FROM: BRAND, TO: BRAND
    #    - created by brand and broadcasted to supply chain
    # 2) TAGGANT ORDER
    #    - FROM: BRAND, TO: SICPA
    #    - should only be processed by SICPA
    #    - only one input and one output
    #    - has target volume/mass and concentration
    # 3) TAGGANT READY
    #    - FROM: SICPA, TO: SICPA
    #    - QA on volume/mass and concentration > Certificate
    # 3b) TAGGANT DELIVERY
    # 4) MIX ORDER
    #    - FROM: SICPA, TO: CLARION
    #    - has target volume/mass and concentration
    #    - mix properties: cannot unmix
    # 5) MIX READY
    #    - FROM: CLARION, TO: CLARION_WAREHOUSE, CLARION_DESTROY
    #    - QA on target volume/mass and concentration > Certificate

    tx_order = create_simple_tx(
        brand_pub, brand_priv,
        asset={
            'type': 'composition',
            'policy': [
                {
                    'condition': {
                        'expr': "%0 EQ '{}'".format("TAGGANT_ORDER"),
                        'locals': ["transaction.metadata['state']"]
                    },
                    'rule': {
                        'expr': "%0 EQ {} AND %1 EQ {}".format(1, 1),
                        'locals': ["len(transaction.outputs), len(transaction.inputs)"]
                    }
                },
                {
                    'condition': {
                        'expr': "%0 EQ '{}'".format("TAGGANT_ORDER"),
                        'locals': ["transaction.metadata['state']"]
                    },
                    'rule': {
                        'expr': "%0 EQ '{}'".format(sicpa_pub),
                        'locals': ["transaction.outputs[0].public_keys[0]"]
                    }
                },
                {
                    'condition': {
                        'expr': "%0 EQ '{}'".format("TAGGANT_ORDER"),
                        'locals': ["transaction.metadata['state']"]
                    },
                    'rule': {
                        'expr': "%0 EQ {}".format(1),
                        'locals': ["len(transaction.outputs[0].public_keys)"]
                    }
                },
                {
                    'condition': {
                        'expr': "%0 EQ '{}'".format("TAGGANT_ORDER"),
                        'locals': ["transaction.metadata['state']"]
                    },
                    'rule': {
                        'expr': "%0 EQ {}".format(1),
                        'locals': ["len(transaction.inputs[0].owners_before)"]
                    }
                },
                {
                    'condition': {
                        'expr': "%0 EQ '{}'".format("TAGGANT_ORDER"),
                        'locals': ["transaction.metadata['state']"]
                    },
                    'rule': {
                        'expr': "%0 EQ {}".format(1),
                        'locals': ["len(transaction.outputs[0].public_keys)"]
                    }
                },
                {
                    'condition': {
                        'expr': "%0 EQ '{}'".format("TAGGANT_READY"),
                        'locals': ["transaction.metadata['state']"]
                    },
                    'rule': {
                        'expr': "%0 EQ {}".format(1000),
                        'locals': ["transaction.metadata['conservation']['volume']"]
                    }
                },
                {
                    'condition': {
                        'expr': "%0 EQ '{}'".format("TAGGANT_READY"),
                        'locals': ["transaction.metadata['state']"]
                    },
                    'rule': {
                        'expr': "%0 EQ {}".format(0.99),
                        'locals': ["transaction.metadata['conservation']['concentration']"]
                    }
                },
            ]
        },
        metadata={
            'state': "INIT"
        })
    response = post_tx(b, None, tx_order)
    assert response.status_code == 202

    from bigchaindb.models import Transaction

    tx_taggant_order = Transaction.transfer(
        tx_order.to_inputs(),
        [([sicpa_pub], 1)],
        tx_order.id,
        metadata={
            'state': "TAGGANT_ORDER"
        }
    )

    tx_mix_signed = tx_taggant_order.sign([brand_priv])
    response = post_tx(b, None, tx_mix_signed)
    assert response.status_code == 202

    # tx_taggant_order = Transaction.transfer(
    #     tx_order.to_inputs(),
    #     [([sicpa_pub], 1)],
    #     tx_order.id,
    #     metadata={
    #         'state': "TAGGANT_ORDER",
    #         'conservation': {
    #             'volume': '1000',
    #             'concentration': '99%'
    #         }
    #     }
    # )
    #
    # tx_mix_signed = tx_taggant_order.sign([brand_priv])
    # response = post_tx(b, None, tx_mix_signed)
    # assert response.status_code == 202


@pytest.mark.bdb
@pytest.mark.usefixtures('inputs')
def test_asset_type_mix(b, client):
    from bigchaindb.models import Transaction

    alice_priv, alice_pub = crypto.generate_key_pair()

    create_a = create_simple_tx(
        alice_pub, alice_priv,
        asset={
            'type': 'mix',
            'data': {
                'material': 'secret sauce'
            }
        })
    response = post_tx(b, client, create_a)
    assert response.status_code == 202

    transfer_a = transfer_simple_tx(alice_pub, alice_priv, create_a)
    response = post_tx(b, client, transfer_a)
    assert response.status_code == 202

    bob_priv, bob_pub = crypto.generate_key_pair()
    tx_b = create_simple_tx(
        bob_pub,
        bob_priv,
        asset={
            'type': 'mix',
            'data': {
                'material': 'bulk'
            }
        })
    response = post_tx(b, client, tx_b)
    assert response.status_code == 202

    carly_priv, carly_pub = crypto.generate_key_pair()

    tx_mix = Transaction.transfer(
        transfer_a.to_inputs() + tx_b.to_inputs(),
        [([carly_pub], 1)],
        transfer_a.id
    )

    tx_mix_signed = tx_mix.sign([alice_priv, bob_priv])
    response = post_tx(b, client, tx_mix_signed)
    assert response.status_code == 202

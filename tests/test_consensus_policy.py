from bigchaindb.common import crypto
import pytest


@pytest.mark.bdb
@pytest.mark.usefixtures('inputs')
def test_consensus_load(b):
    from .utils import create_simple_tx, post_tx
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
    from .utils import create_simple_tx, post_tx

    alice_priv, alice_pub = crypto.generate_key_pair()

    create_a = create_simple_tx(
        alice_pub, alice_priv,
        asset={
            'policy': [
                {
                    'condition': 'transaction.metadata["state"] == "INIT"',
                    'rule': 'AMOUNT(transaction.outputs) == 1'
                },
                {
                    'condition': 'transaction.inputs[0].owners_before == "{}"'.format(alice_pub),
                    'rule': 'LEN(transaction.outputs) == 1'
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
    from .utils import create_simple_tx, post_tx

    alice_priv, alice_pub = crypto.generate_key_pair()

    create_a = create_simple_tx(
        alice_pub, alice_priv,
        asset={
            'policy': [
                {
                    'condition': "'INIT' == 'INIT'",
                    'rule': "'INIT' == 'INIT'"
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
    from .utils import create_simple_tx, post_tx

    albi_priv, albi_pub = crypto.generate_key_pair()
    bruce_priv, bruce_pub = crypto.generate_key_pair()
    carly_priv, carly_pub = crypto.generate_key_pair()

    # recipe stages:
    # 1) PUBLISH RECIPE
    #    - FROM: ALBI, TO: ALBI
    #    - created by albi and broadcasted to supply chain
    # 2) CONCENTRATE ORDER
    #    - FROM: ALBI, TO: BRUCE
    #    - should only be processed by BRUCE
    #    - only one input and one output
    #    - has target volume/mass and concentration
    # 3) CONCENTRATE READY
    #    - FROM: BRUCE, TO: BRUCE
    #    - QA on volume/mass and concentration > Certificate
    # 3b) CONCENTRATE DELIVERY
    # 4) MIX ORDER
    #    - FROM: BRUCE, TO: CARLY
    #    - has target volume/mass and concentration
    #    - mix properties: cannot unmix
    # 5) MIX READY
    #    - FROM: CARLY, TO: CARLY_WAREHOUSE, CARLY_DESTROY
    #    - QA on target volume/mass and concentration > Certificate

    tx_order = create_simple_tx(
        albi_pub, albi_priv,
        asset={
            'policy': [
                {
                    'condition':
                        "transaction.metadata['state'] == 'CONCENTRATE_ORDER'",
                    'rule':
                        "LEN(transaction.outputs) == 1"
                        " AND LEN(transaction.inputs) == 1"
                        " AND LEN(transaction.outputs[0].public_keys) == 1"
                        " AND LEN(transaction.inputs[0].owners_before) == 1"
                        " AND transaction.outputs[0].public_keys[0] == '{}'"
                        .format(bruce_pub),
                },
                {
                    'condition':
                        "transaction.metadata['state'] == 'CONCENTRATE_READY'",
                    'rule':
                        "AMOUNT(transaction.outputs) == 1"
                        " AND transaction.metadata['concentration'] > 95"
                        " AND transaction.inputs[0].owners_before[0] == '{}'"
                        " AND ( transaction.outputs[0].public_keys[0] == '{}'"
                        " OR transaction.outputs[0].public_keys[0] == '{}')"
                        .format(bruce_pub, bruce_pub, carly_pub)
                }
            ]
        },
        metadata={
            'state': "INIT"
        })
    response = post_tx(b, None, tx_order)
    assert response.status_code == 202

    from bigchaindb.models import Transaction

    tx_concentrate_order = Transaction.transfer(
        tx_order.to_inputs(),
        [([bruce_pub], 1)],
        tx_order.id,
        metadata={
            'state': "CONCENTRATE_ORDER"
        }
    )

    tx_concentrate_order_signed = tx_concentrate_order.sign([albi_priv])
    response = post_tx(b, None, tx_concentrate_order_signed)
    assert response.status_code == 202

    concentrate_amount = 1
    tx_concentrate_ready = Transaction.transfer(
        tx_concentrate_order.to_inputs(),
        [([carly_pub], concentrate_amount)],
        tx_order.id,
        metadata={
            'state': "CONCENTRATE_READY",
            'concentration': 97
        }
    )

    tx_concentrate_ready_signed = tx_concentrate_ready.sign([bruce_priv])
    response = post_tx(b, None, tx_concentrate_ready_signed)
    assert response.status_code == 202

    bulk_amount = 3500
    tx_bulk = Transaction.create(
        [carly_pub],
        [([carly_pub], bulk_amount)],
        asset={
            'data': {}
        },
        metadata={
            'state': "BULK_READY"
        }
    )
    tx_bulk_signed = tx_bulk.sign([carly_priv])
    response = post_tx(b, None, tx_bulk_signed)
    assert response.status_code == 202

    mix_amount = bulk_amount
    tx_mix_ready = Transaction.transfer(
        tx_bulk.to_inputs(),
        [([carly_pub], mix_amount)],
        tx_bulk.id,
        metadata={
            'state': "MIX_READY",
            'concentration': 97
        }
    )

    tx_mix_ready_signed = tx_mix_ready.sign([carly_priv])
    response = post_tx(b, None, tx_mix_ready_signed)
    assert response.status_code == 202

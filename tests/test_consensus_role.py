from bigchaindb.common import crypto
import pytest


@pytest.mark.skip('')
@pytest.mark.bdb
@pytest.mark.usefixtures('inputs')
def test_permissions(b):
    from .utils import create_simple_tx, post_tx

    admin_priv, admin_pub = crypto.generate_key_pair()

    # class App():
    #   allowed_permissions = [
    #     'ADD_USER'
    #   ]
    #
    #   def __init__(owner, uuid):
    #     self.uuid = uuid
    #     self.owner = owner
    #     for allowed_permission in allowed_permissions:
    #       self.permissions[allowed_permission] = []
    #
    # admin CREATES permissions ASSET
    # admin CREATES app ASSET
    # admin LINKS permission ID
    #
    #   def grant_permission(permission, user):
    #     self.permissions[permission].append(user)
    #
    #   def revoke_permission(permission, user):
    #     self.permissions[permission].remove(user)
    #

    create_permission_add_user = create_simple_tx(
        admin_pub, admin_priv,
        asset={
            'permission': 'ADD_USER'
        })
    response = post_tx(b, None, create_permission_add_user)
    assert response.status_code == 202

    create_app = create_simple_tx(
        admin_pub, admin_priv,
        asset={
            'uuid': 'app',
            'links': create_permission_add_user.id
        })
    response = post_tx(b, None, create_app)
    assert response.status_code == 202


@pytest.mark.skip('')
@pytest.mark.bdb
@pytest.mark.usefixtures('inputs')
def test_roles(b):
    from .utils import create_simple_tx, post_tx

    admin_priv, admin_pub = crypto.generate_key_pair()

    # class AddUserRole():
    #   permissions = [
    #     'ADD_USER'
    #   ]
    #
    #   def __init__(user):
    #     self.user = user
    #
    # class App():
    #   def __init__(owner, uuid):
    #     self.uuid = uuid
    #     self.owner = owner
    #     self.roles = {}
    #
    #   def add_role(role):
    #     self.roles[role.user] = role
    #
    #   def remove_role(role):
    #     self.roles[role.user] = None
    #

    create_permission_add_user = create_simple_tx(
        admin_pub, admin_priv,
        asset={
            'permission': 'ADD_USER'
        })
    response = post_tx(b, None, create_permission_add_user)
    assert response.status_code == 202

    create_app = create_simple_tx(
        admin_pub, admin_priv,
        asset={
            'uuid': 'app',
            'links': create_permission_add_user.id
        })
    response = post_tx(b, None, create_app)
    assert response.status_code == 202


@pytest.mark.bdb
@pytest.mark.usefixtures('inputs')
def test_permission_add_role(b):
    from .utils import create_simple_tx, post_tx, transfer_simple_tx, prepare_transfer, get_message_to_sign
    from bigchaindb.models import Transaction
    from cryptoconditions import Ed25519Fulfillment, ThresholdSha256Fulfillment, PreimageSha256Fulfillment
    from cryptoconditions.crypto import Ed25519VerifyingKey, Ed25519SigningKey

    # admin, albi, bruce
    admin_priv, admin_pub = crypto.generate_key_pair()
    albi_priv, albi_pub = crypto.generate_key_pair()
    bruce_priv, bruce_pub = crypto.generate_key_pair()

    assert len(b.get_owned_ids(admin_pub)) == 0
    assert len(b.get_owned_ids(albi_pub)) == 0
    assert len(b.get_owned_ids(bruce_pub)) == 0

    # admin CREATES role: tx_create_role, 202
    tx_create_role = Transaction.create(
        [admin_pub],
        [([admin_pub], 1)],
        asset={
            "policy": [
                {
                    "condition": "transaction.operation == 'TRANSFER'",
                    "rule": "transaction.inputs[0].owners_before[0] == '{}'".format(admin_pub)
                },
            ]
        }
    )
    tx_create_role.outputs[0].public_keys = [] # trick to not include in balance part 1
    tx_create_role = tx_create_role.sign([admin_priv])
    response = post_tx(b, None, tx_create_role)
    tx_create_role_retrieved = b.get_transaction(tx_create_role.id)

    assert response.status_code == 202
    assert tx_create_role_retrieved.id == tx_create_role.id

    #  admin.unspents = [] # admin doesnt have role, only created it
    #  user_a.unspents = [] # user_a has no role
    #  user_b.unspents = [] # user_b has no role

    assert len(b.get_owned_ids(admin_pub)) == 0
    assert len(b.get_owned_ids(albi_pub)) == 0
    assert len(b.get_owned_ids(bruce_pub)) == 0

    # admin TRANSFERS tx_create_role TO user_a: tx_transfer_role_a, 202

    # tx_transfer_role_a = Transaction.transfer(
    #     [
    #         Input(
    #             fulfillment=Ed25519Fulfillment(
    #                 public_key=Ed25519VerifyingKey(admin_pub)),
    #             owners_before=[admin_pub], # trick to not include in balance part 2
    #             fulfills=TransactionLink(
    #                 txid=tx_create_role.id,
    #                 output=0)
    #             )
    #     ],
    #     [([albi_pub], 1)],
    #     tx_create_role.id)
    # tx_transfer_role_a = tx_transfer_role_a.sign([admin_priv])

    output_condition = ThresholdSha256Fulfillment(threshold=1)
    output_condition.add_subfulfillment(
        Ed25519Fulfillment(public_key=Ed25519VerifyingKey(admin_pub))
    )

    output_condition.add_subfulfillment(
        Ed25519Fulfillment(public_key=Ed25519VerifyingKey(albi_pub))
    )

    tx_transfer_role_a = prepare_transfer(
        inputs=[
            {
                'tx': tx_create_role.to_dict(),
                'output': 0
            }
        ],
        outputs=[
            {
                'condition': output_condition,
                'public_keys': [albi_pub]
            },
        ]
    )

    input_fulfillment = Ed25519Fulfillment(public_key=Ed25519VerifyingKey(admin_pub))
    tx_transfer_role_a.inputs[0].owners_before = [admin_pub]
    message_to_sign = get_message_to_sign(tx_transfer_role_a)
    input_fulfillment.sign(message_to_sign, Ed25519SigningKey(admin_priv))
    tx_transfer_role_a.inputs[0].fulfillment = input_fulfillment

    tx_transfer_role_a.validate(b)

    response = post_tx(b, None, tx_transfer_role_a)
    # tx_create_role_retrieved = b.get_transaction(tx_create_role.id)

    assert response.status_code == 202

    #  user_a.unspents = [tx_transfer_role_a] # user_a has role
    assert len(b.get_owned_ids(admin_pub)) == 0
    assert len(b.get_owned_ids(albi_pub)) == 1
    assert len(b.get_owned_ids(bruce_pub)) == 0

    # user TRANSFERS tx_transfer_role_a TO user_b: -, 400 # only admin can assign role
    tx_transfer_role_b = prepare_transfer(
        inputs=[
            {
                'tx': tx_transfer_role_a.to_dict(),
                'output': 0
            }
        ],
        outputs=[
            {
                'condition': Ed25519Fulfillment(Ed25519VerifyingKey(bruce_pub)),
            },
        ]
    )

    tx_transfer_role_b.inputs[0].owners_before = [albi_pub]

    message_to_sign = get_message_to_sign(tx_transfer_role_b)
    input_fulfillment = ThresholdSha256Fulfillment(threshold=1)
    albi_fulfillment = Ed25519Fulfillment(public_key=Ed25519VerifyingKey(albi_pub))
    albi_fulfillment.sign(message_to_sign, Ed25519SigningKey(albi_priv))

    input_fulfillment.add_subfulfillment(albi_fulfillment)
    input_fulfillment.add_subcondition_uri(
        Ed25519Fulfillment(public_key=Ed25519VerifyingKey(admin_pub)).condition_uri
    )
    tx_transfer_role_b.inputs[0].fulfillment = input_fulfillment
    input_fulfillment.serialize_uri()
    tx_transfer_role_b.validate(b)

    response = post_tx(b, None, tx_transfer_role_b)

    assert response.status_code == 400

    #  user_a.unspents = [tx_transfer_role_a] # user_a has role
    #  user_b.unspents = [] # user_b has no role
    assert len(b.get_owned_ids(admin_pub)) == 0
    assert len(b.get_owned_ids(albi_pub)) == 1
    assert len(b.get_owned_ids(bruce_pub)) == 0

    # admin BURNS tx_create_role_a: tx_burn_role_a

    tx_burn_role_a = prepare_transfer(
        inputs=[
            {
                'tx': tx_transfer_role_a.to_dict(),
                'output': 0
            }
        ],
        outputs=[
            {
                'condition': PreimageSha256Fulfillment(preimage=b'unknown'),
            },
        ]
    )

    tx_burn_role_a.inputs[0].owners_before = [admin_pub]

    message_to_sign = get_message_to_sign(tx_burn_role_a)
    input_fulfillment = ThresholdSha256Fulfillment(threshold=1)
    albi_fulfillment = Ed25519Fulfillment(public_key=Ed25519VerifyingKey(admin_pub))
    albi_fulfillment.sign(message_to_sign, Ed25519SigningKey(admin_priv))

    input_fulfillment.add_subfulfillment(albi_fulfillment)
    input_fulfillment.add_subcondition_uri(
        Ed25519Fulfillment(public_key=Ed25519VerifyingKey(albi_pub)).condition_uri
    )
    tx_burn_role_a.inputs[0].fulfillment = input_fulfillment
    input_fulfillment.serialize_uri()
    tx_burn_role_a.validate(b)

    response = post_tx(b, None, tx_burn_role_a)

    assert response.status_code == 202

    #  user_a.unspents = [] # user_a has no role
    assert len(b.get_owned_ids(admin_pub)) == 0
    assert len(b.get_owned_ids(albi_pub)) == 0
    assert len(b.get_owned_ids(bruce_pub)) == 0

    # admin TRANSFERS (REFILL) role to user_b: tx_transfer_role_b, 202 etc...

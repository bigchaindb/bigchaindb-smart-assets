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
    from .utils import create_simple_tx, post_tx
    from bigchaindb.models import Transaction
    from bigchaindb import Bigchain
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
        asset=None,
        metadata=None)
    tx_create_role.outputs = []
    tx_create_role = tx_create_role.sign([admin_priv])
    response = post_tx(b, None, tx_create_role)
    tx_create_role_retrieved = b.get_asset_by_id(tx_create_role.id)

    print(tx_create_role_retrieved)

    assert response.status_code == 202
    assert len(b.get_owned_ids(admin_pub)) == 0
    assert len(b.get_owned_ids(albi_pub)) == 0
    assert len(b.get_owned_ids(bruce_pub)) == 0
    assert tx_create_role_retrieved['id'] == tx_create_role['id']

    #  admin.unspents = [] # admin doesnt have role, only created it
    #  user_a.unspents = [] # user_a has no role
    #  user_b.unspents = [] # user_b has no role
    # admin TRANSFERS tx_create_role TO user_a: tx_transfer_role_a, 202
    #  user_a.unspents = [tx_transfer_role_a] # user_a has role
    # user TRANSFERS tx_transfer_role_a TO user_b: -, 400 # only admin can assign role
    #  user_a.unspents = [tx_transfer_role_a] # user_a has role
    #  user_b.unspents = [] # user_b has no role
    # admin BURNS tx_create_role_a: tx_burn_role_a
    #  user_a.unspents = [] # user_a has no role
    # admin TRANSFERS role to user_b: tx_transfer_role_b, 202
    #  admin.unspents = [] # admin doesnt have role, only created it
    #  user_a.unspents = [] # user_a has no role
    #  user_b.unspents = [tx_transfer_role_b] # user_b has role

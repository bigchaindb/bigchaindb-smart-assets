from functools import singledispatch

import rethinkdb as r

from bigchaindb.common.exceptions import ValidationError
from bigchaindb.backend.mongodb.connection import MongoDBConnection
from bigchaindb.backend.rethinkdb.connection import RethinkDBConnection

TX_ENDPOINT = '/api/v1/transactions/'


@singledispatch
def list_dbs(connection):
    raise NotImplementedError


@list_dbs.register(RethinkDBConnection)
def list_rethink_dbs(connection):
    return connection.run(r.db_list())


@list_dbs.register(MongoDBConnection)
def list_mongo_dbs(connection):
    raise NotImplementedError


@singledispatch
def flush_db(connection, dbname):
    raise NotImplementedError


@flush_db.register(RethinkDBConnection)
def flush_rethink_db(connection, dbname):
    try:
        connection.run(r.db(dbname).table('bigchain').delete())
        connection.run(r.db(dbname).table('backlog').delete())
        connection.run(r.db(dbname).table('votes').delete())
    except r.ReqlOpFailedError:
        pass


@flush_db.register(MongoDBConnection)
def flush_mongo_db(connection, dbname):
    connection.conn[dbname].bigchain.delete_many({})
    connection.conn[dbname].backlog.delete_many({})
    connection.conn[dbname].votes.delete_many({})


@singledispatch
def update_table_config(connection, table, **kwrgas):
    raise NotImplementedError


@update_table_config.register(RethinkDBConnection)
def update_table_config(connection, table, **kwargs):
    return connection.run(r.table(table).config().update(dict(**kwargs)))


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


def prepare_transfer(inputs, outputs, metadata=None):
    """Create an instance of a :class:`~.Output`.

    Args:
        inputs (list of
                    (dict):
                        {
                            'tx': <(bigchaindb.common.transactionTransaction):
                                    input transaction, can differ but must have same asset id>,
                            'output': <(int): output index of tx>
                        }
                )
        outputs (list of
                    (dict):
                        {
                            'condition': <(cryptoconditions.Condition): output condition>,
                            'public_keys': <(optional list of base58): for indexing defaults to `None`>,
                            'amount': <(int): defaults to `1`>
                        }
                )
        metadata (dict)
    Raises:
        TypeError: if `public_keys` is not instance of `list`.
            """
    from bigchaindb.common.transaction import (
        Input,
        Output,
        TransactionLink
    )

    from bigchaindb.models import Transaction

    from cryptoconditions import (
        Fulfillment,
        Condition
    )

    asset = inputs[0]['tx']['asset']
    asset = {
        'id': asset['id'] if 'id' in asset else inputs[0]['tx']['id']
    }

    _inputs, _outputs = [], []

    for _input in inputs:

        _output = _input['tx']['outputs'][_input['output']]
        _inputs.append(
            Input(
                fulfillment=Condition.from_uri(_output['condition']['uri']),
                owners_before=_output['public_keys'],
                fulfills=TransactionLink(
                    txid=_input['tx']['id'],
                    output=_input['output'])
            )
        )

    for output in outputs:
        _outputs.append(
            Output(
                fulfillment=output['condition'],
                public_keys=output['public_keys'] if "public_keys" in output else [],
                amount=output['amount'] if "amount" in output else 1
            )
        )

    return Transaction(
        operation='TRANSFER',
        asset=asset,
        inputs=_inputs,
        outputs=_outputs,
        metadata=metadata,
    )


def sign_ed25519(transaction, private_keys):
    from cryptoconditions import Ed25519Fulfillment
    from cryptoconditions.crypto import Ed25519VerifyingKey

    for index, _input in enumerate(transaction.inputs):
        receiver = _input.owners_before[0]
        transaction.inputs[index].fulfillment = Ed25519Fulfillment(
            public_key=Ed25519VerifyingKey(receiver)
        )

    private_keys = [private_keys] if not isinstance(private_keys, list) else private_keys
    return transaction.sign(private_keys).to_dict()


def get_message_to_sign(transaction):
    from bigchaindb.common.transaction import Transaction
    # fulfillments are not part of the message to sign
    tx_dict = Transaction._remove_signatures(transaction.to_dict())
    return Transaction._to_str(tx_dict).encode()

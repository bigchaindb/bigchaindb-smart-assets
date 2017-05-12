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

from bigchaindb.common.exceptions import ValidationError
from bigchaindb.consensus import BaseConsensusRules
from bigchaindb.models import Transaction

from bigchaindb_smart_assets.policy import PolicyParser

ASSET_TYPE_PURE = 'pure'
ASSET_TYPE_COMPOSITION = 'composition'

ASSET_TYPES = [
    ASSET_TYPE_PURE,
    ASSET_TYPE_COMPOSITION
]


class AssetCompositionConsensusRules(BaseConsensusRules):

    @staticmethod
    def validate_transaction(bigchain, transaction):

        input_txs = None
        if transaction.operation == Transaction.TRANSFER:
            input_txs = transaction.get_input_txs(bigchain)

        result = transaction.validate(bigchain, input_txs)

        AssetCompositionConsensusRules\
            .validate_asset(bigchain, transaction, input_txs)

        return result

    @staticmethod
    def validate_asset(bigchain, transaction, input_txs):
        assets = AssetCompositionConsensusRules\
            .resolve_asset(bigchain, transaction, input_txs)

        asset_types = set(
            [asset['data']['type']
             for asset in assets
             if 'data' in asset and asset['data'] is not None
             and 'type' in asset['data'] and asset['data']['type'] is not None
             and asset['data']['type'] in ASSET_TYPES])

        asset_type = ASSET_TYPE_PURE
        if len(asset_types) == 1:
            asset_type = asset_types.pop()
        if len(asset_types) > 1:
            raise ValidationError('Cannot mix assets')

        if asset_type == ASSET_TYPE_PURE:
            return AssetCompositionConsensusRules\
                .validate_pure(bigchain, transaction, input_txs)
        elif asset_type == ASSET_TYPE_COMPOSITION:
            return AssetCompositionConsensusRules\
                .validate_composition(bigchain, transaction, input_txs)

    @staticmethod
    def validate_pure(bigchain, transaction, input_txs):
        if transaction.operation == Transaction.TRANSFER:
            transaction.validate_asset(
                bigchain,
                [input_tx
                 for (input_, input_tx, status)
                 in input_txs if input_tx is not None])

            AssetCompositionConsensusRules\
                .validate_amount_conservation(transaction, input_txs)

        return transaction

    @staticmethod
    def validate_composition(bigchain, transaction, input_txs):
        asset = AssetCompositionConsensusRules \
            .resolve_asset(bigchain, transaction, input_txs)[0]['data']

        if 'policy' in asset:
            policies = asset['policy']
            if not isinstance(policies, list):
                raise ValidationError('policy must be a list')

            for policy in policies:
                if 'condition' not in policy \
                        or'rule' not in policy:
                    raise ValidationError(
                        'policy item must contain a condition and rule')

                parser = PolicyParser(transaction)
                try:
                    if parser.parse(policy['condition']) is True:
                        if not parser.parse(policy['rule']) is True:
                            raise ValidationError(
                                'Rule {} evaluated to false'.format(policy['rule']))

                except (AttributeError, KeyError) as e:
                    raise ValidationError(
                        'Wrong policy format: {}'.format(policy))
                except TypeError as e:
                    pass

        if transaction.operation == Transaction.TRANSFER:
            pass

        return transaction

    @staticmethod
    def validate_amount_conservation(transaction, input_txs):
        transaction.validate_amount(
            [input_tx.outputs[input_.fulfills.output]
             for (input_, input_tx, status)
             in input_txs
             if input_tx is not None])

    @staticmethod
    def resolve_asset(bigchain, transaction, input_txs):
        if not hasattr(transaction, 'asset'):
            raise ValidationError('Asset not found in transaction {}'.format(transaction))

        if transaction.operation == Transaction.GENESIS:
            return []
        elif transaction.operation == Transaction.CREATE:
            return [transaction.asset]
        elif transaction.operation == Transaction.TRANSFER:
            asset_ids = transaction.get_asset_ids(
                [input_tx
                 for (input_, input_tx, status)
                 in input_txs
                 if input_tx is not None])
            return [bigchain.get_transaction(asset_id).asset
                    for asset_id
                    in asset_ids]

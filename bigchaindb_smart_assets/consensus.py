from bigchaindb.common.exceptions import ValidationError
from bigchaindb.consensus import BaseConsensusRules
from bigchaindb.models import Transaction

from bigchaindb_smart_assets.policy import PolicyParser

ASSET_RULE_POLICY = 'policy'
ASSET_RULE_ROLE = 'role'


class SmartAssetConsensusRules(BaseConsensusRules):

    @staticmethod
    def validate_transaction(bigchain, transaction):

        input_txs = None
        if transaction.operation == Transaction.TRANSFER:
            input_txs = transaction.get_input_txs(bigchain)

        result = transaction.validate(bigchain, input_txs)

        SmartAssetConsensusRules\
            .validate_asset(bigchain, transaction, input_txs)

        return result

    @staticmethod
    def validate_asset(bigchain, transaction, input_txs):
        assets = SmartAssetConsensusRules \
            .resolve_assets(bigchain, transaction, input_txs)

        for asset in assets:
            if asset['data'] and ASSET_RULE_POLICY in asset['data']:
                policy = asset['data']['policy']
                return SmartAssetConsensusRules\
                    .validate_policy(policy, transaction)
            else:
                SmartAssetConsensusRules\
                    .validate_standard(bigchain, transaction, input_txs)

    @staticmethod
    def validate_standard(bigchain, transaction, input_txs):
        if transaction.operation == Transaction.TRANSFER:
            transaction.validate_asset(
                bigchain,
                [input_tx
                 for (input_, input_tx, status)
                 in input_txs if input_tx is not None])

            SmartAssetConsensusRules\
                .validate_amount_conservation(transaction, input_txs)

        return transaction

    @staticmethod
    def validate_policy(policy, transaction):
        if not isinstance(policy, list):
            raise ValidationError('policy must be a list')

        for policy_rule in policy:
            if 'condition' not in policy_rule or'rule' not in policy_rule:
                raise ValidationError(
                    'policy item must contain a condition and rule')

            parser = PolicyParser(transaction)
            try:
                if parser.parse(policy_rule['condition']) is True:
                    if not parser.parse(policy_rule['rule']) is True:
                        raise ValidationError(
                            'Rule {} evaluated to false'
                            .format(policy_rule['rule']))

            except (AttributeError, KeyError) as e:
                raise ValidationError(
                    'Wrong policy format: {}'.format(policy_rule))
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
    def resolve_assets(bigchain, transaction, input_txs):
        if not hasattr(transaction, 'asset'):
            raise ValidationError('Asset not found in transaction {}'
                                  .format(transaction))

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

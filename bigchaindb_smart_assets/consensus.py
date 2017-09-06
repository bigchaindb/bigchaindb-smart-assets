from bigchaindb.common.exceptions import ValidationError
from bigchaindb.consensus import BaseConsensusRules
from bigchaindb.models import Transaction

from bigchaindb_smart_assets.policy import PolicyParser

ASSET_RULE_POLICY = 'policy'
ASSET_RULE_ROLE = 'role'
ASSET_RULE_LINK = 'link'
METADATA_RULE_CAN_LINK = 'canLink'


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

        SmartAssetConsensusRules.validate_link(transaction, bigchain)

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
            if 'condition' not in policy_rule or 'rule' not in policy_rule:
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
    def validate_link(transaction, bigchain):
        public_key = transaction.inputs[0].owners_before[0]
        cant_link_error = 'Linking is not authorized for: {}'.format(public_key)

        if transaction.operation == Transaction.GENESIS or\
            transaction.operation == Transaction.TRANSFER:
            return

        if not hasattr(transaction, 'asset'):
            raise ValidationError('Asset not found in transaction {}'
                                  .format(transaction))

        if transaction.asset['data'] and ASSET_RULE_LINK not in transaction.asset['data']:
            return

        link = transaction.asset['data']['link']
        tx_to_link = bigchain.get_transaction(link)
        
        if tx_to_link and not hasattr(tx_to_link, 'metadata'):
            raise ValidationError(cant_link_error)
        
        if tx_to_link.metadata is None or METADATA_RULE_CAN_LINK not in tx_to_link.metadata:
            raise ValidationError(cant_link_error)

        can_link = tx_to_link.metadata[METADATA_RULE_CAN_LINK]
        wallet_tx = bigchain.get_owned_ids(public_key)
        wallet_tx_ids = [tx.txid for tx in wallet_tx]
        wallet_tx_assets = bigchain.get_assets(wallet_tx_ids)

        if wallet_tx_assets:
            role_asset_tx = [asset for asset in wallet_tx_assets if asset['data']['link'] and\
             asset['data']['link'] == can_link]

        if not role_asset_tx:
            raise ValidationError(cant_link_error)

        return

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

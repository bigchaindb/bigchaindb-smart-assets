import logging

from bigchaindb.common.exceptions import ValidationError
from bigchaindb.consensus import BaseConsensusRules
from bigchaindb.models import Transaction

from bigchaindb_smart_assets.policy import PolicyParser

ASSET_RULE_POLICY = 'policy'
ASSET_RULE_ROLE = 'role'
ASSET_RULE_LINK = 'link'
METADATA_RULE_CAN_LINK = 'canLink'

logger = logging.getLogger(__name__)

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
        logger.info('Validating link')
        public_key = transaction.inputs[0].owners_before[0]
        logger.info('Owner: %s', public_key)

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
        logger.info('Link: %s', link)
        tx_to_link = bigchain.get_transaction(link)

        if not tx_to_link:
            raise ValidationError('Transaction to link not found {}'
                                    .format(link))

        logger.info('Link Transaction: %s', tx_to_link.id)

        if tx_to_link and not hasattr(tx_to_link, 'metadata'):
            raise ValidationError('Metadata not found in transaction {}'
                                    .format(tx_to_link))

        if tx_to_link.metadata is None or METADATA_RULE_CAN_LINK not in tx_to_link.metadata:
            raise ValidationError('canLink not found in metadata of transaction {}'
                                    .format(tx_to_link))

        can_link = tx_to_link.metadata[METADATA_RULE_CAN_LINK]
        logger.info('Can link: %s', can_link)

        if isinstance(can_link, list):
            logger.info('canLink is a list, looking up for public key of owner')
            if public_key in can_link:
                logger.info('Link valid: public key found in canLink')
                return
            else:
                raise ValidationError(cant_link_error)
        elif isinstance(can_link, str):
            logger.info('canLink is a string, looking up assets in owner wallet')
            wallet_tx = bigchain.get_owned_ids(public_key)
            wallet_tx_ids = [tx.txid for tx in wallet_tx]

            for asset_id in wallet_tx_ids:
                asset = bigchain.get_transaction(asset_id).asset
                if asset and asset['data'] and ASSET_RULE_LINK in asset['data']:
                    if asset['data']['link'] == can_link:
                        logger.info('Link valid: asset link is equal to canLink')
                        break
                else:
                    continue
            else:
                raise ValidationError(cant_link_error)
        else:
            raise ValidationError('canLink is not valid')

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

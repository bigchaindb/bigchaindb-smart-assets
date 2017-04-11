from bigchaindb.common.exceptions import ValidationError
from bigchaindb.consensus import BaseConsensusRules
from bigchaindb.models import Transaction

ASSET_TYPE_MIX = 'mix'
ASSET_TYPE_PURE = 'pure'
ASSET_TYPE_COMPOSITION = 'composition'

ASSET_TYPES = [
    ASSET_TYPE_MIX,
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
        elif asset_type == ASSET_TYPE_MIX:
            return AssetCompositionConsensusRules\
                .validate_mix(bigchain, transaction, input_txs)
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
    def validate_mix(bigchain, transaction, input_txs):
        if transaction.operation == Transaction.TRANSFER:
            pass
        return transaction

    @staticmethod
    def validate_composition(bigchain, transaction, input_txs):
        import re

        asset = AssetCompositionConsensusRules.resolve_asset(bigchain, transaction, input_txs)[0]['data']
        if 'policy' in asset:
            policies = asset['policy']
            if not isinstance(policies, list):
                raise ValidationError('policy must be a list')
            for policy in policies:
                if 'condition' not in policy:
                    raise ValidationError('policy item must contain a condition')
                if 'rule' not in policy:
                    raise ValidationError('policy item must contain a rule')

                def parse_policy(condition_or_rule):
                    if 'expr' not in condition_or_rule:
                        raise ValidationError('condition or rule must contain an expr')

                    locs = []
                    if 'locals' in condition_or_rule:
                        if not isinstance(condition_or_rule['locals'], list):
                            raise ValidationError('locals must be a list')
                        locs = condition_or_rule['locals']

                    expr = condition_or_rule['expr']
                    r = re.search('^(?P<subject>\S+)\s+(?P<predicate>\S+)\s+(?P<object>\S+)$', expr)
                    if not r:
                        raise ValidationError('could not parse rule {}'.format(condition_or_rule))

                    subj, pred, obj = r.group('subject'), r.group('predicate'), r.group('object')

                    def parse_local(raw_query, raw_locs):
                        r_ = re.search('^%(?P<index>\d+)$', raw_query)
                        if r_:
                            index = int(r_.group('index'))
                            if index > len(raw_locs):
                                raise ValidationError("Query {} not found in locals".format(raw_query))
                            return raw_locs[index]
                        return raw_query

                    subj, obj = parse_local(subj, locs), parse_local(obj, locs)

                    return subj, pred, obj

                def map_predicates(pred, subj, obj):
                    if pred == 'EQ':
                        return subj == obj

                def eval_expr(raw_condition, transaction):
                    try:
                        subj = eval(raw_condition[0])
                        obj = eval(raw_condition[2])
                        return map_predicates(raw_condition[1], subj, obj)
                    except:
                        return False

                condition = eval_expr(parse_policy(policy['condition']), transaction)
                if condition is True:
                    rule = eval_expr(parse_policy(policy['rule']), transaction)
                    if not rule:
                        raise ValidationError('Rule {} evaluated to false'.format(policy['rule']))

        if transaction.operation == Transaction.TRANSFER:
            AssetCompositionConsensusRules \
                .validate_amount_conservation(transaction, input_txs)

        return transaction

    @staticmethod
    def validate_amount_conservation(transaction, input_txs):
        transaction.validate_amount(
            [input_tx.outputs[input_.fulfills.output]
             for (input_, input_tx, status)
             in input_txs if input_tx is not None])

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
                 in input_txs if input_tx is not None])
            return [bigchain.get_transaction(asset_id).asset for asset_id in asset_ids]

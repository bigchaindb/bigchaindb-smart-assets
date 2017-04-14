import re

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

                try:
                    condition_policy = PolicyParser(policy['condition']['expr'], policy['condition']['locals'])

                    if condition_policy.eval(transaction) is True:
                        rule_policy = PolicyParser(policy['rule']['expr'], policy['rule']['locals'])

                        if not rule_policy.eval(transaction):
                            raise ValidationError('Rule {} evaluated to false'.format(policy['rule']))

                except (AttributeError, KeyError) as e:
                    raise ValidationError('Wrong policy format: {}'.format(policy))

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


class PolicyParser():
    def __init__(self, expression, variables):

        if not expression:
            raise AttributeError('policy must contain an expr')
        self.expression = expression

        self.variables = []
        if variables:
            if not isinstance(variables, list):
                raise AttributeError('locals must be a list')
            self.variables = variables

        self.subj, self.pred, self.obj = self.parse()

    def parse(self):
        import ast
        self._parse_expression(self.expression)

    def _parse_expression(self, expression):
        r = re.search('^(?P<subject>\S+)\s+(?P<predicate>\S+)\s+(?P<object>\S+)$', expression)
        if not r:
            raise ValidationError('could not parse rule {}'.format(expression))

        subj, pred, obj = \
            r.group('subject'), \
            r.group('predicate'), \
            r.group('object')

        subj, obj = \
            PolicyParser.parse_local(subj, self.variables), \
            PolicyParser.parse_local(obj, self.variables)

        return subj, pred, obj

    def eval(self, transaction):
        # transaction object needed for eval
        try:
            # TODO: subsitute eval by `transaction.<attribute>.<subattribute>`
            subj_eval = eval(self.subj)
            obj_eval = eval(self.obj)
            return PolicyParser.map_predicates(subj_eval, self.pred, obj_eval)
        except:
            return False

    @staticmethod
    def parse_local(raw_query, raw_locs):
        r_ = re.search('^%(?P<index>\d+)$', raw_query)
        if r_:
            index = int(r_.group('index'))
            if index > len(raw_locs):
                raise ValidationError("Query {} not found in locals".format(raw_query))
            return raw_locs[index]
        return raw_query

    @staticmethod
    def map_predicates(subj, pred, obj):
        if pred == 'EQ':
            return subj == obj
        if pred == 'NEQ':
            return subj != obj
        if pred == 'LEQ':
            return subj <= obj
        if pred == 'LT':
            return subj < obj


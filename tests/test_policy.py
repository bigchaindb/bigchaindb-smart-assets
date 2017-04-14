import pytest
from bigchaindb_consensus_composition.policy import PolicyParser


def print_lexer(_lexer):
    while True:
        tok = _lexer.token()
        if not tok:
            break
        print(tok, tok.type)


def test_policy_lexer_string():
    test_inputs = [
        'x = 3 * 4 + 5 * 6 AND 8'
        'AND/6*4',
        'BANDANA',
        'x == djsjh + AND + d > d >= 4',
        'transaction.metadata["data"] == "test" OR 4 + 3',
        "transaction.inputs[0].public_keys['value'] == 'somekey'"
    ]

    for test_input in test_inputs:
        parser = PolicyParser()
        parser.input(test_input)
        print_lexer(parser)


@pytest.mark.bdb
@pytest.mark.usefixtures('inputs')
def test_policy_lexer_transaction(b, user_pk):
    test_inputs = [
        "transaction.inputs[0].owners_before == 'somekey'"
    ]

    transaction = b.get_transaction(b.get_owned_ids(user_pk)[0].txid)

    for test_input in test_inputs:
        lexer = PolicyParser(transaction=transaction)
        lexer.input(test_input)
        print_lexer(lexer)


def test_policy_grammar_string():
    test_inputs = [
        (' "3" * (4 + 5 * 6) == 102', True),
        (' 3 * (4 + 5 * 6) > 100', True),
        (' 3 * (4 + 5 * 6) < 103', True),
        ('"TEST" == "TEST"', True),
        ('1 == 1 AND 3 == 3', True),
        ('1 == 1 AND 3 == "DUMMY"', False),
        ('1 == 1 OR 3 == "DUMMY"', True),
        ('LEN([2, 2]) == 1', True)
    ]

    for test_input in test_inputs:
        parser = PolicyParser()
        result = parser.parse(test_input[0], lexer=parser.lexer)
        assert result == test_input[1]


@pytest.mark.bdb
@pytest.mark.usefixtures('inputs')
def test_policy_grammar_transaction(b, user_pk):
    test_inputs = [
        ('transaction.operation == "CREATE"', True),
        ('transaction.outputs[0].public_keys[0] == "{}"'.format(user_pk), True)
    ]

    transaction = b.get_transaction(b.get_owned_ids(user_pk)[0].txid)

    for test_input in test_inputs:
        parser = PolicyParser(transaction=transaction)
        result = parser.parse(test_input[0], lexer=parser.lexer)
        assert result == test_input[1]

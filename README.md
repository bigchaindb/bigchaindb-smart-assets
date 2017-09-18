# Smart Assets

## Installation

### Clone
Clone or fork this repo

```bash
git clone git@github.com:ascribe/bigchaindb-smart-assets.git
```

and

```bash
cd bigchaindb-smart-assets
```

now we need a specific branch of bigchaindb `kyber-master`, hence clone

```bash
git clone git@github.com:bigchaindb/bigchaindb.git
cd bigchaindb
git checkout kyber-master
cd ..
```

## Quickstart with Docker (Windows, OSX, lazy Linux)

> Supports BigchainDB Server v1.0

### Prequisites

You must have `docker`, `docker-compose` (and `make`) installed.
These versions or higher should work:

- `docker`: `v1.13.0`
- `docker-compose`: `v1.7.1`

### Make or docker-compose

To spin up the services, simple run the make command, which will orchestrate `docker-compose`

```bash
make
```

This might take a few minutes, perfect moment for a :coffee:!

Once docker-compose has built and launched all services, have a look:

```bash
docker-compose ps
```

```
            Name                          Command               State                        Ports                       
------------------------------------------------------------------------------------------------------------------------
bigchaindbsmartassets_bdb_1   bigchaindb start                 Up      0.0.0.0:49984->9984/tcp                 │
bigchaindbsmartassets_mdb_1   docker-entrypoint.sh mongo ...   Up      0.0.0.0:27017->27017/tcp  
```

If you already built the images and want to `restart`:

```bash
make restart
```

Stop (and remove) the containers with

```bash
make stop
```

### Launch docker-compose services manually

No make? Launch the services manually:


```bash
docker-compose up -d mdb
docker-compose up -d bdb
```

## Intro


### Asset Policy
Asset policies allows to compose rules for transactions at the asset level.
Each asset can hence define a policy that will be inherited by every subsequent transaction that involves the asset.

### Asset Permissions

## Transaction Model

This section acts as a reference for the transaction model in BigchainDB.
The full specification can be found [here](https://docs.bigchaindb.com/projects/server/en/latest/data-models/transaction-model.html)

Transactions are linked together in a transaction chain using inputs and outputs.
To start a transaction chain, one needs to create an asset using a `CREATE` transaction.

The `CREATE` transaction will define the asset, see the section below.
For this specific plugin a `TRANSFER` transaction will always execute the rules that you defined in the asset upon `CREATE`. 

The transaction model takes the following form:

```json

transaction = {
    "id": "<hash of transaction, excluding signatures>",
    "version": "<version number of the transaction model>",
    "inputs": ["<list of inputs, see below>"],
    "outputs": ["<list of outputsm see below>"],
    "operation": "<string: 'CREATE' or 'TRANSFER'>",
    "asset": "<digital asset description (explained in the next section)>",
    "metadata": "<any JSON document to store per-transaction information>"
}
```

Inside of a transaction there are lists of inputs and outputs:

```json
input = {
    "owners_before": ["<list of public keys>"],
    "fulfillment": "crypto-conditions fulfillment URI",
    "fulfills": {
        "output": "<integer pointing to an output index>",
        "txid": "<input transaction ID>"
    }
}

output = {
    "condition": {
        "details": "<condition object>",
        "uri": "<string>"
    },
    "public_keys": ["<new owner public key>"],
    "amount": "<int>"
}

```
## Asset Policy

The asset model is explained in the 
[BigchainDB documentation](https://docs.bigchaindb.com/projects/server/en/latest/data-models/asset-model.html).

The `SmartAssetPlugin` allows to define a specific asset that will provide additional consensus checks 
(ie. when a transaction gets accepted to the chain).

```json

asset = {
    "policy": [
        {
            "condition": "<expression:if>",
            "rule": "<expression:check>"
        },
        {
            "condition": "<expression:if>",
            "rule": "<expression:check>"
        },
        ...
    ]
}

```

### Rules-based API

The assets encode all the rules, and read like a recipe.
This means that each rule needs to be checked under a specific condition (ie. a step in the recipe).

In technical terms, the recipe is made up as follows:

```
IF <expression1>
CHECK <expression2>
...
IF <expressionN>
CHECK <expressionN+1>
```

Both `condition` and `rule` use the same expression language, see below.

### Conditions

The `condition` field defines in which state or under which condition a rule needs to be applied.
Some example conditions could be:
 - a certain stage of the supply chain
 - a specific actor (or set of actors) in the supply chain

### Rules

The `rule` field specifies how the transaction needs to be structured to become valid.
Some example rules could be:
- Fixing the amount of inputs and outputs
- Fixing the actors that can receive or send a transaction
- Checking specific Quality Assurance (QA) targets

### Language

There are many possible languages to implement the above conditions and rules. 
For this prototype we chose to limit the functional scope in order not to deal 
with too many complexity vs security constraints.

The language exists of simple arithemetic and boolean logic:

```json
{ 
    "condition": "3 * (4 + 5 * 6) > 100 AND ('TEST' == 'TEST' OR 'DUMMY' == 'TEST')"
}
```
The compiler parses the integers and strings and then applies the precedence rules and logic, yielding `True`.

The `transaction` object is available during compilation and execution, which allows to verify fields in the current transaction:

```json
{ 
    "condition": "transaction.metadata['state'] == 'INIT' or transaction.operation == 'CREATE'"
}
```

Notice that the content of a transaction can be used inside both conditions and rules.
The values need to be resolved first, hence they are put in the `locals` field and referred to by index: `%<index>`.

Strings are injected by surrounding with single quotes (`'`) if the JSON format is using double quotes (and vice versa).

#### Keywords

- Variables:
  - Integers
  - Strings: denoted by single `'<string>'` or double `"<string>"` quotes
  - Arrays: denoted by square brackets: `[<item1>, ..., <itemN> ]`
- Precedence:
  - Regular precedence for `*`, `/`, `+`, `-`
  - Round brackets to enforce precedence
- Logic:
  - `AND`, `OR`
- Comparison: 
  - `==`: Equality of strings and integers
  - `!=`: Not-equal
  - `<=`: Less than or equal to  
  - `<`: Less than
  - `>=`: More than or equal to   
  - `>`: More than
- Aggregates/Lists:
  - `LEN(<list>)`: The length of a list
  - `SUM(<list of int/double>)`: The sum of a list of values
  - `AMOUNT(<list of outputs>)`: Amount at transaction output `sum([output.amount for output in outputs])`  
- TODO's:
  - `IN`: check if an item belongs to a list
  - `@`: reference another transaction or an input

### Examples

#### Logic & Predicates:

##### Check the transaction state or the operation

```json
{ 
    "condition": "transaction.metadata['state'] == 'INIT'"
}
```

```json
{ 
    "condition": "transaction.operation == 'CREATE'"
}
```


##### Transaction can only be given to specific users

```json
{ 
    "condition": "transaction.inputs[0].owners_before[0] == 'carly'",
    "rule": "transaction.outputs[0].public_keys[0] == 'albi' OR transaction.outputs[0].public_keys[0] == 'bruce'"
}
```

#### Aggregates/Lists:

```json
{
    "condition": "SUM([1, 3, 4]) > 5"
}
```


##### Check the amount at the outputs

```json
{ 
    "condition": "transaction.metadata['state'] == 'INIT'",
    "rule": "AMOUNT(transaction.outputs) == 1"
}
```

##### Check the number of inputs, outputs, public_keys

```json
{ 
    "condition": "LEN(transaction.inputs) == 1",
    "rule": "LEN(transaction.outputs) == 1 AND LEN(transactions.outputs[0].public_keys) == 2"
}
```

##### A more elaborate mixing recipe example

```python
asset={
    'policy': [
        {
            'condition':
                "transaction.metadata['state'] == 'ORDER'",
            'rule':
                "LEN(transaction.outputs) == 1"
                " AND LEN(transaction.inputs) == 1"
                " AND LEN(transaction.outputs[0].public_keys) == 1"
                " AND LEN(transaction.inputs[0].owners_before) == 1"
                " AND transaction.outputs[0].public_keys[0] == '{}'"
                    .format(albi_pub),
        },
        {
            'condition':
                "transaction.metadata['state'] == 'ORDER_READY'",
            'rule':
                "AMOUNT(transaction.outputs) == 1000"
                " AND transaction.metadata['concentration'] > 95"
                " AND transaction.inputs[0].owners_before[0] == '{}'"
                " AND ( transaction.outputs[0].public_keys[0] == '{}'"
                " OR transaction.outputs[0].public_keys[0] == '{}')"
                    .format(albi_pub, albi_pub, bruce_pub)
        },
        {
            'condition':
                "transaction.metadata['state'] == 'MIX_READY'",
            'rule':
                "AMOUNT(transaction.outputs) >= 4000"
                " AND transaction.metadata['concentration'] > 20"
                " AND ( transaction.inputs[0].owners_before[0] == '{}'"
                " OR transaction.inputs[0].owners_before[0] == '{}')"
                " AND transaction.outputs[0].public_keys[0] == '{}'"
                    .format(bruce_pub, carly_pub, carly_pub)
        },

    ]
},
```

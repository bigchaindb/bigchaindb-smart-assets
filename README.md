# Asset Composition: Conditions and Rules

## Intro

This consensus plugin allows to compose rules for transactions at the asset level.
Each asset can hence define a policy that will be inherited by every subsequent transaction that involves the asset.

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
## Asset Composition

The asset model is explained in the 
[BigchainDB documentation](https://docs.bigchaindb.com/projects/server/en/latest/data-models/asset-model.html).

The `AssetCompositionConsensusPlugin` allows to define a specific asset that will provide additional consensus checks 
(ie. when a transaction gets accepted to the chain).

```json

asset = {
    "type": "composition",
    "policy": [
        {
            "condition": {
                "expr": "<expression>",
                "locals": ["<variables to be evaluated>"]
            },
            "rule": {
                "expr": "<expression>",
                "locals": ["<variables to be evaluated>"]
            }
        }
    ]
}

```

## Rules-based API

The assets encode all the rules, and read like a recipe.
This means that each rule needs to be checked under a specific condition (ie. a step in the recipe).

In technical terms, the recipe is made up as follows:

```
IF <condition1>
CHECK <rule1>
...
IF <conditionN>
CHECK <ruleN>
```

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
For this prototype we chose to limit the functional scope in order not to deal with too many complexity vs security constraints.

The language exists of triples `(subject, predicate, object)` and can be parametrized in `subject` and `object` through the use of locals.
An example expression could be:

```json
{ 
    "expr": "%0 EQ 'INIT'",
    "locals": ["transaction.metadata['state']"]
}
```
Which would be interpreted by the consensus engine as:

_The `state` (encoded in `transaction.metadata`) needs to be equal (`EQ`) to `'INIT'`_

Notice that the content of a transaction can be used inside of the conditions and rules.
The values need to be resolved first, hence they are put in the `locals` field and referred to by index: `%<index>`.

Strings are injected by surrounding with single quotes (`'`) if the JSON format is using double quotes (and vice versa).

#### Keywords

- Logic:
  - `AND`, `OR`, `NOT` 
- Predicates: 
  - `EQ`: Equality of strings, integers and doubles (`==`)
  - `NEQ`: Not-equal to (`!=`) 
  - `LEQ`: Less than or equal to (`<=`)  
  - `LT`: Less than (`<`)
- Aggregates/Lists:
  - `LEN(<list>)`: The length of a list
  - `SUM(<list of int/double>)`: The sum of a list of values
  - `<object> IN <list>`: Boolean function to check if an element is in a list  

### Examples

#### Logic & Predicates:

##### Check the transaction state or the operation

```json
{ 
    "expr": "%0 EQ 'INIT' OR %1 EQ 'CREATE'",
    "locals": ["transaction.metadata['state']", "transaction.operation"]
}
```

#### Aggregates/Lists:

##### Same amount of inputs and outputs

```json
{ 
    "expr": "LEN(%0) EQ LEN(%1)",
    "locals": ["transaction.inputs", "transaction.outputs"]
}
```

##### Transaction can only be given to specific users

```json
{ 
    "expr": "%0 IN [%1, %2]",
    "locals": ["transaction.outputs[0].public_keys[0]", "<some_public_key>", "<another_public_key>"]
}
```


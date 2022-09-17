
name_values = (
    [{'name': 'a', 'value': 1},
     {'name': 'b', 'value': 2},
     {'name': 'c', 'value': 3},],
    [{'name': 'a', 'value': 11},
     {'name': 'b', 'value': 12},
     {'name': 'c', 'value': 13},
     {'name': 'd', 'value': 14},
     {'name': 'v', 'value': 15},],
)

nested_values = [
    [{'a': dict(nm), 'b': nm['value']*2}
        for nm in name_value]
    for name_value in name_values
]


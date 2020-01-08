"""Util for making parameterized effects

Borrowed from dliu's merkaba project
"""

import itertools
import logging
import random
import enum
from typing import Any, Dict, Union


class Param(object):
    """Defines the schema for a parameter.
    """
    def __init__(self, name):
        self.name = name

    def random(self):
        raise NotImplementedError

    def to_jsonable(self):
        return {
            "name": self.name,
            "type": self.__class__.__name__,
        }

    def value_to_jsonable(self, value):
        raise NotImplementedError

    def value_from_jsonable(self, jsonable):
        raise NotImplementedError


class BoolParam(Param):
    def random(self):
        return random.choice([True, False])

    def value_to_jsonable(self, value):
        return bool(value)

    def value_from_jsonable(self, jsonable):
        return bool(jsonable)


class IntParam(Param):
    def __init__(self, name, min=0, max=10):
        super().__init__(name)
        self.min = min
        self.max = max

    def random(self):
        return random.randint(self.min, self.max)

    def to_jsonable(self):
        d = super().to_jsonable()
        d.update({
            "min": self.min,
            "max": self.max,
        })
        return d

    def value_to_jsonable(self, value):
        return int(value)

    def value_from_jsonable(self, jsonable):
        return int(jsonable)


class FloatParam(Param):
    def __init__(self, name, min=0, max=1):
        super().__init__(name)
        self.min = min
        self.max = max

    def random(self):
        return random.uniform(self.min, self.max)

    def to_jsonable(self):
        d = super().to_jsonable()
        d.update({
            "min": self.min,
            "max": self.max,
        })
        return d

    def value_to_jsonable(self, value):
        return float(value)

    def value_from_jsonable(self, jsonable):
        return float(jsonable)


class SelectParam(Param):
    def __init__(self, name, choices):
        super().__init__(name)
        self.choices = list(choices)

    def random(self):
        return random.choice(self.choices)

    def to_jsonable(self):
        d = super().to_jsonable()
        d.update({
            "choices": self.choices,
        })
        return d

    def value_to_jsonable(self, value: str):
        return value

    def value_from_jsonable(self, jsonable: str):
        return jsonable


class EnumParam(Param):
    def __init__(self, name, enum_class):
        super().__init__(name)
        self.enum_class = enum_class

    def random(self):
        return random.choice(self.enum_class.__members__.values())

    def to_jsonable(self):
        d = super().to_jsonable()
        d.update({
            "choices": [c.name for c in self.enum_class.__members__.values()],
        })
        return d

    def value_to_jsonable(self, value: enum.Enum):
        return value.name

    def value_from_jsonable(self, jsonable: str):
        return self.enum_class[jsonable]


class MultiParam(Param):
    def __init__(self, name, elem_param, min_instances, max_instances):
        super().__init__(name)
        self.elem_param = elem_param
        self.min_instances = min_instances
        self.max_instances = max_instances

    def random(self):
        return [self.elem_param.random() for i in range(random.randint(self.min_instances, self.max_instances))]

    def to_jsonable(self):
        d = super().to_jsonable()
        d.update({
            "elem_param": self.elem_param.to_jsonable()
        })
        return d

    def value_to_jsonable(self, value):
        return [self.elem_param.value_to_jsonable(elem_value) for elem_value in value]

    def value_from_jsonable(self, jsonable):
        return [self.elem_param.value_from_jsonable(elem_jsonable) for elem_jsonable in jsonable]


#################################

SUB_SEP = "."


def prefix_keys(map_of_map):
    """
    >>> prefix_keys({'pre': {'b': 1, 'c': None, 'd': True, 'e': 'str'}})
    {'pre.b': 1, 'pre.c': None, 'pre.d': True, 'pre.e': 'str'}
    """
    return {prefix + SUB_SEP + k: v
            for (prefix, map) in map_of_map.items()
            for (k, v) in map.items()}


def unprefix_keys(map):
    """
    >>> unprefix_keys({'pre.b': 1})
    ({'pre': {'b': 1}}, {})
    >>> unprefix_keys({'pre.b.c': 1, 'pre.c': None, 'pre.d': True, 'pre.e': 'str'})
    ({'pre': {'b.c': 1, 'c': None, 'd': True, 'e': 'str'}}, {})
    >>> unprefix_keys({'pre.b.c': 1, 'noprefix': 'test'})
    ({'pre': {'b.c': 1}}, {'noprefix': 'test'})
    """
    prefixed, noprefix = {}, {}
    prefixed_items = []
    for k, v in map.items():
        if SUB_SEP in k:
            prefixed_items.append((k, v))
        else:
            noprefix[k] = v

    for prefix, g in itertools.groupby(
            sorted(prefixed_items), lambda k_v: k_v[0].split(SUB_SEP, 1)[0]):
        prefixed[prefix] = {k.split(SUB_SEP, 1)[1]: v for (k, v) in g}
    return prefixed, noprefix


class ParamProvider(object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._param_schema = {}
        self._param_vals = {}
        self._trigger_schema = {}
        self._triggers_active = set()
        self._subproviders = {}

    #
    # Subproviders

    def add_param_subprovider(self, name: str, subprovider: 'ParamProvider') -> None:
        if subprovider is None:
            self.del_param_subprovider(name)
        else:
            self._subproviders[name] = subprovider

    def del_param_subprovider(self, name: str) -> None:
        if name in self._subproviders:
            del self._subproviders[name]

    # def param_subproviders(self):
    #     return self._subproviders

    #
    # Triggers

    def activate_trigger(self, fullname, cur_path=()):
        if SUB_SEP in fullname:
            prefix, name = fullname.split(SUB_SEP, 1)
            self._subproviders[prefix].activate_trigger(name, cur_path + (prefix,))
        else:
            self._triggers_active.add(fullname)

    def remove_trigger(self, trigger_name: str) -> None:
        assert SUB_SEP not in trigger_name, "Subprovider function not yet implemented"

        self._triggers_active.remove(trigger_name)
        del self._trigger_schema[trigger_name]

    def read_and_clear_trigger(self, trigger_name: str) -> bool:
        assert SUB_SEP not in trigger_name, "Subprovider function not yet implemented"

        self._trigger_schema[trigger_name] = None
        if trigger_name in self._triggers_active:
            self._triggers_active.remove(trigger_name)
            return True
        return False

    #
    # Params

    def add_param(self, param: Param, val: Any = None) -> None:
        assert param.name not in self._param_schema, "Duplicate param " + param.name
        self._param_schema[param.name] = param
        self._param_vals[param.name] = val if val is not None else param.random()

    def remove_param(self, name: str) -> None:
        if name in self._param_schema:
            del self._param_schema[name]
        if name in self._param_vals:
            del self._param_vals[name]

    def param_schema(self, param_name: str) -> Union[None, Param]:
        assert SUB_SEP not in param_name, "Subprovider function not yet implemented"
        return self._param_schema.get(param_name, None)

    #
    # Param values

    def param(self, param_name: str) -> Any:
        assert SUB_SEP not in param_name, "Subprovider function not yet implemented"
        return self._param_vals[param_name]

    def set_param(self, param_name: str, param_val_jsonable: Any, trigger_onchange=True) -> None:
        assert SUB_SEP not in param_name, "Subprovider function not yet implemented"
        val = self._param_schema[param_name].value_from_jsonable(param_val_jsonable)
        old_val = self._param_vals[param_name]
        self._param_vals[param_name] = val
        if trigger_onchange and val != old_val:
            self.on_param_change(param_name, val, old_val)

    def on_param_change(self, param_name: str, param_val: Any, old_val: Any) -> None:
        pass

    #
    # Randomization

    def randomize_all(self, subproviders=True, cur_path=()) -> None:
        i = 0
        while True:
            i += 1

            for param in self._param_schema.values():
                try:
                    self._param_vals[param.name] = param.random()
                except:
                    logging.exception("Couldn't randomize %s %s", cur_path, param.name)

            if subproviders:
                for k, subprovider in self._subproviders.items():
                    subprovider.randomize_all(True, cur_path + (k,))

            if self.can_accept_randomization():
                break

            if i >= 50 and i % 50 == 0:
                logging.warning('Randomizing %s (%s) is taking more than %d attempts',
                                cur_path, self.__class__.__name__, i)

        if i > 1:
            logging.info('Randomizing %s (%s) took %d attempts',
                         cur_path, self.__class__.__name__, i)

    def randomize(self, param_name: str) -> None:
        assert SUB_SEP not in param_name, "Subprovider function not yet implemented"
        self._param_vals[param_name] = self._param_schema[param_name].random()

    # TODO: How can we make meta-parameters (e.g. randomization min and max for each param) updateable?
    # TODO: Params should be able to be controlled by e.g. sound level, time (oscillate between), etc.

    def can_accept_randomization(self):
        return True

    #
    # Serialization/deserialization

    def param_schema_jsonable(self) -> Dict[str, Any]:
        d = prefix_keys({k: v.param_schema_jsonable()
                              for (k,v) in self._subproviders.items()})
        d.update({p.name: p.to_jsonable() for p in self._param_schema.values()})
        return d

    def param_vals_jsonable(self) -> Dict[str, Any]:
        d = prefix_keys({k: v.param_vals_jsonable()
                              for (k,v) in self._subproviders.items()})
        d.update({p.name: p.value_to_jsonable(self._param_vals.get(p.name))
                  for p in self._param_schema.values()})
        return d

    def trigger_schema(self):
        l = [k + SUB_SEP + vt
             for k, v in self._subproviders.items()
             for vt in v.trigger_schema()]
        l.extend(self._trigger_schema)
        return sorted(l)

    def set_params_from_jsonable(self, jsonable: Dict[str, Any], cur_path=()) -> None:
        prefixed, noprefix = unprefix_keys(jsonable)

        for k, v in noprefix.items():
            try:
                self.set_param(k, v)
            except:
                logging.exception("Could not set param %s %s to %s", cur_path, k, v)
                raise

        for prefix, map in prefixed.items():
            try:
                self._subproviders[prefix].set_params_from_jsonable(map, cur_path + (prefix,))
            except:
                logging.exception("Could not set %s %s %s", cur_path, prefix, map)
                raise


#################################

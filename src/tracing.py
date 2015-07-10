from abc import ABCMeta
from six import with_metaclass
from wrapt import ObjectProxy
from collections.abc import MutableSequence

class TraceElement(with_metaclass(ABCMeta, object)):
    pass

class Invocation(TraceElement):
    def __init__(self, key, target):
        self.key = key
        self.target = target
        self.dependencies = []
        self.parent = None
        self.orphans = []

    def __repr__(self):
        (rule, source) = self.key
        return '{ "source": "%s", "transformedBy": "%s", "dependencies": %s, "target": %s, "orphans": %s }' % \
            (source.__class__.__name__, type(rule).__name__, self.dependencies, self.target, self.orphans)

class Recall(TraceElement):
    def __init__(self, invocation):
        self.invocation = invocation
        self.parent = None

    def __repr__(self):
        (rule, source) = self.invocation.key
        return '{ "recalled": { "source": "%s", "transformedBy": "%s" } }' % \
            (source.__class__.__name__, type(rule).__name__)

class Proxy(ObjectProxy):
    def __init__(self, obj, tx=None):
        super().__init__(obj)
        self._self_tx = tx

    def __call__(self, *args, **kwargs):
        return self.__wrapped__(*args, **kwargs)

    def __getattr__(self, name):
        value = super().__getattr__(name)
        if value is not None:
            value = self.proxify(value)
        return value

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if not name.startswith("_self"):
            self.retain(value)

    def is_primitive(self, value):
        return isinstance(value, (int, str, float, complex, bool))

    def proxify(self, value):
        value_type = type(value)
        if not self.is_primitive(value_type):
            if value_type == list and value_type != str:
                value = ListProxy(value, self._self_tx)
            else:
                value = Proxy(value, self._self_tx)
            # TODO handle slices
        return value

    def retain(self, value):
        if not self.is_primitive(value):
            if not self._self_tx.reverse(value):
                if hasattr(self._self_tx, 'trace'):
                    self._self_tx.get_level()[-1].orphans.append(value)

class ListProxy(Proxy, MutableSequence):
    def append(self, value):
        self.__wrapped__.append(value)
        if hasattr(self._self_tx, 'trace'):
            self.retain(value)

    def __setitem__(self, name, value):
        super().__setitem__(name, value)
        self.retain(value)

    def insert(self, idx, value):
        super().insert(idx, value)
        self.retain(value)

    def __getitem__(self, idx):
        item = super().__getitem__(idx)
        if item is not None:
            item = self.proxify(item)
            return item

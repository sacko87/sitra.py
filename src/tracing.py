from abc import ABCMeta
from six import with_metaclass
from wrapt import ObjectProxy
import itertools

try:
    from collections import (MutableSequence, Sequence)
except ImportError:
    # moved in 3.3
    from collections.abc import (MutableSequence, Sequence)

class TraceElement(with_metaclass(ABCMeta, object)):
    def __init__(self):
        self.parent = None

class Invocation(TraceElement):
    def __init__(self, key, target):
        super(Invocation, self).__init__()
        self.key = key
        self.target = target
        self.dependencies = []
        self.orphans = []

    @property
    def targets(self):
        return itertools.chain(
            [ self.target ] if not isinstance(self.target, Sequence)
                            else self.target,
            self.orphans)

class Recall(TraceElement):
    def __init__(self, invocation):
        self.invocation = invocation

class WrapperWrapper(ObjectProxy):
    _cache = {}

    def __init__(self, wrapped, tx):
        super(WrapperWrapper, self).__init__(wrapped)
        self._self_tx = tx

    def wrap(self, value):
        try:
            exclude = (int, float, long, complex, bool, str, type(None))
        except NameError:
            exclude = (int, float, complex, bool, str, type(None))

        if id(value) in WrapperWrapper._cache:
            return WrapperWrapper._cache[id(value)]

        # if it isn't already a proxy
        if not isinstance(value, WrapperWrapper) and not isinstance(value, exclude):
            # wrap it
            if isinstance(value, MutableSequence):
                value = MutableSequenceWrapper(value, self._self_tx)
            elif isinstance(value, Sequence):
                value = SequenceWrapper(value, self._self_tx)
            else:
                value = ObjectWrapper(value, self._self_tx)

            WrapperWrapper._cache[id(value)] = value

        return value

    def orphan(self, value):
        try:
            exclude = (int, float, long, complex, bool, str, type(None))
        except NameError:
            exclude = (int, float, complex, bool, str, type(None))

        if isinstance(value, exclude):
            return

        try:
            # have we seen this before? i do need to check for primitives here
            # i don't really care about int, str, bool, float, etc.
            next(trace for trace in self._self_tx.trace if value in trace.targets)
        except StopIteration:
            # we haven't found it, so keep it as an orphan
            try:
                self._self_tx.stack[-1].orphans.append(value)
            except IndexError:
                raise RuntimeError("An orphan has been created, it will not be " +
                    "tracked, as it isn't within a transformation.")


class ObjectWrapper(WrapperWrapper):
    def __getattribute__(self, name):
        # delegate to a the parent instance
        attr = super(ObjectWrapper, self).__getattribute__(name)

        # so we don't override proxy values
        if name.startswith('_self_') or name == "__wrapped__":
            return attr

        # we only care about instance variables
        try:
            if name in vars(self.__wrapped__):
                # wrap it
                attr = self.wrap(attr)
        except TypeError:
            pass # vars doesn't work on str

        return attr

    def __setattr__(self, name, value):
        # if not within the proxy and only for instance variables
        if not name.startswith('_self_'):
            try:
                if name in vars(self.__wrapped__):
                    # wrap if necessary
                    value = self.wrap(value)

                    # is this an orphan? save it.
                    self.orphan(value)
            except TypeError:
                pass # vars doesn't work on str

        # delegate
        return super(ObjectWrapper, self).__setattr__(name, value)

class SequenceWrapper(WrapperWrapper, Sequence):
    def __getitem__(self, key):
        # get the item
        item = self.__wrapped__[key]

        # if it isn't already a proxy
        if not isinstance(item, ObjectProxy):
            # wrap it
            item = self.wrap(item)

        return item

    def __len__(self):
        return len(self.__wrapped__)

class MutableSequenceWrapper(SequenceWrapper, MutableSequence):
    def __getitem__(self, key):
        # get the item
        item = self.__wrapped__[key]

        # if it isn't already a proxy
        if not isinstance(item, ObjectProxy):
            # wrap it
            item = self.wrap(item)

            # set it locally
            self[key] = item

        return item

    def __setitem__(self, key, value):
        # wrap if necessary
        value = self.wrap(value)

        # is this an orphan? save it.
        self.orphan(value)

        # delegate
        self.__wrapped__[key] = value

    def __delitem__(self, key):
        del self.__wrapped__[key]

    def insert(self, index, value):
        # wrap if necessary
        value = self.wrap(value)

        # is this an orphan? save it.
        self.orphan(value)

        # delegate
        self.__wrapped__.insert(index, value)

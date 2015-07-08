from abc import (ABCMeta, abstractmethod)
from six import with_metaclass
from sitra.tracing import (Invocation, Recall, Proxy)

class Transformer(with_metaclass(ABCMeta, object)):
    @abstractmethod
    def transform(self, source, rule=None):
        pass

    def transformAll(self, sources, rule=None):
        results = []
        for source in sources:
            target = self.transform(source, rule)
            if target is not None:
                results.append(target)
        return results

    @abstractmethod
    def recall(self, key):
        pass

    @abstractmethod
    def remember(self, key, target):
        pass

    @abstractmethod
    def forget(self, key):
        pass

    @abstractmethod
    def reverse(self, target):
        pass

class Rule(with_metaclass(ABCMeta, object)):
    @abstractmethod
    def check(self, source):
        """Check to see if this rule is valid for this source."""
        pass

    @abstractmethod
    def build(self, source):
        """Return a target model object."""
        pass

    def set_properties(self, target, source, transformer):
        pass

class SimpleTransformer(Transformer):
    def __init__(self):
        self.rules = []
        self.cache = {}

    def transform(self, source, rule=None):
        dynamic = rule is None
        if dynamic:
            for rule in self.rules:
                check = rule.check(source)
                if check != False:
                    break
            else:
                return None
        else:
            check = rule.check(source)

        key = (rule, source)
        hit = self.recall(key)
        if hit is not None:
            return Proxy(hit, self)

        target = rule.build(source, self)
        if target is not None:
            target = Proxy(target, self)
            self.remember(key, target)
            rule.set_properties(target, source, self)
            self.forget(key)

        return target

    def recall(self, key):
        return self.get_cache().get(key)

    def remember(self, key, target):
        self.get_cache()[key] = target

    def forget(self, key):
        pass

    def reverse(self, target):
        for (_, s), v in self.get_cache().items():
            if target in v:
                return s

        return None

    def get_cache(self):
        return self.cache

class SimpleTraceableTransformer(SimpleTransformer):
    def __init__(self):
        super(SimpleTraceableTransformer, self).__init__()
        self.level = []
        self.trace = []

    def recall(self, key):
        try:
            (target, trace) = super(SimpleTraceableTransformer, self).recall(key)
            recalled = Recall(trace)
            try:
              level = self.get_level()[-1]
              level.dependencies.append(recalled)
              recalled.parent = level
            except IndexError:
              # ignore when using the eAllContent approach
              # or indeed when there is no leveling
              pass
            return target
        except TypeError:
            return None

    def remember(self, key, target):
        trace = Invocation(key, target)
        super(SimpleTraceableTransformer, self).remember(key, (target, trace))
        if not self.get_level():
            self.trace.append(trace)
        else:
            try:
                level = self.get_level()[-1]
                level.dependencies.append(trace)
                trace.parent = level
            except IndexError:
              # ignore when using the eAllContent approach
              # or indeed when there is no leveling
              pass
        self.get_level().append(trace)

    def forget(self, key):
        self.get_level().pop()

    def reverse(self, target):
        for (_, s), (_, t) in self.get_cache().items():
            if t.target == target:
                return s
        return None

    def get_trace(self):
        return self.trace

    def get_level(self):
        return self.level

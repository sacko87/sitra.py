from abc import (ABCMeta, abstractmethod)
from six import with_metaclass
from sitra.tracing import (Invocation, Recall)

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

        if check:
            key = (rule, source)
            hit = self.recall(key)
            if hit is not None:
                return hit

            target = rule.build(source, self)
            if target is not None:
                self.remember(key, target)
                try:
                    rule.set_properties(target, source, self)
                finally:
                    self.forget(key)

        return target


    def recall(self, key):
        return self.cache.get(key, None)

    def remember(self, key, target):
        self.cache[key] = target

    def forget(self, key):
        pass

    def reverse(self, target):
        for (_, s), t in self.cache.items():
            if(t == target):
                return s

        return None

class SimpleTraceableTransformer(SimpleTransformer):
    def __init__(self):
        super(SimpleTraceableTransformer, self).__init__()
        self.level = []
        self.trace = []

    def recall(self, key):
        trace = super(SimpleTraceableTransformer, self).recall(key)
        if trace is not None:
            recalled = Recall(trace)
            try:
                level = self.level[-1]
                level.dependencies.append(recalled)
                recalled.parent = level
            except IndexError:
                # ignore when using the eAllContent approach
                # or indeed when there is no leveling
                pass

            return trace.target

        return None

    def remember(self, key, target):
        trace = Invocation(key, target)
        self.trace.append(trace)
        super(SimpleTraceableTransformer, self).remember(key, trace)
        if len(self.level) > 0:
            try:
                level = self.level[-1]
                level.dependencies.append(trace)
                trace.parent = level
            except IndexError:
              # ignore when using the eAllContent approach
              # or indeed when there is no leveling
              pass
        self.level.append(trace)

    def forget(self, key):
        self.level.pop()

    def reverse(self, target):
        for (_, s), t in self.cache.items():
            if t.target == target:
                return s
        return None

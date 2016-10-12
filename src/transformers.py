from abc import (ABCMeta, abstractmethod)
from collections.abc import (MutableSequence, Sequence)
from six import with_metaclass
from sitra.tracing import (Invocation, Recall, ObjectWrapper, SequenceWrapper, MutableSequenceWrapper)

class Transformer(with_metaclass(ABCMeta, object)):
    def __init__(self, verbose=False):
        self.verbose = verbose

    @abstractmethod
    def transform(self, source, rule=None):
        pass

    def transformAll(self, sources, rule=None):
        results = []
        for source in sources:
            target = self.transform(source, rule=rule)
            if target is not None:
                results.append(target)
        return results

    @abstractmethod
    def recall(self, key):
        pass

    @abstractmethod
    def begin(self, key, target):
        pass

    @abstractmethod
    def end(self, key):
        pass

class TraceableTransformer(Transformer):
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
    def __init__(self, verbose=False):
        super(SimpleTransformer, self).__init__(verbose=verbose)
        self.rules = []
        self.cache = {}

    def transform(self, source, rule=None):
        if self.verbose:
            print("transforming", source.__class__.__name__)
        target = None
        dynamic = rule is None
        if dynamic:
            for rule in self.rules:
                check = rule.check(source)
                if check != False:
                    break
            else:
                if self.verbose:
                    print("  no applicable rule, skipping.")
                return None
        else:
            # this was added as it should really be okay to pass the
            # definition rather than an instance
            try:
                if isinstance(type(rule), type):
                    rule = next(r for r in self.rules if type(r) == rule)
            except StopIteration:
                raise RuntimeError(rule.__name__ + " isn't part of this transformer.")

            check = rule.check(source)

        if check:
            if self.verbose:
                print("  using", rule.__class__.__name__)
            key = (rule, source)
            hit = self.recall(key)
            if hit is not None:
                if self.verbose:
                    print("  previously transformed, returning cached target")
                return hit

            if self.verbose:
                print("  instantiating target object, build()")
            target = rule.build(source, self)
            if target is not None:
                self.begin(key, target)
                try:
                    if self.verbose:
                        print("    binding taget object, set_properties()")
                    rule.set_properties(target, source, self)
                finally:
                    self.end(key)
                    if self.verbose:
                        print("  leaving the transformation of", source.__class__.__name__, "using", rule.__class__.__name__)
        else:
            if self.verbose:
                print(source.__class__.__name__, "fails the guard of", rule.__class__.__name__)

        return target


    def recall(self, key):
        if self.verbose:
            print("  checking for a previous transformation")
        return self.cache.get(key, None)

    def begin(self, key, target):
        if self.verbose:
            print("    storing the transformation for later requests.")
        self.cache[key] = target

    def end(self, key):
        pass

class SimpleTraceableTransformer(SimpleTransformer, TraceableTransformer):
    def __init__(self, verbose=False):
        super(SimpleTraceableTransformer, self).__init__(verbose=verbose)
        self.stack = []
        self.trace = []

    def recall(self, key):
        trace = super(SimpleTraceableTransformer, self).recall(key)
        if trace is not None:
            recalled = Recall(trace)
            try:
                stack = self.stack[-1]
                stack.dependencies.append(recalled)
                recalled.parent = stack
            except IndexError:
                # ignore when using the eAllContent approach
                # or indeed when there is no stacking
                pass

            return trace.target

        return None

    def begin(self, key, target):
        trace = Invocation(key, target)
        self.trace.append(trace)
        # opposed to k -> targets, we use k -> trace element
        super(SimpleTraceableTransformer, self).begin(key, trace)

        # are we a dependent transformation?
        if len(self.stack) > 0:
            try:
                # get the invocation that called us
                stack = self.stack[-1]
                # store this relationship
                stack.dependencies.append(trace)
                trace.parent = stack
            except:
                # ignore when using the eAllContent approach
                # or indeed when there is no stacking
                pass

        # increment the stack
        self.stack.append(trace)

    def end(self, key):
        self.stack.pop()

    def reverse(self, target):
        for key, t in self.cache.items():
            (r, s) = key
            if target in t.targets:
                return key
        return None

class SimpleOrphanTraceableTransformer(SimpleTraceableTransformer):
    def transform(self, source, rule=None):
        if self.verbose:
            print("transforming", source.__class__.__name__)
        target = None
        dynamic = rule is None
        if dynamic:
            for rule in self.rules:
                check = rule.check(source)
                if check != False:
                    break
            else:
                if self.verbose:
                    print("  no applicable rule, skipping.")
                return None
        else:
            # this was added as it should really be okay to pass the
            # definition rather than an instance
            try:
                if isinstance(type(rule), type):
                    rule = next(r for r in self.rules if type(r) == rule)
            except StopIteration:
                raise RuntimeError(rule.__name__ + " isn't part of this transformer.")

            check = rule.check(source)

        if check:
            if self.verbose:
                print("  using", rule.__class__.__name__)
            key = (rule, source)
            hit = self.recall(key)
            if hit is not None:
                if self.verbose:
                    print("  previously transformed, returning cached target")
                return hit

            if self.verbose:
                print("  instantiating target object, build()")
            target = rule.build(source, self)
            if target is not None:
                if isinstance(target, MutableSequence):
                    if self.verbose:
                        print("  wrapping with a mutable sequence wrapper")
                    target = MutableSequenceWrapper(target, self)
                elif isinstance(target, Sequence):
                    if self.verbose:
                        print("  wrapping with an immutable sequence wrapper")
                    target = SequenceWrapper(target, self)
                else:
                    if self.verbose:
                        print("  wrapping with an object wrapper")
                    target = ObjectWrapper(target, self)
                self.begin(key, target)
                try:
                    if self.verbose:
                        print("    binding taget object, set_properties()")
                    rule.set_properties(target, source, self)
                finally:
                    self.end(key)
                    if self.verbose:
                        print("  leaving the transformation of", source.__class__.__name__, "using", rule.__class__.__name__)
        else:
            if self.verbose:
                print(source.__class__.__name__, "fails the guard of", rule.__class__.__name__)

        return target

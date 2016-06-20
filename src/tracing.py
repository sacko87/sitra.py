from abc import ABCMeta
from six import with_metaclass
from wrapt import ObjectProxy

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

    def __repr__(self):
        (rule, source) = self.key
        return '{ "source": "%s", "transformedBy": "%s", "dependencies": %s, "target": %s, "orphans": %s }' % \
            (source.__class__.__name__, type(rule).__name__, self.dependencies, self.target, self.orphans)

class Recall(TraceElement):
    def __init__(self, invocation):
        super(Invocation, self).__init__()

        self.invocation = invocation

    def __repr__(self):
        (rule, source) = self.invocation.key
        return '{ "recalled": { "source": "%s", "transformedBy": "%s" } }' % \
            (source.__class__.__name__, type(rule).__name__)

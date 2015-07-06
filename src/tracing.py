from abc import ABCMeta
from six import with_metaclass

class TraceElement(with_metaclass(ABCMeta, object)):
    pass

class Invocation(TraceElement):
    def __init__(self, key, target):
        self.key = key
        self.target = target
        self.dependencies = []
        self.parent = None

    def __repr__(self):
        (rule, source) = self.key
        return '{ "source": "%s", "transformedBy": "%s", "dependencies": %s }' % \
            (source.__class__.__name__, type(rule).__name__, self.dependencies)

class Recall(TraceElement):
    def __init__(self, invocation):
        self.invocation = invocation
        self.parent = None

    def __repr__(self):
        (rule, source) = self.invocation.key
        return '{ "recalled": { "source": "%s", "transformedBy": "%s" } }' % \
            (source.__class__.__name__, type(rule).__name__)

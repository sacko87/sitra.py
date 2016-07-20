from abc import ABCMeta
from six import with_metaclass

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

class Recall(TraceElement):
    def __init__(self, invocation):
        self.invocation = invocation

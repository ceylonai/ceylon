# encoding: utf-8
# module rakun.rakun
# from E:\CeylonAI\Research\Rakun\rakun\python\rakun\rakun.cp311-win_amd64.pyd
# by generator 1.147
""" A Python module implemented in Rust. """


# no imports

# functions

def get_start_time(*args, **kwargs):  # real signature unknown
    """ Formats the sum of two numbers as string. """
    pass


def get_version(*args, **kwargs):  # real signature unknown
    pass


# classes

class Event(object):
    # no doc
    def __init__(self, *args, **kwargs):  # real signature unknown
        pass

    @staticmethod  # known case of __new__
    def __new__(*args, **kwargs):  # real signature unknown
        """ Create and return a new object.  See help(type) for accurate signature. """
        pass

    content = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """Event Data Message"""

    creator = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    dispatch_time = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    event_type = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    origin_type = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default


class EventProcessor(object):
    # no doc
    def __init__(self, *args, **kwargs):  # real signature unknown
        pass

    @staticmethod  # known case of __new__
    def __new__(*args, **kwargs):  # real signature unknown
        """ Create and return a new object.  See help(type) for accurate signature. """
        pass


class FunctionInfo(object):
    # no doc
    def __init__(self, *args, **kwargs):  # real signature unknown
        pass

    @staticmethod  # known case of __new__
    def __new__(*args, **kwargs):  # real signature unknown
        """ Create and return a new object.  See help(type) for accurate signature. """
        pass

    handler = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    is_async = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    number_of_params = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default


class OriginatorType(object):
    # no doc
    def __eq__(self, *args, **kwargs):  # real signature unknown
        """ Return self==value. """
        pass

    def __ge__(self, *args, **kwargs):  # real signature unknown
        """ Return self>=value. """
        pass

    def __gt__(self, *args, **kwargs):  # real signature unknown
        """ Return self>value. """
        pass

    def __init__(self, *args, **kwargs):  # real signature unknown
        pass

    def __int__(self, *args, **kwargs):  # real signature unknown
        """ int(self) """
        pass

    def __le__(self, *args, **kwargs):  # real signature unknown
        """ Return self<=value. """
        pass

    def __lt__(self, *args, **kwargs):  # real signature unknown
        """ Return self<value. """
        pass

    @staticmethod  # known case of __new__
    def __new__(*args, **kwargs):  # real signature unknown
        """ Create and return a new object.  See help(type) for accurate signature. """
        pass

    def __ne__(self, *args, **kwargs):  # real signature unknown
        """ Return self!=value. """
        pass

    def __repr__(self, *args, **kwargs):  # real signature unknown
        """ Return repr(self). """
        pass

    Agent = OriginatorType.Agent
    System = OriginatorType.System
    __hash__ = None


class Server(object):
    # no doc
    def add_event_processor(self, *args, **kwargs):  # real signature unknown
        pass

    def publish(self, *args, **kwargs):  # real signature unknown
        pass

    def remove_message_handler(self, *args, **kwargs):  # real signature unknown
        pass

    def start(self, *args, **kwargs):  # real signature unknown
        pass

    def __init__(self, *args, **kwargs):  # real signature unknown
        pass

    @staticmethod  # known case of __new__
    def __new__(*args, **kwargs):  # real signature unknown
        """ Create and return a new object.  See help(type) for accurate signature. """
        pass


# variables with complex values

__all__ = [
    'get_version',
    'get_start_time',
    'FunctionInfo',
    'EventProcessor',
    'Event',
    'OriginatorType',
    'Server',
]

__loader__ = None  # (!) real value is '<_frozen_importlib_external.ExtensionFileLoader object at 0x00000214FC77CD90>'

__spec__ = None  # (!) real value is "ModuleSpec(name='rakun.rakun', loader=<_frozen_importlib_external.ExtensionFileLoader object at 0x00000214FC77CD90>, origin='E:\\\\CeylonAI\\\\Research\\\\Rakun\\\\rakun\\\\python\\\\rakun\\\\rakun.cp311-win_amd64.pyd')"

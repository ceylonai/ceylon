def startup(func):
    def wrapper(self, *args, **kwargs):
        self.startup = func
        return func(self, *args, **kwargs)

    return wrapper


def shutdown(func):
    def wrapper(self, *args, **kwargs):
        self.shutdown = func
        return func(self, *args, **kwargs)

    return wrapper


class EventProcessorWrapper:
    def __init__(self, func, event_type):
        self.name = func.__qualname__
        self.event_type = event_type
        self.is_decorated = True  # identifiable attribute
        self.args = func.__code__.co_varnames
        self.func = func

    def function(self, instance):
        def function(*args, **kwargs):
            return self.func(instance, *args, **kwargs)

        return function

    @classmethod
    def fill_agent(cls, agent):
        agent.decorated_methods = []
        for fn in dir(agent):
            attr = getattr(agent, fn)
            if isinstance(attr, EventProcessorWrapper):
                name = attr.name
                args = attr.args
                event_type = attr.event_type
                function = attr.function(agent)  # Agent Instance need to call with functio
                agent.decorated_methods.append((name, args, event_type, function))


class Processor:
    def __init__(self, event_type):
        self.event_type = event_type

    def __call__(self, func):
        return EventProcessorWrapper(func, self.event_type)

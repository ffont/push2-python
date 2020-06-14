import weakref
import functools
import time 


def function_call_interval_limit(interval):
    """Decorator that makes sure the decorated function is only executed once in the given
    time interval (in seconds). It stores the last time the decorated function was executed
    and if it was less than "interval" seconds ago, a dummy function is returned instead.
    This decorator also check at runtime if the first argument of the decorated function call
    has the porperty "function_call_interval_limit_overwrite" exists. If that is the cases,
    it uses its value as interval rather than the "interval" value passed in the decorator
    definition.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()
            last_time_called_key = '_last_time_called_{0}'.format(func.__name__)
            if not hasattr(function_call_interval_limit, last_time_called_key):
                setattr(function_call_interval_limit, last_time_called_key, current_time)
                return func(*args, **kwargs)

            try:
                # First argument in the func call should be class instance (i.e. self), try to get interval
                # definition from calss at runtime so it is adjustable
                new_interval = args[0].function_call_interval_limit_overwrite
                interval = new_interval
            except AttributeError:
                # If property "function_call_interval_limit_overwrite" not found in class instance, just use the interval
                # given in the decorator definition
                pass
    
            if current_time - getattr(function_call_interval_limit, last_time_called_key) >= interval:
                setattr(function_call_interval_limit, last_time_called_key, current_time)
                return func(*args, **kwargs)
            else:
                return lambda *args: None

        return wrapper
    return decorator

class AbstractPush2Section(object):
    """Abstract class to be inherited when implementing the interfacing with specific sections
    of Push2. It implements an init method which gets a reference to the main Push2 object and adds
    a property method to get it de-referenced.
    """

    main_push2_object = None

    def __init__(self, main_push_object):
        self.main_push_object = weakref.ref(main_push_object)

    @property
    def push(self):
        return self.main_push_object()  # Return de-refernced main Push2 object

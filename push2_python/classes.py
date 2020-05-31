import weakref
import functools
import time 


def function_call_interval_limit(interval):
    """Decorator that makes sure the decorated function is only executed once in the given
    time interval (in seconds). It stores the last time the decorated function was executed
    and if it was less than "interval" seconds ago, a dummy function is returned instead.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()
            last_time_called_key = '_last_time_called_{0}'.format(func.__name__)
            if not hasattr(function_call_interval_limit, last_time_called_key):
                setattr(function_call_interval_limit, last_time_called_key, current_time)
                return func(*args, **kwargs)

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

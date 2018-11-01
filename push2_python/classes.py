import weakref


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

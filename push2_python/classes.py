import weakref


class AbstractPush2Section(object):
    """Abstract class to be inherited when implementing the interfacing with specific sections
    of Push2. It implements an init method which gets a reference to the main Push2 object and adds
    a property method to get it de-referenced.
    """

    main_push2_object = None

    def __init__(self, main_push2_object):
        self.main_push2_object = weakref.ref(main_push2_object)

    @property
    def push2(self):
        return self.main_push2_object()  # Return de-refernced main Push2 object


class Push2View(object):
    """TODO: document this class
    """

    def on_pad_pressed(self, msg):
        raise NotImplementedError

    def on_pad_released(self, msg):
        raise NotImplementedError


class Push2DebugView(Push2View):

    @staticmethod
    def on_pad_pressed(msg):
        print('Pad pressed', msg)

    @staticmethod
    def on_pad_released(msg):
        print('Pad released', msg)

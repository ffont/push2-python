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


class AbstractPush2View(AbstractPush2Section):
    """TODO: document this class
    Inherit from AbstractPush2Section so that it also has the self.push2 property.
    """

    @property
    def name(self):
        return str(self)

    def on_pad_pressed(self, pad_n, pad_ij, velocity):
        raise NotImplementedError

    def on_pad_released(self, pad_n, pad_ij, velocity):
        raise NotImplementedError

    def on_pad_aftertouch(self, pad_n, pad_ij, velocity):
        raise NotImplementedError


class Push2DebugView(AbstractPush2View):

    def on_pad_pressed(self, pad_n, pad_ij, velocity):
        print('Pad pressed', pad_n, pad_ij, velocity)

    def on_pad_released(self, pad_n, pad_ij, velocity):
        print('Pad released', pad_n, pad_ij, velocity)

    def on_pad_aftertouch(self, pad_n, pad_ij, velocity):
        print('Pad aftertouch', pad_n, pad_ij, velocity)

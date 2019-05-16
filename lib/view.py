import prompt_toolkit.layout.containers as pt_containers
from prompt_toolkit.document import Document
from prompt_toolkit.widgets import TextArea


class HSplit(pt_containers.HSplit):
    """Container class for Horizontal Splits that contains Views"""
    def __init__(self, top, bottom):
        valid = [False, False]
        for valid_type in [View, HSplit, VSplit]:
            if isinstance(top, valid_type):
                valid[0] = True
            if isinstance(bottom, valid_type):
                valid[1] = True
        if not valid[0] or not valid[1]:
            raise RuntimeError("HSplit subviews aren't Views "
                               "(did you forget to create a View() around "
                               "the module?)")
        children = [
            top,
            pt_containers.Window(height=1, char='-'),
            bottom
        ]
        self.subviews = [top, bottom]
        pt_containers.HSplit.__init__(self, children)

    def update(self):
        """Update all the subviews for this container"""
        for subview in self.subviews:
            subview.update()


class VSplit(pt_containers.VSplit):
    """Container class for Vertical Splits that contains Views"""
    def __init__(self, left, right):
        valid = [False, False]
        for valid_type in [View, HSplit, VSplit]:
            if isinstance(left, valid_type):
                valid[0] = True
            if isinstance(right, valid_type):
                valid[1] = True
        if not valid[0] or not valid[1]:
            raise RuntimeError("VSplit subviews aren't Views "
                               "(did you forget to create a View() around "
                               "the module?)")
        subviews = [
            left,
            pt_containers.Window(width=1, char='|'),
            right
        ]
        self.subviews = [left, right]
        pt_containers.VSplit.__init__(self, subviews)

    def update(self):
        """Update all the subviews for this container"""
        for subview in self.subviews:
            subview.update()


class View(TextArea):
    """ Wraps a hardware module into a Container that can be displayed"""
    def __init__(self, module):
        self.module = module
        TextArea.__init__(self, text="")


    def update(self):
        """Update this view and all subviews"""
        new_text = str(self.module)
        self.buffer.document = Document(text=new_text)


class Display():
    """ Abstract class for debugging displays to implement"""
    def __init__(self, model):
        self.top_view = self.gen_top_view(model)

    def gen_top_view(self, model):
        """ Subclass implement this -- build the top-level view out of
        HSplits, VSplits, and Views"""
        raise NotImplementedError

    def get_top_view(self):
        """ Get the top level container"""
        return self.top_view

    def update(self):
        """ Update all Views in the Display """
        self.get_top_view().update()

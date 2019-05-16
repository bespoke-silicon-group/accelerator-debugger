import prompt_toolkit.layout.containers as pt_containers
from prompt_toolkit.document import Document
from prompt_toolkit.widgets import TextArea

# Make a container class that wraps a Container and a HWModule
#  1. Need to be able to get list of all HWModules contained & update text
#  2. Need way of creating layout of views
#
#  Could just pass a list to init that the View appends to (bad)
#

class HSplit(pt_containers.HSplit):
    """Container class for Horizontal Splits that contains Views"""
    def __init__(self, top, bottom):
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
    # Try passing pointer to module, if it doesn't work just pass the name
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
        raise NotImplementedError

    def get_top_view(self):
        return self.top_view

    def update(self):
        self.get_top_view().update()

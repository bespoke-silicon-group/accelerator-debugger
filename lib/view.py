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
    def __init__(self, top_child, bottom_child):
        self.subviews = [
            top_child,
            pt_containers.Window(height=1, char='-'),
            bottom_child
        ]
        self.children = [top_child, bottom_child]
        super(HSplit, self).__init__(self.subviews)

    def update(self):
        """Update all the subviews for this container"""
        for child in self.children:
            child.update()


class VSplit(pt_containers.VSplit):
    """Container class for Vertical Splits that contains Views"""
    def __init__(self, left_child, right_child):
        self.subviews = [
            left_child,
            pt_containers.Window(width=1, char='|'),
            right_child
        ]
        self.children = [left_child, right_child]
        super(VSplit, self).__init__(self.subviews)

    def update(self):
        """Update all the subviews for this container"""
        for child in self.children:
            child.update()


class View(TextArea):
    # Try passing pointer to module, if it doesn't work just pass the name
    def __init__(self, module):
        self.module = module
        super(View, self).__init__(text="")

    def update(self):
        """Update this view and all subviews"""
        new_text = str(self.module)
        super(View, self).buffer.document = Document(text=new_text)


class Display():
    """ Abstract class for debugging displays to implement"""
    pass

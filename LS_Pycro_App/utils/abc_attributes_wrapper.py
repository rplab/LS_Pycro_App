"""
Class wrapper that requires implementation of all class attributes in
base class. If not implemented, throws NotImplementedError at runtime.

Reason for this is that this error is thrown while class definition is
interpreted rather than when the attribute is accessed. Thus, the program
will not run unless these attributes are defined.
"""
import inspect

def abstractattributes(base_cls):
    @classmethod
    def __init_subclass__(cls):
        annotations = list(inspect.get_annotations(base_cls).keys())
        for annotation in annotations:
            if annotation not in dir(cls):
                raise NotImplementedError(f"Class {cls} lacks required {annotation} class attribute.")
    base_cls.__init_subclass__ = __init_subclass__
    return base_cls
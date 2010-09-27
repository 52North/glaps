"""
a very small collection of dbus-related conveniences.
"""

import dbus

inttypes = (dbus.Int16, dbus.Int32, dbus.Int64, 
                  dbus.Byte, dbus.UInt16, dbus.UInt32, dbus.UInt64)
booltypes = (dbus.Boolean)
floattypes = (dbus.Double)
strtypes = (dbus.ByteArray, dbus.String, dbus.UTF8String, dbus.Signature,
                   dbus.ObjectPath)

def undbox(x):
    """
    undbox is a function that unwraps dbus types such as dbus.Int64 into python
    types such as int.  The principal purpose of this unwrapping is to allow
    pickling, because dbus objects cannot be pickled.
    
    @type x: any type
    @param x: an object that might contain dbus types
    @return: an object that compares as equal to x, but has been recursively
    stripped of all dbus types
    
        >>> a = dbus.Struct((dbus.UInt64(4252), dbus.ByteArray('asdf;lkj')))
        >>> b = undbox(a)
        >>> b
        (4252, 'asdf;lkj')
        >>> a == b
        True
    """
    if isinstance(x, inttypes):
        return int(x)
    elif isinstance(x, booltypes):
        return bool(x)
    elif isinstance(x, strtypes):
        return str(x)
    elif isinstance(x, floattypes):
        return float(x)
    elif isinstance(x, (dbus.Struct, tuple)):
        return tuple(undbox(y) for y in x)
    elif isinstance(x, (dbus.Array, list)):
        return [undbox(y) for y in x]
    elif isinstance(x, (dbus.Dictionary, dict)):
        return dict((undbox(a),undbox(b)) for (a,b) in x.iteritems())
    else:
        return x

"""Groupthink is a library of self-sharing data structures written in python
and shared over dbus. Together with the D-Bus Tubes provided by the Telepathy
framework, this enables data structures to be shared over a network.

Groupthink's tagline is "Collaboration should be easy.".

Concepts
========

The goal of Groupthink is to make it tremendously easy for programmers to write
distributed networked applications.  To achieve this goal, Groupthink
introduces the concept of a Distributed Object, or DObject.  A DObject is an
abstract object whose state is regarded as existing independently of any
individual computer.  Each instance of a shared application contains local
objects that may be regarded as views into a shared DObject.  Edits to the local
object propagate into the shared state, and vice versa.

The DObject provides an abstraction barrier that permits a programmer to
manipulate the data structure without worrying about any network-related issues.
For example, if an application stores its local state in a python dict(), it may
be possible to substitute a Groupthink L{CausalDict} and immediately achieve
coherent sharing over the network.

The key guarantee provided by DObjects is decentralized coherence.  Coherence,
in Groupthink, means that any group of connected computers maintaining instances
of a single DObject will observe that object to be in the same state at
quiescence, which will occur in a bounded, short amount of time.  Decentralized
coherence means that this property is achieved without any single point of
failure.  Anyone with a view into a DObject can leave the group unexpectedly
without destroying the DObject, or even interrupting communication.

Providing these guarantees, and also maintaining useful behaviors,
is not always easy, and sometimes constrains the
behavior or efficiency of a DObject.  Many DObjects employ techniques related
to Operational Transformation in order to ensure coherence without negotiation.

Dependencies
============

Mandatory dependencies:
    - Python 2.5 or later
    - dbus-python
Optional dependencies:
    - pygtk
    - Sugar (U{http://wiki.sugarlabs.org/})

Groupthink is written in Python.  It requires Python 2.5 or later, and depends
heavily on dbus-python for all communication between
instances of an application.  In principle, dbus-python is the only dependency.
However, Groupthink's principal use is in shared, networked applications. To
forward D-Bus messages over IP, Groupthink supports the Telepathy library via
telepathy-python.

For users writing GTK applications, Groupthink provides the L{gtk_tools}
submodule, which contains GTK-related objects like self-sharing widgets.

For users writing Sugar activities, Groupthink provides the L{sugar_tools}
submodule, which contains additional Sugar-related convenience objects,
including L{GroupActivity}, a subclass of sugar.activity.activity.Activity
that handles all
Telepathy interaction and L{Group} setup automatically.

Status
======

Groupthink is under active development, and is very much a work in progress.
No official releases have yet been made, and further API changes are virtually
certain.  However, Groupthink is already sufficiently useful that developers may
wish to take a snapshot of the repository and import it into their projects.
"""
__license__ = """
Copyright 2008 Benjamin M. Schwartz

Groupthink is LGPLv2+

Groupthink is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

Groupthink is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with Groupthink.  If not, see <http://www.gnu.org/licenses/>.
"""

from groupthink_base import *

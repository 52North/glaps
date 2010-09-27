"""
a helper library providing a number of fundamental tree data structures,
ultimately intended to improve performance in L{SimpleStringTree}.  These data
structures are sufficiently generic that they might also be of use for other
purposes.
"""

class Node:
    """
    Node represents a node in a binary tree.  It is entirely passive, acting
    as a container much a like a C struct.  Its unusual features include a
    distinction between annotation and value, and references not only to its children
    but also to its parent.
    """
    parent = None
    """
    @ivar: The parent of the node, or None if the node has no parent
    @type: L{Node}
    """
    leftchild = None
    """
    @ivar: The left child of the node, or None if the node has no left child
    @type: L{Node}
    """
    rightchild = None
    """
    @ivar: The right child of the node, or None if the node has no right child
    @type: L{Node}
    """
    annotation = None
    """
    @ivar: A piece of data associated with a node, assigned by a
        tree-specific function and satisfying a related constraint.
    @type: tree-specific type
    """
    value = None
    """
    @ivar: A value assigned by the user of the tree.  In monoid-annotated
        trees, only the leaves typically have values, and internal nodes will
        therefore have a value of None.
        The purpose of
        the annotation is to permit the construction of monoid-annotated trees,
        which often have both highly constrained annotations and completely
        unconstrained values.
        See, for example,
        U{http://scienceblogs.com/goodmath/2009/05/finally_finger_trees.php}.
        Non-monoid-annotated trees may ignore this variable.
    @type: typically unconstrained
    """

class AANode(Node):
    """
    An AANode is a L{Node} that can be used in an AA tree.  AA trees require
    that each node have an associated level.
    """
    level = 1
    """
    @ivar: The level index for the node.  For more information on the level
        in AA trees, see U{http://en.wikipedia.org/wiki/AA_tree}.
    @type: int
    """

class Walker:
    """
    A Walker walks up and down trees according to a specific objective.  Its
    goal is typically to find some particular element, such as the element
    at a specific index, or with a specific value.
    
    Walker is an abstract base class.
    """
    def descend(self, node):
        """
        @type node: Node
        @param node: A node from which to descend.
        @rtype: int
        @return: descend must return 0 if the node in question is the one desired,
            -1 if the left child would be better, or 1 if the right child would be
            better.
        """
        raise
    def prepare_descend(self, *args):
        """An optional method to prepare for descent"""
        raise
    def ascend(self, node):
        """
        @type node: Node
        @param node: A node from which to ascend
        @rtype: bool
        @return: ascend should return True iff it should run again on the parent
            of node. It should set the walker's internal state such that a
            subsequent descent would retrace these steps."""
        raise
    def prepare_ascend(self, *args): 
        """ An optional method to prepare for ascent"""
        raise

class SearchWalker(Walker):
    """
    A L{Walker} that can be used to search a classic binary tree.  This class
    exists solely to expose the concept of the Walker.  As a convention, the
    binary tree being search must satisfy::
        leftchild.annotation < annotation < rightchild.annotation
    """
    val = 0
    compare = cmp
    def prepare_descend(self, val, comparator=cmp):
        self.val = val
        self.compare = comparator
    def descend(self, node):
        x = self.compare(node.annotation, self.val)
        return x
    def ascend(self, node):
        self.val = node.annotation
        return False

class RandomWalker(Walker):
    """
    An experimental Walker that could be used to select a random
    sub-leaf position in a binary tree.  ascent is not implemented.
    """
    def prepare_descend(self):
        from random import choice as choice
        self.choice = choice
    def descend(self, node):
        return self.choice((-1,1))

def descend(node, walker): #move down from a root node
    """
    @type node: L{Node}
    @param node: A node from which to start descent
    @type walker: L{Walker}
    @param walker: A L{Walker} to apply recursively from node.
    @rtype: tuple(L{Node}, int)
    @return: If the L{Walker} accepted a L{Node} n, the function
        returns (n, 0).  Otherwise, the function returns (L, 1), or (L, -1),
        where L is a node that has no right or left child, respectively.
        These return values typically indicate that the walker is looking for a
        node that is not present in the tree, but, if it were present, would be
        in the (currently empty) subtree right (or left) of L.
    """
    x = walker.descend(node)
    while x != 0:
        if x == 1:
            if node.rightchild is None:
                return (node, 1)
            else:
                node = node.rightchild
        else: #x == -1
            if node.leftchild is None:
                return (node, -1)
            else:
                node = node.leftchild
        x = walker.descend(node)
    return (node, 0)
    
def ascend(node, walker):
    """
    @type node: L{Node}
    @type walker: L{Walker}
    @param node: the L{Node} from which to ascend.
    @param walker: The L{walker} with which to ascend.
    @rtype: None
    ascend causes walker to ascend until walker asks to stop or the tree's
    root node is reached.  Nothing is returned; instead, state is accumulated
    inside the walker
    """
    while node is not None and walker.ascend(node):
        node = node.parent

def search(root, val):
    """
    @type root: L{Node}
    @type val: comparable
    Searches a correctly sorted binary tree, starting with the root Node, for
    val.  Returns a node that contains val if val is present, otherwise a node
    for which val would be an acceptable child value.
    
    Provided solely as an example."""
    w = SearchWalker
    w.prepared_descend(val)
    return descend(root, w)
        
def findmin(root):
    """
    Simple search function for the leftmost element in a tree, or subtree.
    @type root: L{Node}
    @param root: The node from which to start walking.
    @rtype: L{Node}
    @return: the leftmost element in the subtree of root
    """
    while root.leftchild is not None:
        root = root.leftchild
    return root

def findmax(root):
    """
    Simple search function for the rightmost element in a tree, or subtree.
    @type root: L{Node}
    @param root: The node from which to start walking.
    @rtype: L{Node}
    @return: the rightmost element in the subtree of root
    """
    while root.rightchild is not None:
        root = root.rightchild
    return root

class MonoidTree:
    """
    A Monoid Annotation Tree is a binary tree whose nodes are each annotated
    by values from some monoid.  The annotation of an internal node is computed
    by applying the operation to the annotations of its children.  The annotation of a leaf
    node is specified by the user.  Every node must either have two children or
    be a leaf node.

    Each leaf node may also be associated with an arbitrary opaque value of the user's
    choosing.  This node and value will remain associated."""
    makenode = Node
    """
    @cvar: a factory function that returns nodes of the type required
    for this tree.  It is provided so that subclasses can easily override it
    to use subtypes of L{Node}.
    """
    def __init__(self, operation, rootnode):
        """
        Let M be the monoid type.
        @type operation: f(M,M) -> M
        @param operation: a function taking two arguments from the monoid set
            and returning another element from the monoid set.  The monoid
            operation must obey an associativity criterion; see U{http://en.wikipedia.org/wiki/Monoid#Definition}.
        @type rootnode: L{makenode}
        @param rootnode: The root node for the tree. rootnode must have a valid annotation, and its parent and children must be None."""
        self.op = operation
        self.root = rootnode
    def _update(self, node, sentinel=None):
        """node must be an internal node"""
        while node is not sentinel:
            #oldval = node.annotation
            node.annotation = self.op(node.leftchild.annotation, node.rightchild.annotation)
            #if oldval == node.annotation:
            #    #this node has not changed, so nodes above it will also not have changed
            #    break
            #else:
            node = node.parent
    _update_add = _update
    _update_del = _update
    def _split_link(self, node):
        """Introduce and return a new node (newparent) between node and its parent"""
        newparent = self.makenode()
        newparent.parent = node.parent
        if node.parent is not None:
            if node.parent.leftchild is node:
                node.parent.leftchild = newparent
            else:
                assert node.parent.rightchild is node
                node.parent.rightchild = newparent
        else:
            self.root = newparent
        node.parent = newparent
        return newparent
    def addleft(self, new, old):
        """
        Add a new leaf node to the left of an old leaf node.  The new node's
        parent will be assigned to be a new internal node.
        @type new: makenode
        @param new: a new node, not yet present in the tree
        @type old: makenode
        @param old: A leaf node currently in the tree.
        """
        newparent = self._split_link(old)
        newparent.rightchild = old
        newparent.leftchild = new
        new.parent = newparent
        self._update_add(newparent)
    def addright(self, new, old):
        """
        Add a new leaf node to the right of an old leaf node.  The new node's
        parent will be assigned to be a new internal node.
        @type new: makenode
        @param new: a new node, not yet present in the tree
        @type old: makenode
        @param old: A leaf node currently in the tree.
        """
        newparent = self._split_link(old)
        newparent.rightchild = new
        newparent.leftchild = old
        new.parent = newparent
        self._update_add(newparent)        
    def add(self, new, walker):
        """
        Add a new leaf node at a position determined by walker.  Acts as a
        thin wrapper around L{aatree.descend} and addleft or addright.
        If the walker descent process returns a position of zero, the new node
        will be added left of the returned node.
        @type new: makenode
        @param new: a new node to add to the tree.
        @type walker: L{Walker}
        @param walker: A walker that will determine the insertion position
        """
        leaf, position = descend(self.root, walker)
        assert leaf.leftchild is None
        assert leaf.rightchild is None
        if position == 1:
            self.addright(new, leaf)
        else: #Makes left the default for duplicate values
            self.addleft(new, leaf)
    def remove(self, leaf):
        """
        Remove a leaf node.  The leaf will be removed from the tree, and the
        tree will retain no reference to it.
        @type leaf: makenode
        @param leaf: A leaf node to remove.
        """
        p = leaf.parent
        if p.leftchild is leaf:
            sibling = p.rightchild
        else:
            assert p.rightchild is leaf
            sibling = p.leftchild
        gp = p.parent
        if gp.leftchild is p:
            gp.leftchild = sibling
        elif gp.rightchild is p:
            gp.rightchild = sibling
        sibling.parent = gp
        # The only remaining reference to p is now in leaf itself, and the only
        # remaining reference to leaf is in the user's hands
        self._update_del(gp)
    def change_annotation(self, leaf, newann):
        """
        When changing the annotation of a leaf, it is required to use this method,
        so that the change may be propagated up through the tree according to the
        operation.  Note that no such method is needed for the value of a leaf,
        because the value is opaque to the tree.
        @type leaf: makenode
        @param leaf: the node whose annotation should be altered
        @type newann: element of the monoid set
        @param newann: the new annotation which should be associated with leaf
        """
        assert leaf.leftchild is None
        assert leaf.rightchild is None
        leaf.annotation = newann
        self._update(leaf.parent)
    def getnext(self, leaf, skip=None):
        """
        Get the next rightward leaf node from leaf.  Optionally, skip any nodes
        meeting some criterion.
        @type leaf: makenode
        @param leaf: The leaf node whose next rightward neighbor will be returned
        @type skip: f(makenode)->bool
        @param skip: An optional function returning True if a given node should
        be skipped.  This function will be called on each internal node during
        the search, not only on leaf nodes.  It will typically implement a 
        criterion on the annotation such that a node will be skipped only
        if every descendant of that node would also be skipped if considered
        individually.
        """
        assert leaf.leftchild is None
        assert leaf.rightchild is None
        node = leaf
        while ((node.parent is not None) and
               ((node.parent.rightchild is node) or 
                ((skip is not None) and skip(node.parent.rightchild)))):
            # Move up until you can move right
            node = node.parent
        if (node.parent is not None) and (node.parent.leftchild is node):
            node = node.parent.rightchild
            while node.leftchild is not None:
                # Move down, staying as far left as possible.
                assert node.rightchild is not None
                if (skip is not None) and skip(node.leftchild):
                    node = node.rightchild
                else:
                    node = node.leftchild
            return node
        else:
            raise StopIteration("No next node")
                
    def _build_subtree(self, nodes):
        #FIXME: This cannot be helpful because insertion of a subtree requires
        #rebalancing the main tree by more than one level, which is not possible
        #with a single invocation of skew and split
        L = len(nodes)
        if L == 1:
            return nodes[0]
        else:
            next = []
            sentinel = 'g' #must not be None, since None is the root sentinel
            if L % 2:
                n2 = nodes.pop()
                n1 = nodes.pop()
                newnode = self.makenode()
                newnode.parent=sentinel #totally arbitrary constant
                newnode.leftchild = n1
                n1.parent = newnode
                newnode.rightchild = n2
                n2.parent = newnode
                self._update_add(newnode, sentinel)
                nodes.append(newnode)            
            for i in xrange(0,L,2):
                n1,n2 = nodes[i:(i+2)]
                newnode = self.makenode()
                newnode.parent=sentinel #totally arbitrary constant
                newnode.leftchild = n1
                n1.parent = newnode
                newnode.rightchild = n2
                n2.parent = newnode
                self._update_add(newnode, sentinel)
                
                

class SumWalker(Walker):
    """
    SumWalker is designed to walk over full trees where each leaf has annotation 1
    and the monoid is +.  Target is the zero-indexed position of the target node.
    
    There is one exception: the last node in every tree has annotation 0."""
    target = None
    offset = None
    def prepare_descend(self, target):
        self.target = target
        self.offset = 0
    def descend(self, node):
        if node.annotation == 0: #empty leaf at the last position
            assert self.target == self.offset
            return -1
        elif node.leftchild is None: #leaf node case
            assert node.rightchild is None
            assert self.target == self.offset
            return 0
        else: #internal node case
            p = self.offset + node.leftchild.annotation
            if p <= self.target:
                self.offset = p
                return 1
            else:
                return -1
    def prepare_ascend(self):
        self.target = 0
    def ascend(self, node):
        if node.parent is not None:
            if node.parent.rightchild is node:
                self.target += node.parent.leftchild.annotation
            else:
                assert node.parent.leftchild is node
            return True
        else:
            return False
        
class TreeList:
    """Implements a list-like interface, backed by a MonoidTree"""
    _treetype = MonoidTree
    def __init__(self):
        self._makenode = self._treetype.makenode
        r = self._makenode()
        r.annotation = 0
        from operator import add
        self._tree = self._treetype(add, r)
        self._walker = SumWalker()
        # We regard the fields of this walker as public API, and manipulate
        # them directly
        self._index = {}
    def __len__(self):
        return self._tree.root.annotation
    def _getnode(self, i):
        self._walker.prepare_descend(i)
        node, pos = descend(self._tree.root, self._walker)
        assert pos == 0
        return node
    def __getitem__(self, s):
        if isinstance(s, int):
            node = self._getnode(s)
            return node.value
        else:
            raise UnimplementedError
    def __setitem__(self, s, v):
        if isinstance(s, int):
            if s < len(self):
                node = self._getnode(s)
                oldv = node.value
                self._index[oldv].remove(node)
                if not self._index[oldv]:
                    del self._index[oldv]
                node.value = v
                if v not in self._index:
                    self._index[v] = set()
                self._index[v].add(node)
            else:
                self.insert(s, v)
        else:
            raise UnimplementedError
    def __delitem__(self, s):
        if isinstance(s, int):
            if s < len(self):
                node = self._getnode(s)
                oldv = node.value
                self._index[oldv].remove(node)
                if not self._index[oldv]:
                    del self._index[oldv]
                self._tree.remove(node)
        else:
            raise UnimplementedError
    def insert(self, p, v):
        if p > len(self):
            raise IndexError("Index out of range")
        self._walker.prepare_descend(p)
        newnode = self._makenode()
        newnode.annotation = 1
        newnode.value = v
        self._tree.add(newnode, self._walker)
        if v not in self._index:
            self._index[v] = set()
        self._index[v].add(newnode)
    def index(self, v):
        """index returns some index such that self[i] == v.  No promises about ordering."""
        self._walker.prepare_ascend()
        for node in self._index[v]: #Pull one arbitrary node out of the set
            assert node.value == v
            ascend(node, self._walker)
            break
        return self._walker.target

class TreeHideList:
    """Implements the EagerHideList interface, backed by a MonoidTree"""
    _treetype = MonoidTree
    class MultiSumWalker(Walker):
        index = 0
        target = 0
        offset = 0
        def prepare_descend(self, target, index):
            self.index = index
            self.target = target
            self.offset = 0
        def descend(self, node):
            if node.annotation == (0,0): #empty leaf at the last position
                assert self.target == self.offset
                return -1
            elif node.leftchild is None: #leaf node case
                assert node.rightchild is None
                assert self.target == self.offset
                return 0
            else: #internal node case
                p = self.offset + node.leftchild.annotation[self.index]
                if p <= self.target:
                    self.offset = p
                    return 1
                else:
                    return -1
        def prepare_ascend(self, index):
            self.target = 0
            self.index = index
        def ascend(self, node):
            if node.parent is not None:
                if node.parent.rightchild is node:
                    self.target += node.parent.leftchild.annotation[self.index]
                else:
                    assert node.parent.leftchild is node
                return True
            else:
                return False
    
    @staticmethod            
    def op(a,b):
        # Convention: a[0] is visible elements.  a[1] is all elements.
        return (a[0] + b[0], a[1] + b[1])
    
    @staticmethod
    def skip(node):
        return node.annotation[0] == 0

    def __init__(self):
        self._makenode = self._treetype.makenode
        r = self._makenode()
        r.annotation = (0, 0)
        self._tree = self._treetype(self.op, r)
        self._walker = self.MultiSumWalker()
        # We regard the fields of this walker as public API, and manipulate
        # them directly
        self._index = {}
        unique = True
        if unique:
            self._index_lookup = self._index.__getitem__
            self._index_assign = self._index.__setitem__
        else:
            self._index_lookup = self._index_lookup_set
            self._index_assign = self._index_assign_set
    def _index_lookup_set(self, item):
        for v in self._index[item]:
            return v
    def _index_assign_set(self, key, value):
        if key not in self._index:
            self._index[key] = set()
        self._index[key].add(value)
    def __len__(self):
        return self._tree.root.annotation[0]
    def _getnode(self, i, a):
        self._walker.prepare_descend(i, a)
        node, pos = descend(self._tree.root, self._walker)
        assert (pos == 0) or ((pos == -1) and (i == len(self)))
        return node
    def __getitem__(self, s):
        if isinstance(s, int):
            if s < len(self): #FIXME: negative indices
                node = self._getnode(s, 0)
                return node.value
            else:
                raise IndexError("Index out of range")
        else:
            start, stop, stride = s.indices(len(self))
            if start == stop:
                return []
            elif stride == 1:
                # runs in k + log(N) (amortized)
                nodes = [self._getnode(start,0)]
                k = stop - start
                while len(nodes) < k:
                    nodes.append(self._tree.getnext(nodes[-1],self.skip))
                return [n.value for n in nodes]
            else:
                #FIXME: runs in k*log(N), could be reduced to k*log(step) + log(N)
                return [self[i] for i in xrange(start,stop,stride)]
    def index(self, v, visible=True):
        """index returns some index such that self[i] == v.  No promises about ordering."""
        self._walker.prepare_ascend(0 if visible else 1)
        node = self._index_lookup(v) #Pull one arbitrary node out of the set
        assert node.value == v
        ascend(node, self._walker)
        return self._walker.target
    def hide(self, position, length):
        #self.__getitem__ is eager, so we acquire the list of nodes before
        #acting on them
        node = self._getnode(position,0)
        for i in xrange(position+1,position+length):
            self._tree.change_annotation(node,(0,1))
            node = self._tree.getnext(node, self.skip)
        self._tree.change_annotation(node,(0,1))
        #FIXME: runs in length*log(N).  Could be reduced using a priority queue,
        #possibly to length + log(N)
    def getitem_all(self, s):
        if isinstance(s, int):
            node = self._getnode(s, 1)
            return node.value
        else:
            #FIXME: runs in k*log(N), could be reduced to k + log(N) by linked list
            return [self.getitem_all(i) for i in xrange(*s.indices())]
    def index_all(self, item):
        return self.index(item, False)
    def is_visible(self, i):
        node = self._getnode(i, 1)
        return node.annotation[0] == 1
    def is_visible_item(self, item):
        node = self._index_lookup(item)
        return node.annotation[0] == 1
    def insert_sequence_all(self, position, sequence, visibility):
        node = self._getnode(position,1)
        self._insert_sequence_leftofnode(node, sequence, visibility)
    def insert_sequence_leftof(self, target, sequence, visibility):
        node = self._index_lookup(target)
        self._insert_sequence_leftofnode(node, sequence, visibility)
    def _insert_sequence_leftofnode(self, node, sequence, visibility):
        for i in xrange(len(sequence)):
            v = sequence[i]
            viz = visibility[i]
            newnode = self._makenode()
            newnode.annotation = (1 if viz else 0, 1)
            newnode.value = v
            self._tree.addleft(newnode, node)
            self._index_assign(v, newnode)

# Skew, split, and decrease_level are the AA balancing functions, as described
# at http://en.wikipedia.org/wiki/AA_tree .  They have been modified
# substantially here to (1) maintain bidirectional linking and (2) maintain
# monoid annotations.
def skew(node, op=None):
    L = node.leftchild
    if (L is not None) and node.level == L.level:
        node.leftchild = L.rightchild
        if node.leftchild is not None:
            node.leftchild.parent = node
        L.rightchild = node
        L.parent = node.parent
        node.parent = L
        if L.parent is not None:
            if L.parent.leftchild is node:
                L.parent.leftchild = L
            else:
                assert L.parent.rightchild is node
                L.parent.rightchild = L
        if op is not None:
            L.annotation = node.annotation
            node.annotation = op(node.leftchild.annotation, node.rightchild.annotation)
            assert L.annotation == op(L.leftchild.annotation, L.rightchild.annotation)
            # This assertion is the condition of associativity, guaranteed for any
            # valid monoid operation.
        return L
    else:
        return node

def split(node, op=None):
    R = node.rightchild
    if ((R is not None) and 
        (R.rightchild is not None) and 
        (node.level == R.rightchild.level)):
        node.rightchild = R.leftchild
        node.rightchild.parent = node
        
        R.leftchild = node
        R.parent = node.parent
        node.parent = R
        
        R.level += 1
        
        if R.parent is not None:
            if R.parent.leftchild is node:
                R.parent.leftchild = R
            else:
                assert R.parent.rightchild is node
                R.parent.rightchild = R
            
        if op is not None:
            R.annotation = node.annotation
            node.annotation = op(node.leftchild.annotation, node.rightchild.annotation)
            assert R.annotation == op(R.leftchild.annotation, R.rightchild.annotation)
            # This assertion is the condition of associativity, guaranteed for any
            # valid monoid operation.
            
        return R
    else:
        return node

def decrease_level(node):
    # Decrease the level of node if necessary.  Returns true if a modification
    # was made.
    target = min(node.leftchild.level, node.rightchild.level) + 1
    if target < node.level:
        node.level = target
        if target < node.rightchild.level:
            node.rightchild.level = target
        return True
    return False

class AAMonoidTree(MonoidTree):
    makenode = AANode
    def _update_add(self, node, sentinel=None):
        """node must be an internal node one level above the leaves, with
        two leaves itself."""
        node.level = 2
        while node is not sentinel:
            #oldval = node.annotation
            node.annotation = self.op(node.leftchild.annotation, node.rightchild.annotation)
            node = skew(node, self.op)
            node = split(node, self.op)
            if node.parent is None:
                self.root = node
            node = node.parent
    def _update_del(self, node, sentinel=None):
        while node is not sentinel:
            #oldval = node.annotation
            #oldlevel = node.level
            node.annotation = self.op(node.leftchild.annotation, node.rightchild.annotation)
            
            decrease_level(node)
            
            node = skew(node, self.op)
            node.rightchild = skew(node.rightchild, self.op)
            if node.rightchild.rightchild is not None:
                node.rightchild.rightchild = skew(node.rightchild.rightchild, self.op)
            node = split(node, self.op)
            node.rightchild = split(node.rightchild, self.op)
            
            #if (oldval == node.annotation) and (oldlevel == node.level):
            #    #Nodes above this point will not have changed
            #    break
            
            if node.parent is None:
                self.root = node
            node = node.parent

class AATreeList(TreeList):
    _treetype = AAMonoidTree

class AATreeHideList(TreeHideList):
    _treetype = AAMonoidTree

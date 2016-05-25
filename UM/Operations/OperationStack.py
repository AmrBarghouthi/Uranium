# Copyright (c) 2015 Ultimaker B.V.
# Uranium is released under the terms of the AGPLv3 or higher.

from UM.Signal import Signal, signalemitter

import threading

##  A stack of operations.
#
#   This maintains the history of operations, which allows for undoing and
#   re-doing these operations.
@signalemitter
class OperationStack():
    def __init__(self):
        self._operations = [] #List of operations.
        self._current_index = -1 #Index of the most recently executed operation.
        self._lock = threading.Lock() #Lock to make sure only one thread can modify the operation stack at a time.

    ##  Push an operation on the stack.
    #
    #   This will perform the following things in sequence:
    #   - If the current index is pointing to an item lower in the stack than
    #     the top, remove all operations from the current index to the top.
    #   - Append the operation to the stack.
    #   - Call redo() on the operation.
    #   - Perform merging of operations.
    #
    #   \param operation \type{Operation} The operation to push onto the stack.
    def push(self, operation):
        if not self._lock.acquire(False):
            return

        try:
            if self._current_index < len(self._operations) - 1:
                del self._operations[self._current_index + 1:len(self._operations)]

            self._operations.append(operation)
            operation.redo()
            self._current_index += 1

            self._doMerge()

            self.changed.emit()
        finally:
            self._lock.release()

    ##  Undo the current operation.
    #
    #   This will call undo() on the current operation and decrement the current index.
    def undo(self):
        with self._lock:
            if self._current_index >= 0 and self._current_index < len(self._operations):
                self._operations[self._current_index].undo()
                self._current_index -= 1
                self.changed.emit()

    ##  Redo the next operation.
    #
    #   This will call redo() on the current operation and increment the current index.
    def redo(self):
        with self._lock:
            n = self._current_index + 1
            if n >= 0 and n < len(self._operations):
                self._operations[n].redo()
                self._current_index += 1
                self.changed.emit()

    ##  Get the list of operations in the stack.
    #
    #   The end of the list represents the more recent operations.
    #
    #   \return A list of the operations on the stack, in order.
    def getOperations(self):
        with self._lock:
            return self._operations

    ##  Whether we can undo any more operations.
    #
    #   \return True if we can undo any more operations, or False otherwise.
    def canUndo(self):
        return self._current_index >= 0

    ##  Whether we can redo any more operations.
    #
    #   \return True if we can redo any more operations, or False otherwise.
    def canRedo(self):
        return self._current_index < len(self._operations) - 1

    ##  Signal for when the operation stack changes.
    changed = Signal()

    ## private:

    ##  Merges two operations at the current position in the stack.
    #
    #   This merges the "most recent" operation with the one before it. The
    #   "most recent" operation is the one that would be undone if the user
    #   would trigger an undo, i.e. the one at _current_index.
    def _doMerge(self):
        if len(self._operations) >= 2:
            op1 = self._operations[self._current_index]
            op2 = self._operations[self._current_index - 1]

            if not op1._always_merge and not op2._always_merge:
                if abs(op1._timestamp - op2._timestamp) > self._merge_window: #For normal operations, only merge if the operations were very quickly after each other.
                    return

            merged = op1.mergeWith(op2)
            if merged: #Replace the merged operations in the stack with the new one.
                del self._operations[self._current_index]
                del self._operations[self._current_index - 1]
                self._current_index -= 1
                self._operations.append(merged)

    _merge_window = 1.0 #Don't merge operations that were longer than this amount of seconds apart.

import { ref } from 'vue'

/**
 * Delete with an undo window. `remove(id)` hides the item at once and only calls
 * `commit(id)` (the real DELETE) after `delay` ms, so "Undo" can bring it back
 * without a server round trip. One deletion is pending at a time: removing a
 * second item commits the first immediately.
 *
 * The caller filters its list by `hiddenIds`, shows `pending` as an undo toast,
 * and calls `flush()` on unmount so a deletion is not lost on navigation. If the
 * tab closes inside the window the DELETE never runs and the item survives,
 * which is the safe direction.
 *
 * Callbacks: `onCommitted(id)` after a successful DELETE (reload the list),
 * `onError(error, id)` when it fails (the item reappears), `onUndo(id, meta)`.
 */
export function useUndoableDelete({ commit, onCommitted, onError, onUndo, delay = 8000 }) {
  const hiddenIds = ref(new Set())
  const pending = ref(null) // { id, meta } while the undo window is open
  let timer = null

  function setHidden(id, hidden) {
    const next = new Set(hiddenIds.value)
    if (hidden) next.add(id)
    else next.delete(id)
    hiddenIds.value = next
  }

  async function run(id) {
    try {
      await commit(id)
      if (onCommitted) await onCommitted(id)
      setHidden(id, false)
    } catch (e) {
      setHidden(id, false)
      if (onError) onError(e, id)
    }
  }

  function flush() {
    if (!pending.value) return Promise.resolve()
    const { id } = pending.value
    clearTimeout(timer)
    timer = null
    pending.value = null
    return run(id)
  }

  function remove(id, meta = null) {
    const previous = flush()
    setHidden(id, true)
    pending.value = { id, meta }
    timer = setTimeout(flush, delay)
    return previous
  }

  function undo() {
    if (!pending.value) return
    const { id, meta } = pending.value
    clearTimeout(timer)
    timer = null
    pending.value = null
    setHidden(id, false)
    if (onUndo) onUndo(id, meta)
  }

  return { hiddenIds, pending, remove, undo, flush }
}

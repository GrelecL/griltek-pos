import { ref, onMounted, onUnmounted } from 'vue'

/**
 * Keyboard-wedge barcode scanner: accumulates chars into a buffer and emits
 * on Enter. Most USB HID scanners act as keyboard wedge by default.
 */
export function useScanner(onScan: (code: string) => void) {
  const buffer = ref('')
  let timer: ReturnType<typeof setTimeout> | null = null

  function flush() {
    const code = buffer.value.trim()
    buffer.value = ''
    if (code.length >= 3) onScan(code)
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      if (timer) clearTimeout(timer)
      timer = null
      flush()
    } else if (e.key.length === 1) {
      buffer.value += e.key
      if (timer) clearTimeout(timer)
      // clear stale buffer after 100 ms of inactivity
      timer = setTimeout(() => { buffer.value = ''; timer = null }, 100)
    }
  }

  onMounted(() => window.addEventListener('keydown', onKeydown))
  onUnmounted(() => window.removeEventListener('keydown', onKeydown))

  return { buffer }
}

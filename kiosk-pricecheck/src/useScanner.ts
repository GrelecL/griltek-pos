import { ref, onMounted, onUnmounted } from 'vue'

export function useScanner(onScan: (code: string) => void) {
  const buffer = ref('')
  let timer: ReturnType<typeof setTimeout> | null = null

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      if (timer) clearTimeout(timer)
      timer = null
      const code = buffer.value.trim()
      buffer.value = ''
      if (code.length >= 3) onScan(code)
    } else if (e.key.length === 1) {
      buffer.value += e.key
      if (timer) clearTimeout(timer)
      timer = setTimeout(() => { buffer.value = ''; timer = null }, 100)
    }
  }

  onMounted(() => window.addEventListener('keydown', onKeydown))
  onUnmounted(() => window.removeEventListener('keydown', onKeydown))

  return { buffer }
}

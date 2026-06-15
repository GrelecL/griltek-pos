import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: { port: 5177 },
  test: {
    environment: 'node',
    include: ['src/__tests__/**/*.test.ts'],
  },
})

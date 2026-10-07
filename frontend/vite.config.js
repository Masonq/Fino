import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  // метка сборки: кэши, которые должны сбрасываться при каждом обновлении сайта (например, список разделов)
  define: { __BUILD__: JSON.stringify(String(Date.now())) },
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    // Сайт открывают по домену, а запрос приходит от nginx с этим же
    // именем. Без разрешения сборщик отвечает отказом: он защищается от
    // чужих имён, но наше собственное тоже надо назвать.
    allowedHosts: ['plonk.rs', 'www.plonk.rs', '89.208.113.147'],
  },
  preview: {
    port: 5173,
    host: true,
    allowedHosts: ['plonk.rs', 'www.plonk.rs', '89.208.113.147'],
  },
})

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
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

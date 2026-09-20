import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({ plugins:[react()], server:{ port:5605, host:'127.0.0.1', proxy:{'/api':'http://127.0.0.1:8559','/media':'http://127.0.0.1:8559'} } })

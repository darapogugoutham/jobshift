import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig(({ mode }) => { const env = loadEnv(mode, '.', 'VITE_'); const target = env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000'; return { plugins: [react()], server: { proxy: { '/api': { target, changeOrigin: false }, '/health': { target, changeOrigin: false } } } }; });

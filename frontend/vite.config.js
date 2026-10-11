import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), babel({ presets: [reactCompilerPreset()] })],
  server: {
    proxy: {
      "/games": "http://localhost:8000",
      "/ws/games": {
        target: "ws://127.0.0.1:8000",
        ws: true,
      },
    },
  },
});

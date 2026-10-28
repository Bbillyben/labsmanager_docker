// @vitest-environment node
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import { describe, expect, it } from 'vitest'

const configFile = fileURLToPath(new URL('./vite.config.ts', import.meta.url))
const indexFile = fileURLToPath(new URL('./index.html', import.meta.url))

describe('development plugin import map', () => {
  it.each(['/app/', '/workspace/'])('uses the resolved Vite base %s on a nested route', async (base) => {
    const server = await createServer({ configFile, base, server: { middlewareMode: true } })
    try {
      const html = await server.transformIndexHtml(
        `${base}employees/73/plugins/modelexample/employee-tab`,
        await readFile(indexFile, 'utf8'),
      )
      const importMap = html.match(/<script type="importmap">(.*?)<\/script>/)?.[1]
      expect(importMap).toBeTruthy()
      expect(JSON.parse(importMap!).imports).toEqual({
        react: `${base}src/plugin-react.ts`,
        'react/jsx-runtime': `${base}src/plugin-jsx-runtime.ts`,
        '@labsmanager/plugin-ui': `${base}src/plugin-api.ts`,
        '@labsmanager/plugin-calendar': `${base}src/plugin-calendar.ts`,
      })
    } finally {
      await server.close()
    }
  })
})

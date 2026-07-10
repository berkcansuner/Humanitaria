import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import prettier from 'eslint-config-prettier'
import globals from 'globals'

export default [
  { ignores: ['dist/**', 'node_modules/**'] },
  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  // Formatting is Prettier's job — disable every stylistic ESLint/vue rule it conflicts with.
  prettier,
  {
    languageOptions: {
      globals: { ...globals.browser },
    },
    rules: {
      // Existing single-word component names (Chat, Sidebar, ...) are established API;
      // renaming them is not worth the churn.
      'vue/multi-word-component-names': 'off',
      // `catch (e) {}` / `catch {}` is the codebase's intentional best-effort
      // pattern (localStorage, clipboard, optional fetches).
      'no-unused-vars': ['error', { caughtErrors: 'none' }],
      'no-empty': ['error', { allowEmptyCatch: true }],
      // v-html only ever renders DOMPurify-sanitized markdown (renderMarkdown.js).
      'vue/no-v-html': 'off',
    },
  },
  {
    // The React island is the one JSX file; parse JSX without pulling in react plugins.
    files: ['**/*.jsx'],
    languageOptions: { parserOptions: { ecmaFeatures: { jsx: true } } },
  },
  {
    files: ['**/*.test.js', 'vite.config.js', 'vitest.config.js'],
    languageOptions: { globals: { ...globals.node } },
  },
]

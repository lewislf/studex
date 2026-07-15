import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      // Variables/args/array holes prefixed with `_` are intentionally unused
      // (eg. destructuring context props we don't read from).
      'no-unused-vars': [
        'error',
        {
          varsIgnorePattern: '^_',
          argsIgnorePattern: '^_',
          destructuredArrayIgnorePattern: '^_',
        },
      ],
    },
  },
  {
    // Test helpers re-export testing-library utilities alongside a custom
    // render function, which isn't a fast-refresh boundary concern.
    files: ['src/test/**/*.{js,jsx}'],
    rules: {
      'react-refresh/only-export-components': 'off',
    },
  },
])

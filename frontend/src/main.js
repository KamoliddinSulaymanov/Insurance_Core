import './index.css'

import { createApp } from 'vue'
import router from './router'
import App from './App.vue'

import { Button, setConfig, frappeRequest, resourcesPlugin } from 'frappe-ui'

/**
 * Ensure window.csrf_token is a real token before any resource fetch.
 * Production page (www/insurance_core.html) injects it via Jinja.
 * Fallback: cookie, then GET frappe.sessions.get_csrf_token.
 */
async function ensureCsrfToken() {
  const bad = (t) =>
    !t ||
    t === '{{ csrf_token }}' ||
    t === 'None' ||
    t === 'null' ||
    t === 'undefined'

  if (!bad(window.csrf_token)) return

  // Cookie used by some Frappe builds
  try {
    const m = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/)
    if (m && m[1] && !bad(decodeURIComponent(m[1]))) {
      window.csrf_token = decodeURIComponent(m[1])
      return
    }
  } catch (e) {
    /* ignore */
  }

  try {
    const res = await fetch('/api/method/frappe.sessions.get_csrf_token', {
      method: 'GET',
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    })
    if (res.ok) {
      const data = await res.json()
      const token = data?.message
      if (token && !bad(token)) {
        window.csrf_token = token
        return
      }
    }
  } catch (e) {
    console.warn('[insurance_core] CSRF refresh failed', e)
  }
}

await ensureCsrfToken()

let app = createApp(App)

setConfig('resourceFetcher', frappeRequest)

app.use(router)
app.use(resourcesPlugin)

app.component('Button', Button)
app.mount('#app')

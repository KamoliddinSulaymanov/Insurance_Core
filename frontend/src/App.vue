<template>
  <div class="min-h-screen bg-gray-50 text-gray-900 flex">
    <!-- Mobile overlay -->
    <transition name="sidebar-overlay">
      <div
        v-if="mobileOpen"
        class="fixed inset-0 bg-black/40 z-30 lg:hidden"
        @click="mobileOpen = false" />
    </transition>

    <!-- Sidebar -->
    <aside
      class="sidebar fixed lg:sticky top-0 left-0 z-40 h-screen flex flex-col bg-white border-r border-gray-200"
      :class="[
        collapsed ? 'sidebar--collapsed' : 'sidebar--expanded',
        mobileOpen ? 'sidebar--mobile-open' : 'sidebar--mobile-closed',
      ]">
      <div class="h-14 flex items-center gap-2 px-3 border-b shrink-0 overflow-hidden">
        <button
          class="hidden lg:inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-gray-600 hover:bg-gray-100 transition-colors"
          :title="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
          @click="collapsed = !collapsed">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <router-link
          to="/"
          class="sidebar-label font-semibold tracking-tight text-gray-900 no-underline truncate"
          @click="mobileOpen = false">
          Insurance Portal
        </router-link>
      </div>

      <nav class="flex-1 overflow-y-auto overflow-x-hidden py-3 px-2 space-y-4">
        <div v-for="group in navGroups" :key="group.title">
          <div
            v-if="group.title"
            class="sidebar-group-title px-2 mb-1 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
            {{ group.title }}
          </div>

          <!-- Flat items (no nested collapsibles) -->
          <div v-if="group.items && !group.sections" class="space-y-0.5">
            <component
              :is="item.external ? 'a' : 'router-link'"
              v-for="item in group.items"
              :key="item.to + item.label"
              v-bind="item.external ? { href: item.to, target: '_blank', rel: 'noopener noreferrer' } : { to: item.to }"
              class="sidebar-link flex items-center gap-3 rounded-md px-2.5 py-2 text-sm text-gray-600 no-underline hover:bg-gray-100 hover:text-gray-900"
              :class="!item.external && isActive(item) ? 'bg-gray-100 text-gray-900 font-medium' : ''"
              :title="item.label"
              @click="mobileOpen = false">
              <span
                class="sidebar-icon shrink-0 w-5 h-5 flex items-center justify-center text-gray-500"
                v-html="item.icon" />
              <span class="sidebar-label truncate">{{ item.label }}</span>
            </component>
          </div>

          <!-- Collapsible LOB sections (Claims etc.) -->
          <div v-if="group.sections" class="space-y-0.5">
            <div v-for="sec in group.sections" :key="sec.key" class="sidebar-section">
              <button
                type="button"
                class="sidebar-link w-full flex items-center gap-3 rounded-md px-2.5 py-2 text-sm text-gray-700 hover:bg-gray-100"
                :title="sec.label"
                @click="toggleSection(sec.key)">
                <span
                  class="sidebar-icon shrink-0 w-5 h-5 flex items-center justify-center text-gray-500"
                  v-html="sec.icon" />
                <span class="sidebar-label flex-1 text-left truncate font-medium">{{ sec.label }}</span>
                <svg
                  class="sidebar-label sidebar-section-chevron w-3.5 h-3.5 shrink-0 text-gray-400 transition-transform duration-200"
                  :class="{ 'rotate-90': openSections[sec.key] }"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
              </button>
              <div
                v-show="openSections[sec.key] && !collapsed"
                class="ml-2 pl-2 border-l border-gray-100 space-y-0.5 mb-1">
                <component
                  :is="item.external ? 'a' : 'router-link'"
                  v-for="item in sec.items"
                  :key="item.to + item.label"
                  v-bind="item.external ? { href: item.to, target: '_blank', rel: 'noopener noreferrer' } : { to: item.to }"
                  class="sidebar-link flex items-center gap-3 rounded-md px-2.5 py-1.5 text-sm text-gray-600 no-underline hover:bg-gray-100 hover:text-gray-900"
                  :class="!item.external && isActive(item) ? 'bg-gray-100 text-gray-900 font-medium' : ''"
                  :title="item.label"
                  @click="mobileOpen = false">
                  <span
                    class="sidebar-icon shrink-0 w-4 h-4 flex items-center justify-center text-gray-400"
                    v-html="item.icon" />
                  <span class="sidebar-label truncate">{{ item.label }}</span>
                </component>
              </div>
            </div>
          </div>
        </div>
      </nav>

      <div class="border-t p-2 shrink-0 overflow-hidden">
        <button
          class="sidebar-link w-full flex items-center gap-3 rounded-md px-2.5 py-2 text-sm text-gray-600 hover:bg-gray-100"
          :title="collapsed ? 'Expand' : 'Collapse'"
          @click="collapsed = !collapsed">
          <span class="sidebar-icon shrink-0 w-5 h-5 flex items-center justify-center">
            <svg
              class="sidebar-chevron w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M15 19l-7-7 7-7" />
            </svg>
          </span>
          <span class="sidebar-label truncate">Collapse</span>
        </button>
      </div>
    </aside>

    <!-- Main column -->
    <div class="flex-1 min-w-0 flex flex-col min-h-screen">
      <!-- Top bar: search + profile -->
      <header class="sticky top-0 z-20 bg-white border-b h-14 flex items-center gap-3 px-3 sm:px-4">
        <button
          class="lg:hidden h-9 w-9 inline-flex items-center justify-center rounded-md text-gray-600 hover:bg-gray-100"
          @click="mobileOpen = true">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        <!-- Spacer pushes search + profile to the right -->
        <div class="flex-1 min-w-0" aria-hidden="true" />

        <div class="relative w-full max-w-md sm:max-w-xl" data-search-root>
          <div class="pointer-events-none absolute inset-y-0 left-0 pl-3 flex items-center text-gray-400">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M21 21l-4.35-4.35M11 18a7 7 0 100-14 7 7 0 000 14z" />
            </svg>
          </div>
          <input
            v-model="searchQuery"
            type="search"
            placeholder="Search policies, claims…"
            class="w-full h-9 pl-9 pr-3 rounded-md border border-gray-200 bg-gray-50 text-sm focus:outline-none focus:ring-2 focus:ring-gray-300 focus:bg-white"
            @focus="searchOpen = true"
            @keydown.escape="closeSearch"
            @keydown.enter.prevent="goFirstResult" />

          <div
            v-if="searchOpen && searchQuery.trim().length >= 2"
            class="absolute left-0 right-0 mt-1 bg-white border rounded-lg shadow-lg overflow-hidden z-30">
            <div v-if="$resources.search.loading" class="px-3 py-3 text-sm text-gray-500">Searching…</div>
            <template v-else>
              <div v-if="searchResults.policies.length" class="py-1">
                <div class="px-3 py-1 text-[11px] font-semibold uppercase text-gray-400">Policies</div>
                <button
                  v-for="p in searchResults.policies"
                  :key="p.name"
                  class="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex justify-between gap-2"
                  @click="goTo(`/policies/${p.name}`)">
                  <span class="truncate">
                    <span class="font-medium">{{ p.policy_number }}</span>
                    <span class="text-gray-500"> · {{ p.scheme }}</span>
                  </span>
                  <span class="text-xs text-gray-400 shrink-0">{{ p.status }}</span>
                </button>
              </div>
              <div v-if="searchResults.claims.length" class="py-1 border-t">
                <div class="px-3 py-1 text-[11px] font-semibold uppercase text-gray-400">Claims</div>
                <button
                  v-for="c in searchResults.claims"
                  :key="c.name"
                  class="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex justify-between gap-2"
                  @click="goTo(`/claims/${c.name}`)">
                  <span class="truncate">
                    <span class="font-medium">{{ c.claim_number }}</span>
                    <span class="text-gray-500"> · {{ c.claim_type }}</span>
                  </span>
                  <span class="text-xs text-gray-400 shrink-0">{{ c.status }}</span>
                </button>
              </div>
              <div
                v-if="!searchResults.policies.length && !searchResults.claims.length"
                class="px-3 py-3 text-sm text-gray-500">
                No matches for “{{ searchQuery }}”
              </div>
            </template>
          </div>
        </div>

        <!-- Profile dropdown -->
        <div class="relative shrink-0" ref="profileRoot">
          <button
            class="flex items-center gap-2 rounded-md pl-1 pr-2 py-1 hover:bg-gray-100"
            @click="profileOpen = !profileOpen">
            <span
              class="h-8 w-8 rounded-full bg-gray-800 text-white text-xs font-semibold flex items-center justify-center overflow-hidden">
              <img v-if="userImage" :src="userImage" alt="" class="h-full w-full object-cover" />
              <span v-else>{{ userInitials }}</span>
            </span>
            <span class="hidden sm:block text-sm font-medium max-w-[9rem] truncate">{{ displayName }}</span>
            <svg class="w-4 h-4 text-gray-500 hidden sm:block" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          <div
            v-if="profileOpen"
            class="absolute right-0 mt-1 w-56 bg-white border rounded-lg shadow-lg py-1 z-30">
            <div class="px-3 py-2 border-b">
              <div class="text-sm font-medium truncate">{{ displayName }}</div>
              <div class="text-xs text-gray-500 truncate">{{ userEmail }}</div>
            </div>
            <router-link
              to="/"
              class="block px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 no-underline"
              @click="profileOpen = false">
              Dashboard
            </router-link>
            <router-link
              to="/policies"
              class="block px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 no-underline"
              @click="profileOpen = false">
              My policies
            </router-link>
            <router-link
              to="/claims"
              class="block px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 no-underline"
              @click="profileOpen = false">
              My claims
            </router-link>
            <a
              href="/app/user-profile"
              target="_blank"
              rel="noopener noreferrer"
              class="block px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 no-underline"
              @click="profileOpen = false">
              Account settings
            </a>
            <div class="border-t my-1" />
            <button
              class="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50"
              :disabled="loggingOut"
              @click="logout">
              {{ loggingOut ? 'Signing out…' : 'Log out' }}
            </button>
          </div>
        </div>
      </header>

      <main class="flex-1">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script>
const icon = {
  home: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M3 12l9-9 9 9M5 10v10h5v-6h4v6h5V10"/></svg>`,
  building: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>`,
  scheme: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/></svg>`,
  policy: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M9 12h6m-6 4h6M7 4h10a2 2 0 012 2v14l-3-2-3 2-3-2-3 2V6a2 2 0 012-2z"/></svg>`,
  users: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M17 20v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M9 10a4 4 0 100-8 4 4 0 000 8zm12 10v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/></svg>`,
  agent: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>`,
  quote: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"/></svg>`,
  opportunity: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>`,
  endorsement: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>`,
  claim: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/></svg>`,
  plus: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M12 4v16m8-8H4"/></svg>`,
  cashless: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/></svg>`,
  hospital: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M12 7v4m0 0v4m0-4h4m-4 0H8"/></svg>`,
  recovery: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>`,
  mail: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>`,
  grievance: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>`,
  compliance: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>`,
  commission: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
  plug: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>`,
  settings: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>`,
  health: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/></svg>`,
  fire: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z"/></svg>`,
  marine: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M3 15s1.5-1 4.5-1 4.5 1 7.5 1 4.5-1 4.5-1M3 19s1.5-1 4.5-1 4.5 1 7.5 1 4.5-1 4.5-1M12 3v9m0 0l-3-3m3 3l3-3"/></svg>`,
  life: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>`,
  motor: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M8 17a2 2 0 100-4 2 2 0 000 4zm8 0a2 2 0 100-4 2 2 0 000 4zM3 11l1.5-4.5A2 2 0 016.4 5h11.2a2 2 0 011.9 1.5L21 11M3 11v5a1 1 0 001 1h1m16-6v5a1 1 0 01-1 1h-1M5 17h2m10 0h2"/></svg>`,
}

export default {
  name: 'App',
  data() {
    return {
      collapsed: false,
      mobileOpen: false,
      profileOpen: false,
      searchOpen: false,
      searchQuery: '',
      searchTimer: null,
      loggingOut: false,
      // Health open by default; other LOBs collapsed
      openSections: {
        health: true,
        fire: false,
        marine: false,
        life: false,
        motor: false,
      },
      navGroups: [
        {
          title: 'Overview',
          items: [{ to: '/', label: 'Dashboard', icon: icon.home, exact: true }],
        },
        {
          title: 'Catalog',
          items: [
            {
              to: '/app/insurance-provider',
              label: 'Insurance Providers',
              icon: icon.building,
              external: true,
            },
            {
              to: '/app/insurance-scheme',
              label: 'Insurance Schemes',
              icon: icon.scheme,
              external: true,
            },
          ],
        },
        {
          title: 'Policies',
          items: [
            { to: '/policies', label: 'Policies', icon: icon.policy, match: '/policies' },
            {
              to: '/app/insurance-client',
              label: 'Clients',
              icon: icon.users,
              external: true,
            },
            {
              to: '/app/insurance-agent',
              label: 'Agents',
              icon: icon.agent,
              external: true,
            },
            {
              to: '/app/insurance-quotation',
              label: 'Quotations',
              icon: icon.quote,
              external: true,
            },
            {
              to: '/app/insurance-opportunity',
              label: 'Opportunities',
              icon: icon.opportunity,
              external: true,
            },
            {
              to: '/app/policy-endorsement',
              label: 'Endorsements',
              icon: icon.endorsement,
              external: true,
            },
          ],
        },
        {
          title: 'Claims',
          sections: [
            {
              key: 'health',
              label: 'Health',
              icon: icon.health,
              items: [
                {
                  to: '/claims',
                  label: 'Claims',
                  icon: icon.claim,
                  match: '/claims',
                  exclude: '/claims/new',
                },
                { to: '/claims/new', label: 'Intimate Claim', icon: icon.plus, exact: true },
                {
                  to: '/app/cashless-authorization',
                  label: 'Cashless Auth',
                  icon: icon.cashless,
                  external: true,
                },
                {
                  to: '/app/network-hospital',
                  label: 'Network Hospitals',
                  icon: icon.hospital,
                  external: true,
                },
                {
                  to: '/app/claim-recovery',
                  label: 'Claim Recoveries',
                  icon: icon.recovery,
                  external: true,
                },
              ],
            },
            {
              key: 'fire',
              label: 'Fire',
              icon: icon.fire,
              items: [
                {
                  to: '/claims?lob=Fire',
                  label: 'Claims',
                  icon: icon.claim,
                  match: '/claims',
                },
                {
                  to: '/claims/new?lob=Fire',
                  label: 'Intimate Claim',
                  icon: icon.plus,
                },
                {
                  to: '/app/insurance-claim?lob=Fire',
                  label: 'Desk Claims',
                  icon: icon.claim,
                  external: true,
                },
              ],
            },
            {
              key: 'marine',
              label: 'Marine',
              icon: icon.marine,
              items: [
                {
                  to: '/claims?lob=Marine',
                  label: 'Claims',
                  icon: icon.claim,
                  match: '/claims',
                },
                {
                  to: '/claims/new?lob=Marine',
                  label: 'Intimate Claim',
                  icon: icon.plus,
                },
                {
                  to: '/app/insurance-claim?lob=Marine',
                  label: 'Desk Claims',
                  icon: icon.claim,
                  external: true,
                },
              ],
            },
            {
              key: 'life',
              label: 'Life',
              icon: icon.life,
              items: [
                {
                  to: '/claims?lob=Life',
                  label: 'Claims',
                  icon: icon.claim,
                  match: '/claims',
                },
                {
                  to: '/claims/new?lob=Life',
                  label: 'Intimate Claim',
                  icon: icon.plus,
                },
                {
                  to: '/app/insurance-claim?lob=Life',
                  label: 'Desk Claims',
                  icon: icon.claim,
                  external: true,
                },
              ],
            },
            {
              key: 'motor',
              label: 'Motor',
              icon: icon.motor,
              items: [
                {
                  to: '/claims?lob=Motor',
                  label: 'Claims',
                  icon: icon.claim,
                  match: '/claims',
                },
                {
                  to: '/claims/new?lob=Motor',
                  label: 'Intimate Claim',
                  icon: icon.plus,
                },
                {
                  to: '/app/insurance-claim?lob=Motor',
                  label: 'Desk Claims',
                  icon: icon.claim,
                  external: true,
                },
              ],
            },
          ],
        },
        {
          title: 'Operations',
          items: [
            {
              to: '/app/insurance-communication',
              label: 'Communications',
              icon: icon.mail,
              external: true,
            },
            {
              to: '/app/insurance-grievance',
              label: 'Grievances',
              icon: icon.grievance,
              external: true,
            },
            {
              to: '/app/compliance-record',
              label: 'Compliance',
              icon: icon.compliance,
              external: true,
            },
            {
              to: '/app/commission-payout',
              label: 'Commissions',
              icon: icon.commission,
              external: true,
            },
          ],
        },
        {
          title: 'System',
          items: [
            {
              to: '/app/insurance-settings',
              label: 'Settings',
              icon: icon.settings,
              external: true,
            },
            {
              to: '/app/reinsurance-treaty',
              label: 'Reinsurance',
              icon: icon.plug,
              external: true,
            },
          ],
        },
      ],
    }
  },
  computed: {
    me() {
      return this.$resources.me?.data
    },
    displayName() {
      return this.me?.client?.full_name || this.me?.user?.full_name || 'Account'
    },
    userEmail() {
      return this.me?.client?.email || this.me?.user?.email || ''
    },
    userImage() {
      const img = this.me?.user?.user_image
      if (!img) return ''
      return img.startsWith('/') || /^https?:/i.test(img) ? img : `/${img}`
    },
    userInitials() {
      const name = this.displayName || '?'
      const parts = name.trim().split(/\s+/).filter(Boolean)
      if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
      return name.slice(0, 2).toUpperCase()
    },
    searchResults() {
      return this.$resources.search?.data || { policies: [], claims: [] }
    },
  },
  resources: {
    me: {
      url: 'insurance_core.portal.portal_me',
      auto: true,
    },
    search: {
      url: 'insurance_core.portal.portal_search',
    },
  },
  watch: {
    searchQuery(q) {
      clearTimeout(this.searchTimer)
      if (!q || q.trim().length < 2) {
        return
      }
      this.searchTimer = setTimeout(() => {
        this.$resources.search.fetch({ q: q.trim(), limit: 8 })
        this.searchOpen = true
      }, 250)
    },
    $route() {
      this.mobileOpen = false
      this.closeSearch()
      this.profileOpen = false
    },
    collapsed(v) {
      localStorage.setItem('insurance_portal_sidebar_collapsed', v ? '1' : '0')
    },
  },
  mounted() {
    document.addEventListener('click', this.onDocClick)
    const saved = localStorage.getItem('insurance_portal_sidebar_collapsed')
    if (saved === '1') this.collapsed = true
  },
  beforeUnmount() {
    document.removeEventListener('click', this.onDocClick)
    clearTimeout(this.searchTimer)
  },
  methods: {
    toggleSection(key) {
      this.openSections[key] = !this.openSections[key]
    },
    isActive(item) {
      if (item.external) return false
      const path = this.$route.path
      if (item.exact) return path === item.to
      if (item.match) {
        if (!path.startsWith(item.match)) return false
        if (item.exclude && path.startsWith(item.exclude)) return false
        if (item.to === '/claims' && path === '/claims/new') return false
        return true
      }
      return path === item.to || path.startsWith(item.to + '/')
    },
    closeSearch() {
      this.searchOpen = false
    },
    goTo(path) {
      this.closeSearch()
      this.searchQuery = ''
      this.$router.push(path)
    },
    goFirstResult() {
      const r = this.searchResults
      if (r.policies?.length) return this.goTo(`/policies/${r.policies[0].name}`)
      if (r.claims?.length) return this.goTo(`/claims/${r.claims[0].name}`)
    },
    onDocClick(e) {
      if (this.$refs.profileRoot && !this.$refs.profileRoot.contains(e.target)) {
        this.profileOpen = false
      }
      if (this.searchOpen && !e.target.closest?.('[data-search-root]')) {
        this.searchOpen = false
      }
    },
    async logout() {
      this.loggingOut = true
      try {
        await fetch('/api/method/logout', {
          method: 'POST',
          headers: {
            'X-Frappe-CSRF-Token': window.csrf_token || '',
            'Content-Type': 'application/json',
          },
          credentials: 'same-origin',
          body: '{}',
        })
      } catch (e) {
        // still redirect
      } finally {
        window.location.href = '/login?redirect-to=/insurance_core'
      }
    },
  },
}
</script>

<style scoped>
.sidebar {
  width: 15rem; /* w-60 */
  transition:
    width 280ms cubic-bezier(0.4, 0, 0.2, 1),
    transform 280ms cubic-bezier(0.4, 0, 0.2, 1);
  will-change: width, transform;
}

.sidebar--collapsed {
  width: 4.25rem;
}

/* Labels & group titles: fade + collapse width so they animate with the rail */
.sidebar-label,
.sidebar-group-title {
  display: inline-block;
  max-width: 12rem;
  opacity: 1;
  white-space: nowrap;
  overflow: hidden;
  transition:
    opacity 200ms cubic-bezier(0.4, 0, 0.2, 1),
    max-width 280ms cubic-bezier(0.4, 0, 0.2, 1),
    margin 280ms cubic-bezier(0.4, 0, 0.2, 1),
    padding 280ms cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar--collapsed .sidebar-label,
.sidebar--collapsed .sidebar-group-title {
  max-width: 0;
  opacity: 0;
  margin: 0;
  padding-left: 0;
  padding-right: 0;
  pointer-events: none;
}

/* Tighten nav links when collapsed so icons sit centered */
.sidebar-link {
  transition: background-color 150ms ease, color 150ms ease, padding 280ms cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar--collapsed .sidebar-link {
  justify-content: center;
  gap: 0;
  padding-left: 0.5rem;
  padding-right: 0.5rem;
}

.sidebar-icon {
  transition: transform 200ms cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar--collapsed .sidebar-icon {
  transform: scale(1.05);
}

/* Collapse chevron rotates when rail is collapsed */
.sidebar-chevron {
  transition: transform 280ms cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar--collapsed .sidebar-chevron {
  transform: rotate(180deg);
}

/* Mobile drawer: off-canvas by default, slide in when open */
@media (max-width: 1023.98px) {
  .sidebar {
    width: 15rem;
  }

  .sidebar--mobile-closed {
    transform: translateX(-100%);
  }

  .sidebar--mobile-open {
    transform: translateX(0);
  }

  /* On mobile always show full labels */
  .sidebar--collapsed .sidebar-label,
  .sidebar--collapsed .sidebar-group-title {
    max-width: 12rem;
    opacity: 1;
    pointer-events: auto;
  }

  .sidebar--collapsed .sidebar-link {
    justify-content: flex-start;
    gap: 0.75rem;
    padding-left: 0.625rem;
    padding-right: 0.625rem;
  }

  .sidebar--collapsed .sidebar-chevron {
    transform: none;
  }
}

/* Overlay fade */
.sidebar-overlay-enter-active,
.sidebar-overlay-leave-active {
  transition: opacity 220ms ease;
}

.sidebar-overlay-enter-from,
.sidebar-overlay-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .sidebar,
  .sidebar-label,
  .sidebar-group-title,
  .sidebar-link,
  .sidebar-icon,
  .sidebar-chevron,
  .sidebar-overlay-enter-active,
  .sidebar-overlay-leave-active {
    transition: none !important;
  }
}
</style>

import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/pages/Home.vue'),
  },
  {
    path: '/policies',
    name: 'Policies',
    component: () => import('@/pages/Policies.vue'),
  },
  {
    path: '/products',
    name: 'Products',
    component: () => import('@/pages/Products.vue'),
  },
  {
    path: '/order/:scheme',
    name: 'OrderWizard',
    component: () => import('@/pages/OrderWizard.vue'),
  },
  {
    path: '/partner',
    name: 'PartnerPortal',
    component: () => import('@/pages/PartnerPortal.vue'),
  },
  {
    path: '/policies/:name',
    name: 'PolicyDetail',
    component: () => import('@/pages/PolicyDetail.vue'),
  },
  {
    path: '/claims',
    name: 'Claims',
    component: () => import('@/pages/Claims.vue'),
  },
  {
    path: '/claims/new',
    name: 'ClaimNew',
    component: () => import('@/pages/ClaimNew.vue'),
  },
  {
    path: '/claims/:name',
    name: 'ClaimDetail',
    component: () => import('@/pages/ClaimDetail.vue'),
  },
]

let router = createRouter({
  history: createWebHistory('/insurance_core'),
  routes,
})

export default router

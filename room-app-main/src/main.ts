import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router/index'
import './assets/theme.css'
import { installDocumentI18n } from './i18n'

createApp(App).use(createPinia()).use(router).mount('#app')
installDocumentI18n()

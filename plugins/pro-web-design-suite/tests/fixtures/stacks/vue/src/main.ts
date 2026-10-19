// The global entry first, before any component is imported.
import './styles/index.css';
import { createApp } from 'vue';
import App from './App.vue';

createApp(App).mount('#app');

<template>
  <el-config-provider :locale="elementLocale">
    <div class="app-layout">
      <header class="top-bar">
        <router-link to="/" class="logo-link">
          <div class="logo-title">
            <svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="32" height="32">
              <path d="M0 0 C0.86625 0.4640625 0.86625 0.4640625 1.75 0.9375 C5.68044566 2.79354378 9.16739736 3.17858347 13.5 3.25 C14.90765625 3.28867188 14.90765625 3.28867188 16.34375 3.328125 C19.42339202 2.94769863 20.65527569 1.95393692 23 0 C23.66 0 24.32 0 25 0 C25 6.6 25 13.2 25 20 C25.66 20 26.32 20 27 20 C27 20.66 27 21.32 27 22 C26.01 22 25.02 22 24 22 C23.74734375 22.59296875 23.4946875 23.1859375 23.234375 23.796875 C21.11082872 27.58700191 17.73672679 29.88252148 14 32 C10.5 32.375 10.5 32.375 8 32 C8 31.01 8 30.02 8 29 C7.4225 28.7525 6.845 28.505 6.25 28.25 C3.70649745 26.83694303 2.04701082 25.04701082 0 23 C-0.66 23 -1.32 23 -2 23 C-1.855625 22.26136719 -1.71125 21.52273437 -1.5625 20.76171875 C-0.28019903 13.75358778 0.25222242 7.11827723 0 0 Z M6 11 C6 12.32 6 13.64 6 15 C6.99 14.67 7.98 14.34 9 14 C8.67 13.01 8.34 12.02 8 11 C7.34 11 6.68 11 6 11 Z M17 11 C17 12.32 17 13.64 17 15 C17.99 14.67 18.98 14.34 20 14 C19.67 13.01 19.34 12.02 19 11 C18.34 11 17.68 11 17 11 Z M12 18 C13 21 13 21 13 21 Z M9 28 C10 30 10 30 10 30 Z " fill="#0052cc" transform="translate(4,0)"/>
            </svg>
            <h1>Blender Flamenco Insights</h1>
          </div>
        </router-link>
        
        <div class="language-switcher">
          <el-select v-model="currentLocale" @change="switchLanguage" size="small" style="width: 100px;">
            <el-option label="中文" value="zh"></el-option>
            <el-option label="English" value="en"></el-option>
          </el-select>
        </div>
      </header>
      <main class="content-area">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </el-config-provider>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElConfigProvider } from 'element-plus';
import zhCn from 'element-plus/dist/locale/zh-cn.mjs';
import en from 'element-plus/dist/locale/en.mjs';

const { locale } = useI18n();
const currentLocale = ref(locale.value);

const elementLocale = computed(() => {
  return currentLocale.value === 'zh' ? zhCn : en;
});

const switchLanguage = (lang) => {
  locale.value = lang;
  localStorage.setItem('locale', lang);
};
</script>


<style>
:root {
  --primary-color: #0052cc;
  --accent-color: #ffae00;
  --font-color: #172b4d;
  --light-font-color: #5e6c84;
  --border-color: #dfe1e6;
  --background-color: #f9fafb;
  --white-color: #ffffff;
  --danger-color: #de350b;
  --success-color: #006644;
  --success-bg-color: #e3fcef;
  --shadow-color: rgba(9, 30, 66, 0.15);
  --transition-speed: 0.3s;
}

body {
  background-color: var(--background-color);
  color: var(--font-color);
  margin: 0;
  font-family: 'Montserrat', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.top-bar {
  background: var(--white-color);
  padding: 0 32px;
  height: 64px;
  display: flex;
  justify-content: space-between; /* 让 logo 和切换器分开 */
  align-items: center;
  border-bottom: 1px solid var(--border-color);
  box-shadow: 0 1px 3px var(--shadow-color);
  position: sticky;
  top: 0;
  z-index: 100;
}

.logo-link {
  text-decoration: none;
  cursor: pointer;
}

.logo-title {
  display: flex;
  align-items: center;
  gap: 12px;
}
.logo-title .logo-svg {
  color: var(--primary-color);
}
.logo-title h1 {
  font-size: 22px;
  font-weight: 600;
  color: var(--font-color);
  margin: 0;
}

.content-area {
  padding: 32px;
  flex: 1;
}
.box-card {
  background-color: var(--white-color);
  border-radius: 8px;
  border: 1px solid var(--border-color);
  box-shadow: 0 1px 3px var(--shadow-color);
  transition: all var(--transition-speed) ease;
}
.box-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 5px 15px var(--shadow-color);
}
.box-card .el-card__header {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--font-color);
    border-bottom: 1px solid var(--border-color);
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

<!--
  仙途 (XianTu) - AI驱动的沉浸式修仙文字冒险游戏
  @author 千夜 (qianye60)
  @license CC BY-NC-SA 4.0
  @copyright Copyright (c) 2024-2026 千夜
  GitHub: https://github.com/qianye60
  Bilibili: https://space.bilibili.com/477576651
  商业使用需经作者授权 | Commercial use requires permission
-->
<template>
  <div id="app-container">
    <ToastContainer />
    <GlobalLoadingOverlay />
    <RetryConfirmDialog />
    <DataValidationErrorDialog />
    <StateChangeViewer
      v-if="uiStore.showStateChangeViewer"
      :log="uiStore.stateChangeLogToShow"
      @close="uiStore.closeStateChangeViewer"
    />
    <DetailModal />
    <!-- 全局操作按钮 - 只在非游戏界面显示 -->
    <!--
    <div v-if="!isInGameView" class="global-actions">
      <label class="theme-toggle" @click.prevent="toggleTheme">
        <input type="checkbox" ref="globalThemeCheckbox" :checked="!isDarkMode" />
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 384 512" class="moon">
          <path
            d="M223.5 32C100 32 0 132.3 0 256S100 480 223.5 480c60.6 0 115.5-24.2 155.8-63.4c5-4.9 6.3-12.5 3.1-18.7s-10.1-9.7-17-8.5c-9.8 1.7-19.8 2.6-30.1 2.6c-96.9 0-175.5-78.8-175.5-176c0-65.8 36-123.1 89.3-153.3c6.1-3.5 9.2-10.5 7.7-17.3s-7.3-11.9-14.3-12.5c-6.3-.5-12.6-.8-19-.8z"
          ></path>
        </svg>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" class="sun">
          <path
            d="M361.5 1.2c5 2.1 8.6 6.6 9.6 11.9L391 121l107.9 19.8c5.3 1 9.8 4.6 11.9 9.6s1.5 10.7-1.6 15.2L446.9 256l62.3 90.3c3.1 4.5 3.7 10.2 1.6 15.2s-6.6 8.6-11.9 9.6L391 391 371.1 498.9c-1 5.3-4.6 9.8-9.6 11.9s-10.7 1.5-15.2-1.6L256 446.9l-90.3 62.3c-4.5 3.1-10.2 3.7-15.2 1.6s-8.6-6.6-9.6-11.9L121 391 13.1 371.1c-5.3-1-9.8-4.6-11.9-9.6s-1.5-10.7 1.6-15.2L65.1 256 2.8 165.7c-3.1-4.5-3.7-10.2-1.6-15.2s6.6-8.6 11.9-9.6L121 121 140.9 13.1c1-5.3 4.6-9.8 9.6-11.9s10.7-1.5 15.2 1.6L256 65.1 346.3 2.8c4.5-3.1 10.2-3.7 15.2-1.6zM160 256a96 96 0 1 1 192 0 96 96 0 1 1 -192 0zm224 0a128 128 0 1 0 -256 0 128 128 0 1 0 256 0z"
          ></path>
        </svg>
      </label>
      <label class="fullscreen-toggle" @click.prevent="toggleFullscreen">
        <input type="checkbox" ref="globalFullscreenCheckbox" />
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512" class="expand">
          <path
            d="M32 32C14.3 32 0 46.3 0 64v96c0 17.7 14.3 32 32 32s32-14.3 32-32V96h64c17.7 0 32-14.3 32-32s-14.3-32-32-32H32zM64 352c0-17.7-14.3-32-32-32s-32 14.3-32 32v96c0 17.7 14.3 32 32 32h96c17.7 0 32-14.3 32-32s-14.3-32-32-32H64V352zM320 32c-17.7 0-32 14.3-32 32s14.3 32 32 32h64v64c0 17.7 14.3 32 32 32s32-14.3 32-32V64c0-17.7-14.3-32-32-32H320zM448 352c0-17.7-14.3-32-32-32s-32 14.3-32 32v64H320c-17.7 0-32 14.3-32 32s14.3 32 32 32h96c17.7 0 32-14.3 32-32V352z"
          ></path>
        </svg>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512" class="compress">
          <path
            d="M160 64c0-17.7-14.3-32-32-32s-32 14.3-32 32v64H32c-17.7 0-32 14.3-32 32s14.3 32 32 32h96c17.7 0 32-14.3 32-32V64zM32 320c-17.7 0-32 14.3-32 32s14.3 32 32 32H96v64c0 17.7 14.3 32 32 32s32-14.3 32-32V352c0-17.7-14.3-32-32-32H32zM352 64c0-17.7-14.3-32-32-32s-32 14.3-32 32v96c0 17.7 14.3 32 32 32h96c17.7 0 32-14.3 32-32s-14.3-32-32-32H352V64zM320 320c-17.7 0-32 14.3-32 32v96c0 17.7 14.3 32 32 32s32-14.3 32-32V384h64c17.7 0 32-14.3 32-32s-14.3-32-32-32H320z"
          ></path>
        </svg>
      </label>
      <a
        href="https://ddct.top"
        target="_blank"
        rel="noopener noreferrer"
        class="theme-toggle"
        title="教程"
      >
        <HelpCircle :size="24" />
      </a>
    </div>
    -->

    <!-- 全局操作按钮（合并菜单） - 只在非游戏界面显示 -->
    <ActionMenu v-if="!isInGameView" position="top-right" openTitle="功能" closeTitle="关闭">
      <template #menu="{ close }">
        <button class="action-menu-item" @click="showSettingsModal = true; close()">
          <Settings :size="18" />
          <span>全局设置</span>
        </button>
        <button class="action-menu-item" @click="showAPIModal = true; close()">
          <Plug :size="18" />
          <span>API管理</span>
        </button>
        <button class="action-menu-item" @click="showPromptModal = true; close()">
          <FileText :size="18" />
          <span>提示词管理</span>
        </button>
        <button class="action-menu-item" :class="{ 'is-disabled': !backendReady }" @click="openWorkshop(close)">
          <Store :size="18" />
          <span>创意工坊</span>
        </button>
        <button class="action-menu-item" :class="{ 'is-disabled': !backendReady }" @click="openAccountCenter(close)">
          <UserCircle :size="18" />
          <span>账号中心</span>
        </button>
        <button class="action-menu-item" @click="toggleTheme(); close()">
          <component :is="themeMode === 'dark' ? Sun : Moon" :size="18" />
          <span>{{ themeMode === 'dark' ? '切换亮色' : '切换暗色' }}</span>
        </button>
        <button class="action-menu-item" @click="toggleFullscreen(); close()">
          <component :is="isFullscreenMode ? Minimize2 : Maximize2" :size="18" />
          <span>{{ isFullscreenMode ? '退出全屏' : '进入全屏' }}</span>
        </button>
        <button class="action-menu-item" @click="showHelp(); close()">
          <BookOpen :size="18" />
          <span>教程说明</span>
        </button>
        <button class="action-menu-item sponsor-item" @click="showSponsorModal = true; close()">
          <Heart :size="18" />
          <span>赞助支持</span>
        </button>
      </template>
    </ActionMenu>

    <!-- 路由视图将在这里渲染所有页面 -->
    <router-view v-slot="{ Component }">
      <component
        :is="Component"
        @start-creation="handleStartCreation"
        @show-character-list="handleShowCharacterList"
        @go-to-login="handleGoToLogin"
        @back="handleBack"
        @creation-complete="handleCreationComplete"
        @loggedIn="handleLoggedIn"
        @login="handleGoToLogin"
        @show-help="showHelp"
      />
    </router-view>

    <!-- Settings Modal -->
    <div v-if="showSettingsModal" class="settings-modal-overlay" @click.self="showSettingsModal = false">
      <div class="settings-modal-content">
        <div class="settings-modal-header">
          <h3>设置</h3>
          <button class="close-btn" @click="showSettingsModal = false">&times;</button>
        </div>
        <div class="settings-modal-body">
          <SettingsPanel />
        </div>
      </div>
    </div>

    <!-- API管理弹窗 -->
    <div v-if="showAPIModal" class="settings-modal-overlay" @click.self="showAPIModal = false">
      <div class="settings-modal-content">
        <div class="settings-modal-header">
          <h3>API管理</h3>
          <button class="close-btn" @click="showAPIModal = false">&times;</button>
        </div>
        <div class="settings-modal-body">
          <APIManagementPanel />
        </div>
      </div>
    </div>

    <!-- 提示词管理弹窗 -->
    <div v-if="showPromptModal" class="settings-modal-overlay" @click.self="showPromptModal = false">
      <div class="settings-modal-content prompt-modal-content">
        <div class="settings-modal-header">
          <h3>提示词管理</h3>
          <button class="close-btn" @click="showPromptModal = false">&times;</button>
        </div>
        <div class="settings-modal-body">
          <PromptManagementPanel />
        </div>
      </div>
    </div>

    <!-- 赞助支持弹窗 -->
    <div v-if="showSponsorModal" class="settings-modal-overlay" @click.self="showSponsorModal = false">
      <div class="settings-modal-content sponsor-modal-content">
        <div class="settings-modal-header">
          <h3>赞助支持（自愿）</h3>
          <button class="close-btn" @click="showSponsorModal = false">&times;</button>
        </div>
        <div class="settings-modal-body sponsor-modal-body">
          <div class="sponsor-qr">
            <img src="https://ddct.top/zhifubao.jpg" alt="支付宝赞助二维码" loading="lazy" />
            <span>支付宝</span>
          </div>
          <div class="sponsor-qr">
            <img src="https://ddct.top/weixing.jpg" alt="微信赞助二维码" loading="lazy" />
            <span>微信</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 教程弹窗 -->
    <div v-if="showAuthorModal" class="help-overlay" @click.self="showAuthorModal = false">
      <div class="help-modal">
        <div class="help-header">
          <h2 class="help-title">仙途教程</h2>
          <button class="help-close" @click="showAuthorModal = false">
            <X :size="18" />
          </button>
        </div>

        <div class="help-body">
          <div class="help-version">v{{ displayVersion }}</div>

          <p class="help-desc">AI驱动的沉浸式修仙文字冒险游戏</p>

          <a href="https://ddct.top/" target="_blank" class="help-link-card">
            <Globe :size="18" />
            <span>查看官网介绍</span>
            <ArrowRight :size="16" />
          </a>

          <div class="help-warning">
            <span>⚠️ 游玩尽量使用推荐预设，了解原理后可自行调整</span>
          </div>

          <div class="help-section">
            <h3>核心功能</h3>
            <div class="help-features">
              <span>🎲 智能判定</span>
              <span>🌟 三千大道</span>
              <span>📖 动态剧情</span>
              <span>💾 多存档</span>
              <span>⚔️ 深度RPG</span>
              <span>🗺️ 世界探索</span>
            </div>
          </div>

          <div class="help-footer">
            <div class="help-author">
              <span>作者：千夜</span>
              <a href="https://github.com/qianye60/XianTu" target="_blank">GitHub</a>
            </div>
            <div class="help-license">CC BY-NC-SA 4.0</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watchEffect, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import $ from 'jquery'; // 导入 jQuery
import { BookOpen, X, Maximize2, Minimize2, Moon, Sun, Settings, Store, Globe, UserCircle, Heart, ArrowRight, Plug, FileText } from 'lucide-vue-next'; // 导入图标
import ToastContainer from './components/common/ToastContainer.vue';
import GlobalLoadingOverlay from './components/common/GlobalLoadingOverlay.vue';
import RetryConfirmDialog from './components/common/RetryConfirmDialog.vue';
import DataValidationErrorDialog from './components/common/DataValidationErrorDialog.vue';
import StateChangeViewer from './components/common/StateChangeViewer.vue';
import DetailModal from './components/common/DetailModal.vue';
import ActionMenu from './components/common/ActionMenu.vue';
import SettingsPanel from './components/dashboard/SettingsPanel.vue';
import APIManagementPanel from './components/dashboard/APIManagementPanel.vue';
import PromptManagementPanel from './components/dashboard/PromptManagementPanel.vue';
import './style.css';
import { useCharacterCreationStore } from './stores/characterCreationStore';
import { useCharacterStore } from './stores/characterStore';
import { useUIStore } from './stores/uiStore';
import { useGameStateStore } from './stores/gameStateStore';
import { toast } from './utils/toast';
import { getTavernHelper } from './utils/tavern'; // 添加导入
import { fetchBackendVersion, isBackendConfigured } from '@/services/backendConfig';
import { heartbeatPresenceSilent } from '@/services/presence';
import { getFullscreenElement, requestFullscreen, exitFullscreen, explainFullscreenError } from './utils/fullscreen';
import type { CharacterBaseInfo } from '@/types/game';
import type { CharacterCreationPayload, Talent } from '@/types';

const backendVersion = ref<string | null>(null);

// --- 响应式状态定义 ---
const isLoggedIn = ref(false);
type ThemeMode = 'light' | 'dark';
const normalizeTheme = (value: string | null): ThemeMode => {
  if (value === 'light' || value === 'dark') return value;
  return 'dark';
};
const themeMode = ref<ThemeMode>(normalizeTheme(localStorage.getItem('theme')));
const isFullscreenMode = ref(localStorage.getItem('fullscreen') === 'true');
const showAuthorModal = ref(false);
const showSettingsModal = ref(false);
const showAPIModal = ref(false);
const showSponsorModal = ref(false);
const showPromptModal = ref(false);
const backendReady = ref(isBackendConfigured());
const displayVersion = computed(() => (
  backendReady.value ? (backendVersion.value ?? '同步中') : APP_VERSION
));

// --- 路由与视图管理 ---
const router = useRouter();
const route = useRoute();
type ViewName = 'ModeSelection' | 'CharacterCreation' | 'Login' | 'CharacterManagement' | 'GameView';

// 判断是否在游戏界面（包括所有游戏子路由）
const isInGameView = computed(() => {
  return route.path.startsWith('/game');
});

watch(isInGameView, (inGame) => {
  if (inGame) showSettingsModal.value = false;
});

const switchView = (viewName: ViewName) => {
  const routeMap: Record<ViewName, string> = {
    ModeSelection: '/',
    CharacterCreation: '/creation',
    Login: '/login',
    CharacterManagement: '/management',
    GameView: '/game',
  };
  const path = routeMap[viewName];
  if (path) {
    router.push(path);
  } else {
    console.warn(`未知的视图名称: ${viewName}，将导航至首页。`);
    router.push('/');
  }
};

// --- Pinia Stores ---
const creationStore = useCharacterCreationStore();
const characterStore = useCharacterStore();
const uiStore = useUIStore();
const gameStateStore = useGameStateStore();

// --- 联机在线心跳（进入联机存档即轮询，停掉=下线） ---
const onlineHeartbeatTimer = ref<number | null>(null);
const ONLINE_HEARTBEAT_INTERVAL = 15_000;
const isOnlineSaveActive = computed(() => isInGameView.value && characterStore.activeCharacterProfile?.模式 === '联机');

const stopOnlineHeartbeat = () => {
  if (onlineHeartbeatTimer.value) {
    clearInterval(onlineHeartbeatTimer.value);
    onlineHeartbeatTimer.value = null;
  }
};

const startOnlineHeartbeat = () => {
  stopOnlineHeartbeat();
  if (!backendReady.value) return;
  if (!isOnlineSaveActive.value) return;
  // 立即心跳一次，随后轮询
  void heartbeatPresenceSilent();
  onlineHeartbeatTimer.value = window.setInterval(() => {
    void heartbeatPresenceSilent();
  }, ONLINE_HEARTBEAT_INTERVAL);
};

watch([isOnlineSaveActive, backendReady], () => {
  if (isOnlineSaveActive.value && backendReady.value) startOnlineHeartbeat();
  else stopOnlineHeartbeat();
});

// --- 事件处理器 ---
const handleStartCreation = async (mode: 'single' | 'cloud') => {
  try {
    // 全局封锁联机模式：未配置后端则禁止进入 cloud
    if (mode === 'cloud' && !backendReady.value) {
      toast.info('未配置后端服务器，联机共修不可用');
      switchView('ModeSelection');
      return;
    }
    const targetMode = mode === 'cloud' ? 'cloud' : 'single';
    creationStore.setMode(targetMode);
    if (true) {
      switchView('CharacterCreation');
    }
  } catch (error) {
    console.error("Failed to initialize creation data:", error);
    toast.error("初始化创角数据失败，请稍后重试。");
    switchView('ModeSelection');
  }
};

const handleShowCharacterList = () => {
  // 导航到角色管理页面
  router.push('/management');
};

const handleBack = () => {
  creationStore.resetCharacter();
  switchView('ModeSelection');
};

const handleLoggedIn = () => {
  isLoggedIn.value = true;
  switchView('ModeSelection');
};

const handleGoToLogin = () => {
  if (!backendReady.value) {
    toast.info('未配置后端服务器，登录不可用');
    return;
  }
  switchView('Login');
};

const openWorkshop = (close: () => void) => {
  if (!backendReady.value) {
    toast.info('未配置后端服务器，创意工坊不可用');
    return;
  }
  router.push('/workshop');
  close();
};

const openAccountCenter = (close: () => void) => {
  if (!backendReady.value) {
    toast.info('未配置后端服务器，账号中心不可用');
    return;
  }
  router.push('/account');
  close();
};

const handleCreationComplete = async (rawPayload: CharacterCreationPayload) => {
  console.log('接收到创角指令...', rawPayload);
  console.log('[App.vue] 种族字段检查:', rawPayload.race);

  // 防止重复创建角色
  if (uiStore.isLoading) {
    console.warn('[App.vue] 角色创建已在进行中，忽略重复请求');
    return;
  }

  // 确保 characterStore 已初始化
  if (!characterStore.initialized) {
    console.log('[App.vue] characterStore 未初始化，等待初始化完成...');
    await characterStore.initializeStore();
  }

  uiStore.startLoading('开始铸造法身...');

  // 在外层生成charId，确保重试时使用同一个ID
  const charId = `char_${Date.now()}`;

  const attemptCreation = async (): Promise<boolean> => {
    try {
      // 如果之前创建失败，先清理残留数据
      if (characterStore.rootState.角色列表[charId]) {
        console.log('[角色创建] 检测到残留数据，清理中...');
        delete characterStore.rootState.角色列表[charId];
        await characterStore.commitMetadataToStorage();
      }
      // 从酒馆获取当前活跃的Persona名字
      let personaName: string = '无名道友';
      try {
        const helper = getTavernHelper();
        if (helper) {
          const vars = await helper.getVariables({ type: 'global' });
          // 尝试获取当前Persona的名字
          const name = vars['persona.name'] || vars['name'] || rawPayload.characterName;
          personaName = (typeof name === 'string' ? name : rawPayload.characterName) || '无名道友';
          console.log('[创角完成] 从酒馆Personas获取名字:', personaName);
        }
      } catch (error) {
        console.warn('[创角完成] 无法从酒馆获取Persona名字，使用用户输入:', error);
        personaName = rawPayload.characterName || '无名道友';
      }

      const convertedAttributes = rawPayload.baseAttributes ? {
        根骨: rawPayload.baseAttributes.root_bone ?? 0,
        灵性: rawPayload.baseAttributes.spirituality ?? 0,
        悟性: rawPayload.baseAttributes.comprehension ?? 0,
        气运: rawPayload.baseAttributes.fortune ?? 0,
        魅力: rawPayload.baseAttributes.charm ?? 0,
        心性: rawPayload.baseAttributes.temperament ?? 0
      } : {
        根骨: 0, 灵性: 0, 悟性: 0, 气运: 0, 魅力: 0, 心性: 0
      };

      const baseInfo: CharacterBaseInfo = {
        名字: personaName, // 使用从酒馆获取的Persona名字
        性别: (rawPayload.gender === '女' || rawPayload.gender === '其他' ? rawPayload.gender : '男') as '男' | '女' | '其他',
        出生日期: { 年: 0, 月: 1, 日: 1 }, // 临时占位符，后续由角色初始化流程计算
        种族: rawPayload.race ?? '人族', // 添加种族，使用 ?? 避免空字符串被当作 falsy
        世界: rawPayload.world || { name: '未知世界' } as any,
        天资: rawPayload.talentTier || { name: '凡品' } as any,
        出生: rawPayload.origin || '随机出身',
        灵根: rawPayload.spiritRoot || '随机灵根',
        天赋: (rawPayload.talents?.map((t: Talent) => ({
          id: t.id,
          name: t.name,
          description: t.description || '',
          talent_cost: t.talent_cost,
          rarity: t.rarity
        })) || []) as Talent[],
        先天六司: convertedAttributes,
        后天六司: {
          根骨: 0,
          灵性: 0,
          悟性: 0,
          气运: 0,
          魅力: 0,
          心性: 0,
        }
      };

      const creationPayload = {
        charId: charId, // 使用外层定义的charId
        baseInfo: baseInfo,
        world: rawPayload.world,
        mode: rawPayload.mode as '单机' | '联机',
        age: rawPayload.age,
      };

      const createdBaseInfo = await characterStore.createNewCharacter(creationPayload);
      if (!createdBaseInfo) {
        throw new Error("角色创建失败，请检查 characterStore 的日志。");
      }

      const profile = characterStore.rootState.角色列表[charId];
      if (!profile) {
        throw new Error('严重错误：角色创建后无法在角色列表中找到！');
      }

      const slotKey = profile.模式 === '单机' ? '存档1' : '云端修行';
      characterStore.rootState.当前激活存档 = { 角色ID: charId, 存档槽位: slotKey };
      await characterStore.commitMetadataToStorage();

      await new Promise(resolve => setTimeout(resolve, 500));
      toast.success(`【${createdBaseInfo.名字}】已成功踏入修行之路！`);

      // 跳转到游戏主界面路由
      await router.push('/game');

      // 路由跳转后，尝试恢复全屏状态
      await new Promise(resolve => setTimeout(resolve, 100)); // 等待路由完全加载
      restoreFullscreenIfNeeded();

      return true; // 创建成功
    } catch (error) {
      console.error("角色创建过程出错：", error);
      const errorMessage = error instanceof Error ? error.message : "法身铸造过程中出现意外";

      // 清理失败的角色数据
      if (characterStore.rootState.角色列表[charId]) {
        console.log('[角色创建] 创建失败，清理残留数据...');
        delete characterStore.rootState.角色列表[charId];
        await characterStore.commitMetadataToStorage();
      }

      // 检查是否是用户主动取消的错误
      if (errorMessage.includes('用户选择终止角色创建') || errorMessage.includes('用户选择不继续重试')) {
        console.log('[角色创建] 用户主动取消创建流程');
        toast.info('角色创建已取消');
        return false; // 用户取消，返回到角色创建页面
      }

      // 其他错误，询问用户是否重试
      return new Promise((resolve) => {
        uiStore.showRetryDialog({
          title: '角色创建失败',
          message: `角色创建过程中遇到问题：\n\n${errorMessage}\n\n是否重新尝试创建角色？`,
          confirmText: '重新创建',
          cancelText: '返回主页重新开始',
          onConfirm: async () => {
            console.log('[角色创建] 用户选择重新创建');
            resolve(await attemptCreation()); // 递归重试，使用相同的charId
          },
          onCancel: () => {
            console.log('[角色创建] 用户选择返回主页重新开始');
            toast.info('已返回主页，可重新开始生成');
            creationStore.resetCharacter();
            router.push('/');
            resolve(false);
          }
        });
      });
    }
  };

  try {
    console.log('[App.vue] 开始执行attemptCreation...');

    const success = await attemptCreation();

    console.log('[App.vue] attemptCreation执行完成,结果:', success);

    if (!success) {
      // 用户取消或选择返回创建页面，不做任何操作
      // 保持在当前的角色创建页面
      console.log('[角色创建] 保持在角色创建页面');
    }
  } catch (error) {
    // 最终兜底错误处理
    console.error("[App.vue] 角色创建流程出现严重错误：", error);
    const errorMsg = error instanceof Error ? error.message : String(error);
    toast.error(`角色创建失败: ${errorMsg}`);
    if (errorMsg.includes('超时')) {
      toast.error("创建过程超时,请检查网络连接和SillyTavern状态");
    }
    // 不要自动跳转,让用户可以重试
  } finally {
    console.log('[App.vue] finally: 停止loading并重置创建状态');
    uiStore.stopLoading();
    // 重置 characterCreationStore 中的创建状态，确保按钮可以再次点击
    creationStore.resetCreationState();
  }
};

// --- 主题与全屏 ---
watchEffect(() => {
  document.documentElement.setAttribute('data-theme', themeMode.value);
  localStorage.setItem('theme', themeMode.value);
});

const toggleTheme = () => {
  themeMode.value = themeMode.value === 'dark' ? 'light' : 'dark';
};

const toggleFullscreen = () => {
  if (!getFullscreenElement()) {
    requestFullscreen(document.documentElement as any).then(() => {
      isFullscreenMode.value = true;
      localStorage.setItem('fullscreen', 'true');
      console.log('[全屏] 已进入全屏模式并保存状态');
    }).catch(err => {
      console.error('无法进入全屏模式:', err);
      toast.error(explainFullscreenError(err));
    });
  } else {
    exitFullscreen().then(() => {
      isFullscreenMode.value = false;
      localStorage.setItem('fullscreen', 'false');
      console.log('[全屏] 已退出全屏模式并保存状态');
    }).catch(err => {
      console.error('无法退出全屏模式:', err);
      toast.error(explainFullscreenError(err));
    });
  }
};

// 全屏状态恢复函数
const restoreFullscreenIfNeeded = () => {
  // 大多数浏览器不允许在非用户手势下自动进入全屏，这里仅做“状态纠正”，不强行 requestFullscreen。
  if (isFullscreenMode.value && !getFullscreenElement()) {
    console.log('[全屏] 检测到需要恢复全屏状态');
    console.warn('[全屏] 浏览器限制：无法自动恢复全屏，请手动点击全屏按钮。');
    isFullscreenMode.value = false;
    localStorage.setItem('fullscreen', 'false');
  }
};

const showHelp = () => {
  showAuthorModal.value = true;
};

// --- 生命周期钩子 ---
onMounted(async () => {
  if (backendReady.value) {
    const fetchedVersion = await fetchBackendVersion();
    if (fetchedVersion) {
      backendVersion.value = fetchedVersion;
    }
  }
  // 0. 等待 characterStore 初始化完成（加载 IndexedDB 数据）
  console.log('[App] 等待 characterStore 初始化...');
  await characterStore.initializeStore();
  console.log('[App] ✅ characterStore 初始化完成');

  // 1. Iframe 高度适配 (主动查询父窗口模式，支持多层iframe嵌套)
  let targetParentWindow: Window | null = null; // 记录找到 #chat 的父窗口，用于后续清理

  const updateHeight = () => {
    try {
      // 检查是否在 iframe 中
      if (window.parent === window) {
        return;
      }

      // 标记为iframe环境
      document.documentElement.classList.add('is-iframe');

      // 向上遍历所有父窗口，最多5层，查找包含 #chat 的窗口
      let currentWindow: Window = window;
      for (let i = 0; i < 5; i++) {
        try {
          if (currentWindow.parent && currentWindow.parent !== currentWindow) {
            const externalDiv = $('#chat', currentWindow.parent.document);
            if (externalDiv.length > 0) {
              const height = externalDiv.height();
              if (height) {
                const calculatedHeight = height * 0.9;
                const newMinHeight = `${calculatedHeight}px`;
                document.documentElement.style.minHeight = newMinHeight;
                console.log(`[App.vue] 在第${i + 1}层父窗口找到#chat，应用min-height: ${newMinHeight}`);
                targetParentWindow = currentWindow.parent;
                return;
              }
            }
            currentWindow = currentWindow.parent;
          } else {
            break;
          }
        } catch {
          // 跨域访问失败，停止向上查找
          break;
        }
      }
      console.warn('[App.vue] 在所有可访问的父窗口中未找到 #chat 元素，无法自动调整高度。');
    } catch (e) {
      console.error('[App.vue] 访问父窗口DOM失败，可能是跨域限制。', e);
    }
  };

  // 初始化并监听父窗口大小变化
  updateHeight();
  // 尝试在找到 #chat 的父窗口上监听 resize，如果没找到则用直接父窗口
  try {
    if (targetParentWindow) {
      $(targetParentWindow).on('resize', updateHeight);
    } else if (window.parent !== window) {
      $(parent.window).on('resize', updateHeight);
    }
  } catch {
    // 跨域错误，忽略
  }

  // 2. 主题已由 watchEffect 处理，此处无需操作

  // 3. 全屏状态同步
  const syncFullscreenState = () => {
    const isCurrentlyFullscreen = !!getFullscreenElement();
    isFullscreenMode.value = isCurrentlyFullscreen;
    localStorage.setItem('fullscreen', isCurrentlyFullscreen.toString());
  };

  document.addEventListener('fullscreenchange', syncFullscreenState);
  document.addEventListener('webkitfullscreenchange', syncFullscreenState);
  document.addEventListener('mozfullscreenchange', syncFullscreenState);
  document.addEventListener('MSFullscreenChange', syncFullscreenState);

  syncFullscreenState(); // 初始检查

  // 4. 页面加载时恢复全屏状态（延迟执行，确保页面完全加载）
  setTimeout(() => {
    restoreFullscreenIfNeeded();
  }, 500);

  // 5. 定时保存当前存档 - 每5分钟
  const saveInterval = setInterval(async () => {
    try {
      if (!gameStateStore.isGameLoaded) return;
      const activeSlot = characterStore.activeSaveSlot;
      if (!activeSlot) return;
      console.log('[定时保存] 保存当前存档...');
      await characterStore.saveCurrentGame();
      console.log('[定时保存] 保存成功');
    } catch (error) {
      console.error('[定时保存] 保存失败:', error);
    }
  }, 5 * 60 * 1000); // 5分钟

  // 统一的清理逻辑
  onUnmounted(() => {
    stopOnlineHeartbeat();
    // 清理定时保存定时器
    clearInterval(saveInterval);
    // 清理父窗口resize监听
    try {
      if (targetParentWindow) {
        $(targetParentWindow).off('resize', updateHeight);
      } else if (window.parent !== window) {
        $(parent.window).off('resize', updateHeight);
      }
    } catch {
      // 忽略跨域错误
    }
    // 清理全屏监听
    document.removeEventListener('fullscreenchange', syncFullscreenState);
    document.removeEventListener('webkitfullscreenchange', syncFullscreenState);
    document.removeEventListener('mozfullscreenchange', syncFullscreenState);
    document.removeEventListener('MSFullscreenChange', syncFullscreenState);
  });
});

// 6. 监听路由变化，在路由切换后恢复全屏状态
watch(route, (newRoute, oldRoute) => {
  if (newRoute.path !== oldRoute?.path) {
    console.log(`[全屏] 路由从 ${oldRoute?.path} 切换到 ${newRoute.path}`);
    // 延迟恢复全屏，确保新页面完全加载
    setTimeout(() => {
      restoreFullscreenIfNeeded();
    }, 200);
  }
}, { immediate: false });
</script>

<style scoped>
/* ============ 教程弹窗样式 ============ */
.help-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  padding: 1rem;
}

.help-modal {
  background: var(--color-surface);
  border-radius: 12px;
  max-width: 420px;
  width: 100%;
  max-height: 85vh;
  overflow: hidden;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
  border: 1px solid var(--color-border);
}

.help-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface-light);
}

.help-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text);
}

.help-close {
  background: transparent;
  border: none;
  color: var(--color-text-secondary);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.help-close:hover {
  background: var(--color-surface-hover);
  color: var(--color-text);
}

.help-body {
  padding: 1.25rem;
  overflow-y: auto;
  max-height: calc(85vh - 60px);
}

.help-version {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-primary);
  background: rgba(var(--color-primary-rgb), 0.1);
  padding: 2px 8px;
  border-radius: 4px;
  margin-bottom: 0.5rem;
}

.help-desc {
  margin: 0 0 1rem;
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}

.help-link-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0.75rem 1rem;
  background: var(--color-surface-light);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  color: var(--color-text);
  text-decoration: none;
  margin-bottom: 1rem;
  transition: background 0.2s;
}

.help-link-card:hover {
  background: var(--color-surface-hover);
}

.help-link-card span {
  flex: 1;
  font-size: 0.9rem;
  font-weight: 500;
}

.help-warning {
  padding: 0.75rem;
  background: rgba(251, 191, 36, 0.1);
  border: 1px solid rgba(251, 191, 36, 0.3);
  border-radius: 8px;
  font-size: 0.85rem;
  color: var(--color-text);
  margin-bottom: 1rem;
}

.help-warning strong {
  color: #ef4444;
}

.help-section h3 {
  margin: 0 0 0.75rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text);
}

.help-features {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 1rem;
}

.help-features span {
  font-size: 0.8rem;
  padding: 4px 10px;
  background: var(--color-surface-light);
  border-radius: 6px;
  color: var(--color-text-secondary);
}

.help-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.help-author {
  display: flex;
  align-items: center;
  gap: 8px;
}

.help-author a {
  color: var(--color-primary);
  text-decoration: none;
}

.help-author a:hover {
  text-decoration: underline;
}

.settings-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1500;
  padding: 20px;
}

.game-info-header::before {
  content: '';
  position: absolute;
  inset: 0;
  background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.08'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
  opacity: 0.5;
  animation: bgFloat 25s ease-in-out infinite;
}

@keyframes bgFloat {
  0%, 100% {
    transform: translate(0, 0);
  }
  50% {
    transform: translate(10px, 10px);
  }
}

.game-info-header .header-bg {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 20% 50%, rgba(255, 255, 255, 0.1) 0%, transparent 50%),
              radial-gradient(circle at 80% 80%, rgba(255, 255, 255, 0.08) 0%, transparent 50%);
}

.game-info-header .header-content {
  position: relative;
  z-index: 1;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.game-info-header .game-title {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
}

.game-info-header .title-icon {
  font-size: 1.75rem;
}

.game-info-header .title-text {
  font-size: 2rem;
  font-weight: 900;
  color: #fff;
  letter-spacing: -0.02em;
  text-shadow: 0 4px 16px rgba(0, 0, 0, 0.4),
               0 2px 8px rgba(0, 0, 0, 0.3);
}

.version-subtitle-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.game-info-header .version-tag {
  background: rgba(255, 255, 255, 0.25);
  color: #fff;
  padding: 0.25rem 0.625rem;
  border-radius: 20px;
  font-size: 0.7rem;
  font-weight: 700;
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.game-info-header .game-subtitle {
  color: rgba(255, 255, 255, 0.95);
  font-size: 0.875rem;
  margin: 0;
  font-weight: 500;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
}

.game-info-header .close-btn {
  position: absolute;
  top: 1.25rem;
  right: 1.25rem;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: #fff;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  line-height: 1;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(8px);
}

.game-info-header .close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.08) rotate(90deg);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

/* 内容区域 */
.game-info-body {
  padding: 2rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  background: var(--color-surface);
}

/* 官网介绍卡片 */
.official-intro-card {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 1.5rem;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(139, 92, 246, 0.05) 100%);
  border: 2px solid rgba(99, 102, 241, 0.2);
  border-radius: 20px;
  text-decoration: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.official-intro-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, transparent 100%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.official-intro-card:hover::before {
  opacity: 1;
}

.official-intro-card:hover {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(139, 92, 246, 0.1) 100%);
  border-color: rgba(99, 102, 241, 0.4);
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(99, 102, 241, 0.3),
              0 4px 12px rgba(0, 0, 0, 0.15);
}

.intro-icon-wrapper {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(139, 92, 246, 0.15) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6366f1;
  flex-shrink: 0;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2),
              inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.official-intro-card:hover .intro-icon-wrapper {
  transform: scale(1.15) rotate(-5deg);
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.35),
              inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

.intro-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.intro-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--color-text);
}

.intro-desc {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.intro-arrow {
  color: var(--color-text-secondary);
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.official-intro-card:hover .intro-arrow {
  transform: translateX(6px);
  color: #667eea;
}

/* 警告横幅 */
.warning-banner {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  padding: 1.25rem 1.5rem;
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.12) 0%, rgba(245, 158, 11, 0.08) 100%);
  border: 2px solid rgba(251, 191, 36, 0.3);
  border-left: 4px solid #f59e0b;
  border-radius: 16px;
  font-size: 0.9rem;
  color: var(--color-text);
  box-shadow: 0 2px 12px rgba(251, 191, 36, 0.15);
  backdrop-filter: blur(8px);
}

.warning-banner .warning-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.warning-banner strong {
  color: #dc2626;
  font-weight: 800;
}

/* 信息卡片 */
.info-card {
  background: var(--color-surface-light);
  border: 2px solid var(--color-border);
  border-radius: 18px;
  padding: 1.5rem;
  transition: all 0.3s ease;
}

.info-card:hover {
  border-color: rgba(99, 102, 241, 0.35);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1),
              0 0 0 1px rgba(99, 102, 241, 0.1);
  transform: translateY(-2px);
}

.info-card .card-header {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin-bottom: 1rem;
}

.info-card .card-icon {
  font-size: 1.25rem;
}

.info-card .card-header h4 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 800;
  color: var(--color-text);
}

.info-card .card-desc {
  margin: 0;
  font-size: 0.925rem;
  line-height: 1.7;
  color: var(--color-text-secondary);
}

/* 功能网格 */
.feature-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 0.875rem;
  padding: 1.125rem;
  background: var(--color-surface);
  border-radius: 14px;
  border: 2px solid var(--color-border);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.feature-item::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, transparent 100%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.feature-item:hover::before {
  opacity: 1;
}

.feature-item:hover {
  border-color: rgba(99, 102, 241, 0.4);
  background: var(--color-surface);
  transform: translateY(-3px);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.15),
              0 2px 8px rgba(0, 0, 0, 0.08);
}

.feature-item .feature-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
  filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.15));
  transition: transform 0.3s ease;
  position: relative;
  z-index: 1;
}

.feature-item:hover .feature-icon {
  transform: scale(1.1);
}

.feature-item .feature-text {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  position: relative;
  z-index: 1;
}

.feature-item .feature-text strong {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--color-text);
}

.feature-item .feature-text span {
  font-size: 0.825rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

/* 紧凑型卡片布局 */
.info-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.info-card.compact {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}

.info-card.compact .card-header {
  margin-bottom: 0.75rem;
}

.author-content, .copyright-content {
  font-size: 0.925rem;
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.65rem;
}

.author-name {
  font-weight: 700;
  color: var(--color-text);
}

.github-link {
  color: #6366f1;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 600;
  transition: all 0.2s ease;
}

.github-link:hover {
  color: #8b5cf6;
  text-decoration: underline;
}

/* 深色主题适配 */
[data-theme='dark'] .game-info-header {
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #c026d3 100%);
}

[data-theme='dark'] .warning-banner {
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.15) 0%, rgba(245, 158, 11, 0.1) 100%);
  border-color: rgba(251, 191, 36, 0.35);
  border-left-color: #f59e0b;
}

[data-theme='dark'] .warning-banner strong {
  color: #fca5a5;
}

[data-theme='dark'] .official-intro-card {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(139, 92, 246, 0.08) 100%);
  border-color: rgba(99, 102, 241, 0.25);
}

[data-theme='dark'] .official-intro-card:hover {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(139, 92, 246, 0.15) 100%);
  border-color: rgba(99, 102, 241, 0.45);
}

[data-theme='dark'] .intro-icon-wrapper {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.25) 0%, rgba(139, 92, 246, 0.2) 100%);
  color: #818cf8;
}

/* 滚动条美化 */
.game-info-body::-webkit-scrollbar {
  width: 8px;
}

.game-info-body::-webkit-scrollbar-track {
  background: transparent;
  margin: 8px 0;
}

.game-info-body::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 4px;
  transition: background 0.2s ease;
}

.game-info-body::-webkit-scrollbar-thumb:hover {
  background: var(--color-text-secondary);
}

.settings-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1500;
  padding: 20px;
}

.settings-modal-content {
  background: var(--color-surface, #ffffff);
  border-radius: 14px;
  width: min(760px, 100%);
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.45);
  border: 1px solid var(--color-border);
  animation: modalIn 0.2s ease;
}

.settings-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface-light);
  color: var(--color-text);
}

.settings-modal-header h3 {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 800;
  color: var(--color-text);
}

.settings-modal-body {
  flex: 1;
  overflow: auto;
}

.sponsor-modal-content {
  width: min(540px, 100%);
}

.prompt-modal-content {
  width: min(900px, 100%);
}

.sponsor-modal-body {
  padding: 1rem 1.25rem 1.5rem;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  justify-items: center;
}

.sponsor-qr {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
}

.sponsor-qr img {
  width: 100%;
  max-width: 240px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.2);
  display: block;
}

.sponsor-qr span {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}

.close-btn {
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text);
  font-size: 1.5rem;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background: var(--color-surface-hover);
}
</style>

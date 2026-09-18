<template>
  <div class="api-management-panel">
    <!-- 头部 -->
    <div class="panel-header">
      <div class="header-left">
        <div class="header-icon">🔌</div>
        <div class="header-info">
          <h3 class="panel-title">{{ t('API管理') }}</h3>
          <span class="settings-subtitle">{{ t('管理多个API配置和功能分配') }}</span>
        </div>
      </div>
      <div class="header-actions">
        <button class="action-btn" @click="handleImport">
          <Upload :size="16" />
          <span class="btn-text">{{ t('导入') }}</span>
        </button>
        <button class="action-btn" @click="handleExport">
          <Download :size="16" />
          <span class="btn-text">{{ t('导出') }}</span>
        </button>
        <button class="action-btn primary" @click="showAddDialog = true">
          <Plus :size="16" />
          <span class="btn-text">{{ t('新增') }}</span>
        </button>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="settings-container">
      <!-- API列表区 -->
      <div class="settings-section">
        <div class="section-header">
          <h4 class="section-title">📡 {{ t('API配置列表') }}</h4>
          <span class="section-count">{{ apiStore.apiConfigs.length }} {{ t('个配置') }}</span>
        </div>
        <div class="api-list">
          <div
            v-for="api in apiStore.apiConfigs"
            :key="api.id"
            class="api-card"
            :class="{ disabled: !api.enabled, default: api.id === 'default' }"
          >
            <div class="api-card-header">
              <label class="card-toggle" :title="t('启用/禁用')">
                <input
                  type="checkbox"
                  :checked="api.enabled"
                  @change="toggleAPI(api.id)"
                />
                <span class="toggle-slider"></span>
              </label>
              <div class="api-info">
                <span class="api-name">{{ getDisplayName(api) }}</span>
                <span class="api-provider" v-if="!(isTavernEnvFlag && api.id === 'default')">{{ getProviderName(api.provider) }}</span>
                <span class="api-provider tavern-tag" v-else>🍺 酒馆配置</span>
              </div>
              <div class="api-actions">
                <button class="icon-btn" @click="testAPI(api)" :title="t('测试连接')">
                  <FlaskConical :size="16" :class="{ 'loading-pulse': testingApiId === api.id }" />
                </button>
                <button class="icon-btn" @click="editAPI(api)" :title="t('编辑')">
                  <Edit2 :size="16" />
                </button>
                <button
                  class="icon-btn danger"
                  @click="deleteAPI(api.id)"
                  :title="t('删除')"
                  :disabled="api.id === 'default'"
                >
                  <Trash2 :size="16" />
                </button>
              </div>
            </div>
            <div class="api-card-body">
              <!-- 酒馆模式下默认API显示特殊提示 -->
              <template v-if="isTavernEnvFlag && api.id === 'default'">
                <div class="tavern-api-hint">
                  <span class="hint-text">🍺 API配置由酒馆管理，此处无需配置</span>
                </div>
              </template>
              <template v-else>
                <div class="api-detail">
                  <span class="detail-label">{{ t('模型') }}:</span>
                  <span class="detail-value">{{ api.model }}</span>
                </div>
                <div class="api-detail">
                  <span class="detail-label">{{ t('地址') }}:</span>
                  <span class="detail-value url">{{ api.url || t('默认') }}</span>
                </div>
                <div class="api-detail">
                  <span class="detail-label">{{ t('状态') }}:</span>
                  <span class="detail-value" :class="getAPIStatus(api.id)">
                    {{ getAPIStatusText(api.id) }}
                  </span>
                </div>
                <div class="api-detail" v-if="['openai', 'deepseek', 'zhipu', 'volcengine', 'custom', 'gemini', 'claude'].includes(api.provider)">
                  <label class="json-toggle">
                    <input
                      type="checkbox"
                      :checked="api.forceJsonOutput"
                      @change="toggleForceJson(api.id, ($event.target as HTMLInputElement).checked)"
                    />
                    <span>{{ t('强制JSON') }}</span>
                  </label>
                </div>
              </template>
            </div>
            <div class="api-card-footer" v-if="getAssignedFunctions(api.id).length > 0">
              <span class="assigned-label">{{ t('已分配功能') }}:</span>
              <div class="assigned-tags">
                <span
                  v-for="func in getAssignedFunctions(api.id)"
                  :key="func"
                  class="function-tag"
                >
                  {{ getFunctionName(func) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 功能分配区 -->
      <div class="settings-section">
        <div class="section-header">
          <h4 class="section-title">⚙️ {{ t('功能分配') }}</h4>
          <span class="mode-badge" :class="isTavernEnvFlag ? 'tavern' : 'web'">
            {{ isTavernEnvFlag ? '酒馆模式' : '网页模式' }}
          </span>
        </div>

        <!-- 模式说明 -->
        <div class="mode-hint" :class="isTavernEnvFlag ? 'tavern' : 'web'">
          <div class="hint-icon">{{ isTavernEnvFlag ? '🍺' : '🌐' }}</div>
          <div class="hint-content" v-if="isTavernEnvFlag">
            <strong>酒馆模式：</strong>主游戏流程（main）<em>永远</em>使用酒馆配置的API。
            辅助功能如需使用独立API，请在下方分配非"默认API"的配置。
            <br/>
            <span class="hint-example">提示：未配置独立API的辅助功能也会走酒馆API，实现请求合并。</span>
          </div>
          <div class="hint-content" v-else>
            <strong>网页模式：</strong>所有功能都通过配置的自定义API调用。
            可为不同功能分配不同的API，实现灵活调度。
            <br/>
            <span class="hint-example">提示：配置了相同API的功能会自动合并请求，节省调用次数。</span>
          </div>
        </div>

        <div class="pipeline-hint">
          <div class="hint-icon">💡</div>
          <div class="hint-content">
            <strong>智能流水线：</strong>“主流程”默认一次性生成正文/行动选项/指令（1次调用）。
            若开启“分步生成”，系统会拆成两次调用：第1步生成正文，第2步生成指令JSON（是否使用独立API由「指令生成」分配决定）。
            <br/>
            <span class="hint-example">示例：关闭分步生成=1次调用；开启分步生成=2次调用（第2步可单独指定模型以提高JSON稳定性）</span>
          </div>
        </div>
        <div class="settings-list">
          <!-- ========== 全局设置 ========== -->
          <div class="function-group-header">
            <h5 class="group-title">⚙️ 全局设置</h5>
            <span class="group-desc">影响所有API调用的通用配置</span>
          </div>

          <!-- 重试次数设置 -->
          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-name">重试次数</label>
              <span class="setting-desc">API调用失败后的重试次数。0=不重试，1=重试1次，以此类推</span>
            </div>
            <div class="setting-control">
              <input
                type="number"
                :value="retryCount"
                @input="updateRetryCount(($event.target as HTMLInputElement).value)"
                min="0"
                max="5"
                class="setting-number-input"
              />
              <span class="input-hint">次</span>
            </div>
          </div>

          <!-- ========== 主游戏流程（3个） ========== -->
          <div class="function-group-header">
            <h5 class="group-title">🎮 主游戏流程</h5>
            <span class="group-desc">控制游戏主要生成流程的API分配</span>
          </div>

          <!-- 1. 主游戏流程 -->
          <div
            class="setting-item"
            :class="{ 'tavern-locked': isTavernEnvFlag && apiStore.apiAssignments.find(a => a.type === 'main') }"
          >
            <div class="setting-info">
              <label class="setting-name">
                {{ getFunctionName('main') }}
                <span v-if="isTavernEnvFlag" class="locked-badge">🔒 酒馆API</span>
              </label>
              <span class="setting-desc">{{ getFunctionDesc('main') }}</span>
            </div>
            <div class="setting-control">
              <template v-if="isTavernEnvFlag">
                <span class="locked-text">使用酒馆配置</span>
              </template>
              <template v-else>
                <select
                  :value="apiStore.apiAssignments.find(a => a.type === 'main')?.apiId"
                  @change="updateAssignment('main', ($event.target as HTMLSelectElement).value)"
                  class="setting-select"
                >
                  <option
                    v-for="api in apiStore.enabledAPIs"
                    :key="api.id"
                    :value="api.id"
                  >
                    {{ getDisplayName(api) }}
                  </option>
                </select>
              </template>
            </div>
          </div>

          <!-- 2. 指令生成 -->
          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-name">{{ getFunctionName('instruction_generation') }}</label>
              <span class="setting-desc">{{ getFunctionDesc('instruction_generation') }}</span>
            </div>
            <div class="setting-control">
              <select
                :value="apiStore.apiAssignments.find(a => a.type === 'instruction_generation')?.apiId"
                @change="updateAssignment('instruction_generation', ($event.target as HTMLSelectElement).value)"
                class="setting-select"
              >
                <option
                  v-for="api in apiStore.enabledAPIs"
                  :key="api.id"
                  :value="api.id"
                >
                  {{ getDisplayName(api) }}
                </option>
              </select>
            </div>
          </div>

          <!-- 分步/指令API提示（避免“主API/指令API”语义混淆） -->
          <div v-if="splitResponseGeneration && apiStore.shouldEnableSplitGeneration" class="auto-split-hint">
            <div class="hint-icon">⚡</div>
            <div class="hint-text">
              <strong>分步生成将使用独立「指令生成」API：</strong>
              第1步（正文/行动）走主流程API；第2步（tavern_commands 等结构化JSON）走你选择的「指令生成」API。
            </div>
          </div>
          <div v-else-if="splitResponseGeneration" class="auto-split-hint">
            <div class="hint-icon">⚡</div>
            <div class="hint-text">
              <strong>分步生成已开启：</strong>
              当前未配置独立「指令生成」API，第2步将复用主流程API。
            </div>
          </div>
          <div v-else-if="apiStore.shouldEnableSplitGeneration" class="auto-split-hint warn">
            <div class="hint-icon">ℹ️</div>
            <div class="hint-text">
              <strong>已配置独立「指令生成」API：</strong>
              但“分步生成”当前关闭，因此该配置不会生效；开启分步生成后才会用于第2步。
            </div>
          </div>

          <!-- 分步生成第2步流式设置 -->
          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-name">分步第2步流式传输</label>
              <span class="setting-desc">分步生成时，第2步（指令生成）是否使用流式传输（默认关闭，部分API不支持流式）</span>
            </div>
            <div class="setting-control">
              <label class="setting-switch">
                <input
                  type="checkbox"
                  :checked="apiStore.aiGenerationSettings.splitStep2Streaming"
                  @change="apiStore.updateAIGenerationSettings({ splitStep2Streaming: ($event.target as HTMLInputElement).checked })"
                />
                <span class="switch-slider"></span>
              </label>
            </div>
          </div>

          <!-- ========== 辅助功能（6个） ========== -->
          <div class="function-group-header">
            <h5 class="group-title">🛠️ 辅助功能</h5>
            <span class="group-desc">可选的辅助生成功能，支持Raw/标准模式切换</span>
          </div>

          <!-- 辅助功能列表 -->
            <div
              v-for="funcType in ['memory_summary', 'text_optimization', 'world_generation', 'event_generation', 'sect_generation', 'crafting', 'embedding']"
              :key="funcType"
              class="setting-item"
            >
            <div class="setting-info">
              <label class="setting-name">
                {{ getFunctionName(funcType as APIUsageType) }}
                <span v-if="funcType !== 'embedding'" class="mode-indicator">
                  {{ apiStore.getFunctionMode(funcType as APIUsageType) === 'raw' ? 'Raw' : '标准' }}
                </span>
              </label>
              <span class="setting-desc">{{ getFunctionDesc(funcType as APIUsageType) }}</span>
            </div>
            <div class="setting-control">
              <div class="control-row">
                <!-- embedding 功能的启用开关 -->
                <div v-if="funcType === 'embedding'" class="inline-toggle">
                  <label class="toggle-label">启用</label>
                  <label class="setting-switch compact">
                    <input
                      type="checkbox"
                      v-model="vectorMemoryEnabled"
                      @change="onVectorMemoryChange"
                    />
                    <span class="switch-slider"></span>
                  </label>
                </div>

                <!-- text_optimization 功能的启用开关 -->
                <div v-if="funcType === 'text_optimization'" class="inline-toggle">
                  <label class="toggle-label">启用</label>
                  <label class="setting-switch compact">
                    <input
                      type="checkbox"
                      :checked="apiStore.isFunctionEnabled('text_optimization')"
                      @change="apiStore.setFunctionEnabled('text_optimization', ($event.target as HTMLInputElement).checked)"
                    />
                    <span class="switch-slider"></span>
                  </label>
                </div>

                <!-- API分配下拉框 -->
                <select
                  :value="apiStore.apiAssignments.find(a => a.type === funcType)?.apiId"
                  @change="updateAssignment(funcType as APIUsageType, ($event.target as HTMLSelectElement).value)"
                  class="setting-select"
                  :class="{ 'disabled-hint': funcType === 'embedding' && !vectorMemoryEnabled }"
                  :disabled="funcType === 'embedding' && !vectorMemoryEnabled"
                  :title="funcType === 'embedding' && !vectorMemoryEnabled ? '请先启用向量检索功能' : ''"
                >
                  <option value="default">使用主API</option>
                  <option
                    v-for="api in apiStore.apiConfigs.filter(a => a.id !== 'default')"
                    :key="api.id"
                    :value="api.id"
                    :disabled="!api.enabled"
                  >
                    {{ getDisplayName(api) }}{{ !api.enabled ? ' (未启用)' : '' }}
                  </option>
                </select>

                <!-- Raw/标准模式选择（仅非embedding功能且为酒馆模式时显示） -->
                <select
                  v-if="funcType !== 'embedding' && isTavernEnvFlag"
                  :value="apiStore.getFunctionMode(funcType as APIUsageType)"
                  @change="updateFunctionMode(funcType as APIUsageType, ($event.target as HTMLSelectElement).value as any)"
                  class="setting-select mode-select"
                >
                  <option value="raw">Raw</option>
                  <option value="standard">标准</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- AI生成设置 -->
      <div class="settings-section">
        <div class="section-header">
          <h4 class="section-title">🤖 {{ t('AI生成设置') }}</h4>
        </div>
        <div class="settings-list">
          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-name">{{ t('流式输出') }}</label>
              <span class="setting-desc">{{ t('开启后AI响应逐字显示') }}</span>
            </div>
            <div class="setting-control">
              <label class="setting-switch">
                <input type="checkbox" v-model="streamingEnabled" />
                <span class="switch-slider"></span>
              </label>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-info">
              <label class="setting-name">{{ t('分步生成') }}</label>
              <span class="setting-desc">{{ t('开启后AI分两步生成：先输出正文，再生成指令') }}</span>
            </div>
            <div class="setting-control">
              <label class="setting-switch">
                <input type="checkbox" v-model="splitResponseGeneration" @change="saveSplitResponseSetting" />
                <span class="switch-slider"></span>
              </label>
            </div>
          </div>

          <div v-if="vectorMemoryEnabled" class="setting-item">
            <div class="setting-info">
              <label class="setting-name">{{ t('检索数量') }}</label>
              <span class="setting-desc">{{ t('每次检索的最大记忆条数') }}</span>
            </div>
            <div class="setting-control">
              <select v-model.number="vectorMemoryMaxCount" @change="onVectorMemoryChange" class="setting-select">
                <option :value="5">5条</option>
                <option :value="10">10条（推荐）</option>
                <option :value="15">15条</option>
                <option :value="20">20条</option>
              </select>
            </div>
          </div>

          <div v-if="isTavernEnvFlag" class="setting-item">
            <div class="setting-info">
              <label class="setting-name">{{ t('🔞 成人内容模式') }}</label>
              <span class="setting-desc">{{ t('启用后NPC可能产生成人向互动内容') }}</span>
            </div>
            <div class="setting-control">
              <label class="setting-switch">
                <input type="checkbox" v-model="nsfwMode" @change="saveNsfwSettings" />
                <span class="switch-slider"></span>
              </label>
            </div>
          </div>

          <div v-if="isTavernEnvFlag && nsfwMode" class="setting-item">
            <div class="setting-info">
              <label class="setting-name">{{ t('🔞 性别偏好过滤') }}</label>
              <span class="setting-desc">{{ t('过滤参与成人互动的NPC性别') }}</span>
            </div>
            <div class="setting-control">
              <select v-model="nsfwGenderFilter" @change="saveNsfwSettings" class="setting-select">
                <option value="female">{{ t('仅女性') }}</option>
                <option value="male">{{ t('仅男性') }}</option>
                <option value="all">{{ t('不限性别') }}</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 新增/编辑API弹窗 -->
    <div v-if="showAddDialog || showEditDialog" class="modal-overlay" @click.self="closeDialogs">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ showEditDialog ? t('编辑API配置') : t('新增API配置') }}</h3>
          <button class="close-btn" @click="closeDialogs">
            <X :size="20" />
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>{{ t('配置名称') }}</label>
            <input v-model="editingAPI.name" class="form-input" :placeholder="t('例如：主力API')" />
          </div>

          <div class="form-group">
            <label>{{ t('API提供商') }}</label>
            <select v-model="editingAPI.provider" class="form-select" @change="onProviderChange">
              <option value="openai">OpenAI</option>
              <option value="claude">Claude</option>
              <option value="gemini">Gemini</option>
              <option value="deepseek">DeepSeek</option>
              <option value="zhipu">智谱AI</option>
              <option value="volcengine">火山引擎(豆包)</option>
              <option value="siliconflow-embedding">硅基流动(Embedding)</option>
              <option value="custom">{{ t('自定义(OpenAI兼容)') }}</option>
            </select>
          </div>

          <div class="form-group">
            <label>{{ t('API地址') }}</label>
            <input
              v-model="editingAPI.url"
              class="form-input"
              :placeholder="getProviderPresetUrl(editingAPI.provider || 'openai')"
            />
          </div>

          <div class="form-group">
            <label>{{ t('API密钥') }}</label>
            <input
              v-model="editingAPI.apiKey"
              type="password"
              class="form-input"
              placeholder="sk-..."
            />
          </div>

          <div class="form-group">
            <label>{{ t('模型名称') }}</label>
            <div class="model-select-wrapper">
              <div class="model-input-row">
                <input
                  v-model="editingAPI.model"
                  class="form-input"
                  :placeholder="getProviderPresetModel(editingAPI.provider || 'openai')"
                  @focus="showModelDropdown = true"
                  @input="filterModels"
                />
                <button class="utility-btn" @click="fetchModelsForEditing" :disabled="isFetchingModels">
                  <RefreshCw :size="16" :class="{ 'loading-pulse': isFetchingModels }" />
                </button>
              </div>
              <div v-if="showModelDropdown && filteredModels.length > 0" class="model-dropdown">
                <div
                  v-for="model in filteredModels"
                  :key="model"
                  class="model-dropdown-item"
                  :class="{ active: editingAPI.model === model }"
                  @mousedown.prevent="selectModel(model)"
                >
                  {{ model }}
                </div>
              </div>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group half">
              <label>{{ t('温度参数') }}</label>
              <input
                v-model.number="editingAPI.temperature"
                type="number"
                class="form-input"
                min="0"
                max="2"
                step="0.1"
              />
            </div>
            <div class="form-group half">
              <label>{{ t('最大Token数') }}</label>
              <input
                v-model.number="editingAPI.maxTokens"
                type="number"
                class="form-input"
                min="100"
                :max="getProviderMaxOutputTokens(editingAPI.provider || 'openai')"
              />
            </div>
          </div>

          <!-- 强制JSON输出选项 -->
          <div
            class="form-group"
            v-if="['openai', 'deepseek', 'zhipu', 'volcengine', 'custom', 'gemini', 'claude'].includes(editingAPI.provider || 'openai')"
          >
            <label class="checkbox-label">
              <input
                type="checkbox"
                v-model="editingAPI.forceJsonOutput"
                class="form-checkbox"
              />
              <span>{{ t('强制JSON格式输出') }}</span>
            </label>
            <div class="form-hint">
              {{ t('启用后，API将强制返回JSON格式。需要在提示词中包含"json"字样并给出JSON格式样例。') }}
              <br/>
              <span class="hint-warning" v-if="editingAPI.provider === 'gemini'">
                ℹ️ {{ t('Gemini使用response_mime_type实现JSON模式') }}
              </span>
              <span class="hint-warning" v-else-if="editingAPI.provider === 'claude'">
                ℹ️ {{ t('Claude使用prefill技巧实现JSON模式') }}
              </span>
              <span class="hint-warning" v-else>
                ⚠️ {{ t('仅支持OpenAI兼容API（如DeepSeek）。使用前请确保提示词中包含JSON格式说明。') }}
              </span>
              <br v-if="editingAPI.provider === 'custom'"/>
              <span class="hint-warning" v-if="editingAPI.provider === 'custom'">
                ⚠️ {{ t('重要：如果使用New-API等中转服务，需确认底层模型支持！') }}
                <br/>
                {{ t('• 底层是OpenAI/DeepSeek/Qwen/GLM-4: ✅ 通常可用') }}
                <br/>
                {{ t('• 底层是Gemini/Claude/旧模型: ❌ 可能报错') }}
                <br/>
                <strong>{{ t('• 务必先用"测试连接"验证！') }}</strong>
              </span>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="closeDialogs">{{ t('取消') }}</button>
          <button class="btn-confirm" @click="saveAPI">{{ t('保存') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { Plus, Edit2, Trash2, Upload, Download, X, RefreshCw, FlaskConical } from 'lucide-vue-next';
import { useAPIManagementStore, type APIConfig, type APIUsageType } from '@/stores/apiManagementStore';
import { aiService, API_PROVIDER_PRESETS, type APIProvider } from '@/services/aiService';
import { useUIStore } from '@/stores/uiStore';
import { vectorMemoryService } from '@/services/vectorMemoryService';
import { getNsfwSettingsFromStorage, type NsfwGenderFilter } from '@/utils/nsfw';
import { isTavernEnv } from '@/utils/tavern';
import { toast } from '@/utils/toast';
import { useI18n } from '@/i18n';

const { t } = useI18n();
const apiStore = useAPIManagementStore();
const uiStore = useUIStore();

// 初始化加载
onMounted(() => {
  apiStore.loadFromStorage();
  loadAIServiceConfig();
  loadLocalSettings();
  loadVectorMemoryConfig();

});

// AI服务通用配置
const streamingEnabled = ref(true);
const splitResponseGeneration = ref(false); // 分步生成开关，默认关闭
const vectorMemoryEnabled = ref(false);
const vectorMemoryMaxCount = ref(10);
const isTavernEnvFlag = ref(isTavernEnv());
const nsfwMode = ref(true);
const nsfwGenderFilter = ref<NsfwGenderFilter>('female');
const retryCount = ref(1); // 重试次数，默认1次

const readGameSettings = (): Record<string, unknown> => {
  try {
    const raw = localStorage.getItem('dad_game_settings');
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
};

const saveGameSettings = (updates: Record<string, unknown>) => {
  const base = readGameSettings();
  localStorage.setItem('dad_game_settings', JSON.stringify({ ...base, ...updates }));
};

const loadAIServiceConfig = () => {
  const config = aiService.getConfig();
  streamingEnabled.value = config.streaming !== false;
};

const loadLocalSettings = () => {
  const nsfwSettings = getNsfwSettingsFromStorage();
  nsfwMode.value = nsfwSettings.nsfwMode;
  nsfwGenderFilter.value = nsfwSettings.nsfwGenderFilter;
  isTavernEnvFlag.value = isTavernEnv();

  // 加载分步生成设置
  const gameSettings = readGameSettings();
  splitResponseGeneration.value = gameSettings.splitResponseGeneration === true; // 默认关闭

  // 加载重试次数设置
  const savedRetryCount = gameSettings.retryCount;
  if (typeof savedRetryCount === 'number' && savedRetryCount >= 0 && savedRetryCount <= 5) {
    retryCount.value = savedRetryCount;
  } else {
    retryCount.value = 1; // 默认1次
  }
};

const saveSplitResponseSetting = () => {
  saveGameSettings({
    splitResponseGeneration: splitResponseGeneration.value,
  });
};

const saveNsfwSettings = () => {
  saveGameSettings({
    enableNsfwMode: nsfwMode.value,
    nsfwGenderFilter: nsfwGenderFilter.value,
  });
};

const updateRetryCount = (value: string) => {
  const num = parseInt(value, 10);
  if (isNaN(num) || num < 0 || num > 5) {
    toast.error('重试次数必须在 0-5 之间');
    return;
  }
  retryCount.value = num;
  saveGameSettings({ retryCount: num });

  // 更新 aiService 的配置
  const currentConfig = aiService.getConfig();
  aiService.saveConfig({ ...currentConfig, maxRetries: num });

  toast.success(`重试次数已设置为 ${num} 次`);
};

const loadVectorMemoryConfig = () => {
  const config = vectorMemoryService.getConfig();
  // 🔥 同时检查 apiStore 中的 embedding 启用状态，两者需要同步
  const storeEnabled = apiStore.isFunctionEnabled('embedding');
  vectorMemoryEnabled.value = config.enabled && storeEnabled;
  vectorMemoryMaxCount.value = config.maxRetrieveCount;
};

const onVectorMemoryChange = () => {
  // 🔥 同时更新 vectorMemoryService 和 apiStore 中的 embedding 启用状态
  vectorMemoryService.saveConfig({
    enabled: vectorMemoryEnabled.value,
    maxRetrieveCount: vectorMemoryMaxCount.value,
  });
  // 同步到 apiStore，确保 embedding 功能启用状态一致
  apiStore.setFunctionEnabled('embedding', vectorMemoryEnabled.value);

  if (vectorMemoryEnabled.value) {
    toast.success(`向量记忆检索已启用，每次最多检索 ${vectorMemoryMaxCount.value} 条`);
  } else {
    toast.info('向量记忆检索已禁用，将使用全量发送模式');
  }
};

// 监听通用配置变化
watch(streamingEnabled, () => {
  aiService.saveConfig({
    streaming: streamingEnabled.value
  });
  uiStore.useStreaming = streamingEnabled.value;
});

// 对话框状态
const showAddDialog = ref(false);
const showEditDialog = ref(false);
const editingAPI = ref<Partial<APIConfig>>({
  name: '',
  provider: 'openai',
  url: '',
  apiKey: '',
  model: 'gpt-4o',
  temperature: 0.7,
  maxTokens: 16000,
  enabled: true
});
const editingAPIId = ref<string | null>(null);

// 模型获取状态
const isFetchingModels = ref(false);
const availableModels = ref<string[]>([]);
const showModelDropdown = ref(false);

// 过滤后的模型列表
const filteredModels = computed(() => {
  const query = editingAPI.value.model?.toLowerCase() || '';
  if (!query) return availableModels.value;
  return availableModels.value.filter(m => m.toLowerCase().includes(query));
});

// 过滤模型
const filterModels = () => {
  showModelDropdown.value = true;
};

// 选择模型
const selectModel = (model: string) => {
  editingAPI.value.model = model;
  showModelDropdown.value = false;
};

// API测试状态
const testingApiId = ref<string | null>(null);
const apiTestResults = ref<Record<string, 'success' | 'fail' | null>>({});

// 获取提供商名称
const getProviderName = (provider: APIProvider): string => {
  return API_PROVIDER_PRESETS[provider]?.name || provider;
};

/**
 * 获取API的显示名称
 * 酒馆模式下，默认API显示为"酒馆API"
 */
const getDisplayName = (api: APIConfig): string => {
  if (isTavernEnvFlag.value && api.id === 'default') {
    return '🍺 酒馆API';
  }
  return api.name;
};

const getProviderPresetUrl = (provider: APIProvider): string => {
  return API_PROVIDER_PRESETS[provider]?.url || 'https://api.openai.com';
};

const getProviderPresetModel = (provider: APIProvider): string => {
  return API_PROVIDER_PRESETS[provider]?.defaultModel || 'gpt-4o';
};

const getProviderPresetMaxTokens = (provider: APIProvider): number => {
  return API_PROVIDER_PRESETS[provider]?.defaultMaxTokens || 16000;
};

const getProviderMaxOutputTokens = (provider: APIProvider): number => {
  return API_PROVIDER_PRESETS[provider]?.maxOutputTokens || 384000;
};

// 当提供商变化时更新默认值
const onProviderChange = () => {
  const preset = API_PROVIDER_PRESETS[editingAPI.value.provider as APIProvider];
  if (preset) {
    editingAPI.value.url = preset.url;
    editingAPI.value.model = preset.defaultModel;
    editingAPI.value.maxTokens = preset.defaultMaxTokens || 16000;
  }
};

// 获取功能名称
const getFunctionName = (type: APIUsageType): string => {
  const names: Record<APIUsageType, string> = {
    main: '主流程（正文/行动）',
    memory_summary: '记忆总结',
    embedding: '向量检索(Embedding)',
    text_optimization: '文本优化',
    instruction_generation: '指令生成（分步第2步）',
    world_generation: '世界生成',
      event_generation: '事件生成',
      sect_generation: '宗门生成',
      crafting: '炼丹炼器'
    };
  return names[type] || type;
};

// 获取功能描述
const getFunctionDesc = (type: APIUsageType): string => {
  if (isTavernEnvFlag.value) {
    // 酒馆模式的描述
    const descs: Record<APIUsageType, string> = {
      main: '游戏主要交互（正文/行动选项/指令；酒馆模式下永远使用酒馆API）',
      memory_summary: '压缩总结历史记忆，包括NPC记忆（可配置Raw/标准模式）',
      embedding: '向量记忆语义检索用Embedding（需要embedding模型，建议使用独立API）',
      text_optimization: '优化AI输出文本（可配置Raw/标准模式）',
      instruction_generation: '分步生成的第2步：生成 tavern_commands 等结构化JSON（可单独指定更擅长JSON的模型）',
      world_generation: '生成世界、地点等（可配置Raw/标准模式）',
        event_generation: '生成世界事件（可配置Raw/标准模式）',
        sect_generation: '生成宗门内容如藏经阁、贡献商店（可配置Raw/标准模式）',
        crafting: '炼丹炼器系统（可配置Raw/标准模式）'
      };
    return descs[type] || '';
  } else {
    // 网页模式的描述
    const descs: Record<APIUsageType, string> = {
      main: '游戏主要交互与叙事生成（正文/行动选项/指令等的默认承载）',
      memory_summary: '压缩总结历史记忆，包括NPC记忆（可用快速模型节省成本）',
      embedding: '向量记忆语义检索用Embedding（需要embedding模型）',
      text_optimization: '优化AI输出的文本质量',
      instruction_generation: '分步生成的第2步：生成 tavern_commands 等结构化JSON（可单独指定更擅长JSON的模型）',
      world_generation: '生成世界、地点等内容（开局时使用）',
        event_generation: '生成世界事件（可用快速模型）',
        sect_generation: '生成宗门内容如藏经阁、贡献商店（可用快速模型）',
        crafting: '炼丹炼器系统（可用快速模型）'
      };
    return descs[type] || '';
  }
};

const updateFunctionMode = (type: APIUsageType, mode: 'raw' | 'standard') => {
  apiStore.setFunctionMode(type, mode);
  toast.success(`${getFunctionName(type)} ${t('模式已设置为')} ${mode}`);
};

// 获取已分配到某API的功能列表
const getAssignedFunctions = (apiId: string): APIUsageType[] => {
  return apiStore.apiAssignments
    .filter(a => a.apiId === apiId)
    .map(a => a.type);
};

// 获取API状态
const getAPIStatus = (apiId: string): string => {
  const result = apiTestResults.value[apiId];
  if (result === 'success') return 'success';
  if (result === 'fail') return 'fail';
  return 'unknown';
};

const getAPIStatusText = (apiId: string): string => {
  const result = apiTestResults.value[apiId];
  if (result === 'success') return t('连接正常');
  if (result === 'fail') return t('连接失败');
  return t('未测试');
};

// 切换API启用状态
const toggleAPI = (id: string) => {
  apiStore.toggleAPI(id);
};

// 切换强制JSON
const toggleForceJson = (id: string, enabled: boolean) => {
  apiStore.updateAPI(id, { forceJsonOutput: enabled });
  toast.success(enabled ? t('已启用强制JSON') : t('已关闭强制JSON'));
};

// 编辑API
const editAPI = (api: APIConfig) => {
  editingAPI.value = { ...api };
  editingAPIId.value = api.id;
  showEditDialog.value = true;
};

// 删除API
const deleteAPI = (id: string) => {
  if (id === 'default') {
    toast.error(t('不能删除默认API配置'));
    return;
  }

  uiStore.showRetryDialog({
    title: t('确认删除'),
    message: t('确定要删除这个API配置吗？使用它的功能将自动回退到默认API。'),
    confirmText: t('删除'),
    cancelText: t('取消'),
    onConfirm: () => {
      apiStore.deleteAPI(id);
      toast.success(t('API配置已删除'));
    },
    onCancel: () => {}
  });
};

// 测试API连接
const testAPI = async (api: APIConfig) => {
  if (testingApiId.value) return;

  testingApiId.value = api.id;
  try {
    // 根据是否启用强制JSON选择不同的测试提示词
    const testPrompt = api.forceJsonOutput
      ? '你正在进行API连通性测试。请按照以下JSON格式输出测试结果：\n\n示例JSON格式：\n{"status": "ok", "message": "仙途本-连通测试-OK"}\n\n请严格按照上述JSON格式输出。'
      : '你正在进行API连通性测试。请仅输出：仙途本-连通测试-OK';

    // 使用直接测试方法，绕过环境检测
    const response = await aiService.testAPIDirectly({
      provider: api.provider,
      url: api.url,
      apiKey: api.apiKey,
      model: api.model,
      temperature: api.temperature,
      maxTokens: 1000,
      forceJsonOutput: api.forceJsonOutput
    }, testPrompt);

    // 根据是否启用强制JSON进行不同的验证
    let ok = false;
    if (api.forceJsonOutput) {
      try {
        const jsonResponse = JSON.parse(response);
        ok = jsonResponse.status === 'ok' ||
             (jsonResponse.message && jsonResponse.message.includes('仙途本')) ||
             response.toLowerCase().includes('ok');
      } catch {
        // JSON解析失败，尝试普通文本匹配
        ok = response.toLowerCase().includes('仙途本') || response.toLowerCase().includes('ok');
      }
    } else {
      ok = response.toLowerCase().includes('仙途本') || response.toLowerCase().includes('ok');
    }

    apiTestResults.value[api.id] = ok ? 'success' : 'fail';

    if (ok) {
      toast.success(`${api.name} ${t('连接成功')}`);
    } else {
      toast.warning(`${api.name} ${t('响应异常')}`);
    }
  } catch (error) {
    apiTestResults.value[api.id] = 'fail';
    toast.error(`${api.name} ${t('连接失败')}: ${error instanceof Error ? error.message : '未知错误'}`);
  } finally {
    testingApiId.value = null;
  }
};

// 获取模型列表
const fetchModelsForEditing = async () => {
  if (isFetchingModels.value) return;
  if (!editingAPI.value.url || !editingAPI.value.apiKey) {
    toast.warning(t('请先填写API地址和密钥'));
    return;
  }

  isFetchingModels.value = true;
  try {
    // 临时设置配置
    const currentConfig = aiService.getConfig();
    aiService.saveConfig({
      mode: 'custom',
      customAPI: {
        provider: editingAPI.value.provider as APIProvider,
        url: editingAPI.value.url,
        apiKey: editingAPI.value.apiKey,
        model: editingAPI.value.model || 'gpt-4o',
        temperature: editingAPI.value.temperature || 0.7,
        maxTokens: editingAPI.value.maxTokens || 16000
      }
    });

    const models = await aiService.fetchModels();
    availableModels.value = models;
    showModelDropdown.value = true;
    toast.success(`${t('获取到')} ${models.length} ${t('个模型')}`);

    // 恢复配置
    aiService.saveConfig(currentConfig);
  } catch (error) {
    toast.error(t('获取模型列表失败'));
  } finally {
    isFetchingModels.value = false;
  }
};

// 保存API配置
const saveAPI = () => {
  if (!editingAPI.value.name) {
    toast.warning(t('请填写配置名称'));
    return;
  }

  if (showEditDialog.value && editingAPIId.value) {
    // 编辑模式
    apiStore.updateAPI(editingAPIId.value, editingAPI.value);
    toast.success(t('API配置已更新'));
  } else {
    // 新增模式
    const newConfig = {
      name: editingAPI.value.name!,
      provider: editingAPI.value.provider as APIProvider,
      url: editingAPI.value.url || getProviderPresetUrl(editingAPI.value.provider as APIProvider),
      apiKey: editingAPI.value.apiKey || '',
      model: editingAPI.value.model || getProviderPresetModel(editingAPI.value.provider as APIProvider),
      temperature: editingAPI.value.temperature || 0.7,
      maxTokens: editingAPI.value.maxTokens || getProviderPresetMaxTokens(editingAPI.value.provider as APIProvider),
      enabled: true,
      forceJsonOutput: editingAPI.value.forceJsonOutput || false
    };
    apiStore.addAPI(newConfig);
    toast.success(t('API配置已添加'));
  }

  closeDialogs();

  // 同步默认API配置到aiService
  syncDefaultAPIToService();
};

// 同步默认API到aiService
const syncDefaultAPIToService = () => {
  const defaultAPI = apiStore.apiConfigs.find(a => a.id === 'default');
  if (defaultAPI) {
    aiService.saveConfig({
      mode: 'custom',
      customAPI: {
        provider: defaultAPI.provider,
        url: defaultAPI.url,
        apiKey: defaultAPI.apiKey,
        model: defaultAPI.model,
        temperature: defaultAPI.temperature,
        maxTokens: defaultAPI.maxTokens,
        forceJsonOutput: defaultAPI.forceJsonOutput
      }
    });
  }
};

// 更新功能分配
const updateAssignment = (type: APIUsageType, apiId: string) => {
  apiStore.assignAPI(type, apiId);

  // 如果分配指令生成到独立API，自动开启分步生成
  if (type === 'instruction_generation' && apiId !== 'default') {
    if (!splitResponseGeneration.value) {
      splitResponseGeneration.value = true;
      saveSplitResponseSetting();
      toast.success('已自动开启分步生成（指令生成需要分步模式）');
    }
  }

  toast.success(`${getFunctionName(type)} ${t('已分配到')} ${apiStore.apiConfigs.find(a => a.id === apiId)?.name || 'API'}`);
};

// 关闭对话框
const closeDialogs = () => {
  showAddDialog.value = false;
  showEditDialog.value = false;
  editingAPIId.value = null;
  editingAPI.value = {
    name: '',
    provider: 'openai',
    url: '',
    apiKey: '',
    model: 'gpt-4o',
    temperature: 0.7,
    maxTokens: getProviderPresetMaxTokens('openai'),
    enabled: true
  };
  availableModels.value = [];
};

// 导出配置
const handleExport = () => {
  const data = apiStore.exportConfig();
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `仙途-API配置-${new Date().toISOString().split('T')[0]}.json`;
  link.click();
  URL.revokeObjectURL(url);
  toast.success(t('API配置已导出'));
};

// 导入配置
const handleImport = () => {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.json';
  input.onchange = async (e) => {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      const data = JSON.parse(text);
      apiStore.importConfig(data);
      syncDefaultAPIToService();
      toast.success(t('API配置已导入'));
    } catch (error) {
      toast.error(t('导入失败，请检查文件格式'));
    }
  };
  input.click();
};
</script>

<style scoped>
.api-management-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-background);
  overflow: hidden;
  padding: 1rem;
  gap: 1rem;
  position: relative;
}

/* 头部 */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--color-surface);
  border-radius: 0.75rem;
  border: 1px solid var(--color-border);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.header-icon {
  font-size: 1.5rem;
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.panel-title {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-text);
}

.settings-subtitle {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.header-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  justify-content: flex-end;
  min-width: 0;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  width: auto !important;
  height: auto !important;
  min-width: 0;
  min-height: 38px;
  max-width: 100%;
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  background: var(--color-surface);
  color: var(--color-text);
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.875rem;
  line-height: 1.2;
  white-space: normal;
  overflow-wrap: anywhere;
}

/* 修复按钮文字被全局样式覆盖的问题 */
.action-btn .btn-text {
  display: inline-block;
  min-width: 0;
  max-width: 100%;
  text-align: center;
  font-size: inherit;
  line-height: 1.2;
  color: inherit;
  overflow-wrap: anywhere;
  white-space: normal;
}

.action-btn:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-border-hover);
}

.action-btn.primary {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-white-soft);
}

.action-btn.primary:hover {
  background: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
}

/* 内容区域 */
.settings-container {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  padding: 0 0.5rem 3rem 0.5rem;
  scrollbar-width: thin;
  scrollbar-color: transparent transparent;
}

.settings-container::-webkit-scrollbar {
  width: 8px;
}

.settings-container::-webkit-scrollbar-track {
  background: transparent;
  border-radius: 4px;
}

.settings-container::-webkit-scrollbar-thumb {
  background: transparent;
  border-radius: 4px;
}

/* 设置区块 */
.settings-section {
  margin-bottom: 1.5rem;
  background: var(--color-surface);
  border-radius: 0.75rem;
  border: 1px solid var(--color-border);
  overflow: hidden;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  background: var(--color-surface-light);
  border-bottom: 1px solid var(--color-border);
}

.section-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text, #1e293b);
}

/* 流水线提示 */
.pipeline-hint {
  display: flex;
  gap: 0.75rem;
  padding: 0.875rem 1.25rem;
  background: linear-gradient(135deg, rgba(var(--color-primary-rgb), 0.08), rgba(var(--color-accent-rgb), 0.08));
  border-bottom: 1px solid var(--color-border);
}

.hint-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.hint-content {
  font-size: 0.8rem;
  color: var(--color-text-secondary, #64748b);
  line-height: 1.5;
}

.hint-content strong {
  color: var(--color-text, #1e293b);
}

.hint-example {
  display: inline-block;
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: var(--color-text-muted, #94a3b8);
  font-style: italic;
}

.section-count {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

/* 模式标识 */
.mode-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  border-radius: 1rem;
  font-size: 0.75rem;
  font-weight: 600;
}

.mode-badge.tavern {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #92400e;
  border: 1px solid #f59e0b;
}

.mode-badge.web {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  color: #1e40af;
  border: 1px solid #3b82f6;
}

/* 模式说明 */
.mode-hint {
  display: flex;
  gap: 0.75rem;
  padding: 0.875rem 1.25rem;
  border-bottom: 1px solid var(--color-border);
}

.mode-hint.tavern {
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.1), rgba(245, 158, 11, 0.08));
}

.mode-hint.web {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(37, 99, 235, 0.08));
}

.mode-hint .hint-content em {
  font-style: normal;
  font-weight: 600;
  color: var(--color-error);
}

/* API卡片列表 */
.api-list {
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.api-card {
  background: var(--color-surface);
  border: 2px solid var(--color-border);
  border-radius: 1rem;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.api-card:hover {
  border-color: var(--color-primary);
  box-shadow: 0 4px 12px rgba(var(--color-primary-rgb), 0.15);
  transform: translateY(-2px);
}

.api-card.disabled {
  opacity: 0.5;
  filter: grayscale(0.3);
}

.api-card.disabled:hover {
  transform: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.api-card.default {
  border-color: #3b82f6;
  background: linear-gradient(135deg, #eff6ff 0%, #ffffff 100%);
}

.api-card-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  row-gap: 0.5rem;
  padding: 1rem 1.25rem;
  background: linear-gradient(135deg, var(--color-surface-light) 0%, var(--color-surface) 100%);
  border-bottom: 1px solid var(--color-border);
}

/* 卡片开关样式 */
.card-toggle {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 28px;
  flex-shrink: 0;
  cursor: pointer;
}

.card-toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}

.card-toggle .toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #cbd5e1 0%, #94a3b8 100%);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: 28px;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card-toggle .toggle-slider:before {
  position: absolute;
  content: '';
  height: 22px;
  width: 22px;
  left: 3px;
  bottom: 3px;
  background: var(--color-white-soft);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.card-toggle input:checked + .toggle-slider {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  box-shadow: 0 0 8px rgba(59, 130, 246, 0.4);
}

.card-toggle input:checked + .toggle-slider:before {
  transform: translateX(20px);
}

.api-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
  flex-wrap: wrap;
}

.api-name {
  font-weight: 600;
  font-size: 1rem;
  color: var(--color-text);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.api-provider {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  background: var(--color-surface-light);
  padding: 0.25rem 0.625rem;
  border-radius: 1rem;
  font-weight: 500;
}

.api-provider.tavern-tag {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #92400e;
  border: 1px solid #f59e0b;
  font-weight: 500;
}

.api-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 0.5rem;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.icon-btn:hover {
  background: var(--color-surface-light);
  color: var(--color-text);
  transform: scale(1.05);
}

.icon-btn.danger:hover {
  background: rgba(var(--color-error-rgb), 0.15);
  color: var(--color-error);
}

.icon-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.icon-btn:disabled:hover {
  transform: none;
}

.api-card-body {
  padding: 0.75rem 1rem;
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

/* 酒馆模式下默认API的提示样式 */
.tavern-api-hint {
  width: 100%;
  padding: 0.5rem 0;
}

.tavern-api-hint .hint-text {
  font-size: 0.875rem;
  color: #92400e;
  font-style: italic;
}

.api-detail {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  min-width: 0;
}

.detail-label {
  color: var(--color-text-secondary);
}

.detail-value {
  color: var(--color-text);
  font-weight: 500;
  min-width: 0;
}

.detail-value.url {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-value.success {
  color: #059669;
}

.detail-value.fail {
  color: #dc2626;
}

.detail-value.unknown {
  color: var(--color-text-secondary);
}

.json-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--color-text);
  user-select: none;
}

.json-toggle input {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: #3b82f6;
}

.thinking-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--color-text);
  user-select: none;
}

.thinking-toggle input {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: #f59e0b;
}

.thinking-toggle span {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  padding: 2px 8px;
  border-radius: 4px;
  color: #92400e;
  font-weight: 500;
}

.api-card-footer {
  padding: 0.5rem 1rem;
  background: rgba(var(--color-primary-rgb), 0.05);
  border-top: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.assigned-label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.assigned-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.function-tag {
  font-size: 0.75rem;
  background: var(--color-primary);
  color: var(--color-white-soft);
  padding: 0.125rem 0.5rem;
  border-radius: 1rem;
}

/* 设置列表 */
.settings-list {
  padding: 0.5rem;
}

/* 功能分组头部 */
.function-group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem 0.5rem;
  margin-top: 1rem;
}

.function-group-header:first-child {
  margin-top: 0;
}

.group-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text);
}

.group-desc {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

/* 自动分步生成提示 */
.auto-split-hint {
  display: flex;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  margin: 0.75rem 0.5rem;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.08), rgba(37, 99, 235, 0.05));
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 0.5rem;
}

.auto-split-hint.warn {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.12), rgba(251, 191, 36, 0.06));
  border-color: rgba(245, 158, 11, 0.28);
}

.auto-split-hint.warn .hint-text {
  color: #92400e;
}

.auto-split-hint.warn .hint-text strong {
  color: #78350f;
}

.auto-split-hint .hint-icon {
  font-size: 1.25rem;
}

.auto-split-hint .hint-text {
  flex: 1;
  font-size: 0.875rem;
  color: #1e40af;
  line-height: 1.5;
}

.auto-split-hint .hint-text strong {
  font-weight: 600;
  color: #1e3a8a;
}

.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-radius: 0.5rem;
  transition: background 0.2s ease;
}

.setting-item:hover {
  background: var(--color-surface-light);
}

/* 控制行样式 */
.control-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* 内联开关样式 */
.inline-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-right: 0.5rem;
}

.toggle-label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.setting-switch.compact {
  transform: scale(0.85);
}

/* 模式指示器 */
.mode-indicator {
  display: inline-flex;
  align-items: center;
  margin-left: 0.5rem;
  padding: 0.125rem 0.4rem;
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  color: #1e40af;
  font-size: 0.65rem;
  font-weight: 600;
  border-radius: 0.5rem;
  border: 1px solid #93c5fd;
}

.setting-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.setting-name {
  font-weight: 500;
  color: var(--color-text);
}

.setting-desc {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

/* 酒馆模式锁定状态 */
.setting-item.tavern-locked {
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.08), rgba(245, 158, 11, 0.05));
  border-radius: 0.5rem;
}

.locked-badge {
  display: inline-flex;
  align-items: center;
  margin-left: 0.5rem;
  padding: 0.125rem 0.5rem;
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #92400e;
  font-size: 0.7rem;
  font-weight: 500;
  border-radius: 0.75rem;
  border: 1px solid #f59e0b;
}

.locked-text {
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: var(--color-surface-light);
  border: 1px dashed var(--color-border);
  border-radius: 0.5rem;
  color: var(--color-text-secondary);
  font-size: 0.875rem;
  font-style: italic;
}

.setting-control {
  display: flex;
  align-items: center;
}

.assignment-control {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  align-items: flex-end;
}

.function-mode-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.mode-label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.setting-select.mode-select {
  min-width: 120px;
}

.setting-select {
  padding: 0.5rem 2rem 0.5rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background-color: var(--color-surface);
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23374151' d='M6 9L1 4h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.75rem center;
  background-size: 12px;
  color: var(--color-text);
  font-size: 0.875rem;
  cursor: pointer;
  appearance: none;
  min-width: 140px;
}

.setting-select.disabled-hint {
  opacity: 0.5;
  cursor: not-allowed;
  background-color: #f3f4f6;
}

.setting-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background-color: #f3f4f6;
}

/* 数字输入框样式 */
.setting-number-input {
  width: 80px;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background-color: var(--color-surface);
  color: var(--color-text);
  font-size: 0.875rem;
  text-align: center;
  transition: all 0.2s;
}

.setting-number-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(var(--color-primary-rgb), 0.1);
}

.setting-number-input:hover {
  border-color: var(--color-border-hover);
}

.input-hint {
  margin-left: 0.5rem;
  color: var(--color-text-muted);
  font-size: 0.875rem;
}

/* 开关样式 */
.setting-switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}

.setting-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.switch-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #cbd5e1;
  transition: 0.2s;
  border-radius: 24px;
}

.switch-slider:before {
  position: absolute;
  content: '';
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: var(--color-white-soft);
  transition: 0.2s;
  border-radius: 50%;
}

input:checked + .switch-slider {
  background-color: var(--color-primary);
}

input:checked + .switch-slider:before {
  transform: translateX(20px);
}

/* 模态框 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--color-surface);
  border-radius: 1rem;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
}

.modal-header h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-text);
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 0.5rem;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.close-btn:hover {
  background: var(--color-surface-light);
  color: var(--color-text);
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  font-weight: 500;
  color: #374151;
  margin-bottom: 0.5rem;
}

.form-input,
.form-select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  font-size: 0.875rem;
  background: var(--color-surface);
  color: var(--color-text);
  box-sizing: border-box;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(var(--color-primary-rgb), 0.1);
}

.form-row {
  display: flex;
  gap: 1rem;
}

.form-group.half {
  flex: 1;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-weight: 500;
  color: #374151;
}

.form-checkbox {
  width: 1.25rem;
  height: 1.25rem;
  cursor: pointer;
  accent-color: #3b82f6;
}

.form-hint {
  margin-top: 0.5rem;
  padding: 0.75rem;
  background: #f3f4f6;
  border-radius: 0.5rem;
  font-size: 0.8125rem;
  color: #6b7280;
  line-height: 1.5;
}

.hint-warning {
  color: #d97706;
  font-weight: 500;
}

.model-input-row {
  display: flex;
  gap: 0.5rem;
}

.model-input-row .form-input {
  flex: 1;
}

.model-select-wrapper {
  position: relative;
}

.model-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  max-height: 200px;
  overflow-y: auto;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 100;
  margin-top: 4px;
}

.model-dropdown-item {
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--color-text);
  transition: background 0.15s ease;
}

.model-dropdown-item:hover {
  background: var(--color-surface-light);
}

.model-dropdown-item.active {
  background: rgba(var(--color-primary-rgb), 0.1);
  color: var(--color-primary);
  font-weight: 500;
}

.utility-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  background: var(--color-surface);
  color: var(--color-text);
  cursor: pointer;
}

.utility-btn:hover {
  background: var(--color-surface-light);
  border-color: var(--color-border-hover);
}

.utility-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.model-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.model-tag {
  padding: 0.25rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 1rem;
  font-size: 0.75rem;
  background: var(--color-surface-light);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.model-tag:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.model-tag.active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-white-soft);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--color-border);
}

.btn-cancel,
.btn-confirm {
  padding: 0.625rem 1.25rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-cancel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-text);
}

.btn-cancel:hover {
  background: var(--color-surface-light);
  border-color: var(--color-border-hover);
}

.btn-confirm {
  background: var(--color-primary);
  border: 1px solid var(--color-primary);
  color: var(--color-white-soft);
}

.btn-confirm:hover {
  background: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
}

/* 加载动画 */
.loading-pulse {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* 响应式 */
@media (max-width: 640px) {
  .header-actions {
    flex-wrap: wrap;
  }

  .header-actions .action-btn {
    padding: 0.4rem 0.6rem;
    font-size: 0.75rem;
  }

  .header-actions .btn-text {
    display: inline;
  }

  .api-card-body {
    flex-direction: column;
    gap: 0.5rem;
  }

  /* 关键：极窄屏下把卡片右侧操作（编辑/删除）换到新行，避免被裁切 */
  .api-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .form-row {
    flex-direction: column;
    gap: 1rem;
  }
}

/* 深色主题 */
[data-theme='dark'] .api-management-panel {
  background: var(--color-background);
}

[data-theme='dark'] .panel-header,
[data-theme='dark'] .settings-section {
  background: #1e293b;
  border-color: #475569;
}

[data-theme='dark'] .section-header {
  background: #334155;
  border-bottom-color: #475569;
}

[data-theme='dark'] .panel-title,
[data-theme='dark'] .section-title,
[data-theme='dark'] .setting-name,
[data-theme='dark'] .api-name,
[data-theme='dark'] .group-title {
  color: #f1f5f9;
}

[data-theme='dark'] .settings-subtitle,
[data-theme='dark'] .setting-desc,
[data-theme='dark'] .detail-label,
[data-theme='dark'] .group-desc {
  color: #94a3b8;
}

[data-theme='dark'] .api-card {
  background: #334155;
  border-color: #475569;
}

[data-theme='dark'] .api-card-header {
  background: #1e293b;
  border-bottom-color: #475569;
}

[data-theme='dark'] .setting-item:hover,
[data-theme='dark'] .api-card:hover {
  background: #334155;
}

[data-theme='dark'] .action-btn,
[data-theme='dark'] .setting-select,
[data-theme='dark'] .form-input,
[data-theme='dark'] .form-select {
  background: #374151;
  border-color: #4b5563;
  color: #e5e7eb;
}

[data-theme='dark'] .form-group label {
  color: #e2e8f0;
}

[data-theme='dark'] .modal-content {
  background: #1e293b;
}

[data-theme='dark'] .modal-header {
  border-bottom-color: #475569;
}

[data-theme='dark'] .modal-header h3 {
  color: #f1f5f9;
}

[data-theme='dark'] .modal-footer {
  border-top-color: #475569;
}

[data-theme='dark'] .api-provider {
  background: #475569;
  color: #e5e7eb;
}

[data-theme='dark'] .api-provider.tavern-tag {
  background: linear-gradient(135deg, #78350f 0%, #92400e 100%);
  color: #fef3c7;
  border-color: #b45309;
}

[data-theme='dark'] .tavern-api-hint .hint-text {
  color: #fcd34d;
}

[data-theme='dark'] .model-tag {
  background: #475569;
  border-color: #4b5563;
  color: #e5e7eb;
}

[data-theme='dark'] .model-dropdown {
  background: #374151;
  border-color: #4b5563;
}

[data-theme='dark'] .model-dropdown-item {
  color: #e5e7eb;
}

[data-theme='dark'] .model-dropdown-item:hover {
  background: #4b5563;
}

[data-theme='dark'] .model-dropdown-item.active {
  background: #1e40af;
  color: #93c5fd;
}

/* 深色主题 - 模式标识 */
[data-theme='dark'] .mode-badge.tavern {
  background: linear-gradient(135deg, #78350f 0%, #92400e 100%);
  color: #fef3c7;
  border-color: #b45309;
}

[data-theme='dark'] .mode-badge.web {
  background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
  color: #dbeafe;
  border-color: #2563eb;
}

[data-theme='dark'] .mode-hint.tavern {
  background: linear-gradient(135deg, rgba(120, 53, 15, 0.3), rgba(146, 64, 14, 0.2));
}

[data-theme='dark'] .mode-hint.web {
  background: linear-gradient(135deg, rgba(30, 58, 138, 0.3), rgba(30, 64, 175, 0.2));
}

[data-theme='dark'] .mode-hint .hint-content em {
  color: #fca5a5;
}

/* 深色主题 - 锁定状态 */
[data-theme='dark'] .setting-item.tavern-locked {
  background: linear-gradient(135deg, rgba(120, 53, 15, 0.2), rgba(146, 64, 14, 0.15));
}

[data-theme='dark'] .locked-badge {
  background: linear-gradient(135deg, #78350f 0%, #92400e 100%);
  color: #fef3c7;
  border-color: #b45309;
}

[data-theme='dark'] .locked-text {
  background: #334155;
  border-color: #475569;
  color: #94a3b8;
}
</style>

<!-- AUTONOMY DIRECTIVE - DO NOT REMOVE -->

YOU ARE AN AUTONOMOUS CODING AGENT. EXECUTE CLEAR, SAFE TASKS TO COMPLETION WITHOUT ASKING FOR PERMISSION. DO NOT STOP TO ASK "SHOULD I PROCEED?" ON OBVIOUS NEXT STEPS. IF BLOCKED, TRY A SAFE ALTERNATIVE APPROACH. ONLY ASK WHEN THE CHOICE IS TRULY AMBIGUOUS, DESTRUCTIVE, CREDENTIAL-GATED, OR EXTERNAL-PRODUCTION AFFECTING.

<!-- END AUTONOMY DIRECTIVE -->

# AGENTS.md

## 仓库用途

- 本仓库是《仙途（Xian Tu）》：AI 驱动的沉浸式修仙文字冒险游戏。
- 核心形态是 Vue 3 + TypeScript 前端，兼容独立网页版与 SillyTavern 嵌入环境；`server/` 是可选 FastAPI 后端，用于账号、存档和联机相关能力。
- 这是叙事游戏和状态系统项目，不是通用聊天壳、纯展示站点或后端优先项目。
- 修仙世界观、存档结构、AI 叙事指令和联机同步契约与代码正确性同样重要。

## 工作立场

- 默认用简体中文沟通，除非用户明确指定其他语言。
- 本机按 Windows 项目处理；需要命令时优先使用 PowerShell 语法和 Windows 路径习惯。
- 本项目默认在本地 Windows 环境开发和调试，远程 VPS 用于部署和最终验收；需要连接服务器时使用既有 `ssh gcp` 入口。
- 改动要小而准，优先复用现有 Vue/Pinia/service/types 结构，不顺带重构无关模块。
- 不确定业务语义时，先读当前实现和 `docs/` 文档；仍不清楚再问，不要自行补设定。
- 前端改动不要破坏桌面端、移动端、暗/亮主题、独立网页版和 SillyTavern 兼容性。

## 术语、字段与契约保护

- 不要随意重命名、翻译或重新解释这些领域词：`仙途`、`Xian Tu`、`朝天大陆`、`境界`、`灵根`、`三千大道`、`功法`、`宗门`、`神识`、`寿元`、`先天六司`、`后天六司`。
- 存档 V3 顶层只能是：`元数据`、`角色`、`社交`、`世界`、`系统`。相关改动必须同时检查 [docs/save-schema.md](./docs/save-schema.md) 和 [src/types/saveSchemaV3.ts](./src/types/saveSchemaV3.ts)。
- 角色状态语义必须分清：
  - `角色.属性` 是数值属性；
  - `角色.效果` 是 buff/debuff 列表；
  - `角色.修炼` 是修炼过程；
  - `角色.功法` 是功法掌握与进度。
- 背包是物品唯一数据源；`角色.装备` 只保存槽位到物品 ID 的引用，不复制完整物品。
- 联机模式下世界状态以服务端为权威；不要绕过 `系统.联机.只读路径`、`服务器版本` 或冲突策略。
- AI 生成链路要保留“叙事正文”和“结构化指令/状态变更”的边界，不要把纯展示文本当成权威状态写入。

## 仓库导航

- 项目入口和常用命令看 [README.md](./README.md)；贡献约定看 [CONTRIBUTING.md](./CONTRIBUTING.md)。
- 前端入口：`src/main.ts`、`src/App.vue`、`src/router/index.ts`、`src/stores/`、`src/components/dashboard/`。
- 游戏状态、存档、地图、NPC、AI 指令相关类型优先看 `src/types/`、`src/data/`、`src/services/`、`src/utils/`。
- 可选后端入口：`server/main.py`、`server/requirements.txt`、`server/.env.example`。
- 关键领域文档：
  - [docs/save-schema.md](./docs/save-schema.md)：存档 V3、AI 数据发送规范、短路径和关键子结构。
  - [docs/npc-relation-network.md](./docs/npc-relation-network.md)：NPC-NPC 关系网络设计和剧情影响。
  - [docs/地图逻辑重构需求_境界视角.md](./docs/地图逻辑重构需求_境界视角.md)：境界分层地图 PRD。该文档是设计基线，是否已实现必须以当前代码为准。

## 文档维护路由

- `AGENTS.md` 只维护长期有效的工作规则、术语保护、契约边界、入口路径和验证顺序。
- `README.md` 维护项目介绍、快速开始、常用命令、部署和面向新接手者的信息。
- `docs/save-schema.md` 维护存档结构、AI 数据发送规范和状态路径语义；涉及存档字段时优先更新它。
- `docs/*.md` 中的需求或设计文档维护功能边界、验收口径和阶段性方案，不要把全文复制到根文件。
- `CHANGELOG.md` 维护面向用户的版本变化；一次性排查过程不要塞进根级文档。
- 当同一变更影响多份文档时，只在职责最强的文档写完整说明，其他位置只放入口或简短引用。

## 验证与执行规则

- 最新安装、运行和部署命令以 `README.md`、`package.json` 和当前文件系统为准。
- 前端有意义改动后，优先运行：
  1. `npm run type-check`
  2. `npm run lint:check`
  3. `npm run build`
- 若改动影响单文件产物或 SillyTavern 嵌入能力，再运行 `npm run build:single` 并检查生成结果。
- `npm run lint` 会自动修复；只在明确需要格式/自动修复时使用，验证优先用 `npm run lint:check`。
- 后端改动后运行 `python -m pytest server`；需要手动服务验证时再参考 README 启动 `uvicorn server.main:app --reload --port 12345`。
- 每次完成 bug 修复、功能优化或其他代码修改后，本地验证通过只是第一步；还要通过 [http://35.212.255.180/](http://35.212.255.180/) 登录远程 VPS 做最终验收。
- 远程验收若需要服务器操作，优先通过 `ssh gcp` 连接 VPS；如果缺少账号、密钥、部署权限或登录凭据，明确说明未完成远程验收及缺失前提。
- 如果依赖或环境导致验证无法运行，说明缺失前提，并至少完成类型/静态检查或代码路径复核。

## 改动策略与安全默认行为

- 先读现有实现，再决定是否改；不要只根据文档或旧计划推断当前行为。
- 优先修复边界、复用已有工具函数和类型，不新增平行状态源。
- 不新增依赖，除非用户明确要求或现有栈无法合理完成。
- 涉及存档迁移、联机同步、AI 状态指令、地图生成、NPC 关系网络时，保持向后兼容并补充最小回归验证。
- 不要把阶段性 PRD 当作已完成事实；实现状态以代码、测试和构建结果为准。

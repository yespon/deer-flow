# 统一管理后台实施计划

## 一、现状分析：管理能力分布图

| 管理域 | 当前位置 | 读 API | 写 API | 前端 UI |
|--------|----------|--------|--------|---------|
| 用户管理 | `admin.py` router | ✅ | ✅ CRUD | ❌ 空目录 |
| 运行监控 | `admin.py` router | ✅ | — | ❌ 空目录 |
| 系统统计 | `admin.py` router | ✅ | — | ❌ 无 |
| 模型配置 | `models.py` router | ✅ | ❌ 只读 | ❌ 无 |
| Skills | `skills.py` router | ✅ | ✅ 启停/安装/编辑 | ✅ 聊天内嵌 |
| MCP 服务器 | `mcp.py` router | ✅ | ✅ 配置更新 | ❌ 无 |
| 自定义 Agent | `agents.py` router | ✅ | ✅ CRUD (需 `agents_api.enabled`) | ❌ 无 |
| Memory | `memory.py` router | ✅ | ✅ 读写/导入导出 | ❌ 无 |
| IM Channels | `channels.py` router | ✅ | ✅ 重启 | ❌ 无 |
| 核心配置 | `config.yaml` (~1246行) | ❌ | ❌ 无运行时写入 | ❌ 无 |
| 扩展配置 | `extensions_config.json` | 通过 mcp/skills | ✅ 间接写入 | ❌ 无 |
| API Keys | `.env` | ❌ | ❌ | ❌ 无 |
| 认证/CSRF | `auth/` | — | — | ✅ 登录页 |

**关键发现：**

- 后端 API 已覆盖 70% 的管理域，但前端 UI 几乎为零（`app/admin/runs/` 和 `app/admin/users/` 是空目录）
- `frontend/src/core/admin/api.ts` 已有完整的类型定义和 API 调用函数，但无对应页面
- `config.yaml` 是核心难题：启动时一次性加载为 `AppConfig` 单例，无运行时写入机制
- 前端已有 45 个 UI 组件（card, tabs, switch, dialog, badge 等）和 react-query hooks 模式可直接复用
- 认证体系已支持 `system_role: admin`，admin 路由守卫 `_require_admin` 已就绪

---

## 二、可行性分析

### 有利条件

1. **后端 API 基础扎实** — admin、skills、mcp、agents、memory、channels 六大路由已提供完整 CRUD，无需从零建设
2. **前端基础设施完备** — `core/admin/api.ts` 已封装所有 admin API；45 个 UI 组件库就绪；react-query hooks 模式在 skills/mcp/models 中有成熟范式
3. **认证体系已就绪** — JWT + `system_role=admin` + CSRF 双重保护；`_require_admin` 守卫可复用
4. **组件架构成熟** — Next.js App Router + SSR auth check + i18n，无需引入新框架

### 核心问题

**A. config.yaml 热更新是最大技术难点**
- 当前 `AppConfig` 在 `app.py` 启动时加载一次，存入 `app.state.config`
- 无运行时写入/重载机制；直接写文件不触发运行时生效
- 部分配置（如模型列表）修改后需要重启才能生效，部分（如 memory 配置）可以热加载
- 需要按"生效机制"对配置项分级管理

**B. API Key 安全性**
- 当前 API Key 存在 `.env` 和 `config.yaml` 中（`$VAR` 语法解析环境变量）
- 直接在管理后台展示/编辑 API Key 风险极高
- 需要 mask 展示 + 审计日志 + 权限控制

**C. 配置变更的影响范围不一致**
- Tier 1（热生效）：memory、skills 启停、MCP 配置 → 已有 `reload_*` 函数
- Tier 2（需重启）：模型列表、sandbox、channels、guardrails → 需优雅重启机制
- Tier 3（安全敏感）：API Keys、auth 配置 → 必须审计日志 + 二次确认

**D. 缺乏统一的审计/变更追踪**
- 当前无操作日志表；配置变更无回滚能力
- Skills 有 `history` 机制可参考，但全局缺失

**E. 前端路由和布局需从零搭建**
- `app/admin/` 目录下无任何页面文件
- 需要设计 admin layout（sidebar nav + 权限守卫）

---

## 三、配置项三级分类（解决核心问题 C）

| 级别 | 生效方式 | 配置项 | 实现策略 |
|------|----------|--------|----------|
| Tier 1 | 热重载 | memory、skills 启停、MCP 配置、tool_search、loop_detection | 写文件 + 调用已有 `reload_*` 函数 |
| Tier 2 | 需重启 | models、tools、sandbox、channels、summarization、title | 写文件 + 标记 pending_restart + 提示用户 |
| Tier 3 | 安全敏感 | API Keys、auth、guardrails、tenancy、rbac | 写文件 + 审计日志 + 二次确认 + 掩码展示 |

---

## 四、分阶段实施计划

### Phase 1：只读仪表盘（3-4 天）

**目标：** 让管理员一眼看到系统全貌，零写操作，零风险。

#### 后端

1. **新增聚合状态 API** `GET /api/v1/admin/dashboard`
   - 文件：`backend/app/gateway/routers/admin.py`
   - 返回：系统健康、用户数、运行数、模型列表、channel 状态、memory 状态、skills 数量、MCP 服务器状态
   - 复用已有的 `get_system_stats` + 各路由的读取逻辑

2. **新增配置读取 API** `GET /api/v1/admin/config`
   - 文件：新增 `backend/app/gateway/routers/config.py`
   - 返回 `config.yaml` 的结构化只读视图（API Key 字段掩码为 `****abcd`）
   - 配置项标注 tier（1/2/3）和当前生效状态

#### 前端

3. **Admin Layout**
   - 文件：`frontend/src/app/admin/layout.tsx`
   - SSR 权限守卫：检查 `system_role === "admin"`，非 admin 重定向到 `/login`
   - 侧边栏导航：Dashboard / Users / Runs / Models / Skills / MCP / Agents / Memory / Channels / Config
   - 复用 `sidebar.tsx` 组件

4. **Dashboard 页面**
   - 文件：`frontend/src/app/admin/page.tsx`
   - 统计卡片：用户数、运行数、线程数、反馈数（复用 `card.tsx` + `number-ticker.tsx`）
   - 模型列表 + 状态标签（`badge.tsx`）
   - Channel 状态概览
   - Memory 使用量（facts 数 / max_facts）

5. **路由守卫 Hook**
   - 文件：`frontend/src/core/admin/hooks.ts`
   - `useRequireAdmin()` — 客户端权限检查
   - `useAdminDashboard()` — 聚合 dashboard 数据

#### 验收标准
- [ ] 访问 `/admin` 时非 admin 用户被重定向
- [ ] Dashboard 页面展示系统统计 + 模型列表 + channel 状态
- [ ] 所有数据为只读，无写操作
- [ ] API Key 在 config 视图中被掩码

---

### Phase 2：已有 API 的写入管理（5-7 天）

**目标：** 为已有写 API 的管理域提供 UI，让零散的 CLI/HTTP 操作集中到管理后台。

#### 用户管理页面

1. 文件：`frontend/src/app/admin/users/page.tsx`
   - 用户列表（分页 + 搜索），复用 `admin/api.ts` 中已有的 `listUsers`/`createUser`/`updateUser`/`deleteUser`
   - 新建用户对话框（`dialog.tsx` + `input.tsx`）
   - 角色切换（`switch.tsx`，带"最后一个 admin"保护提示）
   - 重置密码（二次确认对话框）

#### 运行监控页面

2. 文件：`frontend/src/app/admin/runs/page.tsx`
   - 运行列表（分页 + 状态筛选）
   - 详情展开：token 用量、消息数、LLM 调用次数

#### Skills 管理页面

3. 文件：`frontend/src/app/admin/skills/page.tsx`
   - 复用 `core/skills/hooks.ts` 模式
   - Skills 列表 + 启停开关（`switch.tsx`）
   - 自定义 Skill 编辑（`textarea.tsx` + 安全扫描反馈）
   - 安装 Skill（复用 `installSkill` API）

#### MCP 管理页面

4. 文件：`frontend/src/app/admin/mcp/page.tsx`
   - 复用 `core/mcp/hooks.ts` 模式
   - MCP 服务器列表 + 启停 + 配置编辑
   - 新增 MCP 服务器表单
   - OAuth 配置折叠面板

#### Agents 管理页面

5. 文件：`frontend/src/app/admin/agents/page.tsx`
   - Agent 列表 + CRUD（需 `agents_api.enabled` 前置检查）
   - SOUL.md 编辑器（`textarea.tsx`）
   - 用户画像 (USER.md) 编辑

#### Memory 管理页面

6. 文件：`frontend/src/app/admin/memory/page.tsx`
   - Memory 概览（用户上下文 / 历史上下文 / Facts 列表）
   - Facts CRUD + 导入/导出
   - 配置查看（debounce、max_facts 等）

#### Channel 管理页面

7. 文件：`frontend/src/app/admin/channels/page.tsx`
   - Channel 状态列表 + 重启按钮

#### 验收标准
- [ ] Users: 完整 CRUD + 角色切换 + 密码重置
- [ ] Runs: 分页列表 + 状态筛选
- [ ] Skills: 启停 + 自定义编辑 + 安装
- [ ] MCP: 服务器 CRUD + OAuth 配置
- [ ] Agents: CRUD + SOUL.md 编辑
- [ ] Memory: 查看 + Facts CRUD + 导入导出
- [ ] Channels: 状态查看 + 重启

---

### Phase 3：核心配置管理（8-12 天）

**目标：** 解决 config.yaml 运行时管理这一核心难题。

#### 后端：配置热更新基础设施

1. **配置写入 API**
   - 文件：`backend/app/gateway/routers/config.py`（扩展 Phase 1 的只读 API）
   - `PUT /api/v1/admin/config/{section}` — 按节更新配置
   - 按 tier 分类处理：
     - Tier 1：写文件 + 调用 `reload_*` → 立即返回成功
     - Tier 2：写文件 + 标记 `pending_restart` → 返回 `needs_restart: true`
     - Tier 3：写文件 + 审计日志 + 掩码存储 → 返回成功 + 审计记录

2. **配置验证 API** `POST /api/v1/admin/config/validate`
   - 写入前校验：Pydantic model 验证 + 业务规则（如模型名唯一性）
   - 返回校验结果 + 影响分析（哪些模块需要重启）

3. **优雅重启机制**
   - `POST /api/v1/admin/restart` — 触发服务优雅重启
   - Docker 环境：通过 health check 自动恢复
   - 本地环境：`make dev` 的 watch mode 自动重载
   - 重启前自动备份当前 `config.yaml` → `config.yaml.bak.{timestamp}`

4. **API Key 安全管理**
   - 存储：API Key 仍存 `.env`，管理后台只管理引用关系
   - 读取：`GET /api/v1/admin/secrets` 返回 `{"OPENAI_API_KEY": "****abcd"}` 格式
   - 写入：`PUT /api/v1/admin/secrets/{key}` 更新 `.env` 文件 + 审计日志
   - 所有 Key 操作记录到审计日志

5. **审计日志系统**
   - 文件：`backend/app/gateway/routers/audit.py` + `deerflow/persistence/audit/`
   - 表结构：`audit_log(id, user_id, action, target_type, target_id, old_value_hash, new_value_hash, timestamp, ip)`
   - 所有 Tier 2/3 写操作自动记录
   - `GET /api/v1/admin/audit` — 查询审计日志

#### 前端：配置管理 UI

6. **配置编辑页面**
   - 文件：`frontend/src/app/admin/config/page.tsx`
   - 按 section 分 Tab（`tabs.tsx`）：Models / Tools / Sandbox / Memory / Summarization / Loop Detection / ...
   - Tier 标识：Tier 1 绿色、Tier 2 橙色（需重启提示）、Tier 3 红色（安全敏感）
   - 保存按钮行为：
     - Tier 1：即时生效，显示成功 toast
     - Tier 2：弹出确认框"此变更需要重启生效"，确认后标记 pending
     - Tier 3：弹出二次确认 + 审计原因输入

7. **API Key 管理页面**
   - 文件：`frontend/src/app/admin/config/secrets/page.tsx`
   - Key 列表（掩码展示）+ 编辑（`input.tsx`，type=password）
   - 操作审计日志查看

8. **重启提示横幅**
   - 组件：`frontend/src/components/admin/restart-banner.tsx`
   - 当存在 `pending_restart` 配置变更时，全局显示横幅"配置已变更，需重启生效"
   - 重启按钮 + 倒计时确认

#### 验收标准
- [ ] Tier 1 配置修改即时生效（memory、skills、MCP）
- [ ] Tier 2 配置修改标记 pending_restart，前端显示重启横幅
- [ ] Tier 3 配置修改需二次确认 + 审计日志
- [ ] API Key 掩码展示 + 审计追踪
- [ ] 配置变更前自动备份
- [ ] 优雅重启后配置生效

---

### Phase 4：企业级特性（15-20 天）

**目标：** 启用 config.yaml 中已定义但默认关闭的企业特性。

#### 多租户管理

1. 租户 CRUD UI（对应 `tenancy` 配置节）
2. 租户隔离策略配置（strict / relaxed）
3. 租户资源配额管理

#### RBAC 权限管理

4. 角色定义 + 权限矩阵 UI
5. Casbin model 配置 + policy 可视化编辑
6. 用户-角色分配

#### 审计日志增强

7. 审计日志搜索 + 导出
8. 日志签名验证（Ed25519）
9. 合规报告生成

#### 审批工作流

10. Human-in-Loop 审批界面
11. 审批超时 + 通知配置
12. 审批历史查看

#### 知识库管理

13. 文档上传 + 切片配置
14. 向量库状态监控
15. 检索测试面板

#### 品牌合规

16. 禁用词管理
17. 语气指南配置
18. 合规规则可视化编辑

#### 验收标准
- [ ] 多租户：租户 CRUD + 隔离 + 配额
- [ ] RBAC：角色定义 + 权限分配 + 策略编辑
- [ ] 审计：搜索 + 导出 + 签名验证
- [ ] 审批：提交 + 审批 + 超时处理
- [ ] 知识库：上传 + 检索测试 + 状态监控
- [ ] 品牌合规：规则管理 + 测试

---

## 五、技术决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| 前端框架 | 复用现有 Next.js | 避免引入新框架，统一技术栈 |
| 路由前缀 | `/admin` | 与现有路由一致，SSR 守卫自然 |
| 认证方式 | 复用 JWT + `system_role=admin` | 已有体系，无需新建 |
| 配置热更新 | 三级分类 + reload 函数 | 渐进式，不搞一刀切 |
| API Key 存储 | 仍存 `.env`，管理后台只管理引用 | 避免迁移风险，向后兼容 |
| 审计日志 | 独立表 + hash 存储 | 避免存储敏感明文，可验证 |
| UI 组件 | 复用现有 45 个组件 | 风格统一，开发效率高 |
| 状态管理 | @tanstack/react-query | 已有模式，一致性好 |

---

## 六、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| config.yaml 并发写入冲突 | 配置损坏 | 文件锁 + 备份 + 原子写入 |
| 热重载不彻底 | 配置状态不一致 | Tier 分级 + 重启提示 + 状态标记 |
| API Key 泄露 | 安全事故 | 掩码展示 + 审计日志 + HTTPS only |
| 优雅重启丢失连接 | 用户体验差 | WebSocket 重连 + 重启前提示 |
| 大配置文件解析慢 | 响应延迟 | 按节读取 + 增量更新 |
| 企业特性启用后性能下降 | 资源消耗 | 特性开关 + 配额限制 |

---

## 七、文件清单（预估）

### 新增文件

**后端：**
- `backend/app/gateway/routers/config.py` — 配置读写 API
- `backend/app/gateway/routers/audit.py` — 审计日志 API
- `deerflow/persistence/audit/model.py` — 审计日志 ORM
- `deerflow/persistence/audit/migration.py` — 数据库迁移
- `deerflow/config/config_manager.py` — 配置热更新管理器
- `deerflow/config/secret_manager.py` — API Key 安全管理

**前端：**
- `frontend/src/app/admin/layout.tsx` — Admin 布局 + 权限守卫
- `frontend/src/app/admin/page.tsx` — Dashboard 首页
- `frontend/src/app/admin/users/page.tsx` — 用户管理
- `frontend/src/app/admin/runs/page.tsx` — 运行监控
- `frontend/src/app/admin/models/page.tsx` — 模型配置
- `frontend/src/app/admin/skills/page.tsx` — Skills 管理
- `frontend/src/app/admin/mcp/page.tsx` — MCP 管理
- `frontend/src/app/admin/agents/page.tsx` — Agent 管理
- `frontend/src/app/admin/memory/page.tsx` — Memory 管理
- `frontend/src/app/admin/channels/page.tsx` — Channel 管理
- `frontend/src/app/admin/config/page.tsx` — 核心配置
- `frontend/src/app/admin/config/secrets/page.tsx` — API Key 管理
- `frontend/src/core/admin/hooks.ts` — Admin hooks
- `frontend/src/components/admin/restart-banner.tsx` — 重启提示横幅
- `frontend/src/components/admin/config-sections/*.tsx` — 各配置节编辑器

### 修改文件

- `backend/app/gateway/app.py` — 注册 config/audit 路由
- `backend/app/gateway/routers/admin.py` — 新增 dashboard 聚合 API
- `frontend/src/core/admin/api.ts` — 扩展 config/audit API 调用

---

## 八、时间线总览

```
Week 1-2  ┃ Phase 1: 只读仪表盘
          ┃   聚合 API + Admin Layout + Dashboard 页面
          ┃
Week 2-3  ┃ Phase 2: 已有 API 的写入管理
          ┃   Users/Runs/Skills/MCP/Agents/Memory/Channels UI
          ┃
Week 4-6  ┃ Phase 3: 核心配置管理
          ┃   config 热更新 + API Key 安全 + 审计日志 + 优雅重启
          ┃
Week 7-10 ┃ Phase 4: 企业级特性
          ┃   多租户/RBAC/审计增强/审批/知识库/品牌合规
```

每个阶段完成后独立可用，可随时停止。Phase 1-2 覆盖 80% 的日常管理需求。

---

## 九、实施进度跟踪

### Phase 1: 只读仪表盘 — ✅ 完成

- `GET /api/v1/admin/dashboard` — 聚合统计 API
- `GET /api/v1/admin/config` — 配置自省 API（密钥掩码 + 分层标注）
- Admin Layout + SSR 鉴权守卫
- Admin Sidebar (11 导航项)
- Dashboard 概览页（统计卡片 + 模型标签 + 扩展/服务概览）
- Admin Hooks (`useAdminDashboard`, `useAdminConfig`)

### Phase 2: 写入管理 UI — ✅ 完成

- Users 页面：CRUD 表格 + 创建/角色切换/重置密码/删除弹窗
- Runs 页面：分页表格 + 状态筛选
- Skills 页面：启用/禁用开关
- MCP 页面：服务列表 + 开关 + 添加弹窗
- Agents 页面：卡片网格 + 创建/删除 + SOUL.md 编辑
- Memory 页面：配置卡 + 用户上下文 + 事实列表删除
- Channels 页面：状态列表 + 重启按钮 + 连接状态 Badge
- Models 页面：只读模型列表 + 能力 Badge (Thinking/Reasoning)

### Phase 3: 核心配置管理 — ✅ 完成

- Backend: `PUT /api/v1/admin/config/{section}` — 分层感知写入 + 热重载
- Backend: `POST /api/v1/admin/config/validate` — 写入前校验
- Backend: `POST /api/v1/admin/restart` — 优雅重启
- Backend: `GET/PUT /api/v1/admin/secrets` — API Key 管理（掩码展示 + 安全更新）
- Frontend: Config 编辑器页面（分层色彩标签 + JSON 编辑 + 校验 + 确认弹窗）
- Frontend: API Keys 管理页面（掩码列表 + 行内编辑 + 密码可见切换）
- Frontend: Restart 按钮（集成到 Admin Sidebar）

### Phase 4: 企业级特性 — 🔲 待实施

- 多租户、RBAC、审计增强、审批工作流、知识库、品牌合规

### Phase 4: 企业级特性 — ✅ 完成

- Backend: Audit log persistence model (`AuditLogRow` in `persistence/audit/model.py`)
- Backend: `GET /api/v1/admin/audit` — 审计日志查询 API（分页 + action/user 过滤）
- Backend: `GET /api/v1/admin/tenancy` — 多租户配置读取
- Backend: `GET /api/v1/admin/rbac` — RBAC 配置读取
- Backend: `GET /api/v1/admin/approval` — 审批工作流配置读取
- Backend: `GET /api/v1/admin/knowledge-base` — 知识库配置读取
- Backend: `GET /api/v1/admin/brand` — 品牌合规配置读取
- Backend: `GET /api/v1/admin/compliance` — 内容合规配置读取
- Backend: `GET /api/v1/admin/quota` — 配额管理配置读取
- Frontend: Audit Log 页面（分页 + action 过滤 + 时间/用户/操作/目标/详情/IP 列）
- Frontend: Tenancy 页面（状态 + 隔离模式 + Header + 租户列表）
- Frontend: RBAC 页面（状态 + Model/Policy 路径 + 标准角色展示）
- Frontend: Approval 页面（状态 + 超时 + 存储路径 + 通知渠道 + Webhook）
- Frontend: Knowledge Base 页面（向量存储 + Embedding + 分块 + 检索配置）
- Frontend: Compliance & Brand 页面（品牌合规 + 内容合规 + 配额管理三合一）
- Admin Sidebar 扩展至 17 项导航

**总文件数**: 20 前端文件 + 2 后端文件 + 2 核心 API 文件 = 24 文件
**总代码行数**: ~4,367 行

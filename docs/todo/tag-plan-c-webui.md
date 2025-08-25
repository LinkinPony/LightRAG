## LightRAG WebUI 标签（Tags）支持 — 开发实施文档（Tag Plan C / 前端）

版本: v1.0  
适用范围: `lightrag_webui`  
参考: `docs/todo/tag-plan-c.md`

---

## 1. 背景与目标

为 WebUI 增加“标签（Tags）”支持，使之与后端 Tag Plan C 完全对齐：
- 插入时允许用户附带 `tags`（键值对；值支持字符串或字符串数组）。
- 查询/检索/图谱相关操作支持 `tag_equals` 与 `tag_in` 过滤（两者均为 AND 语义，可同时存在）。
- 前端仅负责采集、校验、展示与透传；默认不传则与现有行为保持一致。

非目标/不在本次范围：复杂标签推理、模糊匹配、前端聚合统计、自动补全来源等。

---

## 2. 术语与约束

- TagMap: `Record<string, string | string[]>`
- TagEquals: `Record<string, string>`
- TagIn: `Record<string, string[]>`
- 过滤语义：
  - `tag_equals` 与 `tag_in` 同时生效，均为 AND 逻辑。
  - 同一 `key` 同时出现在两者中时，需同时满足（等值也需包含在 in 列表内）。
- 兼容性：字段为空或未提供时不影响现有行为；只在非空时发送对应字段。

---

## 3. 数据模型与类型定义（前端）

在以下其一位置新增/导出类型（建议优先 `src/contexts/types.ts`，否则放在 `src/api/lightrag.ts`）：

```ts
export type TagMap = Record<string, string | string[]>;
export type TagEquals = Record<string, string>;
export type TagIn = Record<string, string[]>;

export type InsertPayload = {
  // ...已有字段
  tags?: TagMap; // 可选，仅在非空时发送
};

export type QueryParam = {
  // ...已有字段（如 mode、k、query 等）
  tag_equals?: TagEquals; // 可选，仅在非空时发送
  tag_in?: TagIn;         // 可选，仅在非空时发送
};
```

输入清洗规则（在提交请求前统一应用）：
- 去除 key 的首尾空白；空 key 丢弃。
- 对值进行去空白；空字符串值丢弃。
- 数组值去重、去空白、去空后若变为空数组则丢弃该 key。
- 最终 `tags`/`tag_equals`/`tag_in` 若为空对象，则不在请求体中包含该字段。

---

## 4. API 透传（前端调用层）

位置：`src/api/lightrag.ts`

- 插入接口：在现有文档/文本插入的请求体中新增可选字段 `tags`，遵循“仅在非空时发送”。
- 检索/对话接口：在 QueryParam 中新增可选 `tag_equals`、`tag_in`，遵循“仅在非空时发送”。
- 图谱相关接口（若存在独立入口）：同样支持透传 `tag_equals`、`tag_in`。
- 返回值展示：若响应中存在 `tags` 或 `tags_json`，在 UI 进行只读展示；缺省则不展示。

示例（插入）：

```json
{
  "text": "...",
  "tags": {
    "project": "alpha",
    "owner": ["alice", "bob"],
    "lang": "zh"
  }
}
```

示例（查询参数）：

```json
{
  "query": "...",
  "mode": "naive",
  "tag_equals": {"project": "alpha"},
  "tag_in": {"owner": ["alice", "charlie"], "lang": ["zh", "en"]}
}
```

---

## 5. UI 组件与集成点

### 5.1 新增通用组件

- `src/components/ui/TagsEditor.tsx`
  - 作用：编辑 `TagMap`（值可为单值/多值）。
  - 功能：添加/删除 key，切换单值/多值，新增/删除值项，基础校验（空 key/空值）。
  - 输出：`onChange(TagMap)`。

- `src/components/ui/TagFilterEditor.tsx`
  - 作用：同时编辑 `tag_equals` 与 `tag_in`。
  - 功能：两组独立区域（等值/包含），各自的键值行编辑、校验与清空。
  - 输出：`onChange({ tag_equals: TagEquals, tag_in: TagIn })`。

交互建议：
- 使用行式编辑（Key 输入 + 值输入/多值 Chips），提供“添加键 / 添加值 / 移除”操作。
- 长列表可折叠；提供 Tooltip 查看完整值。

### 5.2 集成位置

- 文档插入表单：`src/features/DocumentManager.tsx` 及 `src/components/documents/*`
  - 在上传/插入表单中嵌入 `TagsEditor`，默认隐藏或折叠，展开可编辑。
  - 提交前按清洗规则构造 `tags` 并透传。

- 检索设置：`src/components/retrieval/QuerySettings.tsx`
  - 新增“标签过滤”分组区域，嵌入 `TagFilterEditor`。
  - 将输出合并进 QueryParam（空则不发送）。

- 图谱视图：`src/features/GraphViewer.tsx`、`src/hooks/useLightragGraph.tsx`
  - 在筛选区域新增 `tag_equals`/`tag_in` 过滤；查询构建时透传。
  - 节点/边详情面板：若存在 `tags` 或 `tags_json`，按只读方式展示（可折叠、可复制）。

- 设置存储（可选）：`src/stores/settings.ts`
  - 缓存 `tagEquals`、`tagIn`（如需会话内持久化，可使用 localStorage）。

---

## 6. 国际化（i18n）

位置：`src/locales/*.json`

需新增的最小键集合（英文键名示例）：
- `tags.title`: Tags
- `tags.insert.title`: Insert Tags
- `tags.filter.equals`: Tag Equals
- `tags.filter.in`: Tag In
- `tags.key`: Key
- `tags.value`: Value
- `tags.addKey`: Add key
- `tags.addValue`: Add value
- `tags.remove`: Remove
- `tags.clear`: Clear
- `tags.collapse`: Collapse
- `tags.expand`: Expand
- `tags.invalidKey`: Key cannot be empty
- `tags.invalidValue`: Value cannot be empty

覆盖 `en.json`、`zh.json`、`zh_TW.json`、`fr.json`、`ar.json`。

---

## 7. 校验与容错

- 校验规则（表单层）：
  - Key 必须为非空字符串。
  - 值必须为非空字符串或非空字符串数组。
  - 自动去重、去空白；空数组键不发送。
- 提交前清洗（参见第 3 节）。
- 后端未返回 `tags`/`tags_json` 时，隐藏展示区域，不影响主流程。

---

## 8. 向后兼容与回退

- 默认不填写即不发送 `tags`/`tag_equals`/`tag_in`，与现有行为一致。
- 若后端暂不支持该字段，因仅在非空时发送，避免产生 400；展示区域基于可选字段，缺省即隐藏。

---

## 9. 分步实施计划（可独立验收）

### 阶段 A：类型与 API 扩展
- 任务：
  - 定义 `TagMap`、`TagEquals`、`TagIn`、`InsertPayload`、`QueryParam` 类型。
  - `src/api/lightrag.ts` 更新请求体构造逻辑（仅在非空时发送）。
  - 编写输入清洗工具函数（建议置于 `src/lib/utils.ts`）。
- 交付物：类型定义、API 调用更新、清洗函数及单测（如有测试框架）。
- 验收（DoD）：
  - 构造含/不含 `tags`/`tag_equals`/`tag_in` 的请求体，网络面板中字段行为符合“仅在非空时发送”。

### 阶段 B：通用组件
- 任务：实现 `TagsEditor.tsx`、`TagFilterEditor.tsx`（含基础样式与交互）。
- 交付物：组件源码与 Story/示例用法（可选）。
- 验收（DoD）：
  - 可添加/删除/编辑键值，切换单值/多值；校验生效；`onChange` 输出结构正确。

### 阶段 C：文档插入集成
- 任务：在上传/插入表单中集成 `TagsEditor`，提交时透传清洗后的 `tags`。
- 交付物：表单改造、与 API 的打通。
- 验收（DoD）：
  - 插入成功；后续检索中可在返回的 chunk/详情里看到标签展示（若后端返回）。

### 阶段 D：检索过滤集成
- 任务：在 `QuerySettings.tsx` 集成 `TagFilterEditor`，将输出并入 QueryParam。
- 交付物：检索设置 UI 与参数透传。
- 验收（DoD）：
  - 设置过滤后，检索结果上下文符合预期；清空过滤后恢复无过滤状态。

### 阶段 E：图谱筛选与展示
- 任务：在图谱视图增加过滤项透传；节点/边详情展示 `tags`/`tags_json`（若存在）。
- 交付物：筛选 UI、查询构造更新、详情面板展示。
- 验收（DoD）：
  - 设置过滤后，实体/关系候选与详情与后端一致；无过滤时行为不变。

### 阶段 F：国际化与文档
- 任务：补齐所有新增文案的多语言；更新 README 或使用指南片段。
- 交付物：`src/locales/*.json` 更新、示例截图（可选）。
- 验收（DoD）：
  - 语言切换后文案完整，布局不异常。

---

## 10. 手工测试用例（最小覆盖）

1) 插入-不含标签  
步骤：留空提交 → 观察请求体不含 `tags`。  
期望：后端成功；之后查询正常。

2) 插入-含标签（单值 + 多值）  
步骤：填写 `{"project":"alpha","owner":["alice","bob"]}` 提交。  
期望：请求体包含 `tags`；后续检索能看到标签展示。

3) 检索-仅等值过滤  
步骤：设置 `tag_equals={project: "alpha"}`，执行检索。  
期望：返回上下文的所有 chunk 满足 `project == alpha`。

4) 检索-仅包含过滤  
步骤：设置 `tag_in={owner:["alice","charlie"]}`。  
期望：返回上下文所有 chunk 的 `owner` 至少包含其一。

5) 检索-等值 + 包含并存  
步骤：同时设置 `tag_equals={lang:"zh"}` 与 `tag_in={owner:["alice"]}`。  
期望：两者同时满足；请求体两个字段均存在。

6) 过滤清空回退  
步骤：清空所有过滤项后检索。  
期望：请求体不含 `tag_equals`/`tag_in`；结果恢复为无过滤。

7) 图谱-筛选与详情  
步骤：在图谱页设置过滤，查看节点/边详情。  
期望：查询透传过滤；详情展示 `tags`/`tags_json`（若存在）。

---

## 11. 风险与缓解

- 标签数量较多导致 UI 冗长：采用折叠、滚动与 Tooltip；仅首行展示，展开查看全部。
- 非法输入：前端进行清洗与最小校验；无法纠正的输入阻止提交并给出提示。
- 后端版本差异：仅在非空时发送新字段；展示基于可选字段，缺省即隐藏。

---

## 12. 验收标准（总体）

- 插入：提供 `tags` 时成功提交并可在随后的查看中展示；未提供时与现状一致。
- 检索：设置 `tag_equals`/`tag_in` 后，返回上下文严格满足过滤；清空后恢复。
- 图谱：过滤透传有效；详情面板展示可用字段；无字段时无异常。
- i18n：新增文案完整，语言切换无缺失。

---

## 13. 附录：字段与示例

示例 TagMap：

```json
{
  "project": "alpha",
  "owner": ["alice", "bob"],
  "lang": "zh"
}
```

示例 QueryParam：

```json
{
  "query": "What is LightRAG?",
  "mode": "naive",
  "tag_equals": {"project": "alpha"},
  "tag_in": {"owner": ["alice", "charlie"], "lang": ["zh", "en"]}
}
```



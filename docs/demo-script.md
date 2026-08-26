# Nightingale 72HR Build 演示脚本

本脚本严格使用 Sarah Lim 合成故事，目标时长约 6–8 分钟。禁止替换为真实患者资料。

## 演示前准备

1. 使用一份全新、已完成 Alembic migration 的演示数据库运行 seed，确保 clinician note `00000000-0000-0000-0000-00000000000a` 的 `current_version` 为 `1`。
2. 启动 FastAPI（`http://127.0.0.1:8000`）和 Next.js（`http://localhost:3000`）。
3. 确认本地 `backend/.env` 已配置真实 `DEEPSEEK_API_KEY` 与 `DEEPSEEK_MODEL=deepseek-v4-flash`；不要在屏幕、终端或录屏中展示 Key。
4. 浏览器准备两个标签页：Nightingale 首页与 `http://127.0.0.1:8000/docs`。
5. 首页身份选择为 **Clinician view / Dr Priya Nair**。

## 15 步主演示

### 1. 打开 Sarah

在患者列表打开 **Sarah Lim**。指出页面只使用合成患者 `PAT-001`，主区域是单一纵向 care note，而不是彼此割裂的就诊记录。

### 2. 阅读 Care Glance

依次指向四块：

- **Critical**：Penicillin allergy。
- **Recent changes**：Worsening chest pressure。
- **Open actions**：Clinician review。
- **Conflicts**：Atorvastatin dose discrepancy。

说明 Glance 是可解释的优先视图，不是 AI 自动诊断。

### 3. 从 Glance 回到 Timeline 来源

展开 **Worsening chest pressure → Evidence & details**，展示精确 source quote，再点击 **Jump to source**。页面应跳到 2026-08-23 的 AI patient session，原文证据应被高亮。

讲解句：每个重点都可沿 `Highlight → ClinicalFact → Entry → ConsultSession` 回到来源；人工记录则回到对应 Entry。

### 4. 运行 New AI Scribe

点击 **New AI Scribe**，保留 **Doctor–patient consultation**，粘贴以下合成 transcript：

```text
Doctor: Please confirm your details.
Patient: I am Sarah Lim, phone 91234567, ID S1234567A.
Doctor: Have you noticed any new allergies?
Patient: I have a severe latex allergy and previously had anaphylaxis.
```

点击 **Generate**。等待真实 DeepSeek 返回；不要刷新页面或重复点击。

### 5. 展示 PHI redaction 边界

对照输入中的合成姓名、电话和 ID，指向结果区的 **PHI redacted**。说明已知姓名、Singapore phone 与 ID 在调用 DeepSeek 前分别替换为 `[PATIENT_NAME]`、`[PHONE]`、`[ID]`。

当前 UI 有意不把 redacted transcript 回传到浏览器，避免形成第二份敏感文本副本；屏幕上展示的是处理成功标记、摘要、结构化事实和精确 source quote。

### 6. 新建议即时出现

确认结果区出现 AI summary 与 latex allergy extracted fact，然后关闭弹窗。页面会重新读取 Timeline 与 Care Glance；最新 AI consult summary 应位于 Timeline 顶部，并出现一条新的、仍为 **Suggested** 的 latex allergy Highlight。

如果真实模型未把该事实输出为 `critical + persistent`，不要现场修改数据库或假装成功：保留返回结果并记录为最终 DeepSeek 验证问题。

### 7. Clinician 接受建议

在新 latex allergy 建议上点击 **Accept**。确认按钮消失，并显示 **Accepted by Dr Priya Nair**。

说明 Accept 是人类审核动作：AI 输出默认只能是 suggested，不能自行变成 clinician-confirmed clinical truth。

### 8. 展示 medication conflict

打开 **Atorvastatin dose discrepancy** 的证据：患者报告 10 mg，4 月 clinician-authoritative record 是 20 mg。强调系统同时保留两方来源，不静默覆盖，也不让 LLM 生成新处方。

如需演示解决动作，在 resolution note 输入 `Medication dose verified as 20 mg.`，再点击 **Resolve conflict**；否则保留冲突供讲解即可。

### 9. 展示 staff comment

滚动到 2026-08-24 的 **Follow-up escalated** staff note。展示 Amanda Wong 的 `@clinician` 评论与内部协作线程；可回复 `@clinician Reviewed during today's consultation.`。

### 10. 创建 revision

切换到 FastAPI `/docs`，展开：

```text
PATCH /api/v1/entries/{entry_id}
```

参数：

- `entry_id`: `00000000-0000-0000-0000-00000000000a`
- Header `X-Demo-User-ID`: `00000000-0000-0000-0000-000000000005`

Request body 必须发送完整新正文：

```json
{
  "content": "Penicillin allergy confirmed; previous reaction was urticaria. Atorvastatin 20 mg once daily remains the clinician-confirmed medication dose. Review again in four weeks.",
  "expected_version": 1
}
```

执行后确认 `current_version` 为 `2`。解释 `expected_version` 防止并发静默覆盖；不匹配时返回 `409 version_conflict`。

### 11. 查看 explainable diff

在 `/docs` 执行：

```text
GET /api/v1/entries/00000000-0000-0000-0000-00000000000a/diff?from_version=1&to_version=2
```

使用同一 clinician Header。响应应把原文标为 `unchanged`，把 `Review again in four weeks.` 标为 `added`。

### 12. Revert 但不删除历史

在 `/docs` 执行：

```text
POST /api/v1/entries/00000000-0000-0000-0000-00000000000a/revert
```

Header 仍为 clinician，body：

```json
{
  "target_version": 1,
  "expected_version": 2
}
```

确认响应为 `new_version: 3`、`reverted_from: 1`。说明 revert 是追加第三个完整快照，版本 2 和 audit event 都被保留，不执行破坏性删除。

### 13. 切换 Patient role

回到 Nightingale 首页，将右上角身份切换为 **Patient view / Sarah Lim**。

### 14. 内部信息消失

等待角色范围 API 重新加载。确认 staff note、内部评论、AI suggested Highlight、open action 与未解决 conflict 不再可见；患者只能看到自己的允许范围与已接受内容。强调这是后端 RBAC 过滤，不只是前端隐藏。

### 15. 解释 bounded self-learning

切回 Clinician view，以刚才的 Accept 收尾：

- 同 clinic 对相似实体的每次 accept 提供 `+0.25`，reject 抵消 `0.20`。
- learning bonus 被限制在 `0..3`，只影响后续相似内容的排序。
- 它不改变事实的 `risk_level`，不跨 clinic 学习，也不能绕过 suggested → clinician review。
- 页面只展示可读的 risk reason 与来源，不向临床用户暴露内部原始分数。

## 失败时的诚实处理

- DeepSeek 超时、502 或结构验证失败：保留错误画面，说明系统在一次修复重试后 fail closed；不要改用假响应冒充真实调用。
- Revision 返回 409：说明数据库不是全新演示状态；先读取 Timeline 的 `current_version`，不要盲目重复 PATCH/Revert。
- Patient 切换后仍出现内部信息：立即停止录制，按 RBAC 缺陷处理，不把前端视觉隐藏当作通过。
- 任何真实 Key、数据库密码或未脱敏患者资料出现在屏幕上：停止并重录。

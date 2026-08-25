# Sarah Lim 合成患者故事

这是 Nightingale 的唯一演示故事规范。所有姓名、号码、病历与事件均为合成数据。测试、UI、演示视频和说明文档必须共同引用 `backend/app/seed/sarah_lim.py`，不得各自编写互相冲突的版本。

## 人物与权限

- 患者：Sarah Lim，1984-05-18，`PAT-001`。
- Staff：Amanda Wong，可记录 staff note、评论和随访结果。
- Clinician：Dr Priya Nair，负责临床确认、Highlight 审核和版本操作。
- Admin：Daniel Tan，第一版仅提供诊所范围只读视图。

## 纵向时间线

### 2026-04-15 — Clinician note

Dr Priya Nair 确认 Sarah 对 Penicillin 过敏，既往反应为 urticaria；同时确认 Atorvastatin 剂量为每日 20 mg。这两项属于 clinician-authoritative context，其中过敏是不会因时间衰减而消失的 persistent critical safety context。

### 2026-07-12 — Staff follow-up

Amanda Wong 完成常规电话随访。Sarah 当时明确没有胸痛或胸部压迫感，也没有提出新的药物问题。这条记录为后续“新出现/恶化”的胸部症状提供时间对照。

### 2026-08-23 — Patient–AI session

Sarah 在 AI session 中报告新出现的胸部压迫感已持续三天，且前一晚比之前更强。AI 只提取受原文支持的事实，保存精确 quote，并把事实和 Highlight 保持为 `suggested`；它不能自行确认诊断或最终排序。

### 2026-08-24 — Staff follow-up

Amanda 确认胸部压迫感仍存在，写入 staff note，通过 `@clinician` 评论请求审核，并建立一个 open high-priority task，要求 clinician 评估并记录下一步安排。

### 2026-08-25 — Doctor consult

原始合成 transcript 特意包含 Sarah Lim、Singapore phone `91234567` 和合成 ID `S1234567A`。发送给 LLM 的版本必须先替换为 `[PATIENT_NAME]`、`[PHONE]`、`[ID]`。

Sarah 在咨询中说自己以为服用 Atorvastatin 10 mg，而 4 月 clinician-authoritative note 明确记录 20 mg。系统创建 `medication_dose` conflict；不能静默覆盖任何一方，也不能让 AI 声称哪一个剂量是新的临床处方。

## 预期 Glance 上下文

- Critical：Penicillin allergy，clinician confirmed，持久保留。
- Recent change：Worsening chest pressure，AI suggested，等待 clinician review。
- Open action：评估持续胸部压迫感并记录下一步安排。
- Conflict：Atorvastatin 10 mg patient report vs 20 mg clinician record。

所有 Highlight 都必须能够沿 `Highlight → ClinicalFact → Entry → ConsultSession`（人工记录除外）回到精确来源；临床事实确认与 Highlight 是否值得置顶是两个独立审核动作。

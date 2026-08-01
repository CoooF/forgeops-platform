# EPIC-02.7 五分钟走查

1. 启动：`pnpm --dir apps/web dev -- --host 127.0.0.1`，或使用交付回复中的稳定本地 URL。
2. 打开 `/design-preview/prototype?view=project`：确认顶部持续显示“本地合成 / 未接后端 / Advisory Not Executed”。
3. 点击主 Agent：确认它只做目标理解、步骤和 Builder diff，并明确没有 DATA/CONTROL 端口、不调用子 Agent Skill/MCP。
4. 进入“工作流”：选中三个执行 Agent，逐一比较模型、Skills、MCP Servers、Scope 和预算；切到节点库“能力”，确认 Skill/MCP 只能装配到已选执行 Agent。
5. 打开调试台 Evidence/错误：确认没有真实 PortEmission、Trace 或 Run。
6. 进入“运行与推演”：查看合成路径、三个候选、风险、Evidence Ledger 与人工等待状态。
7. 进入“数据与知识”“领域”“治理”：确认真实 API、混合边界、本地原型和未来能力标签；通过“返回真实 API 页面”检查既有页面。
8. 在 1280×800 和 476×770 检查导航抽屉、节点、检查器、调试台与主 Agent 面板。

最终验收前请明确提出修改，或明确表示“接受 EPIC-02.7 最终原型”。“我看看/先这样/继续完善”不构成接受。


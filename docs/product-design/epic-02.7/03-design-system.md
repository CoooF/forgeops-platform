# EPIC-02.7 设计系统 v1

状态：方向 A「静默控制台」已选定；Design Tokens 与组件只服务本地高保真原型和 EPIC-03 交接。

## 视觉母题

ForgeOps 是长时间使用的工业工程工具：暖白全幅画布、低反差产品壳层、精细边界、紧凑检查器和少量橙色风险/选中信号。记忆点来自 typed DATA/CONTROL 端口、执行 Agent 节点级装配、Evidence 账本和稳定的 Advisory 边界，不来自营销 Hero、渐变、玻璃拟态或大屏风格。

`frontend-design` 用于冻结“安静但有辨识度”的专业工具表达；`ui-ux-pro-max` 用于检查信息层级、44px 移动触控区、键盘焦点、对比度、响应式、渐进披露和 reduced-motion。其自动检索返回的黑色 Hero、超大标题、外部 Google Fonts 与本产品约束冲突，未采用。

## Token 约束

| 类别 | 约定 |
| --- | --- |
| Surface | `paper #fbfaf6`、`ground #e9eae4`、`white #fff`，画布使用近白点阵 |
| Text | `ink #172a24`、`muted #68756f`；正文与背景保持可读对比 |
| Border | `line #ccd3ce`、`soft-line #e4e8e4` |
| Action | 主操作深绿 `#183c31`；选中/风险橙 `#d65f2b`；键盘焦点蓝 `#146c94` |
| State | Success `#326e55`、Warning `#a55c23`、Error `#a13d2d`、Waiting/Prototype 暖黄 |
| Type | 本地系统中文字体优先；标题可回退宋体；ID/端口使用本地等宽字体；无外部字体 CDN |
| Spacing | 4/8px 节奏；面板紧凑，移动触控区至少 44px |
| Motion | 150—220ms，仅用于抽屉、选中和面板状态；`prefers-reduced-motion` 下关闭 |

## 组件语义

- `SourceBadge`：真实 API、混合边界、本地原型、未来能力；不能只靠颜色。
- `PrototypeNode`：typed DATA/CONTROL 端口、状态、失败出口；执行 Agent 额外显示 Skill/MCP/Scope 计数。
- `NodeInspector`：配置、端口、测试；执行 Agent 节点显示独立模型、Skills、MCP Servers、权限和预算。
- `MainAgentPanel`：深色项目协作层，明确无执行端口；与画布节点在层级、颜色和文案上完全不同。
- `DebugPanel`：端口、变量、Evidence、Trace、错误、结果；未接后端时只显示 0 emissions / Not Executed。
- `BoundaryBar`：所有原型页面常驻，不能被业务内容替代。

## 响应式

- 1440×900：产品导航、节点库、全幅画布、检查器和底栏同时可见。
- 1280×800：收紧导航/节点宽度，仍保留完整核心操作；节点不得重叠。
- 476×770：产品导航变抽屉；画布节点纵向排列；检查器与调试台进入同一主滚动；主 Agent 使用全高侧面板；无页面横向滚动。


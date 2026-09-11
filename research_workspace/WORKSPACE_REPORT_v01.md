# 本轮交付：CAVERN 工作区

已在当前仓库落地生成系统、训练前交付接口与论文工程之间的组织关系。
写作使用 ARIS paper-write / paper-compile，按其要求完成 GPT-5.5 xhigh
独立初稿审查；两图使用用户指定的本机 figures4papers skill。

## 可以直接打开

| 交付 | 位置 |
|---|---|
| 六页英文论文初稿 PDF | `overleaf/build/main.pdf` |
| 可独立编译的 Overleaf 导入包 | `outputs/cavern_paper_v01/overleaf_draft.zip` |
| 唯一 claim / evidence 清单 | `overleaf/CLAIM_EVIDENCE.yaml` |
| 方法图：SVG / PDF / PNG | `overleaf/figures/generated/cave_composer_method.*` |
| 总框架图：SVG / PDF / PNG | `overleaf/figures/generated/cavern_framework.*` |
| 两图可编辑 Python 源码 | `overleaf/figures/src/render_figures.py` |
| 写作、图表素材、后续实验排序 | `overleaf/PAPER_PLAN.md`、`overleaf/FIGURE_PLAN.md` |
| 官方模板原件及下载溯源 | `overleaf/template_original/` |
| 平台接口草案 | `research_workspace/contracts/platform_proposal_v01.json` |
| 冻结的离线对接样例 | `outputs/cavern_handoff_review_v01/` |
| 结果字段与接收说明 | `research_workspace/contracts/result_protocol.md` |
| 现实来源分组及使用历史审计 | `research_workspace/source_registry_v02.yaml` |

接口由用户授权先拟定，保留 **UNCONFIRMED**。候选观测为双目 RGB、相对目标、
IMU、压力及上一动作；用真值位姿算相对目标时，论文明确为定位辅助条件。
六维机体速度指令仅为待修改草案，没有替代同学当前的 actor/action 配置。
地图、规划路径和构建中心线与默认 actor 输入分离。

离线交付复用三个历史场景、36 个任务，创建新快照并逐文件检查哈希。
保留原来的 split、源代码版本、资产、球形包络、reset 和 goal。现有任务是洞内
端点对，不能当作完整出洞基准；真正的 Isaac 导入与异构实例运行仍需外部日志。
结果接收器拒绝漏报、重复 episode、切换 checkpoint、无效数值、冲突终止状态、
路径越界及轨迹字节变化，保留未运行记录；接收通过仍只标为 adapter_checked。

## 实际执行与结果

以下命令从仓库根目录运行，`python` 为 `.venv/Scripts/python.exe`。

| 命令 / 检查 | 实际结果 |
|---|---|
| `python scripts/fetch_icra2027_template.py` | 下载官方 class/BST 压缩包和规则页，保存 URL、UTC 时间、SHA256 |
| `python scripts/fetch_cavern_references.py`，另取 CrossRef / RSS 官方 BibTeX | 核对五篇引用；Tobin 更新为 IROS 2017，FlashSAC 更新为 RSS 2026，其余明确引用预印本版本 |
| `python scripts/audit_cavern_workspace.py --output research_workspace/evidence/local_audit_v01.json` | 三个历史任务包：36 请求、36 已存接受记录；另有六个单场景 seed 的形态配置 |
| `python -m pytest -q --junitxml=outputs/cavern_workspace_v01/baseline_tests.xml` | 修改前 110 项通过 |
| `python scripts/prepare_navigation_handoff.py --packs outputs/pipeline_v04_tasks/branching_stereo outputs/pipeline_v04_tasks/loop outputs/pipeline_v04_tasks/multi_loop --output outputs/cavern_handoff_review_v01` | 创建新对接快照；3 个不同碰撞资产哈希组、36 个任务 |
| `python scripts/prepare_navigation_handoff.py --check outputs/cavern_handoff_review_v01` | 文件、任务对应关系及几何记录完整性通过；非运行验证 |
| `python scripts/build_cavern_paper.py` | pdfLaTeX → BibTeX → 两遍 pdfLaTeX，成功编译 |
| `python scripts/check_cavern_paper.py` | 共 6 页；字体嵌入、引用、溢出及有限匿名检查通过 |
| `python scripts/check_cavern_paper.py --submission` | 按预期返回 1：占位、待做实验和作者审核未解决 |
| `python scripts/audit_cavern_sources.py` | 来源元数据一致性通过；当前没有获准的完全 untouched OOD 组 |
| `python -m pytest -q --junitxml=outputs/cavern_workspace_v01/final_tests.xml` | **131 passed，31.65 秒** |
| `python scripts/package_cavern_overleaf.py --output outputs/cavern_paper_v01/overleaf_draft.zip` | 18 个文件；解压到独立目录后四遍构建成功，无仓库外引用依赖 |
| `git diff --check` | 通过 |

以 Poppler 渲染并检查所有 PDF 页面，图中没有拿 Blender 渲染伪装 Isaac 运行。
初稿仍有明确 TODO 与空结果表；六页是当前完整篇幅，不是已完成八页终稿。
机器检查不能证明实验真实或完成全部匿名审查，不能自动代替作者决定投稿。

最终审计保存为 `evidence/local_audit_final_v01.json`。它与开始时的审计相比：
既有生成器代码哈希未改变；已固定的原始证据、三个任务包与六个形态包完全一致。
新增工作位于新文件/目录，README 只增加工作区入口。之前未提交的扫描裁剪资产
及脚本保留。没有开启 RL 训练、改写同学当前训练清单、提交或推送 Git。

## 仍缺的材料与最先做的工作

当前支持的是 C1 的具体实现及特定版本的几何记录，尚不支持“提高学习或泛化”
结论。下一轮首先做修改后资产的验证能力测试，以及多 seed、等预算的 C1
对照和消融，报告所有请求/失败、有效产出成本及实际几何覆盖。

随后需要同学提供实际 Isaac Lab/Sim 版本、观测与动作配置、车辆与控制参数、
训练 manifest、导入/碰撞/双目/reset/异构实例运行记录，才能冻结正式训练数据。
训练之后回传配置、数据和 checkpoint 哈希、固定 episode、轨迹及原始日志。

现实来源仍需补齐第五个 Sketchfab 资产身份、物理洞穴分组、使用历史、许可，
以及两个 Metashape 重建的尺度。已知裁剪/导出操作与未知的训练/调参使用分别
登记，没有将未知使用默认为安全。同源长段训练、短段验证应写成空间留出；
冻结策略在现实重建资产上的局部仿真测试也不等于实体机器人 sim-to-real。
作者身份、许可、AI 披露及最终投稿由人审核决定。

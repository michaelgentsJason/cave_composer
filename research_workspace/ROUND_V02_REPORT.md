# Cave Composer / CAVERN 本轮执行报告

日期：2026-09-10。入口：`outputs/cavern_round_v02/index.html`。
本轮聚焦 C1 实验与最终产物验证、C2 训练前交付、C3 资格协议。
没有启动 RL、修改同学学习算法、安装大型仿真平台、提交或推送 Git。
此前 30 个难度场景、旧训练任务与扫描资产保持独立版本。

## 实际修复

- `field.py` / `pipeline.py` 提供真正关闭 protected union 的消融开关，
  生产默认仍启用；没有用“半径设零”冒充完全关闭保护。
- `planning.py` 在 closed-reference 协议下先拒绝非水密/绕序不一致的输入；
  明确采样间距扣除及工程数值余量，不能视为浮点严格误差证明。
- `delivery_validation.py` 重新加载实际交付的视觉/碰撞 OBJ，按精确相同位置
  合并 UV 接缝拓扑并检查对应路径，将证据绑定文件与路径 hash。
  该接缝适配是实验开始后的声明修正；旧检查结果与原始源代码均保留。
- `exit_tasks.py` 检查按顺序穿越真实入口/出口边界及孔径余量，内部段使用
  闭合参考，整段使用开放面 unsigned clearance。开放面不套用 inside 证书。
- 新测试覆盖薄壁/仅视觉异常/导出缩放/开放协议/出口绕行。全套 136 tests 通过，
  见 `outputs/cavern_round_v02/tests.xml`。未宣称车辆动力学或闭环执行安全。

## C1 已运行实验

`outputs/c1_pilot_v02/preregistration.json` 固定六个 base requests、三条件、
18 次单次生成，4 个正常+2 个压力请求，seed 88010–88015；每请求不重试、
不追加种子，300 s / 4M voxels / 500k A* expansion 上限。
配置、原始 18 条结果、全部失败、原始代码快照和成本保留。

| 条件 | 正常通过 | 压力通过 | 全部通过 |
|---|---:|---:|---:|
| 完整 Composer | 4/4 | 1/2 | 5/6 |
| 关闭通行保护 | 4/4 | 0/2 | 4/6 |
| 受限生成 | 4/4 | 2/2 | 6/6 |

这些数值来自声明后的精确位置 OBJ 接缝重检，不直接聚合原始导入器的 accepted。
可复算入口：`scripts/analyze_c1_pilot_v02.py`；权威结果：`summary.json` /
`delivery_recheck.json`。每请求的阶段耗时、路径长度、交付面净空在 `results.csv`。
失败包括保守机器人栅格端点不合法，以及大块不连通自由空间；均未删除。
保护改善了一个压力请求，受限几何总体产出更高。六个固定请求不支持统计优势。

每网格使用 17 个固定截面，记录 span、面积、非凸性、中心偏移与方向代理。
这里的实测跨度包含分岔/腔室，不能视为精准宽高跟踪；没有证明自由空间精确
拓扑或与真实洞穴几何分布一致。布局筛选没有在显式路线中启用，因此不报告
“关闭筛选”的消融结果。成本包含失败、测量与两轮导入检查，不是隔离吞吐量。

`faults/results.json` 中四个解析故障全部检出，两个解析可行控制全部通过；
标签来自明确 box/slab 几何，不来自检查器自身。这不等于任意网格故障检出率。

PLUME 使用真实上游 revision `0ab6548c2a44c98cbae05a84affcdbc94ad7ed36`。
原生运行受到 `noise` 的 MSVC 构建依赖阻塞；外部图初次适配错误也保留，
按上游规则修正图清理后进入 mesh generation，最终受 Blender 5.2 API 阻塞。
实际日志在 `external/plume`。没有有效配对数值，不把接口/依赖问题记为算法失败。

## C2 实际交付与运行

冻结目录：`exports/cavern_pretraining_v02`。
完整/受限各 4 洞，每条件 train 2 / development 1 / generated-ID-test 1；
按 base_group 隔离，24 个固定任务，其中 16 个主配对任务和 8 个辅助内部任务。
包含 8 个具有真实几何开口的 full-exit 任务，不代表物理机器人运行。

每洞提供带纹理 GLB、OBJ+MTL+PNG、非凸三角面碰撞、闭合参考、开放面、rig、
坐标变换与文件 hash。首次 portable 导出有一个边界重叠告警，保留原结果后，
统一采用 5 cm terminal inset 新版本；8 个新导出全部通过纹理/拓扑/重导入检查。
所有任务在变化后的开放视觉/碰撞面与 portable 重导入面重新检查。

独立冻结 manifest SHA256：
`0ba40c65e6ed375fdb22f2b8244dbf9742b9039c889718afa527dca476a3e2e5`。
同学最小命令和日志回传要求见 `COLLABORATOR_HANDOFF_v02.md`。
名义参数与主任务端点匹配，但实际净空不同；这仍是接口 pilot，不能解释为
严格净空匹配的因果训练对照。实际 actor、动作、车辆配置继续 UNCONFIRMED。

安全复用已有 Isaac Sim 5.0 环境，实跑两个不同场景的 direct-USD adapter：
两个 namespace、80 m 原点间隔、reset 位置、空腔/壁面碰撞探针、左右 RGB。
最终 rig 为 1280×720 / 0.12 m，实际 K 来自任务包，24 个仿真步。
最终 receipt 为 PASS，进程正常退出。启动超时、首次过暗图及中间 rig 结果保留。
权威证据在 `outputs/cavern_round_v02/isaac_runtime/final_rig_and_portals`。
这不是 Isaac Lab、全 8 洞、原生 GLB 材料导入、车辆动力学或共享策略测试。

## C3 与论文产物

`source_registry_v02.yaml` 与 `contracts/local_transfer_protocol_v02.json`
保留物理来源组、已用外观先验、尺度和资格信息。第五 Sketchfab 身份未确认；
两份 Metashape 重建未确认真实尺度，长段训练/短段验证不自动成为 unseen-cave。
没有符合资格的最终任务清单，没有针对最终几何调参，也没有真实迁移结果。

图件在 `overleaf/figures/generated/c1_v02`：真实网格匹配 clay/textured 图、
保护诊断、自动定量图、真实内部视图、实际 Isaac 双目图和私有旧裁剪准备图。
保留可编辑 SVG/PDF、PNG 和原图、相机/源 hash/命令。没有生成式图像。
按 figures4papers 制作；写作与独立审阅使用 ARIS 技能。

唯一 `overleaf/CLAIM_EVIDENCE.yaml`、Method/Evaluation/Limitations 和图计划已更新。
正式量化表由脚本生成。旧稿已备份；新 PDF、源码 ZIP 和最终页图均在本地。
最终 PDF 为 8 页，字体全部嵌入，无溢出或未解析引用；24 文件源码 ZIP 已在
独立解压目录成功编译。26 条 claim 原始文件 hash 和图鉴 50 个本地链接通过
验收，详见 `outputs/cavern_round_v02/final_checks.json`。
ZIP 只带正文引用的图，排除原始扫描、私有准备图和 provenance。
缺失的策略成绩仍明确标为未运行，不能作为可投稿终稿。

独立实验审计结论为 WARN：pilot 范围和导入器修正需要保留限定；未发现其
审计范围内的伪造 GT、自归一化或虚构 PLUME 成绩。原始回复与落实记录保留在
`research_workspace/evidence`，完整 reviewer trace 位于本地 `.aris/traces`。

## Claim 与剩余缺口

- C1.6：加强为实际运行的配对小 pilot；C1.7 为解析故障诊断；C1.8 为实际
  最终文件检查和协议修复。C1.9 的基准规模、外部对照与广泛有效性仍未证明。
- C2.5：有两洞实际 Isaac 静态运行证据。C2.6：有冻结的八洞 24 任务接口包。
  单策略跨洞学习、训练收益、实际车辆控制与动力学仍未验证。
- C3：来源协议得到落实；尺度/来源资格、最终任务冻结、真实日志仍是阻塞。

下一项有价值的工作是先固定“名义与实测控制”的容差定义、解决正式训练对照
的净空匹配，再在兼容环境恢复 PLUME 对照。训练效果与迁移结论应等待同学实际
平台日志；不从几何 witness 生成替代成绩。

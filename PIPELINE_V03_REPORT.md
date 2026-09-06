# Cave Composer v0.3 优化与验收

本轮完成结构语法采样、独立路径搜索、配对保护机制压力测试，以及研究证据计划。
这是一轮可复现的生成器工程改进，尚未完成与 PLUME 的运行对照或机器人训练实验。

[完整场景画廊](outputs/pipeline_v03_final/index.html) · [使用指南](docs/pipeline_v03.md) ·
[ICRA 证据计划](docs/icra_generator_evidence_plan.md)

## 主要变化

- 新增 winding、branching、loop、chambers 四类训练结构；主路转弯数量和分支位置等可变。
  multi_loop 双回环结构只用于拓扑 OOD，旧采样器保留为 `legacy_v02`。
- 在同一个 seed 内进行有界布局筛选，并保存尝试次数与拒绝原因。
- 从碰撞体素和起终点独立运行净空加权 A*；不输入生成中心线或导航图。
  找到的折线路径需同时通过最终视觉/碰撞网格的连续净空检查。
- 输出 `planned_path.json`，在路线图中以粉色虚线显示搜索路径；批次质量统计增加环、
  路口、搜索净空、耗时和布局尝试次数。
- 修复精确回接时重复插入终点造成的零长度路线段，保留既有角度与长度语义。

## 完整场景验收

固定 base_seed 32000，2 个 worker，视觉/碰撞体素 0.20/0.34 m，开启无界面 Blender、
独立三角形相交审计和打包 `.blend`。全部请求及首次失败均保留。

| 组别 | 请求 | 首次成功 | 原 seed 重试后 |
|---|---:|---:|---:|
| 旧采样器 | 6 | 6 | 6 |
| 多弯道 | 3 | 3 | 3 |
| 分支网络 | 3 | 3 | 3 |
| 单回环 | 3 | 3 | 3 |
| 连续洞厅 | 3 | 2 | 3 |
| 几何 OOD | 3 | 3 | 3 |
| 因素组合 OOD | 3 | 3 | 3 |
| 双回环拓扑 OOD | 3 | 3 | 3 |
| 合计 | 27 | 26 | 27 |

27 个最终场景均有通过检查的独立路径。其中碰撞网格上的搜索路径净空下界最小为
0.764 m，高于所需的 0.55 m 安全半径。新场景的总路线长度约 76.6–276.3 m，
包含 0–2 个设计回环。此处回环数来自语义图，不宣称精确恢复了所有自由空间拓扑。

初次完整运行约 1,213 秒。不同布局长度和复杂度不同，且包含渲染与审计，
不能用这个时长与 v0.2 或 PLUME 做速度优劣比较。

[首次验收](outputs/pipeline_v03_final/first_pass_evaluation.json) ·
[最终清单汇总](outputs/pipeline_v03_final/evaluation.json)

## 配置覆盖和机制压力测试

在另外两组各 100 个 seed 上，仅采样配置、不生成网格。按
“主路转弯数／分支数／回环数／洞厅数”统计，旧采样器出现 4 种组合，新采样器出现
24 种组合；两组均接受 100 个配置，新采样器最多尝试 5 次布局。
这是配置组合覆盖，不等于自然度提高六倍，也不等于新增 200 个有效洞穴。
[原始配置统计](outputs/pipeline_v03_final/configuration_coverage.json)

另做 8 对狭窄、强岩壁扰动的配对压力测试。每对配置与 seed 相同，唯一干预是关闭
通行保护区；使用 0.34 m 碰撞分辨率，保留全部 16 个模型及诊断：

| 条件 | 设计路线达标 | 独立搜索得到合格路径 |
|---|---:|---:|
| 关闭保护区 | 0/8 | 0/8 |
| 开启保护区 | 8/8 | 8/8 |

关闭组的搜索均因端点不满足保守体素空间条件而拒绝，不能解释为证明整个洞穴无路。
本实验支持保护机制在所测压力条件下维持设计路线净空；不外推一般分布失败率或训练收益。

[配对结果和全部参数](outputs/protection_ablation_v03/results.json) ·
[压力测试图](outputs/protection_ablation_v03/paired_stress.png)

## 原生依赖异常

首次运行中，chambers/scene_000002 在所有几何及独立路径检查通过后，于 metrics 阶段
发生原生访问异常。原 seed 重试成功，第一次失败保存在 `.attempts`，没有替换 seed。
之后对同一碰撞模型重复创建索引并计算指标，在第 7 次复现；堆栈定位到
Rtree 1.0.1 / libspatialindex 1.9.3 的 `Index_Intersects_id`。
[复现堆栈](outputs/pipeline_v03_final/metrics_replay_failure.json)

项目依赖最低版本已提升到 Rtree 1.4.1，并在独立 `.venv` 中复测。该版本 Windows wheel
使用 libspatialindex 2.1.0；系统 Anaconda 未被修改。官方版本变化见
[Rtree changelog](https://rtree.readthedocs.io/en/latest/changes.html)。

新版环境中，50 项测试全部通过；相同模型连续 12 次指标重算全部通过，结果逐次一致，
且与原保存指标一致。另用相同 seed 完整重建 3 个洞厅场景，均通过渲染、相交审计和
双网格路径验证，四个几何文件均与原场景逐字节一致。这是针对已观察异常的复测证据，
不能保证原生库不存在其他缺陷。27 场景原始验收的依赖环境与新版复测环境分别记录。

[50 项测试记录](outputs/pipeline_v03_tests_rtree_141.xml) ·
[12 次指标复测](outputs/pipeline_v03_final/metrics_replay_rtree_141.json) ·
[3 个完整场景复测](outputs/pipeline_v03_runtime_check/index.html) ·
[几何文件一致性](outputs/pipeline_v03_runtime_check/geometry_identity.json)

画廊 9 个页面已检查桌面和手机尺寸，四种视角均正常加载，无 JavaScript 错误。
可安装包为 [v0.3 wheel](outputs/package/rtree141/cave_composer-0.3.0-py3-none-any.whl)。
源代码、场景摘要、测试与运行环境的可追溯记录见 [验收快照](docs/pipeline_v03_checkpoint.json)。

## 对 ICRA 主贡献的判断

本轮强化了“可控任务条件 → 多种结构 → 最终网格通行证据”的完整链路。
独立 A*、体积网格和模板增加本身不构成新颖性证据。主贡献仍需证明约束机制的作用、
与 PLUME 在相近预算下的对比，以及结构多样性对导航泛化的收益。

当前仍有规则通道和重复层纹；分支都接在主路上，未实现任意递归洞网或自动多层布局。
默认起终点沿主路，回环通常为可选绕行，任务难度分布仍需平衡。
拓扑 OOD 伴随总长度变化；压力测试样本较少；通行证据适用于球形机器人包络，
不替代动力学、跟踪误差或真实洞穴迁移验证。

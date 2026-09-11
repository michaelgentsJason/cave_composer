# 同学接手：CAVERN v02 训练前资产与验收

本轮交付 `exports/cavern_pretraining_v02`，不覆盖此前 30 个难度场景或旧训练包。
包含 8 个洞穴、24 个固定任务；完整与受限条件各 4 洞，分别为 train 2、
development 1、generated-ID-test 1。同一个 base_group 的两种条件及所有任务
在同一 split。主比较清单 16 任务，另 8 个辅助内部任务不进入主比较采样器。
内部目标与物理出口是不同任务类型，不能混报成功率。

## 1. 校验与格式

在仓库根目录，用有现有依赖的 Python 执行：

```powershell
.venv/Scripts/python.exe scripts/check_c2_release_v02.py --release exports/cavern_pretraining_v02
```

预期 PASS / 8 scenes / 24 fixed episodes / 16 primary episodes。
冻结 manifest SHA256：
`0ba40c65e6ed375fdb22f2b8244dbf9742b9039c889718afa527dca476a3e2e5`。
GLB 自带纹理；OBJ 必须连同 MTL 和 PNG 一起复制。碰撞使用 open/collision 下
的静态非凸三角面，`approximation=none`，不能用实体凸包把洞腔填实。
OBJ/NPZ 是米制 Z-up；GLB 是 Y-up，只应用 manifest 中记录的变换一次。

## 2. 最小 Isaac Sim 运行验收，不更新策略

先从冻结包校验并复制两个代表输入到一个新目录：

```powershell
.venv/Scripts/python.exe scripts/stage_c2_runtime_v02.py --release exports/cavern_pretraining_v02 --output outputs/c2_runtime_inputs_NEW
```

在同学已有 Isaac Sim 环境运行；本机实测环境命令为：

```powershell
& 'D:/Desktop/Research/OceanSim/myenv/python.exe' scripts/isaac_cave_smoke_v02.py --root outputs/c2_runtime_inputs_NEW --output outputs/c2_runtime_check_NEW
```

该环境为 Isaac Sim 5.0.0.0，不是 Isaac Lab。脚本把实际 NPZ 网格转为 USD，
两个洞穴使用不同命名空间和相距 80 m 的原点，检查 reset 位置、空腔/壁面碰撞探针，
输出两个场景的左右 RGB、USD 和 `runtime_receipt.json`。当前实测 rig 为
1280×720、12 cm 基线，K 与任务包一致；照明是诊断照明，不代表水下光学校准。
检查 receipt 的 status，而不能只看 Python 进程退出码。异常 receipt 和控制台
日志也要保留。此脚本不证明所有 8 洞、车辆控制、动力学、GLB 原生加载或 Lab 接入。

原始运行证据：`outputs/cavern_round_v02/isaac_runtime/final_rig_and_portals`。
从冻结包复制的验收输入在 `outputs/cavern_round_v02/runtime_from_release`。

## 3. 接到实际训练接口时确认的字段

实际 actor/action/vehicle 配置暂未提供，`platform_profile.json` 是 UNCONFIRMED
提案，可在新版本对接配置中调整，不直接修改冻结包。已确认的视觉观测为双目 RGB。
若相对目标依赖真值位置计算，须注明 localization-assisted；其他 IMU、压力、
previous action、动作尺度、控制周期、记忆和动力学均按同学真实实现确认。
规划路径、occupancy、centerline、全局位姿和验证记录是环境/评估特权数据，
不能把整份 task JSON 输入 actor。

完整与受限条件匹配了场景数、主任务端点和名义设置，但实测净空有差异，
见 `matched_conditions.json`。这是接口 pilot，不是完成严格净空匹配的因果训练对照。
正式实验需预先固定清单、交互预算及实际接口，并处理该差异。
`approved_for_training=false` 表示此包尚未通过同学真实训练栈的验收。

## 4. 返回原始日志，不回填假结果

复用 `research_workspace/contracts/run_template.json`、`results.schema.json`
和 `result_protocol.md`。一个算法/训练 seed/checkpoint 一个目录，至少返回：

- `run.json`：数据 manifest、固定 episodes、checkpoint、config、normalizer、
  preprocessing 的 SHA256；实际平台版本、actor/action/rig、训练 seed、冻结声明。
- 预先冻结的 `episodes.json` 及逐条 `results.jsonl`，保留所有 scheduled episodes。
  未运行和基础设施中断标为 not_run 并写原因，不伪装 timeout，也不删掉失败。
- 带仿真时间戳的原始位姿、动作、终止事件、碰撞、传感器时间；逐文件 hash；
  真实运行 receipt 和视频/图片来源。规划证据不得替代策略执行轨迹。
- 进度必须说明可通行距离估计方法；不存在有效估计时为 null+原因。
  路径效率不能拿净空加权 A* witness 冒充最短路。

```powershell
.venv/Scripts/python.exe scripts/import_navigation_results.py --run RETURN/run.json --episodes RETURN/episodes.json --results RETURN/results.jsonl --root RETURN --output outputs/collaborator_intake_NEW
```

现有 importer 检查 episode 文件、成员、轨迹 bytes 与结果格式；其余 hash 的实际
文件及运行关系仍须随日志核验。通过 importer 不自动成为 policy_evaluated。
本轮没有 RL 训练或任何策略结果，真实测试 eligibility 也尚待尺度/来源确认。

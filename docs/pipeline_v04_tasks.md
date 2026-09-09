# 面向双目导航实验的任务与数据扩展

本轮复用 v0.3 已有洞穴，补齐任务分布、双目 RGB 接口和参考数据审计。
核心洞穴生成器版本仍为 0.3.0；新增任务包使用独立的 schema version 1。
这里的 PASS 指工程/几何检查通过，不是机器人策略成功，也不是达到某个会议的录用标准。

## 新增能力

### 1. 一个场景，多个独立验证的任务

`cave_composer.tasks` 提供四种端点请求：主路到主路、主路到分支、分支到主路、
不同分支之间。单回环和双回环的内部点也可作为目标。分支端点必须离其他路线
足够远，避免把路口附近的点误计为分支内部目标。

构建路线只用于选择端点。`NavigationSpace` 只接收占据数据、原点、体素大小和
机器人安全半径，缓存一次 EDT 与连通域后服务多个独立 A* 请求。
每个候选路径都重新在闭合视觉、碰撞网格上做内部判定和连续净空检查。

每次运行的请求数量、随机种子、端点类别在规划前固定；失败不会被新的请求替换。
测试覆盖搜索预算耗尽、仅视觉网格拒绝、占据缓存原始数组被修改等情况。
旧场景未保存占据栅格，本轮从原配置重放一次，并要求碰撞网格摘要与原场景完全一致。
派生任务包单独保存，原始 bundle 不变。

### 2. 几何分层与训练输入分离

每个任务保存路径长度、净空下界、净空与要求半径的比值、高程跨度和约 3 m
采样尺度下的累计方向变化。easy/medium/hard 是预先写定的几何规则，
尚未按策略成功率校准；本轮选中的三个复杂洞穴主要产生 medium/hard 任务。
邻近语义路口只作为描述，不等同于实际决策次数或精确自由空间拓扑。

`episodes.json` 是环境 reset 的位姿和目标元数据；`training_contract.json`
声明坐标、文件和观测约定。路径、占据栅格和语义图单独放在特权数据目录，
不得默认加入策略观测。任务继承源洞穴的数据 split，不能把同一洞穴的 episodes
随机拆进 train/test。

用户指定传感器为双目 RGB，因此 actor sensor keys 仅包含 `rgb_left` 和 `rgb_right`。
目标如何传达、动作空间和记忆机制尚未指定：多分支目标任务的可观测性必须由
后续实验协议解决，不能暗中给仅 RGB 的策略添加真实位置、深度或全局地图。

### 3. 可检查的双目标定与实际配对渲染

`cave_composer.sensors.stereo_rgb_rig` 定义平行、同步、无畸变的双目模型：
默认 1280×720、0.12 m 基线、fx=fy≈675.556 px。这些是**临时仿真参数**，
不是用户硬件的测量标定。接口支持参数化修改，后续需与实际双目参数匹配。

坐标约定为：世界 Z 向上；机体 X 前、Y 左、Z 上；相机光学 X 右、Y 下、Z 前；
姿态四元数 wxyz。左右图共享位姿时刻、灯光与曝光。

Blender 渲染脚本输出实际左右图和相机矩阵，并用已知 3D 点核对 K、外参、
视差符号及极线关系。该检查是解析投影一致性测试，不是图像匹配精度实验。
没有给策略导出真实深度，也没有声称已模拟水体或运行机器人控制闭环。

### 4. 真实参考数据统计与独立分组

核对官方资料后，CAVERS 所有录制归入 **Cueva de la Victoria, Málaga** 一个洞穴组。
不同房间、录制序列和重建派生物不构成独立洞穴。
由于之前已用它做外观先验和开发观察，本仓库将整组标为 `prior`。
[官方数据页](https://zenodo.org/records/19367714)，
[官方代码及论文链接](https://github.com/spaceuma/cavers)。

`audit_reference_registry` 检查来源组交叉、测试组开发使用、未知分组和跨 split
重复文件摘要。没有指定独立测试资产时，`untouched_test_ready` 必须为 false，
即使注册表一致性本身 PASS。该审计依赖如实登记来源，不能识别未声明的派生关系。

本轮从本地已有的米制、RGB 对齐的 CAVERS 深度数据中均匀选择 24 帧，
只读计算有效比例、光学 Z、射线距离和中心区域距离分位数，并核对文件 SHA256。
数据中的深度只用于离线参考统计，不进入双目 RGB 策略输入。
每帧中位光学深度的跨帧中位数约 1.759 m；这个数字**不能解释为洞宽**。
干洞穴数据也不能用于直接估计水下吸收/散射参数。

另实现了有米制网格和标注路线时的横向、垂向首个交点跨度统计，
并在解析长方体及三个生成场景上验证。保留全部样本，也单独报告距语义路口
3 m 以外的统计，以避免把沿分支射出的长射线直接解释为普通通道宽度。
真实几何先验拟合仍需可靠的真实洞穴网格、尺度与路线标注；没有用前向深度伪造它。

## 本轮实际结果

| 原有场景 | 请求/通过 | 分支内部目标数 | 规划路径长度范围 | 最小双网格净空下界 |
| --- | --- | --- | --- | --- |
| branching / scene_000001 | 12/12 | 6 | 29.66–128.90 m | 0.755 m |
| loop / scene_000001 | 12/12 | 4 | 31.47–119.31 m | 1.182 m |
| ood_topology / scene_000001 | 12/12 | 6 | 37.99–99.15 m | 0.950 m |

要求半径均为 0.55 m。36 个任务中有 26 个涉及分支端点，16 个目标在分支内部。
独立场景数是 3，不能把 36 个相关任务当作 36 个独立洞穴来计算泛化置信度。
分支场景重复构建得到相同的请求/路径摘要；没有用重复运行增加样本量。

双目渲染完成 3 对图像，导出参数与 Blender 的最大投影误差约 0.000307 px，
最大垂直视差约 0.0000215 px。参数默认值与真实硬件的匹配尚未验证。
全部 71 项自动测试通过；新增测试覆盖了确定性、失败记录、坐标、分组泄漏、
解析几何统计和验证记录与 reset 的一致性。

## 查看与复现

本机产物：

- `outputs/pipeline_v04_final/index.html`：36 个任务的交互地图和验收表。
- `outputs/pipeline_v04_final/evaluation.json`：几何复查、任务覆盖与截面统计。
- `outputs/pipeline_v04_tasks/{branching_stereo,loop,multi_loop}`：可移植任务包。
- `outputs/pipeline_v04_stereo/stereo_pairs.png`：三组实际左右图。
- `outputs/pipeline_v04_stereo/stereo_verification.json`：标定与投影记录。
- `outputs/pipeline_v04_reference/confirmed`：真实观测统计、来源注册表和 split 审计。

```powershell
python scripts/build_navigation_tasks.py --scene outputs/pipeline_v03_final/branching/scene_000001 --output outputs/new_tasks --count 12 --seed 90401
blender --background --python-exit-code 1 --python scripts/render_stereo_tasks.py -- --pack outputs/new_tasks --output outputs/new_stereo
python scripts/evaluate_navigation_tasks.py --packs outputs/new_tasks --output outputs/new_task_review
python scripts/profile_cave_references.py --dataset /path/to/CAVERS_Dataset --output outputs/new_reference_profile --frames 24
python scripts/audit_reference_registry.py --registry configs/reference_registry_v01.json
python -m pytest -q
```

各输出目录必须是新目录。`load_task_pack` 校验完整文件清单与任务/reset 对应关系；
`evaluate_navigation_tasks.py` 进一步对实际双网格重新计算路径证据。

## 进入策略训练前的剩余条件

1. 确定双目硬件参数、目标表达和动作接口，接通仿真器中的最小闭环。
2. 单独实现并记录水下视觉随机化；其参数不得由最终测试集反复调优。
3. 指定未参与开发的独立真实洞穴资产，冻结组级数据划分与检查点选择规则。
4. 用同策略、同训练预算和多训练种子，比较简单生成器、完整方法、消融和 PLUME。

本轮未运行策略训练、PLUME 对照或实际水下机器人。因此没有新增导航性能、
sim-to-real 或相对 PLUME 优越性的实验结论。

# CAVE_COMPOSER_V0_REPORT

**CAVE_COMPOSER_V0 = PASS（离线生成原型）；Stonefish = PARTIAL；Research = PROMISING BUT INCOMPLETE。**

已交付六类参数化洞穴、独立视觉/碰撞网格、导航真值、几何验证、无界面渲染、批量接口和真实 CAVERS 外观先验实验。此处 PASS 对应本轮要求的六场景生成与离线导航验证，不代表已经完成机器人仿真、千场景压力测试或零样本泛化实验。

[交互画廊](outputs/final/gallery.html) · [六场景总览](outputs/final/contact_sheet.jpg) · [内部视角](outputs/final/inside_contact_sheet.jpg) · [机器可读验收证据](outputs/final/acceptance_evidence.json)

## 1. Architecture

以显式导航语义和安全包络约束隐式洞穴体积，再独立提取视觉/碰撞网格并用实际网格验证可通行路线。

```text
CaveSpec + geometry seed
    → 解析直线 / 指定弯道 / 坡度 / 分支 / 重连环
    → 导航骨架 + 多种截面 + 独立多瓣 chamber
    → 安全包络 + 岩层 / 裂隙式扰动 / 附着岩体
    → 分辨率独立的体积采样与 marching cubes
    → visual mesh + collision mesh
    → 网格距离 / 内外测试 / 侵蚀体素连通 / 捷径检查 / BVH 审计
    → navigation GT + metrics + geometric visibility
    → 独立 material seed / 可选图像先验
    → OBJ bundle + Blender headless previews + Stonefish XML 接口
```

实现的是隐式 level set，不是精确 SDF。KD 近邻候选可能在空间中切换，连续对象是采样后的插值格点场；场值不用于证明距离。安全证据来自最终网格。[初始设计](docs/architecture_v0.md)和[最终架构决定](docs/architecture_final.md)记录了候选比较及迭代依据。

## 2. Why this architecture

纯图扫掠易控制转向但容易留下规则管道；无约束隐式噪声较自由，却难稳定保留实验拓扑和机器人通路；大量网格布尔操作增加批量生成中的失败面。当前混合方案保留可解释的路线命令，将空间形态交给体积运算，并在提取后重新检查，而不以生成意图代替可通行证据。

机器人研究由此直接得到可控弯道、起终点、路线净空和视距。形状随机种子与材质种子独立，可进行几何/外观交叉实验。分割在采样器中定义，使组合 OOD 的禁用组合从训练分布中排除。代价是稠密格点内存开销，以及保护安全包络产生的局部圆孔和中心路线偏置；下一阶段需要更自然的地质形态及稀疏分块。

## 3. Generated caves

以下数据来自最终 bundle 的 `metadata/metrics.json`。长度为全部路线采样折线之和；垂向范围是中心路线的高程范围；宽度为碰撞网格横截面配对射线采样结果，不是输入名义宽度。面数均为三角形。

<!-- BEGIN MEASURED SCENES -->

| Scene | Length m | Turns ° | Branches | Chambers | Verticality m | Min width m | Visual / collision triangles | Generation s | Validation |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| [cave_a_simple](outputs/final/cave_a_simple/metadata/metrics.json) | 50.77 | 12 | 0 | 0 | 0.00 | 3.89 | 96,362 / 32,136 | 21.69 | VALID |
| [cave_b_sharp_turns](outputs/final/cave_b_sharp_turns/metadata/metrics.json) | 80.89 | 60, 90, 120 | 0 | 0 | 0.00 | 2.59 | 88,892 / 29,692 | 25.82 | VALID |
| [cave_c_s_turn](outputs/final/cave_c_s_turn/metadata/metrics.json) | 61.47 | 70, -100, 110 | 0 | 0 | 0.00 | 2.55 | 64,360 / 21,496 | 21.96 | VALID |
| [cave_d_branching](outputs/final/cave_d_branching/metadata/metrics.json) | 93.73 | 35, 55 | 2 | 0 | 0.00 | 2.53 | 106,768 / 35,406 | 30.88 | VALID |
| [cave_e_chamber](outputs/final/cave_e_chamber/metadata/metrics.json) | 50.71 | 18 | 0 | 1 | 0.00 | 2.53 | 88,928 / 29,296 | 25.55 | VALID |
| [cave_f_vertical](outputs/final/cave_f_vertical/metadata/metrics.json) | 64.05 | 65 | 0 | 0 | 8.18 | 2.51 | 97,140 / 32,640 | 55.82 | VALID |

<!-- END MEASURED SCENES -->

B 包含连续同向的三个指定角度，与 C 的交替 S 转向在布局上明确区分。D 有两个分支、两个 junction 和两个 dead end。E 用独立七瓣大厅体积连接窄入口/出口。F 同时包含上坡和下坡，最大坡度 24°。另有额外环路示例 `outputs/extra/cave_g_loop`，语义图 cycle rank 为 1；它不计入上述六场景验收。

计时为各 bundle 当时记录的总生成时间，包含初始预览阶段，后续重验、适配器导出和预览刷新不在其中。不同生成任务存在并发，不能作为公平性能比较。环境为 Python 3.12.7、Blender 5.2.1 LTS、RTX 4060；依赖见 [锁定版本](requirements-lock.txt)。

批量实测：最终训练分布 4/4、几何 OOD 3/3、组合 OOD 3/3 均 VALID，共十个不同场景。四个训练场景用 1 worker 与 2 workers 各生成一次，几何配置、网格摘要以及两个 OBJ、两个 NPZ 均一致。另保留八个早期探索性批量场景，未混入最终通过率。没有开展百/千场景性能或失败率统计。

## 4. Visual quality

每个场景均有总览、两个内部视角、拓扑/视距图及已打包纹理的 `.blend`。下面链接指向实际渲染：

| Cave | 总览 | 内部视角 1 / 2 | 拓扑与视距 |
|---|---|---|---|
| A | [overview](outputs/final/cave_a_simple/previews/overview.png) | [1](outputs/final/cave_a_simple/previews/inside_01.png) / [2](outputs/final/cave_a_simple/previews/inside_02.png) | [topology](outputs/final/cave_a_simple/previews/topology.png) |
| B | [overview](outputs/final/cave_b_sharp_turns/previews/overview.png) | [1](outputs/final/cave_b_sharp_turns/previews/inside_01.png) / [2](outputs/final/cave_b_sharp_turns/previews/inside_02.png) | [topology](outputs/final/cave_b_sharp_turns/previews/topology.png) |
| C | [overview](outputs/final/cave_c_s_turn/previews/overview.png) | [1](outputs/final/cave_c_s_turn/previews/inside_01.png) / [2](outputs/final/cave_c_s_turn/previews/inside_02.png) | [topology](outputs/final/cave_c_s_turn/previews/topology.png) |
| D | [overview](outputs/final/cave_d_branching/previews/overview.png) | [1](outputs/final/cave_d_branching/previews/inside_01.png) / [2](outputs/final/cave_d_branching/previews/inside_02.png) | [topology](outputs/final/cave_d_branching/previews/topology.png) |
| E | [overview](outputs/final/cave_e_chamber/previews/overview.png) | [1](outputs/final/cave_e_chamber/previews/inside_01.png) / [2](outputs/final/cave_e_chamber/previews/inside_02.png) | [topology](outputs/final/cave_e_chamber/previews/topology.png) |
| F | [overview](outputs/final/cave_f_vertical/previews/overview.png) | [1](outputs/final/cave_f_vertical/previews/inside_01.png) / [2](outputs/final/cave_f_vertical/previews/inside_02.png) | [topology](outputs/final/cave_f_vertical/previews/topology.png) |

几何上可看到截面不对称、层状壁台、突出岩块、大厅和坡道，未见明显开裂或穿插。总览主动剖掉顶部供观察，导出网格仍封闭。内部可以观察到转弯遮挡。材质采用周期性多尺度色彩场和 Blender bump，未烘焙水体颜色。

仍有明显限制：岩层过于规则，部分通道保留扫掠方向；附着岩体有时呈圆钝块状；窄处安全包络产生较圆的孔口，E 尤其明显。细节尚不足以声称照片级真实，CAVERS 中的流石、钟乳结构和复杂破碎层次也尚未完整表达。[视觉迭代记录](docs/visual_iteration.md)保留了早期材质网格纹和形态调整依据。未制作可选 fly-through。

## 5. Controllability

| 状态 | 参数 / 能力 | 约束及解释 |
|---|---|---|
| EXACT | 直线命令长度、圆弧转角、XY 转弯半径、每段坡度 | 解析中心线精确；折线/网格有采样误差。坡度突变不自动变成平滑动力学轨迹 |
| EXACT | 30/45/60/90/120/150/180°、正负转向、前后直线顺序 | 解析弧端点和弧长均有测试；并非任意组合都会通过空间验证 |
| EXACT | 输入语义图的分支、重连、chamber 命令数量 | 网格内全部通行拓扑等价性仍是 APPROXIMATE |
| EXACT | 同环境同 seed/config 的确定性、材料与几何分离、split 种子命名空间 | 证据为网格和文件摘要；不保证跨不同依赖版本逐字节一致 |
| APPROXIMATE | 最终物理宽度、高度、截面形状、bottleneck 位置与长度 | 名义值控制场，扰动/合并/格点影响实际表面；测量值单独输出 |
| APPROXIMATE | chamber 轮廓、岩层、裂隙式形态、突出岩体/障碍量 | 多瓣体积与几何参数控制，不能按物理地质解释全部随机参数 |
| APPROXIMATE | 连续自由空间拓扑及自然度 | 有路线连通与采样捷径检测，无完整同伦或图同构证明 |
| APPROXIMATE | 几何视距、图像到外观先验 | 有离散视线采样；照片色彩混入照明，未恢复测量级 PBR |
| NOT IMPLEMENTED | 自动自然语言 runtime parser | 已留 LanguageAdapter 协议，v0 以结构化配置为准 |
| NOT IMPLEMENTED | 物理侵蚀、动态落石/塌方、完整钟乳石族、自动多楼层布局 | 架构保留对应几何/对象层接口 |
| NOT IMPLEMENTED | 水体/传感器/动力学随机化、RL、现实 OOD 导入和导航评测 | 留给后续模拟器与学习阶段 |

八种截面可选，尺寸可沿路线变化。由于必须容纳球形安全体和格点误差，过小宽高会在配置阶段明确拒绝；窄度不是无限可调。[完整规格](docs/specification.md)说明坐标、分支位置、弧长、可见距离和分割支持范围。

## 6. Material experiment

按要求检查了 `/media/hong/Ubun_Shared/Composer` 与共享目录在本机/WSL 的可用性；当前未挂载该路径，未找到所列六个 Sketchfab 洞穴的本地原始资产。另找到的本地扫描 GLB/MTL 中有四张 base-color JPEG，属于扫描烘焙外观，缺少可直接认定为物理 roughness/normal 的信息；没有把其 atlas 搬到新网格。[清单](docs/material_inventory.json)与[初次实验](docs/material_experiment.md)记录了发现和限制。

随后按用户补充读取 `D:/Desktop/Cave_scan/CAVERS_Dataset`。跨四个 handheld 序列抽样 180 帧，检查 16 张候选，从 `rec_handheld_4/RS_COLOR_2575.png` 和 `rec_handheld_5/RS_COLOR_1929.png` 选择岩壁 ROI。提取颜色分位数，聚合成灰褐调色板，再生成新的周期纹理；轻微方向性来自视觉判断。该数据是采集 RGB 图像，不是现成平铺 PBR 材质。

[同几何对照图](outputs/material_experiment/cavers_transfer/appearance_comparison.jpg)与[实验 JSON](outputs/material_experiment/cavers_transfer/experiment.json)已输出。默认材质与 CAVERS 参考材质使用相同相机、灯光、路线和网格；visual/collision 的 OBJ 和 NPZ 四文件均字节相同。两张原始图像的读取前后 SHA256 相同。

**外观先验与解耦实验 PASS；物理材质恢复 PARTIAL。** 结果主要是较深的灰褐色和细节方向变化，不能认定域差距已消除。roughness 0.87 仍是默认值，未恢复真实法线和消除照明。该对照独立于主六场景默认材质；若以后 CAVERS 外观参与训练，就不能将相同数据称为完全未见的外观 OOD。[详细记录](docs/cavers_material_experiment.md)

## 7. Navigation readiness

| 项目 | 结果 | 证据 / 范围 |
|---|---|---|
| centerline / graph | PASS | 带语义节点的采样图、压缩 junction graph、chamber 记录 |
| spawn / goal | PASS | 均位于主路线内部并远离端盖，包含朝向/球半径/余量 |
| collision | PASS（离线） | 独立较低分辨率 OBJ；封闭、绕序一致、法线朝向洞内 |
| clearance | PASS | 对最终 visual 和 collision 计算网格最近距离，减去半个最大采样步长得到整条折线下界 |
| connectivity / blockage | PASS | 起点连通自由体素、侵蚀后的机器人空间连通、路线点内外测试、非局部直线捷径检查 |
| self-intersection | PASS（浮点审计） | 六场景 visual/collision 均为零个检测到的非相邻三角形相交对 |
| slope / bounds | PASS | 配置坡度上限和有限包围盒检查 |
| visibility | PASS（几何指标） | 前向射线视距与视锥内连续可见路线长度；尚未关联 VIO 或策略失败概率 |

<!-- BEGIN CLEARANCE -->
六场景两个网格的连续折线净空下界最小为 **1.081 m**，高于配置的 **0.550 m** 球形安全半径。
<!-- END CLEARANCE -->

这里的机器人模型是沿采样折线运动的球体。最小采样距离不是直接当成连续保证：检查使用距离函数的 Lipschitz 性减去采样间距上界。它未覆盖非球机体、控制跟踪误差超出 margin、动态障碍或相机装配尺寸。自由体积的小孤立分量修复有记录，修复超过阈值则拒绝；Euler 特征只作诊断，不能冒充实际拓扑等价。

`python -m pytest -q`：**22 passed，0 skipped**，包含指定角度、坡度、环路、插入真实阻挡的失败检测、开放房间造成捷径的失败检测、分割契约、复现、OBJ 读回、图像 ROI、材质解耦和 Stonefish XML/坐标变换。测试自行生成临时 bundle，不依赖交付二进制。[测试结果](outputs/final/test_results.xml)

## 8. PLUME comparison

先完成独立原型，再访问 PLUME：独立 Git 检查点 `7bf8111` 和[证据文件](docs/independent_checkpoint.json)包含当时六场景摘要。比较后保留当前架构；最后的 B 布局调整属于本项目视觉验收迭代。

PLUME 更完整的部分是自动多层布局、分块 color/normal/roughness 烘焙及已报告的模拟器示例。本实现更贴合本次任务的部分是显式转角语法、净空下界、导航/视距元数据和组合 OOD 契约。这是功能层面对齐，未做同条件运行比较，不能声称整体视觉或速度领先。[PLUME 论文](https://arxiv.org/abs/2508.20926)、[官方实现](https://github.com/Gabryss/P.L.U.M.E)

应借鉴分块输出、PBR 烘焙和可重用阶段产物；不直接采用会覆盖指定弯角的无约束平滑或未经净空复查的末端简化。PLUME 已包含 Mesh↔Volume 和独立 voxel/lava 洞道实验，不能把它描述成只有平滑管道，也不能把 graph + implicit 表示当成本项目独有创新。[源码](https://github.com/Gabryss/P.L.U.M.E/blob/main/src/blender.py)、[lava 实验](https://github.com/Gabryss/P.L.U.M.E/blob/main/src/lava_tubes.py)

[完整 13 项比较](docs/plume_comparison.md)逐项列出所读源码范围、强项、采用/不采用决策。未复制 PLUME 代码，也未运行 PLUME benchmark。

## 9. Stonefish readiness

**PARTIAL。** 六场景已导出 `stonefish/cave.scn` 与 `adapter.json`，包含分离的 visual/physical 网格、显式材质 look 和深度变换。米制 Z-up 通过 `(x,y,z) → (x,-y,20-z)` 变为 NED；这是行列式 +1 的旋转加平移，保留手性。

碰撞必须使用静态凹三角网格，XML 设置 `convex="false"`，否则凸包会填住洞穴。OBJ 的 MTL 不作为 Stonefish 自动材质入口，XML 显式引用纹理和 roughness。这些选择依据官方场景/材质接口并已做 XML 和文件引用测试。[Stonefish static bodies](https://stonefish.readthedocs.io/en/latest/environment.html#static-bodies)、[looks](https://stonefish.readthedocs.io/en/latest/materials.html#looks)

剩余阻碍是实际加载 `.scn`、检查凹网格碰撞接触及洞内可见面、放入真实机器人和相机、执行 start→goal 路径回放、测量仿真帧率。Blender bump 尚未烘焙为 Stonefish normal map。当前没有模拟器运行结果，因此不能标 READY。[接口说明](docs/stonefish_interface.md)

## 10. Research assessment

**PROMISING BUT INCOMPLETE。** 已具备可独立安装的源码包、CLI、配置、批量 API、失败记录、验证与可追溯资产，适合作为后续导航/OOD 研究的基础。wheel 构建通过，核心生成/渲染入口没有依赖本机绝对路径；具体数据与 Blender 路径由参数传入。

研究贡献候选在于可验证实验控制、视距与净空元数据、因素组合分割和生成器—模拟器的契约，而不是单独的网格生成算法。仍需证明规模稳定性、现实形态覆盖、仿真可用性和学习泛化价值。没有 RL/IL、零样本部署、真实扫描 OOD 导航或与 PLUME 的公平基准结果。源码尚未发布远程仓库；正式开源前需要项目所有者选择许可证，原始扫描素材未打包进源码。

## 11. Next 5 steps

1. 在 Stonefish 中加载 A/B/F，放入目标机器人与相机，验证静态凹网格接触、NED 位姿、灯光和完整 start→goal 回放，产出日志与视频。
2. 固定硬件与依赖开展至少 1,000 个跨 split 的生成压力测试，记录失败原因、峰值内存、分阶段耗时和种子；根据瓶颈实现稀疏分块。
3. 增加完整可通行空间拓扑提取与目标语义图对比，覆盖弯曲捷径、相邻路线误连、复杂重连与非球机器人净空。
4. 建立独立的真实洞穴外观参考集和 untouched OOD 集，改进流石/裂隙/岩块形态，烘焙独立 normal/roughness，并以共同配置运行 PLUME 对照。
5. 完成 Stonefish scene factory 与并行调度后，接入导航训练，冻结训练/ID/几何 OOD/组合 OOD/真实 OOD 协议，检验视距和净空是否解释失败。

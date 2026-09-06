# PLUME comparison after the independent prototype

独立实现检查点：Git `7bf8111`，以及 `independent_checkpoint.json`。
六类洞穴、导航验证、预览和批量接口完成后，才首次访问 PLUME。
Git clone 遇到连接重置，GitHub API 限流；随后成功读取官方论文、README，
并逐文件下载六个官方源码文件。文件摘要保存在 `plume_source_inventory.json`。
这里只做论文与源码静态比较，没有运行 PLUME，也没有公平的速度/视觉基准。

v0.3 更新：新增多结构族采样、留出双回环结构、独立 A* 搜索与双网格路径净空验证。
这些变化强化导航任务条件与产物验收；没有改变下文“尚无 PLUME 运行对照”的证据边界。
当前正式方法和投稿前实验要求见 [ICRA 证据计划](icra_generator_evidence_plan.md)。

| Component | Our Composer v0 | PLUME：已查证范围 |
|---|---|---|
| topology | 显式命令、分支、重连环、语义图 | 概率图、外部图、多层图 [论文](https://arxiv.org/html/2508.20926v1#S3) |
| geometry representation | 约束体积场、marching cubes、保护净空 | Skin 后接 Mesh↔Volume、细分与位移；绝非仅平滑管道 [源码](https://github.com/Gabryss/P.L.U.M.E/blob/main/src/blender.py) |
| turns | 角度、圆弧半径、前后直线命令 | 概率方向；所读代码未发现同等显式弯道语法 [算法](https://github.com/Gabryss/P.L.U.M.E/blob/main/src/algorithm.py) |
| cross-section | 八种截面与宽高变化 | Skin 双轴尺度；独立 lava 实验含椭圆截面 [Blender](https://github.com/Gabryss/P.L.U.M.E/blob/main/src/blender.py)、[lava](https://github.com/Gabryss/P.L.U.M.E/blob/main/src/lava_tubes.py) |
| chambers | 独立多瓣体积 | 图节点聚簇房间；lava 实验含扩张/收缩 [论文](https://arxiv.org/html/2508.20926v1#S3)、[lava](https://github.com/Gabryss/P.L.U.M.E/blob/main/src/lava_tubes.py) |
| multi-level | 显式坡度，未实现楼层自动布局 | 原生多层及层间连接 [论文](https://arxiv.org/html/2508.20926v1#S3) |
| materials | 平铺 albedo、Blender bump、CAVERS 调色板实验 | 分块烘焙 color/normal/roughness [源码](https://github.com/Gabryss/P.L.U.M.E/blob/main/src/blender.py) |
| realism | 岩层明显但仍有路线偏置与重复 | 有公开视觉示例；无同条件对比，不能宣布胜者 [论文](https://arxiv.org/html/2508.20926v1#S4) |
| controllability | 导航实验变量与测量指标直接关联 | 丰富图/网格/材质参数 [配置](https://github.com/Gabryss/P.L.U.M.E/blob/main/src/config.py) |
| batch generation | 多进程、失败清单、分割种子 | 多次生成、后台 Blender、图复用 [入口](https://github.com/Gabryss/P.L.U.M.E/blob/main/src/generation.py) |
| navigation GT | 采样路线、压缩图、spawn/goal、净空、视距 | 图 JSON；所读源码未发现对应净空证书/视距输出 [图](https://github.com/Gabryss/P.L.U.M.E/blob/main/src/graph.py) |
| OOD design | ID、几何 OOD、组合 OOD 支持范围 | 所读配置未发现等价 split contract [配置](https://github.com/Gabryss/P.L.U.M.E/blob/main/src/config.py) |
| robotics readiness | 离线几何已测；Stonefish 接口待运行 | 已报告 Gazebo/SLAM 示例 [论文](https://arxiv.org/html/2508.20926v1#S4.SS3) |

源码还有一个重要细节：主算法的 `loop_closure` 目前是空方法，尽管配置有
对应概率；而独立 `lava_tubes.py` 已探索 voxel 洞道、neck、chamber 和分支。
因此不能仅凭论文或配置名称判断当前实现，也不能声称“隐式混合表示”是我们独有。
[主算法](https://github.com/Gabryss/P.L.U.M.E/blob/main/src/algorithm.py)、
[lava 实验](https://github.com/Gabryss/P.L.U.M.E/blob/main/src/lava_tubes.py)

**PLUME 做得更好：** 已展示模拟器应用；更完整的贴图烘焙与分块方案；自动多层布局。
这些都是我们需要补足的能力，尤其不能用离线 VALID 替代模拟器实测。

**本实现更贴合当前任务：** 精确弯道语法、球形机器人净空下界、失败可追踪、几何视距、
组合 OOD 契约以及材质与几何的独立复现实验。这里说的是功能对齐，未声称算法性能领先。

**应借鉴：** 固定单位面积纹理精度的分块输出、可暂停的阶段产物、独立 normal/roughness
烘焙，以及更丰富的跨层布局。先做共同配置下的视觉/速度/可达率比较，再决定实现取舍。

**当前不应直接借用：** 会覆盖明确弯角的无约束平滑；未复查净空的最终简化；只凭
随机图参数就声称场景可通行。它们可能适用于别的目标，但不能替代本项目的验收条件。

**最终选择：保留独立架构。** 下一版吸收分块材质输出的设计思想；本轮未复制 PLUME
实现代码。研究贡献应定位于可验证、可控、带 OOD 契约的机器人世界工厂，
不应定位于“首次提出 graph + implicit cave generation”。

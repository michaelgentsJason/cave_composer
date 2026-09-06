# Cave Composer v0.3：结构采样与独立通行验证

v0.3 保留 v0.2 的网格生成、材质解耦、批次恢复和文件完整性机制，增加结构语法采样
以及不依赖生成中心线的路径搜索。输出是可供机器人训练环境使用的场景与几何真值。

## 使用

本机已建立项目环境 `.venv`。后续使用 `.venv/Scripts/python.exe` 代替系统 `python`，
或先运行 `.venv/Scripts/Activate.ps1`。环境使用 Rtree 1.4.1 的 Windows wheel；
系统 Anaconda 内的 Rtree 1.0.1 未被修改。新安装可执行：

```powershell
python -m venv .venv --system-site-packages
.venv/Scripts/python.exe -m pip install -e ".[test]"
```

已复现的旧原生空间查询异常及复测记录见本轮报告。依赖版本变化会改变续跑契约，
新环境应使用新输出目录；原环境的成功场景仍保留自己的验证和文件摘要。

```powershell
python generate_dataset.py --distribution configs/topology_distribution.yaml --num-scenes 24 --workers 2 --output outputs/my_topology_caves --render --blender D:/Blender/blender.exe --save-blend
```

断点续跑使用相同命令加 `--resume`。v0.2 输出保持为历史产物；由于生成代码与验证条件
已变化，不能把旧批次直接续跑为 v0.3，必须使用新目录。

```yaml
schema_version: 1
sampler: topology_v03
family: mixed
split: train
difficulty: hard
base_seed: 31000
```

不写 `sampler` 时仍使用 `legacy_v02`，保留既有 YAML 的采样行为。此选项只选择
旧的配置采样器；生成和独立验证仍使用当前 v0.3 代码。也可以继续直接输入 CaveSpec。

Python 接口示例：

```python
from cave_composer import sample
sample(seed=31000, sampler="topology_v03", family="loop", output="outputs/my_loop")
```

## 结构支持

| family | 当前范围 |
|---|---|
| winding | 多次转弯与坡度变化；hard 模式主路 2–5 个弯道 |
| branching | 主路上分布 1–3 条带弯道的探索分支 |
| loop | 一条绕行通路回接主路，语义图恰好一个独立环 |
| chambers | 沿通路分布 2–3 个多瓣洞厅 |
| multi_loop | 两条绕行通路，语义图两个独立环；仅允许 ood_topology |

`mixed` 从对应 split 的支持范围内确定性采样结构族。训练、验证、ID 测试和几何／组合
OOD 使用前四族；拓扑 OOD 使用第五族。配置中只改变 material 可保持几何不变。

语法会先检查非局部通路过近和估计体素预算。在同一个 seed 的随机流内最多尝试
32 次，保存 `sampling.layout_attempts` 和 `sampling.rejected_layouts`。
这些是生成算法内部的布局尝试，必须计入成本；已经失败的完整场景不替换 seed。

筛选会改变实际因素分布，因此必须同时报告最终接受配置的因素联合分布。
拓扑 OOD 的双回环也伴随总长度变化，当前不能解释为纯粹隔离拓扑的因果实验。
环数量是设计语义图的属性；最终可通行空间的所有微小环和意外弯曲捷径尚未精确恢复。

## 独立路径搜索

原来的中心线仍用于验证生成约束。新增的搜索器仅接收碰撞体素、起终点和机器人尺寸，
不接收中心线、分支结构或导航图。主要步骤：

1. 从碰撞体素计算到实心区域的保守距离，按机器人安全半径侵蚀自由空间。
2. 用六邻域、净空加权 A* 搜索，保存搜索量和耗时。默认最多展开 500,000 个节点。
3. 对搜索路径加密采样，直接测量视觉和碰撞网格的距离与内外关系。
4. 两套网格都满足连续净空下界才通过独立路径验收。

搜索在保守格点上失败，或者耗尽搜索预算，不等于证明连续空间绝对不可达。
搜索候选在最终网格上不合格也会被拒绝；错误体素地图无法单独提供 PASS。
输出路径带格点折角，是通行见证；控制器需要按自身运动学生成可执行轨迹。

新增产物为 `navigation/planned_path.json`，包含路径、搜索参数、耗时及双网格证据。
`metadata/validation.json` 新增 `independent_planned_path` 验收项。
`topology.png` 中粉色虚线表示独立搜索路径，青色表示生成中心线。
质量汇总新增回环数、路口数、搜索净空和布局尝试次数。

## 复现本轮验收

```powershell
python -m pytest -q
python scripts/evaluate_topology_pipeline.py --output outputs/pipeline_v03_review --workers 2 --per-family 3 --base-seed 32000 --render --blender D:/Blender/blender.exe
```

该设置共请求 27 个完整场景：旧采样器 6 个、四类新训练结构各 3 个、三类 OOD 各 3 个。
另保存两组各 100 个配置的覆盖统计，配置统计不计为完整场景验证。
结果位于 `evaluation.json`、各批次清单和 `index.html`。不同结构规模不匹配，
生成时间只描述本机运行，不用于声称比旧方法或 PLUME 更快。

研究假设、公平基线与投稿前证据要求见 [ICRA 证据计划](icra_generator_evidence_plan.md)。

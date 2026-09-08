# 双回环洞穴：关联地图与洞内视点

这是一个已有生成场景的定性展示，使用实际网格、相机与资产几何。
原始场景为 `outputs/pipeline_v03_final/ood_topology/scene_000001`，
构建路线总长约 255.57 m，主路约 149.49 m。没有重新生成洞穴布局。

## 查看文件

在仓库根目录打开 `outputs/cave_showcase_v01/index.html`。
页面可离线使用，点击地图编号或缩略图切换八个视点，点击大图查看原始分辨率。

| 文件 | 用途 |
| --- | --- |
| `figures/cave_showcase.png` | 6000 × 3600 总览，300 dpi |
| `figures/cave_showcase.pdf` | 同版式 PDF，文字与连线为矢量，图像为栅格 |
| `views/view_01.png` 至 `view_08.png` | 每张 1800 × 1125 的实际 Cycles 渲染 |
| `cave_showcase.blend` | 已打包材质，独立资产对象，帧 1–8 切换相机与检查灯光 |
| `views/registered_views.json` | 世界坐标相机姿态、投影地图位置、采样说明 |
| `assets/manifest.json` | 资产尺寸、位置、确定性种子与路线排除界 |
| `assets/collision.npz` | 新增资产的合并碰撞三角网格，米制 Z 向上 |
| `validation.json` | 资产加入后的路径验证 |
| `figures/caption.txt` / `latex_include.tex` | 英文图注与论文引用片段 |

所有上表路径均相对于 `outputs/cave_showcase_v01`。完整生成物保留在本机
被 Git 忽略的 `outputs/` 下。总览 PNG、PDF 和八张独立视图另外收录在
[GitHub 展示目录](figures/showcase/README.md)，可直接在仓库中查看。

## 展示内容

- 原有完整洞壁与洞顶，真实打开的入口、出口，不使用删除洞顶来伪装内部视图。
- 100 块程序化落石：底部接触/少量嵌入洞底，用低面数不规则封闭网格表示。
- 三块带支架的棋盘板：8 × 6 格，单格 80 mm，属于场景道具。
- 原有程序化石灰岩颜色贴图，辅以细粒度法线与粗糙度变化；不是 CAVERS 扫描贴图。
- 96 samples 的 Cycles 渲染、AgX 色彩变换、中性检查照明；未模拟水体或水下光传播。

地图由洞壁表面均匀采样，并保留 `abs(normal.z) < 0.72` 的侧向三角面样本。
该平面图旋转 15°，附真实 10 m 比例尺。它是已知生成几何的展示，
不是激光雷达点云、SLAM 重建或传感器实验。

金线在洞内来自原来的独立 occupancy A*；首尾包含已验证终端连接，
洞外是直线接近段。青色虚线是构建路线，不是规划器解。
八个视点分布在主路及两条回环上，不表示机器人已经沿这些点执行过任务。

## 资产加入后的检查

资产按固定种子 `20260908` 放置。对落石或棋盘板各封闭组件使用包围球，
减去构建路线最大采样间隔的一半，保守排除与所有路线的安全通道相交。
棋盘板角点必须位于闭合参考网格内部。落石有意略嵌入承接地面，不进行重力仿真。

此外，把实际资产三角面分别加入 visual 和 collision 几何，
重新检查完整入口到出口路径。两套网格的连续距离下界均为 **0.81 m**，
要求的机器人半径加余量为 **0.55 m**（0.35 + 0.20）。
该数值是采样距离减去半个最大间隔后的保守下界，不是平均洞宽。
这是指定路径的几何检查，不是动力学可行性或任意策略成功率的证明。

## 复现

在仓库 Python 环境安装依赖，另需 Blender（此版本使用 5.2.1 LTS）。
以下第一步只在派生场景目录不存在时运行；它会验证原始 bundle 并开口。

```powershell
python scripts/export_portals.py --scene outputs/pipeline_v03_final/ood_topology/scene_000001 --output outputs/cave_showcase_v01/scene
python scripts/prepare_cave_showcase.py --folder outputs/cave_showcase_v01
blender --background --python scripts/render_cave_showcase.py -- --folder outputs/cave_showcase_v01 --samples 96
python scripts/compose_cave_showcase.py --folder outputs/cave_showcase_v01
python scripts/verify_cave_showcase.py --folder outputs/cave_showcase_v01
```

如果 `blender` 不在 PATH 中，把第三条命令的程序名换为本机 Blender 可执行文件。
准备脚本为这个选定案例设置了八个视点；它是可复现示例脚本，
尚不是适用于任意洞穴的自动最佳视点选择算法。

如修改了资产几何，必须先重新运行准备及验证，再重新渲染与排版。
如只修改灯光、材质、排版，保持相机与几何不变即可复用几何检查。

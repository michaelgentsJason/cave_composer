# Hard 005：论文用关联视点展示

[高清总览与交互包](figures/showcase_hard_v02/README.md)复用新版资产集的
`hard/scene_005`（种子 1080501）。洞穴具有两个回环、两条盲支路和一处洞厅，
构建路线总长 264.53 m。添加 100 块落石与 3 块带支架的棋盘板道具，保留完整洞顶与两个真实终端开口。

版式沿用参考图的黑底、中央灰色地图、黄色路线、红色编号点和周边关联视图：
顶部 6 张、左右各 3 张。所有内部视图来自同一场景的实际 Cycles 渲染，
每张 1600×1200，128 samples。总览 PNG 为 7200×3600；PDF 保留矢量文字、路线和连线，
模型采样图与内部渲染为栅格。附英文图注、LaTeX 引用片段和打包 Blender 场景。

## 语义与检查

黄色曲线是通道构建中心线，不是独立 A* 的解或机器人已经执行的轨迹。
灰色点由视觉网格表面均匀采样，再保留侧向面样本 `abs(normal.z)<0.78`；
这是已知合成几何的 XY 投影（显示旋转 −23°），不是激光雷达或 SLAM 结果。
12 个红点与渲染相机的世界位置对应，覆盖主路和全部 4 条支路。

道具各封闭组件以包围球对所有构建路线进行保守排除；棋盘板角点必须在闭合参考洞穴内部。
资产实际三角面加入视觉与碰撞场景后，再检查原有完整贯穿路径。
两套网格的连续净空下界均为 0.589380 m，大于机器人半径加裕量 0.55 m。
检查包含相机姿态、模型来源、12 张不同图像、PDF 尺寸、离线图片加载、地图点击、
键盘切换、放大和移动端宽度。落石是静态放置，未做刚体沉降；检查灯光没有水体散射。
棋盘板是视觉道具，不表示做过相机标定实验。

## 复现

在仓库根目录运行，Blender 路径按机器调整；交付检查额外使用 `pypdf` 和 `playwright`，
浏览器检查使用本机 Microsoft Edge。

```powershell
python scripts/prepare_hard_showcase.py
blender --background --python-exit-code 1 --python scripts/render_cave_showcase.py -- --folder outputs/cave_showcase_hard_v02 --samples 128
python scripts/compose_hard_showcase.py
python scripts/verify_hard_showcase.py
python scripts/publish_hard_showcase.py
```

本机准备阶段直接复用已有开口场景。新克隆没有 `outputs/` 时，准备脚本从已交付配置与种子重放参考场景，
要求视觉网格顶点与面逐项匹配交付参考后才开口；环境差异造成几何不一致会停止。
已交付的 `.blend` 已打包材质和全部道具，可直接查看，无需上述重放。
帧 1–12 切换相机与灯光，数字小键盘 0 进入相机视图。

原有 30 套 GLB / OBJ 资产保持不变；本展示是单独的派生场景。

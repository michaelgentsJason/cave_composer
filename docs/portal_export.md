# 实际入口、出口与 Blender 查看

历史 v0.3 场景的视觉和碰撞网格都是封闭的自由空间边界，起终点位于内部。
画廊 overview 去掉洞顶仅用于剖切展示，不能把它当作实际入口。

现在可以在完整场景生成后，追加一个独立的 `export_portals.py` 步骤，得到两端真正开口的
视觉和碰撞模型。当前采用主路首尾的横截平面裁剪，不填端盖；适合首尾平面不会切过
其他路线的布局。复杂回绕布局若不满足条件会明确拒绝，不静默裁掉其他通道。
原始场景保留，开口场景有独立的验证记录，不沿用封闭网格的 VALID 标签。

## 本次可直接打开的演示

- 源场景：`outputs/pipeline_v03_final/chambers/scene_000001`
- 洞穴：砂岩材质，三处洞厅，连续转弯和坡度变化。
- Blender 文件：`outputs/blender_open_cave_demo/cave_open_inspection.blend`
- 两套导出模型：`outputs/blender_open_cave_demo/visual/cave_visual.obj` 和
  `outputs/blender_open_cave_demo/collision/cave_collision.obj`
- 几何验证：`outputs/blender_open_cave_demo/metadata/portal_validation.json`
- 相交审计：`outputs/blender_open_cave_demo/metadata/intersection_audit.json`

Blender 默认停在第 40 帧的内部纹理视角。修改 Timeline 的当前帧即可切换已绑定的相机：

| 帧 | 视角 |
|---:|---|
| 1 | 从洞内看入口外侧 |
| 40 | 洞厅内部与砂岩纹理 |
| 80 | 从洞内看出口外侧 |
| 120 | 保留洞顶的完整洞穴外观 |
| 160 | 从入口外侧向洞内看 |

小键盘 `0` 切换相机视图。自由查看可从 `View > Navigation > Walk Navigation` 进入漫游；
默认键位下 `Shift + 反引号` 也可进入，`W/A/S/D` 移动，`Q/E` 升降。
这不是带碰撞的机器人控制器，不用自由漫游是否穿墙判断导航可行性。

纹理保留源场景的程序化砂岩颜色贴图及 bump，已经打包进 `.blend`。
本次未换成扫描纹理。光照为便于观察的中性外部光与洞内工作灯，没有水体或散射。
入口外侧的灰蓝色是世界背景，并非封堵洞口的面。

## 可复现命令（PowerShell）

输出目录必须不存在，避免覆盖已有导出。

```powershell
.venv/Scripts/python.exe scripts/export_portals.py --scene outputs/pipeline_v03_final/chambers/scene_000001 --output outputs/my_open_cave
& 'D:/Blender/blender.exe' --background --python-exit-code 1 --python scripts/prepare_blender_inspection.py -- --scene outputs/my_open_cave
& 'D:/Blender/blender.exe' --background --python-exit-code 1 --python cave_composer/blender_audit.py -- --scene outputs/my_open_cave
Start-Process -FilePath 'D:/Blender/blender.exe' -ArgumentList 'D:/Desktop/cave-composer/outputs/my_open_cave/cave_open_inspection.blend'
```

## 验证语义

1. 先核对原始场景清单、文件校验和以及独立路径的双网格证书。
2. 在原始封闭网格上重新验证“主路首端 → 独立搜索路径 → 主路末端”，确保内部部分确实在洞内。
3. 两个最终网格分别裁剪，保留已有岩块；检查边的流形性质、绕序、零面积面和组成部分。
4. 必须恰好有两个闭合边界环，且各自落在指定的入口、出口平面上，不能多出任意孔洞。
5. 给路径添加入口外侧和出口外侧的直线接近段，对整条折线与实际开口网格的距离检查
   `d_min - h/2 > radius + margin`。不对开口网格调用没有可靠语义的 `contains()`。
6. 可选 Blender BVH 审计检查非邻接三角形相交。

本次视觉、碰撞模型各有两个开口。穿越路径净空下界分别为约 **0.983 m / 1.022 m**，
高于 **0.55 m** 要求；BVH 审计两者均无检测到的非邻接相交。包含新增开口测试的
**55 项测试通过**，记录在 `outputs/portal_export_tests.xml`。

这是开口洞壁表面，不是带岩体厚度和外部地形的完整地质实体。开口后不再满足 watertight，
因此不能直接套用历史封闭场景的网格验证器。外部环境、入口外机器人规划与动力学不在此次验证范围内。
批量生成默认仍保留原有封闭参考表示；需要入口、出口时追加这个导出步骤。

## 论文方法图

[GPT-image2 详细绘图 prompt](figures/cave_composer_pipeline_gpt_image2_prompt.md)
包含精确模块、布局、箭头、颜色、验证机制 inset、caption 和事实边界。
主图描述已实现的生成与验证链路；入口/出口导出作为可选后处理标注。

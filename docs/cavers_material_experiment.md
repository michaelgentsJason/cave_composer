# CAVERS → procedural cave appearance

按用户补充，使用本机真实采集的 CAVERS 洞穴数据集作为主要外观参考。
原始数据目录只读：`D:/Desktop/Cave_scan/CAVERS_Dataset`。

## 选帧与视觉分析

跨 `rec_handheld_2/3/4/5` 各抽取 45 帧，按清晰度、暗区和过曝比例筛选，
再从每个序列四个时间段各选一帧，人工视觉检查 16 张候选。
检查表：`outputs/material_experiment/cavers/cavers_contact.jpg`。
该清晰度分数会受传感器噪声影响，因此没有单凭自动排名直接采用贴图。

观察到的真实外观：灰褐色石灰岩/沉积表面、浅色矿物斑块、垂直流痕、
钟乳状悬垂、平滑流石和粗糙破碎区域混合。拍摄中的照明很不均匀，局部灯光
过曝、冷色偏移和低光噪声都不应直接当成岩石反照率或法线。

最终选择两块无灯芯、无人物、无黑色洞口的岩壁区域：

| 序列 | 帧 | 原图 ROI：x,y,width,height | 用途 |
|---|---|---|---|
| rec_handheld_4 | RS_COLOR_2575.png | 340,140,700,430 | 灰褐流石的颜色范围 |
| rec_handheld_5 | RS_COLOR_1929.png | 630,200,660,400 | 灰色垂向岩壁的颜色范围 |

图像 → 岩石 ROI → RGB 分位数 → 两帧聚合调色板 → 新的周期性多尺度材质。
未复制几何，未将原图/atlas 错配到新 UV，也未把相机噪声直接制成纹理。
轻微的纵向相关性 `detail_anisotropy=1.8` 来自视觉判断，**不是物理标定值**。

## 同几何对照

基准：`outputs/final/cave_b_sharp_turns`。
新外观：`outputs/material_experiment/cavers_transfer/cave_b_cavers`。
对照图：`outputs/material_experiment/cavers_transfer/appearance_comparison.jpg`。

两份 visual OBJ、collision OBJ、两个 mesh.npz 都做了 SHA256 字节一致性比较，
全部相同。灯光、相机、路线、净空和碰撞几何保持一致，仅新材质不同。
调色板中央色从手工 limestone 的暖亮灰，变为 CAVERS 参考的较深灰褐色。
原始两帧读取前后摘要相同，确认未修改。

**结论：外观先验接口与材质/几何解耦 PASS；真实 PBR 反演 PARTIAL。**
相机曝光和照明仍影响颜色；没有恢复真实 albedo、法线或 roughness。
粗糙度 0.87 仍是默认值。这里只证明可以用真实洞穴外观指导新材质，
不证明视觉域差距已经关闭。若未来将 CAVERS 用于完全未见的 realistic OOD，
需将这次外观参考实验与那个评估协议分开。

```bash
python scripts/select_reference_frames.py --root /path/to/CAVERS_Dataset --output outputs/cavers_review
python scripts/cavers_material_experiment.py --dataset /path/to/CAVERS_Dataset --source-scene outputs/final/cave_b_sharp_turns --output outputs/cavers_transfer --blender /path/to/blender
```

# Sketchfab 洞穴纹理：本机检查与接入方案

已检查 `sketchfab_caves/` 中的四个 GLB，原文件未修改。运行
`python scripts/extract_reference_textures.py` 可重复提取内嵌图像并生成离线预览：
`outputs/sketchfab_texture_inventory_v01/index.html`。

| 模型 | 内嵌颜色图 | 材质 | 保守来源分组 |
| --- | --- | --- | --- |
| Font del Truffe Entrance in Winter | JPEG，4096×4096 | unlit | Font del Truffe |
| Font del Truffe, small part of Sump 2 | JPEG，4096×4096 | unlit | Font del Truffe |
| Porth Yr Ogof - Sump 9 | JPEG，4096×4096 | unlit | Porth Yr Ogof |
| Porth Yr Ogof - Upper Cave Water Chamber | JPEG，4096×4096 | unlit | Porth Yr Ogof |

四个 GLB 均只引用 base-color 图像，无独立 normal、roughness、metallic 或 AO 贴图。
`KHR_materials_unlit` 表明原显示材质不依赖场景照明，不能把这些颜色图当作测得的本征反照率。
实际图集包含大量拼接边界、暗区与偏色；部分区域可能来自水面、洞外物体或采集设备，
不能仅凭像素颜色认定全图都是岩壁。两个来源分组根据模型标题保守合并，不将四份文件当作四个独立洞穴。

## 已完成的工作

- 原样提取四张 JPEG，逐项核对与 GLB bufferView 的字节一致。
- 保留 GLB 与图片 SHA-256、图像尺寸、材质通道和原始来源元数据。
- 每个目录附 `ATTRIBUTION.txt`；预览缩小，原图不重编码。
- 生成全图颜色统计与程序化色板预览，明确标为草稿：未做 UV 岛掩码、岩壁筛选或光照分离。
- 当前状态为 `EXTRACTED_NOT_TRAINING_INTEGRATED`。没有替换既有 30 套资产或启动训练。

## 自动纹理库的下一步

1. **筛选岩壁区域**：利用原模型的 UV 连通区域和纹理图，选取足够大的连续岩壁片段，
   排除黑色填充、UV 岛边界、反光、设备、水面等区域；自动筛选后做一次目视复核。
2. **形成两种不同输出**：颜色/频率统计可用于扩充现有程序化材质；真实局部纹理需要接缝处理或纹理合成，
   再做 box/triplanar 投影与烘焙。整张 UV 图集不能作为无缝砖块直接平铺到其他网格。
3. **独立外观随机种子**：固定几何，可随机选择材质来源、纹理尺度、方向和适度色彩变化。
   粗糙度与微表面法线继续作为可控程序化参数，记录它们不是由这些 RGB 图恢复的物理量。
4. **双目一致性**：每个 episode 的表面纹理固定且世界坐标锚定；左右视图共享材质、场景灯光和同步时刻，
   不对两张 RGB 独立随机贴纹理。传感器噪声与水下光学另行建模，避免把采集阴影同时当作表面颜色和新灯光阴影。
5. **评测隔离**：如果这两处洞穴的纹理参与训练，其其他扫描片段不能再代表完全未见的洞穴来源。
   使用这些资产的几何做测试时，应明确其外观已见过。严格测试应另留未用于材质开发的洞穴来源。

可以比较「现有程序化纹理」「参考颜色先验」「筛选后的真实纹理加随机化」三种条件，
保持几何数量、训练步数、传感器设置和测试集合一致，冻结策略后比较成功率与碰撞率。
更多纹理增加的是外观覆盖，是否改善双目水下导航 zero-shot 需要该任务的实验，不能由素材数量直接推断。

## 来源与署名

四个文件内嵌元数据均声明作者 **cave-dive-make**、许可 **CC BY 4.0**，并带原页面链接：

- [Font del Truffe Entrance in Winter](https://sketchfab.com/3d-models/font-del-truffe-entrance-in-winter-46c5b87b385b4e48858926d0db642732)
- [Font del Truffe, small part of Sump 2](https://sketchfab.com/3d-models/font-del-truffe-small-part-of-sump-2-b15476c708f7424ba77b0cd0a4c411e0)
- [Porth Yr Ogof - Sump 9](https://sketchfab.com/3d-models/porth-yr-ogof-sump-9-3cf9f626271f47c2be9dc7e7ad1ecf9e)
- [Porth Yr Ogof - Upper Cave Water Chamber](https://sketchfab.com/3d-models/porth-yr-ogof-upper-cave-water-chamber-10056f5a22c6477db660e58b2a7c526f)

本次网页核对成功访问入口与 Sump 9 页面，其余两页返回 403；这些文件的具体许可版本记录来自 GLB 内嵌元数据。
复用及发布时保留作者、来源、许可链接和修改说明，参见 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。
方法背景：[Domain Randomization](https://arxiv.org/abs/1703.06907)研究了渲染变化对视觉迁移的作用；
其结果不是对本项目水下导航任务的效果保证。
# Integration follow-up

The initial inventory below is now followed by a reviewed four-patch library,
automatic material selection, and one exported easy demo. See
[reference texture pipeline](reference_texture_pipeline_v01.md).

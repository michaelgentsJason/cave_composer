# Automated Cave Composer pipeline v0.2

**自动化洞穴构建流程已可用。** 本轮完善生成、校验、材质、预览、批处理恢复和质量汇总。

[打开全部批次预览](outputs/pipeline_v02_final/index.html) · [使用指南](docs/pipeline.md) · [机器可读验收记录](outputs/pipeline_v02_final/acceptance.json)

配置现在可以直接驱动完整流程：CaveSpec / distribution → 确定性几何 → 独立 visual/collision 网格 → 导航与净空验证 → 独立材质 → Blender 无界面渲染与相交审计 → 批次预览、CSV 和质量报告。每个洞穴都有配置、seed、阶段记录、文件摘要和生成结果。

本轮实测结果如下，全部使用新的 base_seed 24000，2 个 worker，开启预览与 `.blend` 保存：

| 批次 | 请求数 | 通过数 | 说明 |
|---|---:|---:|---|
| Train | 8 | 8 | 先生成 4 个，再续跑扩展到 8 个；前 4 个 OBJ 的摘要和修改时间保持不变 |
| Validation | 4 | 4 | 包含本轮发现并修正的法向误判回归场景 |
| ID test | 4 | 4 | 独立 seed 命名空间 |
| Geometry OOD | 4 | 4 | 更大弯角、更窄通道及更大下坡 |
| Composition OOD | 4 | 4 | 训练中排除的因素组合 |
| CAVERS 外观对照 | 2 | 2 | 复用两个训练 seed，四个几何文件逐字节一致，albedo 不同 |

因此是 **24 个不同几何 + 2 个外观变体**，不是 26 个不同几何。该轮记录的端到端耗时约 416 秒，包含几何、验证、渲染和产物检查；它是当前机器下的批量实测，尚不是受控的性能基准，也不能外推千场景失败率。

**恢复与可追溯性已经补齐。** 总清单会在每个场景完成后原子更新。`--resume` 核对配置、代码、依赖、渲染设置、文件清单和 SHA256，再复用完整场景；场景提交后尚未来得及写总清单的中断也能恢复。未完成场景按原 seed 重建，旧产物归档；明确失败的场景需要 `--retry-failed` 才会重试。请求的 seed 不会被替换，损坏或手工修改的成功产物不会被覆盖。恢复粒度是场景，尚未支持从一半网格计算继续。

**自动测试：38 passed，0 failed，0 skipped。** 覆盖指定弯角、净空和阻挡、组合分割、文件复现、场景内/场景间中断、提交后恢复、扩容、失败归档和原 seed 重试、文件篡改拒绝、输出互斥、材质解耦与法向检查。[测试记录](outputs/pipeline_v02_final/test_results.xml)

本轮也修正了一个实际校验问题：初次批量生成时，一个碰撞网格与原始近似场的方向一致率为 97.9375%，因此被原检查拒绝。对最终网格法线两侧各做内外测试后，2,000/2,000 个采样面都指向洞内。当前实现保留原始一致率，在它不足以判断时追加网格自身的方向检查；反向外壁和反向内部岩体均有拒绝测试。没有改变这个 seed 的几何，也没有降低净空门槛。[原始复核](outputs/pipeline_v02/normal_review.json) · [最终验证](outputs/pipeline_v02_final/validation/scene_000001/metadata/validation.json)

每个批次自动输出 `index.html`、`manifest.json`、`quality.json` 和 `metrics.csv`。画廊支持状态筛选以及 overview / inside / topology 切换，并已通过桌面和移动端浏览器检查。CAVERS 的观察色彩已作为独立 YAML 预设提供，生成时无需读取原始数据集；粗糙度仍是默认值，未声称测量级 PBR 恢复。

直接使用：

```bash
python generate_dataset.py --distribution configs/cavers_distribution.yaml --num-scenes 24 --workers 2 --output outputs/my_caves --render --blender D:/Blender/blender.exe --save-blend
```

中断后执行相同命令并加 `--resume`。安装后的等价入口是 `cave-dataset`。

主要限制仍在几何自然度、多样性与规模验证：部分岩层过于规则，窄处仍有管道/圆孔感；默认批量采样器主要是两段弯道加可选分支/大厅，虽然 CaveSpec 支持更丰富的结构，默认采样分布仍需扩展。目前采用稠密格点，worker 数量受内存限制。已有自动构建和筛选洞穴库的完整流程，后续最有价值的工作是丰富地质形态、增加拓扑覆盖，再做百/千场景压力测试。

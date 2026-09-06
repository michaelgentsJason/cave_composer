# 自动建立 caves：v0.2 pipeline

输入一个 CaveSpec 或分布配置，自动得到洞穴网格、材质、导航结构、几何校验、
可选 Blender 预览和批次质量报告。当前工作集中在这条独立生成流程。

```text
配置预检
  → 固定 split / seed / 配置 / 代码与依赖指纹
  → 多进程生成独立场景
      topology → geometry → validation → metrics
      → material / OBJ export → topology preview
      → 可选 Blender render / intersection audit / packed .blend
  → 每个场景原子提交、校验全部文件摘要
  → 每完成一个场景更新 manifest
  → quality.json + metrics.csv + index.html
```

## 一次生成完整批次

```bash
pip install -e ".[test]"
python generate_dataset.py --distribution configs/train_distribution.yaml --num-scenes 24 --workers 2 --output outputs/my_caves --render --blender D:/Blender/blender.exe --save-blend
```

安装后的等价入口是 `cave-dataset`。`--render` 启用无界面 Blender，自动生成
overview、inside_01、inside_02，并运行独立三角形相交审计。
`--save-blend` 保存包含完整网格和打包纹理的可编辑场景，需要同时启用 `--render`。
不加这两项时只需 Python，仍会输出网格、材质、导航、几何验证与 topology.png。

其他机器可以传自己的 Blender 可执行文件，或者设置 `BLENDER_PATH` / PATH。
无效配置和缺失的 Blender 会在网格生成前报告，避免生成一半才发现参数错误。

单洞穴仍可直接使用：

```bash
python generate.py --config configs/cave_b_sharp_turns.yaml --seed 42 --output outputs/my_b --render --blender D:/Blender/blender.exe --save-blend
```

## 中断、扩容与重试

使用同一配置和相同渲染选项，加上 `--resume`：

```bash
python generate_dataset.py --distribution configs/train_distribution.yaml --num-scenes 24 --workers 2 --output outputs/my_caves --render --blender D:/Blender/blender.exe --save-blend --resume
```

续跑会逐个核对完成场景的配置、seed、运行日志、验证结果、文件清单及 SHA256。
完整且一致的场景直接复用；已提交但来不及写入总清单的成功产物也会被识别。
未完成场景使用相同 seed 从头重建，旧的部分产物保存在 `.attempts/` 中。
这是**场景级断点续跑**，尚不支持从一半网格计算或某一 Blender 帧继续。

可以改变 `--workers`，也可以增加 `--num-scenes` 来扩展原有批次；不能缩小批次。
分布、代码、依赖和渲染配置必须保持一致，渲染时还核对 Blender 可执行文件摘要。
换算法或升级依赖时使用新输出目录，避免将两个版本混成一个实验。

已经明确失败的场景默认保留。恢复磁盘空间等外部条件后，可显式增加
`--retry-failed`，在相同 seed 下重试；每次旧产物及失败诊断都归档。
确定性的几何失败不会因为重复执行而自动修好，失败 seed 不会被偷偷换掉。
`--num-scenes` 表示请求的种子数量，因此总清单可能包含被拒绝的场景。

完成场景被手工改动或损坏时，续跑会拒绝复用，也不会覆盖该文件。
同一输出目录由操作系统文件锁保护，进程退出后锁自动释放；可以在不同目录
并行运行独立批次。v0.1 的旧清单不含这些恢复契约，继续保留为历史产物，
请用新目录开始 v0.2 批次。

## CAVERS 外观预设

```bash
python generate_dataset.py --distribution configs/cavers_distribution.yaml --num-scenes 24 --workers 2 --output outputs/cavers_caves --render --blender D:/Blender/blender.exe --save-blend
```

该配置使用本机 CAVERS 两帧岩壁 ROI 已提取的灰褐调色板和视觉选定的细节方向性，
原始图像无需随生成器安装。roughness 仍是默认值，不能当作测量级 PBR。
材质参数放在 `overrides.material`，几何采样与材质独立。保持 split 和 base_seed
相同，可对比同一批几何的不同外观。出处见 [CAVERS 实验](cavers_material_experiment.md)。

如果需要自定义风格，在分布 YAML 中填写 `overrides.material.palette`、`seed`、
`roughness` 和 `detail_anisotropy`。几何因素不能通过该 overrides 任意覆盖，
以免破坏已经声明的 OOD 支持范围。

## 输出与观察进度

```text
my_caves/
  manifest.json        # 启动和每个场景完成时原子更新；全部种子/状态/尝试次数
  quality.json         # 成功场景的 min/median/p95/max；失败原因；当前执行统计
  metrics.csv          # 每个请求 seed 一行，包括失败
  index.html           # 本地可视化索引，支持状态筛选及视角切换
  .attempts/           # 重试或重建前保留的旧产物
  scene_000000/
    metadata/run.json  # 阶段、起止时间、执行结果、配置与环境指纹
    metadata/validation.json
    metadata/checksums.json
    visual/ collision/ materials/ navigation/ previews/
    cave.blend         # 使用 --render --save-blend 时存在
```

运行过程中查看 `manifest.json` 的 valid / invalid / pending，或各临时场景的
`metadata/run.json`。批次结束或正常收到中断后会生成质量报告。几何无效标为
INVALID；I/O、渲染或 worker 异常标为 ERROR，并记录失败阶段。命令在存在失败
时返回退出码 2，方便外部脚本识别，仍保留完整清单和可用场景。

质量报告的数值来自实际产物。宽度是采样测量值；净空保证适用于配置的球形机器人
沿路线折线运动。没有用几何字段值冒充距离证书。批次中的时间来自本次运行条件，
并发和 GPU 争用会影响它们，不宜直接当作跨算法性能基准。

法向检查保留原始场的方向一致率；若它与实际离散网格不一致，会对最终网格的
面法线两侧做内外测试。需要超过 95% 的采样可判定，且其中超过 98% 指向洞内，
并同时满足封闭、绕序和总体方向检查。这样不会仅因场的近似误差拒绝正确网格，
也不会放行反向的外壁或内部岩体法线。证据保存在 `normal_side_audit` 中。

## 验证这条 pipeline

```bash
python -m pytest -q
python scripts/exercise_pipeline.py --output outputs/pipeline_check --blender D:/Blender/blender.exe --workers 2
```

自动测试覆盖中途退出后续跑、先提交场景再中断的恢复、扩容、完整性篡改拒绝、
配置不匹配拒绝、失败原 seed 重试和归档、输出目录互斥及渲染预检。
验收脚本跨五种 split 生成 24 个场景，先生成 4 个训练场景再扩展到 8 个，
并检查已有 OBJ 摘要和修改时间不变；若 CAVERS 先验文件可用，再生成两个同几何
外观对照。原始失败也会进入验收记录。

稠密格点仍有内存上限，`--workers` 应结合可用内存设置。当前流程适合自动建立
并筛选洞穴库；千场景失败率、稀疏分块和自动地质修复仍需单独验证。

# 蓝色大肥鱼 3D 资产交付规格

给协作美术看的。按这里的规格交付，模型放进 `assets/characters/` 就能直接进展厅和之后的游戏，不用改代码。

## 1. 每个角色要交的文件

| 文件 | 必需？ | 说明 |
| --- | --- | --- |
| `<id>.glb` | 必需 | 游戏实际加载的文件：网格、骨骼、蒙皮、材质、贴图、动画全部打包在一个 glTF 二进制文件里 |
| `<id>.blend`（或 `.ma` / `.max` / `.fbx` 源文件） | 强烈建议 | 源工程，之后改模型、加动作要用 |
| 贴图源文件（`.psd` / `.kra` / `.spp` / 原始 `.png`） | 建议 | 贴图已经打包进 `.glb`，这里是可编辑的原稿 |
| 表情贴图（眼睛、嘴巴，每种表情一张或一张图集） | 有表情的角色必需 | 带透明通道的 PNG，也打包进 `.glb` |
| 一张说明（文字即可） | 必需 | 身高、动作列表、表情列表、有没有不按本规格做的地方 |

头像 `assets/portraits/<id>.jpg` 不用交，我这边渲染。

## 2. 文件名（替换现有模型时用同名）

| id / 文件 | 角色 | 现在的身高 |
| --- | --- | --- |
| `bluefish.glb` | 蓝色大肥鱼 | 0.96 m |
| `whale_baby_a.glb` `whale_baby_b.glb` `whale_baby_c.glb` | 小鲸鱼宝宝（三种体型） | 约 0.25–0.35 m |
| `whale_big.glb` | 大圆鲸 | 0.64 m |
| `dragon.glb` | 白色龙娘 | 1.07 m |
| `doubao.glb` | 豆包帮首领 | 1.22 m |
| `rice_cooker.glb` `golden_cooker.glb` | 电饭煲、黄金电饭煲 | 约 0.21 m |
| `sign.glb` | 「喜欢的话可以点赞谢谢喵」木牌 | 0.30 × 0.19 m |
| `box.glb` | 纸箱 | 0.40 m |
| `rope.glb` | 绑大圆鲸的绳子 | 贴合大圆鲸 |

新角色用小写英文加下划线起名，例如 `seagull_boss.glb`。

## 3. 尺寸、朝向、原点

- 单位：1 = 1 米。身高尽量和上表一致，角色之间比例才对得上。
- 在 Blender 里 Z 轴朝上，角色面朝 **-Y**（前视图里看到的就是正脸）。导出时勾选 +Y Up（默认就是）。
- 原点在两脚中间的地面上，脚底贴 Z=0。
- 所有物体应用变换（Apply All Transforms）：缩放 1、旋转 0。
- 静止姿势（rest pose）用 A 字或自然站姿。

## 4. 骨骼

- 每个文件只有一套骨架，每个顶点最多 4 根骨骼影响（glTF 标准）。
- 骨骼名字大多可以自定，但下面这些名字代码会用到，必须照写：

| 骨骼名 | 谁要有 | 用途 |
| --- | --- | --- |
| `root` | 所有角色 | 根骨骼，放在原点 |
| `eye.L` `eye.R` | 会眨眼的角色 | 眨眼动画在竖直方向压扁这两根骨骼，眼睛贴图只绑在它们上面 |
| `prop` | 蓝色大肥鱼 | 手持道具（木牌、电饭煲）挂在这根骨骼上，挂在胸口骨骼下面，位于胸前 |
| `body` | 大圆鲸 | 绳子挂在这根骨骼上 |

- 左右用 `.L` / `.R` 结尾，角色自己的左边是 `.L`。
- 想沿用我现在做好的动作，就用现有骨架：在 Blender 里导入 `bluefish.glb`，保留 Armature，把新模型重新蒙皮到它上面。现有大肥鱼骨骼（37 根）：`root hips spine chest neck head eye.L eye.R ahoge fin.L fin.R hair.B.1 hair.B.2 hair.L.1 hair.L.2 hair.R.1 hair.R.2 lock.L lock.R upperarm.L lowerarm.L hand.L upperarm.R lowerarm.R hand.R prop upperleg.L lowerleg.L foot.L upperleg.R lowerleg.R foot.R tail.1 … tail.5`
- 飘动的部位（头发、裙摆、尾巴、鳍耳）要有自己的骨骼链，动作才能带动它们。

## 5. 动画

- 每个动作是一个 Blender Action，导出后就是一个 glTF 动画片段，名字必须和下表一致（小写英文）。
- 循环动作首尾帧要能无缝接上；帧率 24 fps。
- `blink` 只动 `eye.L` `eye.R`，约 8 帧，会叠加在其他动作上随机播放。

| 角色 | 动作名（按钮上显示的中文） |
| --- | --- |
| 蓝色大肥鱼 | `idle` 待机、`walk` 走路、`run` 跑步、`cheer` 欢呼、`sign` 举点赞牌、`carry` 抱电饭煲、`swim` 游泳、`peek` 探头、`blink` |
| 小鲸鱼宝宝 | `idle` 待机、`hop` 蹦跳、`flap` 拍鳍、`spin` 开心转圈 |
| 大圆鲸 | `idle` 待机、`happy` 开心、`hop` 蹦跳、`struggle` 被绑挣扎、`blink` |
| 白色龙娘 | `idle` 待机、`walk` 走路、`flap` 扇翅膀、`point` 指人、`blink` |
| 豆包帮首领 | `idle` 待机、`walk` 走路、`stomp` 生气跺脚、`knocked` 被放倒（播一次停住）、`blink` |
| 电饭煲 | `closed` 静置、`open` 打开锅盖（播一次停住） |

- 动作原地播放，不要让角色真的走出原点（游戏里由代码移动角色）。
- 想加新动作可以随便加，告诉我名字和中文叫法，我加到按钮里。

## 6. 表情

- 眼睛、嘴巴做成贴在脸上的独立小网格（贴花），每种表情一个网格，用名字区分，展厅通过显示/隐藏来切换：

| 网格名 | 表情 |
| --- | --- |
| `expr_eyes_open` | 睁眼（默认） |
| `expr_eyes_happy` | 笑眼 ^ ^ |
| `expr_mouth_open` | 张嘴笑（默认） |
| `expr_mouth_small` | 微笑 |
| `expr_mouth_round` | 哦！（圆嘴） |
| `expr_mouth_cat` | ω 猫嘴 |

- 腮红等常驻的贴花随便起名，不要以 `expr_` 开头。
- 贴花材质名以 `face_` 开头，用带透明通道的 PNG。
- 想用形态键（shape key / morph target）做表情也可以，告诉我形态键名字，我改展厅代码支持。

## 7. 材质

材质名的前缀决定展厅怎么渲染：

| 前缀 | 渲染方式 | 适合 |
| --- | --- | --- |
| `pbr_` | 完全按导出的 glTF 材质渲染：底色、法线、粗糙度、金属度、AO 贴图，以及 Principled BSDF 导出的清漆、光泽等扩展都保留 | **推荐专业美术用这个**，你在 Blender / Substance 里看到什么，展厅里基本就是什么 |
| `fig_` | 我写的手办材质：只用底色（贴图或顶点色），光泽参数写在材质自定义属性 `style` 里（JSON，例如 `{"rough":0.4,"coat":0.5,"sheen":0.3}`） | 我现在的程序化模型 |
| `face_` | 不受光照、带透明的贴花 | 眼睛、嘴巴、腮红、木牌上的字 |
| `metal_` | 同 `pbr_` | 金属道具 |

- 贴图：PNG 或 JPG，边长 2 的幂，最大 2048（脸部可以 2048，其余 1024 就够）。
- 底色贴图用 sRGB，法线 / 粗糙度 / 金属度用线性（Blender 设为 Non-Color）。
- 不要用 Draco、Meshopt 压缩，也不要用 KTX2 贴图，展厅目前不支持。需要的话告诉我，我加解码器。

## 8. 面数和文件大小（网页要能在手机上跑）

| 类型 | 三角面 | `.glb` 大小 |
| --- | --- | --- |
| 主角（蓝色大肥鱼） | ≤ 80k | ≤ 5 MB |
| 其他角色 | ≤ 50k | ≤ 4 MB |
| 小鲸鱼宝宝（一次会出现 20 多只） | ≤ 8k | ≤ 0.5 MB |
| 道具 | ≤ 10k | ≤ 0.5 MB |

## 9. 美术方向

- 和原视频一样的萌版手办风格：大头（约 2.2–3 头身）、圆润、柔和的光泽，不要写实、不要性感化。
- 参考帧在仓库 `refs/` 目录（从三部视频截的 23 张图）。现在的模型在 `assets/characters/`，可以直接拖进 Blender 或 https://gltf-viewer.donmccurdy.com 看比例和骨架。
- 场景是写实照片背景，角色要在写实光照下好看。

## 10. Blender 导出设置（File → Export → glTF 2.0）

- Format：glTF Binary (.glb)
- Include：勾选 Custom Properties（`fig_` 材质的 `style` 要靠它）
- Transform：+Y Up
- Data → Mesh：Apply Modifiers、UVs、Normals；用了顶点色就勾 Vertex Color
- Data → Armature / Skinning：开启
- Animation：模式选 Actions，勾选 Always Sample Animations
- Compression：不勾

## 11. 交付后我这边做什么

1. 用 glTF 官方校验工具检查（要求 0 个错误）。
2. 放进 `assets/characters/`，在 `gallery/catalog.js` 里登记动作、表情、道具位置。
3. 渲染三视图、每个动作的截图，发给你们确认。

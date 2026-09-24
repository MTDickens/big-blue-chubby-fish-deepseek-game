# 蓝色大肥鱼 · 同人游戏企划

This is a fan game project based on 天才小白喵's Bilibili 「蓝色大肥鱼」 videos. The current stage is the **character gallery**: every character from the three videos is modeled in 3D, rigged and animated, and viewable in the browser.

- EP1 [BV1AAe264E2r](https://www.bilibili.com/video/BV1AAe264E2r): 抢电饭煲
- EP2 [BV1Zreb6iES3](https://www.bilibili.com/video/BV1Zreb6iES3): 夜盗黄金电饭煲
- EP3 [BV1geeq65E1z](https://www.bilibili.com/video/BV1geeq65E1z): 游艇救出大圆鲸

## The gallery

Open `index.html` (it has to be served over HTTP). After GitHub Pages is on, the address is
`https://mtdickens.github.io/big-blue-chubby-fish-deepseek-game/`.

| Mode | What it shows |
| --- | --- |
| 角色 | Pick a character, then an animation, expression and scene. Drag to rotate, scroll to zoom. |
| 三视图 | Front, side and back views at the same scale. |
| 全员合影 | All characters in one row, labeled with their heights. |
| 片尾复刻 | The EP1 ending: 大肥鱼 holds up the 「喜欢的话可以点赞谢谢喵」 sign while baby whales hop around on the beach. |

Scenes are a studio stand plus four real panoramas: beach, old town at night, seaside at night and a daytime harbor. The panoramas come from [Poly Haven](https://polyhaven.com) and are CC0.

A link can open straight into a given view, for example `index.html#m=solo&c=dragon&bg=night_sea`.

### Turning on GitHub Pages

1. Open the repo's **Settings → Pages**.
2. Under **Build and deployment**, pick **Deploy from a branch**.
3. Select branch `claude/friendly-pascal-6jhbwc` and folder `/ (root)`, then click Save.
4. The site goes live after about a minute.

## Directory layout

```
index.html                 gallery page
gallery/                   gallery code: app.js, catalog.js (character list), stage.js (scenes and lighting), toon.js (materials)
gallery/dist/app.js        bundled build (npm run build)
assets/characters/*.glb    character and prop models: skinned, with animations
assets/bg/                 panorama backgrounds
assets/portraits/          roster portraits
tools/charkit/             modeling toolkit (Blender Python)
tools/gallery/             bundling and screenshot scripts
refs/                      reference frames taken from the videos
vendor/                    three.js r186 and the MToon material (MIT)
```

## How the models are made

The models are sculpted from signed distance fields (SDF) in code, the way you shape clay: spheres, capsules and swept tubes are smoothly fused into each form. Blender then extracts the meshes, cuts the triangle count, binds the skeletons and writes out the animations. Hair is a scalp volume plus swept locks. Eyes and mouths are texture decals projected onto the head, and changing expression swaps the decal. Materials follow the look of a painted PVC figure: clearcoat, sheen and soft reflections.

Rebuild the models (needs Python 3.11 and `pip install bpy==4.5.* scikit-image`):

```bash
python3 tools/charkit/build.py              # every character
python3 tools/charkit/build.py bluefish     # one module: bluefish | whales | rivals | props
```

Rebuild the gallery code:

```bash
npm install
npm run build
```

Headless screenshots for review (needs Playwright):

```bash
node tools/gallery/shot.js out.png "m=hero&still=1.3" 1600x900
node tools/charkit/render.js out.png "m=assets/characters/bluefish.glb&view=turn4"
```

## Adding a character or animation

1. Add a module under `tools/charkit/characters/` that builds the model, rig and animations and exports a `.glb`.
2. Add an entry to `CHARACTERS` in `gallery/catalog.js`. It holds the name, the animation list, the expressions and any props that attach to bones.
3. Add the portrait to `assets/portraits/<id>.jpg`.

This is a free fan work, not for sale. All characters and story belong to the original videos' creator.

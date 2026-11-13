# 角色工廠說明（2026-11-12）

程式位置：`site/office/play/`。展示頁：`site/office/play.html`（左上「圖鑑」可選物種、配色、配件）。

## 一、檔案

| 檔案 | 內容 |
|---|---|
| `species.js` | **物種圖鑑資料**：15 個物種的尺寸、移動方式、配色表、配件位置、組裝函式、待機小動作、招牌動作；`resolveSpec(spec)`、`addAccessories()` |
| `character.js` | 共用骨架 `Character`：彈性身體（擠壓伸展彈簧、果凍晃動）、種在地上的腳、彈簧手與附屬物、表情與姿態、被戳／摸／拎起丟／餵食／接球的反應 |
| `face.js` | Canvas 即時畫的臉：一組參數內插出所有表情；沒變就不重畫 |
| `soft.js` | 軟質材質（漸層、邊緣光、假次表面散射、凹陷、接地壓扁）與圓潤幾何 |
| `world.js` | 展示用的小房間與剛體物理（球、箱子、彈跳床、家具） |
| `fx.js` | 粒子與即時合成音效 |
| `lite.js` | 不需要房間也能用角色：假地面、靜音特效、`renderThumb()` 畫縮圖 |
| `office_character.js` | **給辦公室場景用的工廠 `createCharacter(spec, env)`** |
| `main.js` | 展示頁的輸入、鏡頭、介面 |

## 二、個體規格 spec

```js
{ species: 'mug',           // 物種代號（見下表）
  pal: 2,                   // 配色：編號 0~3 或名稱（例如 '晴藍'）
  hue: 0.02,                // 色相微調 -0.08 ~ 0.08（同配色再拉開個體差異）
  acc: ['glasses', 'tie'],  // 配件：glasses hat bow tie scarf badge；物種戴不了的自動略過
  accColor: 1 }             // 配件顏色 0~5
```

15 物種 × 4 配色 × 色相微調 × 6 種配件的任意組合 × 6 種配件色，44 位成員不會撞臉。

| 代號 | 名字 | 造型重點 | 移動方式 | 待機小動作 | 招牌動作 | 可戴配件 |
|---|---|---|---|---|---|---|
| mochi | 糰糰 | 麻糬糰子、圓耳、短尾 | 小碎步 | 耳朵抖一下 | 彈彈跳 | 眼鏡 帽 蝴蝶結 領帶 識別證 |
| bean | 豆芽 | 豆子身體、真的有手腳、兩片葉子 | 踩步走 | 葉子晃 | 長葉子 | 全部 |
| robo | 啵啵 | 圓頭、發光的臉、彈簧天線 | 踩步走 | 天線尖端閃 | 掃描 | 帽 蝴蝶結 領帶 圍巾 識別證 |
| cloud | 綿綿 | 好幾顆球堆成的雲 | 飄浮 | 偶爾滴一滴雨；難過會下雨 | 下小雨 | 眼鏡 帽 蝴蝶結 |
| flame | 小燭 | 水滴形、尖端歪一邊、會發光 | 彈跳 | 一直搖曳、冒火星 | 燒旺 | 眼鏡 蝴蝶結 |
| cactus | 刺刺 | 盆栽、一高一低兩隻手臂、小花 | 連盆跳 | 抖刺 | 開花 | 眼鏡 帽 蝴蝶結 圍巾 |
| mug | 拿鐵 | 咖啡杯、單邊把手、咖啡會晃 | 搖擺走 | 冒蒸氣 | 乾杯 | 眼鏡 蝴蝶結 領帶 識別證 |
| ghost | 飄飄 | 圓頂＋波浪裙擺＋頭頂一撮 | 飄浮 | 左右飄 | 嚇你一跳 | 眼鏡 帽 蝴蝶結 圍巾 |
| bird | 啾啾 | 蛋形、立體尖嘴、翅膀、頭頂三根毛 | 左右搖擺 | 歪頭、啾一聲 | 拍翅膀 | 全部 |
| octo | 八寶 | 大圓頭＋七條短觸手 | 貼地滑行 | 觸手各自蠕動 | 噴墨 | 眼鏡 帽 蝴蝶結 |
| star | 閃閃 | 鼓鼓的五角星 | 蹦蹦跳 | 尖角閃光 | 側翻 | 眼鏡 帽 蝴蝶結 領帶 識別證 |
| calc | 算算 | 方形、液晶臉、九顆按鍵 | 硬邦邦地走 | 按鍵自己按 | 算一算 | 帽 蝴蝶結 |
| pudding | 布布 | 平頂梯形、焦糖、櫻桃 | 抖著跳 | 自己抖一下 | 抖抖舞 | 眼鏡 蝴蝶結 領帶 識別證 |
| seal | 滾滾 | 橫躺長條、前鰭、翹起的尾鰭 | 一伸一縮 | 尾巴擺 | 翻肚肚 | 眼鏡 帽 蝴蝶結 |
| bulb | 亮亮 | 倒梨形玻璃、螺紋座 | 踮腳走 | 亮度跟心情變 | 靈光一閃 | 眼鏡 帽 蝴蝶結 圍巾 |

## 三、兩種用法

### 1. 完整互動版（展示頁那種，要有房間）

```js
import { Character } from './play/character.js';
const ch = new Character({ species: 'bird', pal: 1, acc: ['scarf'] }, scene, world, fx);
// 每幀：for (子步) { ch.step(h, ctl); world.step(h, ch); }  ch.animate(dt, env);
ch.setGoal(x, z, run);  ch.jump();  ch.emote('happy', 3);  ch.doAct('sig');   // wave bow dance spin talk yawn sig
ch.poke(hitPoint, rayDir);  ch.petStart(hit); ch.petEnd();  ch.grab(); ch.dragTo(p); ch.release();
ch.sit(); ch.sleep(); ch.say('你好');  ch.useThing(world.uses[0]);
```

### 2. 辦公室場景版：`createCharacter(spec, env)`

介面完全照 `site/office/world/js/character.js` 開頭的約定（`object3D、radius、height、state、update、setAction、setExpression、walkTo、stop、sitAt、standAt、faceTo、say、emote、setVisible、dispose`），不用改場景程式：

```
world.html?char=../../play/office_character.js
```

- spec 可以多帶 `species／pal／hue／acc／accColor` 指定外觀；沒帶就依 `race` 關鍵字挑物種（機器人→啵啵、幽靈→飄飄、鳥類→啾啾…），挑不到用 `id` 雜湊平均分配。同一個 `id` 每次長相固定。`lead` 會打領帶；CEO 戴帽子、領帶、識別證。
- 另外多給 `character.look`（實際採用的外觀）與 `character.inner`（底層的 `Character`，要戳它、讓它做招牌動作時用）。
- 動作對應：`type read note listen think nod raise clap cheer drink` 有各自的姿勢；`sleep` 會真的睡；`wave shake angry talk` 用互動版的動作；表情 `neutral happy angry surprised sad think awkward proud` 對應到 8 種臉。
- 已實測：2026-11-12 把 44 位成員全部換成這個工廠，場景可正常載入、0 錯誤（截圖 `world_adapter.png`）。

**還沒做的（如實）**：辦公室版沒有接粒子與音效（`env.fx` 沒給就靜音）；沒有接觸陰影；`spec.isCeo` 沒有特別放大；每位成員一張 256 的臉部貼圖，44 位同時在場的效能只在軟體繪圖下跑過，還沒在真手機量過。

## 四、新增一個物種

在 `species.js` 的 `SPECIES` 加一筆：尺寸（`R` 碰撞半徑、`top` 頭頂高）、`move`（`walk／hop／float／slide`）、`face`（眼睛與嘴在 512 貼圖上的位置大小）、`pals`（至少 1 組配色）、`anc`（配件位置）、`build(c, p)`（把網格加進 `c.deform`，臉要畫在 `c.main` 上）、`idle(c, dt, t)`、`sig: { dur, fn(c, u, a, P) }`。骨架、表情、互動都自動沿用。


## 五、辦公室整合（2026-11-13）

正式角色已是辦公室的預設（`site/office/world.html`，不用再加網址參數；`?char=./character.js` 可換回膠囊佔位角色，只供除錯）。

| 項目 | 位置與做法 |
|---|---|
| 每人固定造型 | `site/office/world/data/roster.json`：CEO 與 43 位成員各自的物種、配色、配件與理由；同部門用部門色的識別證（戴不了的物種改同色圍巾或蝴蝶結），主管多一條領帶；CEO 是戴小皇冠、打領帶、放大 1.18 倍的糰糰。另有 3 隻寵物（迷你版物種）。 |
| 使用者修改 | 進度卡「改造型」可改名字、暱稱、物種、配色、配件（原職稱鎖定，名牌同時顯示暱稱與原職稱）；存在瀏覽器 `localStorage` 的 `aiOffice.roster.v1`，不改資料檔。 |
| 物種 | 19 種：原 15 種＋貼貼（便利貼）、夾夾（資料夾）、筆筆（鉛筆）、印印（印章）。新配件 `crown`（小皇冠）；`accColor` 可直接給色碼。 |
| 動作 | `setAction(name)`：持續型 `idle type read tablet doc note listen think phone drink eat magnify carry present doze sulk sleep paddle`；一次型 `talk nod shake raise cheer clap angry wave stretch slam point pour reach`。姿勢寫在 `play/character.js` 的 `pose()`，坐著與站定都套用；沒有手的物種用身體傾斜、彈跳、附屬物擺動表現。 |
| 道具 | 書、平板、筆記本＋筆、手機、杯子、文件、甜甜圈、放大鏡、球拍；有手的拿在手上，沒手的飄在身邊。筆記本字跡、平板畫面是共用的動態貼圖。 |
| 情緒圖示 | `emote(name)`：`exclaim question anger sweat bulb star heart note dots zzz check`，畫布畫的圖示（不是文字），顯示在名牌上方。 |
| 坐下與起身 | 從椅子旁邊跳上、跳下（拋物線＋擠壓），不再瞬間移動；個子矮的會多一塊加高坐墊，臉不會被桌面擋住。 |
| 互動 | `pet() bonk() feed() grab() dragTo() release()`；被放下後由場景的 `director.dropped` 讓他自己走回座位。 |
| 效能 | `configure({ detail, faceSize, lodNear, lodFar, fxDist })`：桌機幾何細緻度 0.55、手機 0.4；中距離藏很小的零件、遠距離藏手腳配件道具並降低姿態更新頻率；遠處不放粒子。 |
| 螢幕 | `world/js/world.js`：8 種會動的畫面（程式碼、K 線、試算表、設計稿、聊天室、剪輯時間軸、折線圖、文件），依部門與個人分配。 |

**還沒做的（如實）**：真手機沒量過；角色仍是每隻多個網格（沒有合併成單一網格）；會議與任務內容仍是示範資料。

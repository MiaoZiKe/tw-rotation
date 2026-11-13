# AI Office 角色升級：程式碼與角色品質診斷（第一階段，2026-11-13）

範圍：`site/office/play/`（角色工廠）與辦公室端使用角色的部分。本階段**沒有改任何產品程式碼**。規劃見 `upgrade_plan.md`。
擁有者要求原文與優先順序：`scratchpad/upgrade_brief.md` 第二、十、十一節。

## 零、實際讀過什麼、沒讀什麼

### 實際讀過（逐行）
| 檔案 | 讀過的行 |
|---|---|
| `site/office/play/character.js` | 1–621 全部 |
| `site/office/play/soft.js` | 1–110 全部 |
| `site/office/play/limb.js` | 1–153 全部 |
| `site/office/play/face.js` | 1–205 全部 |
| `site/office/play/world.js` | 1–321 全部 |
| `site/office/play/main.js` | 1–271 全部 |
| `site/office/play/office_character.js` | 1–286 全部（含最後 273–286） |
| `site/office/play/lite.js` | 1–32 全部（註：此檔 32 行，內容是 `renderThumb` 與假世界） |
| `site/office/play.html` | 1–69 全部 |
| `site/office/play/fx.js` | 1–110（粒子貼圖、`FX.spawn/burst/update` 前半） |
| `site/office/play/species.js` | 1–75（輔助函式、`DEF`、糰糰 `mochi` 全部、豆芽開頭）、606–719（`resolveSpec`、個體差異、`applyTraits`、`mergeGeos`、`addAccessories`）；另用 grep 看了 seal／dino 的設定列 |
| `site/office/world/js/world.js` | 25–40、255–277（光照、渲染器、接觸陰影）；另 grep 全檔 |
| `site/office/world/js/main.js` | 14–90、225–245（角色模組載入、建立角色、拎起來丟）；另 grep |
| `site/office/world/js/director.js` | 215–232；另 grep `walkTo／sitAt／grab` 等呼叫處 |
| `site/office/world/js/character.js`（佔位版） | 1–40（介面約定） |
| `site/office/vendor/` | 列出檔案、`three.module.min.js` 版本號（r160）、`BufferGeometryUtils.js` 匯出清單 |
| `docs/ai_office/character_factory.md` | 1–90、129–145 |
| `docs/ai_office/character_design_review.md`、`appeal_principles.md`、`tools_research.md` | 只讀標題與 `tools_research.md` 前 42 行 |

### 沒讀（或只掃過）
- `species.js` 76–605：其餘 22 個物種的 `build／idle／sig`（只靠 grep 看過 seal、dino 的設定列）。**因此本文所有「物種造型」結論只對糰糰成立。**
- `fx.js` 111–160（音效合成）、`play.css`（71 行）、`site/office/world/js/{furniture,nav,kit,ui}.js`、`director.js` 其餘部分、辦公室 `main.js／world.js` 其餘部分。
- `site/office/model/*.js`、`site/office/models/boy_*.glb`、`tools/ai_office_pipe/`：只用 grep 看過存在與 `GLTFLoader` 載入寫法（`model/char.js:84`）；這是另一條「人形角色 GLB」的前案，沒有審。
- 沒有在手機實機或有 GPU 的瀏覽器跑過；所有量測都在這個容器的無頭 Chromium（軟體繪圖 SwiftShader）。**只有 JS 端數字（位置、速度、頂點座標、`renderer.info`）可信；任何 fps 或 GPU 時間都沒有量。**

## 一、先講量測方法（所有數字都來自這裡）

小程式都在 `scratchpad/q/`（`m1.js`～`m8.js`、`sdf.js`），用已裝好的 Playwright 對 `http://localhost:8765/office/play.html?manual&test&c=mochi` 取樣；透過頁面上既有的 `window.PLAY`（`sim()` 以固定步進推進、`char`、`keys`）：

| 編號 | 量什麼 | 怎麼量 |
|---|---|---|
| m1 | 糰糰的 Mesh 階層、頂點數、材質參數 | 遞迴走 `char.root`，讀 `geometry.type／position.count`、`material.userData.U` |
| m2 | 跳躍頂點高度／滯空／落地壓縮、不同 fps、彈簧在大時間步 | `PLAY.sim(n, dt)` 以 20/30/60/144 fps 推進；`step(h)` 直接餵 0.016～0.35 秒 |
| m3 | 走路／跑步腳滑動量、步頻、腿長變化、身體最低點 | 每幀記 `feet[i].p`、`planted`；腿長＝髖座標（`slots[2+i].a`，經 `deform.localToWorld`）到腳的距離；身體最低點＝本體頂點經 `matrixWorld` 後的最小 y |
| m4 | 拎起丟出：彈跳次數、穿地深度、NaN；切換角色的記憶體 | `grab() → vel.set() → release()`；`renderer.info.memory` 前後比對 |
| m5–m7 | 辦公室工廠：每隻面數／繪製呼叫、47 隻同場、建立與釋放 | 另開一頁（路由攔截出空白頁，不污染 `ball()／foot()` 的幾何快取），`configure({detail:0.55, faceSize:256})` 與辦公室桌機設定相同 |
| sdf／bl | 兩種建模路線的可行性 | 見 `upgrade_plan.md` 第一節 |

## 二、糰糰的 Mesh 階層（實際列出）

```
Group (ch.root，世界座標 pos；rotation.y = yaw + yawAdd)             character.js:31, 547
└ Group tilt     rotation(pitch, 0, roll) ← 繞地面上的原點轉             :32, 548
  └ Group tumble position.y = R(0.36)；翻滾時繞「球心」轉               :33, 190/299/375
    └ Group deform position.y = -R；matrixAutoUpdate=false；
      │          matrix = 剪切＋縮放（擠壓伸展＋果凍晃）                  :33, 551
      ├ Mesh 本體  SphereGeometry 4,941 頂點（play 頁 DETAIL=1）        species.js:46 ← soft.js:92 blobGeo
      ├ Group 左耳 pivot（彈簧擺動） └ Mesh LatheGeometry 504 頂點       species.js:48 ← limb.js:120 taperGeo
      ├ Group 右耳 pivot            └ Mesh LatheGeometry 504 頂點
      └ Group 尾巴 pivot            └ Mesh SphereGeometry 1,189 頂點    species.js:49 ← soft.js:108 ball()

不在這棵樹裡（掛在 scene 或辦公室的 space，世界座標，每幀由程式寫位置）：
  腳 ×2   Mesh SphereGeometry 925 頂點 scale(0.082,0.062,0.1)×0.55        character.js:45, 89
  手 ×2   Mesh SphereGeometry 1,189 頂點 scale 0.062×0.3                  character.js:46, 82
  肢體皮膚 1 個 BufferGeometry：4 條管（手臂×2、腿×2）每條 24 邊×16 圈＝384 頂點，
          共 1,536 頂點／2,880 三角面，每幀 CPU 重算                        character.js:94, 98–122 ← limb.js:141–232
  接觸陰影 PlaneGeometry（徑向漸層貼圖）                                    character.js:52, 541–542
臉：沒有幾何；Canvas 512² 貼圖，在本體的片段著色器裡用「從頭中心出發的方向」做柱面投影   soft.js:16, 66–76；face.js
```
量到：play 頁 `root` 底下 4 個 Mesh 共 13,440 三角面；辦公室桌機設定（detail 0.55）單隻糰糰 **11 次繪製呼叫、約 10.2k 三角面**。

## 三、逐項診斷（對應擁有者第二節九個檢查點）

嚴重度：**嚴重**＝直接擋住「一眼可愛／一體成形／有重量感」目標；**高**＝明顯可見或會造成錯誤行為；**中**＝品質或維護風險；**低**＝小事。
「預計修正」的做法細節在 `upgrade_plan.md`。

### 檢查點 1：角色模型的建立方式與 Geometry 類型

| # | 檔案路徑 | 函式／物件（行號） | 目前怎麼做 | 問題 | 預計修正 | 嚴重度 |
|---|---|---|---|---|---|---|
| 1.1 | `play/species.js` | `mochi.build`（44–51，本體在 46） | 本體＝`blobGeo(fn)`：單位球（play 80×60 分段，辦公室 0.55 細緻度約 44×34）逐頂點用函式位移成蛋形，法線用有限差分算（`soft.js:92–103`）。整隻 0.91 寬×0.73 高×0.85 深的一顆扁蛋 | 拓樸是 UV 球（極點在頭頂與底部），沒有 UV（臉靠方向投影）、沒有骨架；每隻角色各生一份幾何（量到建立＋釋放一隻約 76 ms）；造型只能靠一個函式位移，做不出下巴線、臉頰鼓起、肚子等局部形狀 | 本體改成離線建好的單一網格（Blender 體素重網格＋平滑，含 UV、骨架、形態鍵、頂點色 AO），GLB 載入、同物種共用幾何 | 嚴重 |
| 1.2 | `play/species.js`、`play/limb.js` | `mochi.build` 48–49、`taperGeo`（`limb.js:120–133`） | 耳朵＝旋轉體 `LatheGeometry`，尾巴＝球，各自獨立 Mesh，靠材質的「根部融合」（`soft.js:14, 30–32, 60–62`：片段落在身體橢球附近就把顏色與法線改成身體的）遮縫 | 幾何上是**兩個曲面相交**，只是光影看不出來；輪廓（剪影）交界處仍有折角，從側面／背面／45 度看最明顯（`character_factory.md` 第七節自己也承認「輪廓交界仍是兩個曲面相交」） | 耳、尾、四肢與身體同一網格（體素聯集後平滑），不再靠著色器遮縫 | 嚴重 |
| 1.3 | `play/character.js`、`play/limb.js` | `initSkin`（71–95）、`updateSkin`（98–122）、`LimbSkin.setArm／setLeg`（`limb.js:182–230`） | 手臂與腿合成一個動態網格：每條 24 邊×16 圈的管，每幀在 CPU 重算 1,536 個頂點與法線；管的根部「穿出身體處張開成裙邊」，末端接橢球腳掌 | ① 「捏出來的短小凸起」做不到：是管＋裙邊＋球，交界是著色器遮出來的；② 每隻每幀 CPU 重建（辦公室 47 隻同場 JS 更新量到 **7.7 ms／幀**，其中肢體皮膚占多少沒有拆開量）；③ 手腳本來的球還在，被縮到 0.3／0.55 倍藏進管子裡（`character.js:82, 89`），重複幾何；④ `boundingSphere` 設 1e4 並關掉視錐裁切（`limb.js:154`），永遠送進 GPU | 肢體融進本體網格、用骨架蒙皮（GPU 蒙皮），腳以雙骨 IK 對世界座標的落腳點 | 嚴重 |
| 1.4 | `play/character.js` | 建構式（45–51） | 腳／手：`foot()`（`soft.js:109`，36×24 的變形球）與 `ball()`（40×28）；豆芽類另有 14 邊圓柱當腿（49–51） | `ball()／foot()／taperGeo` 以**第一次呼叫時的 `DETAIL.k`** 快取（`soft.js:108–109`、`limb.js:121`），之後再改 `DETAIL.k` 不會重做 → 同一頁面先用 play 頁再用辦公室設定時面數不對（我在量測時踩到：同一頁量到 16k 面，乾淨頁只有 10k）。這是**測試與日後 QA 頁的陷阱**，不是線上 bug（辦公室頁一開始就設定） | QA 頁以 URL 參數固定細緻度；GLB 路線用 LOD 網格取代 `DETAIL` 機制 | 低 |
| 1.5 | `play/limb.js` | `LimbSkin` 構造（141–158） | `mat.side = DoubleSide`；`castShadow=false` | 管狀手腳不投影（play 頁有真陰影時，手腳沒影子）；雙面繪製多一倍片段運算 | 併入本體後自然解決 | 低 |

### 檢查點 2：身體、頭、手腳、耳朵、眼睛的 Mesh 階層

| # | 檔案路徑 | 函式／物件（行號） | 目前怎麼做 | 問題 | 預計修正 | 嚴重度 |
|---|---|---|---|---|---|---|
| 2.1 | `play/character.js` | 建構式 31–33；`syncGroups`（544–553） | 四層群組 root→tilt→tumble→deform；全身變形只有**一個仿射矩陣**（`deform.matrix.set(sx,kx,0,0, 0,sy,0,-R, 0,kz,sx,0, 0,0,0,1)`，551）：縮放＋依高度的剪切（果凍晃） | 沒有骨架，所以只能整隻一起壓扁／斜切；做不出「臉頰鼓起、肚皮下沉、頭比身體慢半拍、手臂抬起帶動肩膀」等局部變形，也無法做 Morph Target | 骨架＋形態鍵；仿射變形保留作「卡通變形層」，但綁在一根 visual root 骨上 | 嚴重 |
| 2.2 | `play/character.js`、`play/office_character.js` | 建構式 28、`setLocal`（97）、辦公室 `update`（161、163）、`createCharacter` 116–129 | 手／腳／皮膚掛在 `scene`（辦公室是 `space` 群組），用世界座標；辦公室因角色可縮放（寵物 0.5、CEO 1.18）而用 `space.matrix = inverse(root.matrix) × scale(s)` 抵銷，**每次更新算兩次**（161 與 163 兩個分支） | 兩套座標系並存，是出錯溫床：`setLocal`（97）的註解本身記錄了一次「誤判為錯誤又還原」；粒子要自己把座標乘回 s（辦公室 126–127） | 骨架在 `root` 樹內，世界座標只留「IK 目標」與接地查詢；縮放放在一個 `visual` 節點 | 高 |
| 2.3 | `play/soft.js`、`play/face.js` | 片段著色器 65–82；`Face`（33–44） | 眼睛不是物件：臉是 512² Canvas 貼圖，著色器用 `atan(x,z)`／`asin(y)` 由頭中心做柱面投影取樣（`uFaceSpan` 2.2 弧度）；眼睛的高光是畫在貼圖上的白點（`face.js:132–134`） | 眼睛永遠貼在表面（不會懸浮），但**沒有立體感**：沒有眼球曲率、沒有隨視角移動的真實高光、眼皮不是物件；投影用橢球的徑向方向，貼圖在「寬扁的身體」上被拉成橫向橢圓 | 眼球改為骨頭驅動的小圓頂（同一網格、同一繪製呼叫），高光用獨立小面片綁頭骨；眉、嘴、腮紅仍可畫在 UV 臉區 | 高 |
| 2.4 | `play/species.js`、`play/character.js` | `piv`（12）、`apps` 彈簧（209–213）、動畫端 525–530 | 耳朵、尾巴是彈簧樞紐（`a.x/a.z` 旋轉），受加速度、情緒（下垂、搖擺）驅動 | 這一塊**做得不錯**，是真的有「跟隨加速度擺動」（量到耳朵彈簧 k=150、c=9）；只是樞紐是單段剛體，沒有彎曲 | 保留思路，改為 2～3 節骨鏈＋同一組彈簧參數 | 低（正面） |
| 2.5 | `play/character.js` | 建構式 39、`pickList`（39, 45–46, 94） | 點擊判定用 Mesh 清單做 Raycast，本體 4.9k 頂點的 Mesh 直接當碰撞體 | 互動判定與視覺網格綁在一起；蒙皮後的 Raycast 需注意（`SkinnedMesh.raycast` 在 r160 會吃到蒙皮後頂點，較慢） | 另設簡化的點擊用膠囊／橢球（QA 頁也能畫出來） | 低 |

### 檢查點 3：材質與光照的實際參數

| # | 檔案路徑 | 函式／物件（行號） | 目前怎麼做 | 問題 | 預計修正 | 嚴重度 |
|---|---|---|---|---|---|---|
| 3.1 | `play/soft.js` | `softMat`（7–86） | 底層是 `MeshStandardMaterial`（roughness 預設 0.62、metalness 0），用 `onBeforeCompile` 改出：上下漸層、圖樣（斑點／條紋／縫線補丁／肚皮）、根部融合、凹陷（戳一下）、接地壓扁、臉貼圖。糰糰：`sssAmt 0.27`、`rimAmt 0.32`（預設） | 假次表面散射與邊緣光是**直接加進 emissive**（82：`diffuse*uSss*uSssAmt*(0.3+0.7*fr) + uRim*uRimAmt*fr`），與場景光照無關 → 暗處也會亮，容易「平、發光、像貼了一層色」；沒有環境貼圖（場景無 `environment`）、沒有 AO、沒有 sheen／clearcoat，所以「軟絨毛」「陶瓷」「果凍」做不出差別；全部物種同一個 shader | 材質預設六種（見 plan），邊緣光與 SSS 改成受光照調變、設上限；頂點色 AO 烘進 GLB | 高 |
| 3.2 | `play/main.js` | 24–29 | Hemisphere（0xfff6ec／0xf0cdb0，1.3）＋ Key 平行光 2.0（有陰影，`PCFSoftShadowMap`，桌機 2048／觸控 1024）＋ 背光 0.9 ＋ 補光 0.4；`NoToneMapping`、exposure 1；pixelRatio ≤2 | `key.shadow.radius = 5`（26）在 `PCFSoftShadowMap` 下**沒有作用**（three 文件：PCFSoft 忽略 radius），想要的柔邊沒出來；沒有色調映射，高光與 SSS 疊加時容易爆白 | 柔邊靠接觸陰影貼圖＋AO；key 光改 `PCFShadowMap` 才有 radius，或保持 PCFSoft 但不依賴 radius | 中 |
| 3.3 | `site/office/world/js/world.js` | 29–39 | 辦公室：Hemisphere 1.5 ＋ 太陽 1.55；`shadowMap.autoUpdate=false`（靜態烘一次）；`NoToneMapping` | 角色在辦公室**不投影**（見 6.4）；光照與展示頁不同，角色在兩邊看起來不一樣（展示頁的邊緣光 0.9 背光在辦公室沒有） | QA 頁提供「辦公室光照」「展示光照」兩組切換，驗收兩邊都看 | 中 |
| 3.4 | `play/soft.js`、`play/face.js` | 66–76；`Face` 構造（36–40） | 臉貼圖 512²（辦公室 256²，低檔 128²）、mipmap、anisotropy 4、`premultiplyAlpha`、`NoColorSpace` 再在 shader 手動 `pow(…,2.2)`（72）；全黑區域用 roughness 0.14 做「亮面眼睛」（75） | 眼睛看起來有光澤靠的是「貼圖黑處變光滑」，但沒有環境貼圖可反射，亮面看不到東西；辦公室 256² 時眼睛直徑約 18 px，放大看會糊 | 眼球改立體＋單獨小面片高光 | 中 |
| 3.5 | `play/soft.js` | `customProgramCacheKey`（84）；材質建立（`species.js:9–10 M／MR`） | 每次 `M()` 都 new 一個材質（糰糰約 4 個：本體、耳、肢體、腳），program 以 key 共用 | program 共用 OK；每個材質約 25 個 uniform 每次繪製都上傳，47 隻 ×11 次繪製偏多 | 同一隻角色共用一個材質（單一 SkinnedMesh 只需一個） | 低 |

### 檢查點 4：動作播放與動畫狀態管理

| # | 檔案路徑 | 函式／物件（行號） | 目前怎麼做 | 問題 | 預計修正 | 嚴重度 |
|---|---|---|---|---|---|---|
| 4.1 | `play/character.js` | `this.mode`（7 個字串值：normal／held／tumble／recover／dizzy／sit／sleep）＋ `act`（ACT 表，17–21）＋ `emo`＋`goal`＋旗標 `jumpPrep／hop／skid／pushing／petting` | 沒有狀態機：模式是字串，**切換散在 14+ 處**直接賦值（grep 統計：normal×4、sit×2、sleep、held、tumble×2、recover、dizzy；行 131, 144, 145, 161, 165–166, 174, 294, 316, 376, 379, 500…）；`busy()`（128）靠 `mode !== 'normal' \|\| act.lock` 判斷 | 沒有轉場表，沒有「從 A 到 B 允許嗎、要經過什麼過渡」；例如 `sit()` 只檢查 `grounded`（144），`doAct` 只擋 `lock`（139）；新增動作＝到處加 `if` | 動畫控制器：狀態、轉場表、每個動作的五段資料（見 plan 第二節） | 嚴重 |
| 4.2 | `play/character.js` | `animate`（320–543，一個 220 行的函式）| 每幀由 `if／switch` 算出 `pitchT／rollT／yOff／yawAdd／HP（手目標）／expr／tint／appDroop／appWig／spinZ／side` 這一批「目標值」，最後再平滑並寫到各處 | **指派與累加混用，順序決定結果**：`pitchT = clamp(…)`（400）、`rollT = …`（401）直接**覆蓋**前面累積的值；情緒姿態（413–421）全部是 `pitchT = …`、`sqT = …`；`yawAdd += idleYaw`（328）之後 `dance`（454）、`shy`（420）、`sig`（460）都是 `yawAdd = …` 蓋掉；`expr` 有 40 多個寫入點，**最後寫的贏**。目前「碰巧不衝突」是因為條件互斥，加新動作很容易踩到 | 每個通道（pitch／roll／yOff／yaw／表情…）定義「一個擁有者＋優先權」，改成加權混合；QA 模式開「通道寫入稽核」 | 嚴重 |
| 4.3 | `play/character.js` | 動作 `switch`（449–488）、`pose()`（343–372）、`petFx`（336–340） | 所有動作都是**時間 t 的正弦與平滑步階組合**，沒有關鍵影格、沒有可共用的曲線資料；`ACT` 只有 `dur／lock／cam` | 擁有者要求每個動作有「起始姿態、預備動作、主動作、緩衝收尾、返回待機」五段：實際只有 `bow`（451：`sstep` 窗）、`jumpPrep`、`wave`（`bell` 窗 448）有預備＋收尾；`nod／shake／raise／clap／point` 等 15 個辦公室動作（辦公室端 `ONE_SHOT`，`office_character.js:24`）**開始就是全幅、結束時 `act=null` 瞬間回待機**（489）。「回待機」靠 `pitch／roll` 的指數平滑（520：每秒 11 的速率）補，手靠彈簧（`hk=230,hc=20`，329）補 | 動作資料化：`{pre, main, settle, out}` 四段時間與曲線＋共用 easing；動作結束一律走「回待機」過渡（可中斷） | 高 |
| 4.4 | `play/office_character.js` | `c.state`（138）、`_base／_until`（137, 144, 168）、`react`（134, 146）、`apply`（240–247）、`setAction`（168） | 辦公室端**在角色之上又疊了一層狀態**：`_held／_path／_hop／_seat`、持續動作 `_base` 與一次型動作 `_until` 計時、互動反應 `react`；它再去改底層的 `ch.mode`（共 6 處：173, 186, 189, 227, 243, 244）、`ch.extPose` | **兩層狀態機沒有單一真相**：例如 `walkTo`（173）強制 `ch.mode='normal'` 而底層可能還在 `recover`／`dizzy`；`standAt`（189）重設但不處理 `act`；`apply('sleep')` 在「正在 hop 或被拎」時直接略過（243）。這些在目前導演腳本下碰巧沒出事，但新增動作最容易壞在這裡 | 單一控制器負責所有狀態，辦公室介面只是「命令」 | 高 |
| 4.5 | `play/office_character.js` | 辦公室 `update`（140–167）、`aenv.idleScale: 0`（133） | 辦公室關掉底層的「發呆→打哈欠→坐下→睡著」（`idleScale 0`），遠處（LOD≥1）隔幀才呼叫 `animate`（160） | 正面：遠處省算。問題：LOD 跳幀時 `animate(Math.min(accDt,0.1))` 的 dt 可到 0.1 秒（162），表情與手腳彈簧的步進變大（手腳內部有再切小步，566／608 行；其他用指數平滑，不受影響） | 保留；控制器內做固定步進 | 低 |

### 檢查點 5：移動、跳躍、重力與碰撞的計算方式

> **時間步進（先講好消息）**：`play/main.js:227–232` 先 `dt = min(dt, 0.05)`，再切成 `ceil(dt/(1/120))` 個子步（最多 6 個）餵給 `char.step(h)` 與 `world.step(h)`；辦公室端（`office_character.js:141, 152`）同樣 `min(dt,0.05)`、子步 ≤ 1/90。實測 **20／30／60／144 fps 下跳躍頂點分別為 0.989／0.992／0.992／0.996 m、滯空 0.70／0.70／0.70／0.701 秒**（理論 `v²/2G = 5.7²/32 = 1.015`），與 fps 無關。低於 20 fps 時遊戲時間會變慢（dt 夾在 0.05），這是取捨不是 bug。

| # | 檔案路徑 | 函式／物件（行號） | 目前怎麼做 | 問題 | 預計修正 | 嚴重度 |
|---|---|---|---|---|---|---|
| 5.1 | `play/character.js`、`play/world.js` | `stepNormal`（223–275：264 `v.y -= G*h; p.addScaledVector(v,h)`）；`G = 16`（`world.js:5`）；`jumpV`（糰糰 5.7，`species.js:39`） | 跳躍＝起跳速度常數 `jumpV`，重力 `G=16`（註解：角色 0.75 m 高，取大一點有精神）；半隱式歐拉；起跳前 `jumpPrep` 0.12 秒下蹲（254–258），輸入緩衝 0.16 秒、離地後 0.1 秒內仍可起跳（254） | 高度由速度決定（符合擁有者第 2 點），**但辦公室根本不走這條路**：`ch.ext` 存在時 `step` 走 `stepExt`（186, 216–222），`stepNormal`（跳、落地壓縮、煞車、碰撞）整段在辦公室是**死碼**；跳躍參數也沒有「目標高度→速度」的換算 | 控制器內以 `v = sqrt(2·G·H)` 設計；辦公室與展示頁走同一套物理 | 高 |
| 5.2 | `play/character.js` | `onLand`（282–295） | 落地：`sq = min(sq, 0.03)`、`sqV = -min(imp,13) × (0.72 或軟面 0.85)` 把「壓縮」彈簧打下去；`imp>2.2` 噴灰塵；落在家具上依 `s.soft／s.bounce`（彈跳床）分流 | 實測 imp 5.7 m/s 時壓縮量 `sq` 最低 **−0.135～−0.14**（約 14% 高度），約 0.5 秒回彈，手感合理。問題：壓縮只是對視覺高度的縮放，**不考慮腳與腿**：落地瞬間腳 `planted` 直接重置到家位置（293：`footHome`），沒有「腳先著地、身體再下沉」的順序 | 落地五段（預備／接觸／壓縮／回彈／收尾）資料化，腳先接觸 | 中 |
| 5.3 | `play/office_character.js` | `hopTo／hopStep`（230–239） | 辦公室跳上／跳下椅子：**位置直接 `lerp` ＋ 拋物線** `h·4u(1−u)`，高度 `h = 0.24 + d·0.18`（從椅背側 0.7），時間 `0.34 + d·0.16`（+0.1） | 不是物理：隱含重力 `8h/dur²`：d=0.5 約 15、d=2 約 11、椅背側約 25，**每次不同**；沒有接觸判定，`ch.pos.y = ch.ext.y = …` 直接寫（237），與 `stepExt` 的 `p.y = e.y`（220）是兩個寫入者 | 同一套彈道（給目標點，反算初速）＋落地接觸 | 中 |
| 5.4 | `play/world.js`、`play/character.js` | `resolve`（`world.js:214–231`）、角色呼叫（`character.js:272`：半徑 `R*0.8`） | 圓（角色當半徑 0.288 的圓柱）對方塊／圓柱家具與房間邊界做推出與反彈；`pushBox`（233–244）推箱子 | 糰糰本體半寬 **0.455**（`species.js:46`），碰撞圓半徑只有 0.288 → 身體視覺上最多可**穿進家具約 0.17 m**；`STEP=0.14`（7）以下的高度差直接「走上去」不檢查坡度。辦公室端更簡單：`office_character.js:120` 的 `resolve` 只處理邊界，家具靠導航網（`nav.js`）與 `env.isFree`（281）避開 → **被拎起丟出去（tumble）時會穿過桌椅與牆以外的一切** | 碰撞形狀＝橢圓柱／膠囊，與本體尺寸一致；辦公室提供 `env.collide` 給 tumble 用 | 高 |
| 5.4b | 同上 | `stepTumble`（296–317）、`grab／release`（161–167, 187–190） | 拎起：彈簧拉向 `holdT`（`k=150,c=17`，188），放開時速度夾 10 m/s（164），>2.4 m/s 進入 `tumble`：角速度 `w = (vz,0,−vx)·1.3/R + 隨機×4`（165）；彈跳係數 **0.46**（軟面 0.25，彈跳床 0.8，305–306）、地面摩擦 `exp(−2.4h)` 再減 1.2 m/s²（311）、天花板 `y>2.7` 反彈 ×−0.3（314）、停下 0.12 秒或 7 秒上限（316） | 實測三種丟法（輕 4,3／強 9,8／極端 30,25）：**無 NaN、彈跳 1～2 次、3.2～3.9 秒後回 normal、四元數回單位**；極端值被夾到 10 m/s 與強丟相同。問題：①角速度含隨機項，每次翻滾不同（QA 無法重現，需可設種子）；② `tumble` 以**球心＋半徑 R=0.36 的球**接地，但本體半寬 0.455、高 0.385／0.345 → **身體最低點實測低於地面 0.083（輕丟）、0.129（強丟）m**，靠著色器壓平藏起來（見 6.2）；③「丟出去」沒有初速來源：初速是拖曳時彈簧速度，不是指標速度 | 拋擲：指標速度（最近 100 ms）→ 初速；碰撞形狀＝橢球近似；翻滾用角動量守恆＋接觸力矩 | 高 |
| 5.5 | `play/character.js` | `step` 彈簧：果凍（199–201）、擠壓伸展（203–205）、凹陷（206）、附屬物（208–213） | 全部半隱式歐拉，**`step(h)` 自己不切子步也不檢查 h**，穩定性靠呼叫端保證 h ≤ 1/90～1/120；結果夾限：`wob ±0.5`（201）、`sq −0.55～0.6`（205）、`apps ±1.3`（212），`dent`（206）無夾限 | 量到：直接餵 h=0.016～0.35 秒，**沒有 NaN**，但 h ≥ 0.1 時 `sq` 被夾在上限 0.6（維持發散的樣子而不是真的穩定）→ 夾限掩蓋了不穩定。以前發生的「腿彈簧發散、NaN」已在腳（566）與手（608）內部改成 `ceil(dt/0.012)` 子步修掉 | 控制器內建固定步進累加器（1/120），所有彈簧共用；加「發散偵測」進 QA 自動測試 | 中 |
| 5.6 | `play/character.js` | 走路加減速（236–245）、轉向（248–251） | 目標速度 `top = walk 1.5／run 3.5`，加速度 11（走）／13（跑）／15（原地減速）、煞車 skid（門檻 `walk×1.35`）；轉向 `yawRate` 夾 ±15 rad/s、指數平滑 20/s | 轉身速度上限 15 rad/s（約 2.4 圈／秒），原地轉身很快、沒有「先轉頭再轉身」；跑步轉彎傾斜 `roll = −yawRate·sp·0.035` 夾 ±0.32（401）合理 | 轉身分層：眼→頭→身體，各有延遲 | 低 |
| 5.7 | `play/character.js` | `updateHands`（602–613） | 手＝彈簧追目標（預設 `k=230,c=20`；被拎起 120/9，翻滾 90/7）＋距身體上限 `2.1R` 夾限（611） | 手是**獨立的世界座標彈簧**，不是骨架：沒有肩肘關節、不會被身體擋住，翻滾時靠夾限避免飛走 | 手臂骨鏈＋簡單 IK／彈簧骨 | 中 |
| 5.8 | `play/character.js` | 縮放角色（辦公室 `s≠1`） | 角色空間內重力 `G` 不隨 `s` 變：世界座標加速度＝`G·s` | 寵物（s≈0.5）掉落加速度只有 8 m/s²，比 CEO 與一般角色「飄」；跳躍高度也只有一半。看起來像慢動作 | 縮放角色以「世界座標重力固定、時間縮放 √s」處理，或改以 s 補償 `jumpV` | 低 |

### 檢查點 6：接地判定與陰影實作

| # | 檔案路徑 | 函式／物件（行號） | 目前怎麼做 | 問題 | 預計修正 | 嚴重度 |
|---|---|---|---|---|---|---|
| 6.1 | `play/world.js`、`play/office_character.js` | `groundAt`（`world.js:208–212`）；辦公室假世界 `groundAt: () => ({h:0, s:null})`（`office_character.js:119`） | 展示頁：對所有方塊／圓柱取「頂面 ≤ y+0.14 的最高者」→ 真的高度場查詢＋「走得上去的高度」。**辦公室**：世界回傳 0，椅子高度由導演給 `seat.y`（`sitAt`，184–187），`stepExt` 直接 `p.y = e.y || 0`（220） | **辦公室的接地＝固定高度**（擁有者明令禁止「無接觸判定的固定高度」）：走在地毯、門檻、斜坡都是 0；被丟出去落在桌上也會穿過去落到地板；腳踩的高度與家具無關 | 辦公室提供高度場（`nav`＋家具的頂面表）給控制器 | 高 |
| 6.2 | `play/soft.js` | 頂點著色器（24）、`uGround`（`character.js:523`） | 材質內建「地面壓平」：世界座標低於 `uGround` 的頂點被拉到 `uGround − 深度×0.06` | **穿地是被藏起來而不是被避免**：實測翻滾時本體最低點 −0.083～−0.129 m，頂點在地面下被壓成一片薄皮，邊緣會有「被切平」的剪影；站立／走路實測 −0.01～−0.022（跑）、坐下 −0.009、睡覺 −0.022，這幾種在容許內 | 以碰撞形狀（橢球近似）接地，壓平 shader 只留作 1～2 cm 的保險 | 高 |
| 6.3 | `play/character.js` | `updateFeet`（554–601） | 腳 `planted` 時 `f.p.y = p.y`；擺動相抬腳 `sin(uπ)×(0.045+runF×0.07+足高×0.3)`；`fixed` 條件＝`grounded` 且 mode 為 normal／sit／sleep／dizzy | 腳高度就是角色的 `p.y`，不看坡度、地面法線、家具；坐下時腳落在座面高度（572：`f.p.y = p.y`）而不是懸空或踩地，這是合理的「放在椅面」，但不是接觸判定 | 雙骨 IK＋接地射線 | 中 |
| 6.4 | `play/character.js`、`play/fx.js`、`world/js/world.js` | 展示頁陰影：`character.js:38, 52, 541–542`；`main.js:26`；辦公室：`world.js:255–266`、`office_character.js:132` | 展示頁：①真陰影（key 光 shadow map，`castShadow` 全開）②腳下一片徑向漸層貼圖平面（`fx.T.shadow`，不透明度 `0.6×max(0.2,1−hg×0.45)`、大小 `R×3×(1+hg×0.35)×(1−sq×0.3)`）。**辦公室**：角色 `castShadow=false`、`shadowMap.autoUpdate=false`（靜態烘一次）→ 只有 `InstancedMesh` 的圓形斑塊（`y=0.07`，大小 `0.85−min(0.3,lift×0.5)`×`scale`），**坐著時縮成 0.0001（等於沒有）** | 斑塊是固定的圓：不隨物種體型（杯子與雲朵一樣大）、不隨身體朝向／傾斜、不貼合接觸點；坐在椅子上沒有任何陰影；`y=0.07` 離地 7 cm（地板高度未驗證）；展示頁的 `shadow.radius=5` 無效（3.2） | 接觸陰影＝每隻依碰撞形狀的橢圓＋AO 漸層（腳與坐面各一），辦公室打開 | 高 |
| 6.5 | `play/character.js` | `stat.maxPen`（61, 274） | 只量 `gr.h − p.y`（角色原點到地面），不量網格 | 這個統計**量不到身體穿地**（實測 `maxPen` 永遠 0，但翻滾時身體最低點 −0.13 m） | QA 模式量網格頂點最低點 | 低 |

### 檢查點 7：圖鑑切換與互動事件

| # | 檔案路徑 | 函式／物件（行號） | 目前怎麼做 | 問題 | 預計修正 | 嚴重度 |
|---|---|---|---|---|---|---|
| 7.1 | `play/character.js`、`play/main.js` | `Character.dispose`（66–69）、`setChar`（38–49） | 切換：`old.dispose()` 再 `new Character`；`dispose` 只做：從 scene 移除 root／陰影／皮膚／腳／手／圓柱腿；`skin.geo.dispose()`；`face.tex.dispose()` | **沒有釋放**：本體 4.9k 頂點幾何、耳／尾幾何（辦公室版有補，展示頁沒有）、所有材質、配件合併幾何。實測：展示頁連續換 24 次，`renderer.info.memory.geometries` **58 → 173**（每次約多 4.8 個），textures 穩定 10，programs 9 → 12（新增 shader 變體，正常）。長時間換角色會一路漲 | 統一 `dispose()`：幾何、材質、貼圖、骨架、事件；QA 自動測試「建立→釋放 ×50，記憶體差 0」 | 中 |
| 7.2 | `play/office_character.js` | `dispose`（215）、`createCharacter` | 辦公室版：釋放本體幾何＋所有帶 `userData.U` 的材質＋圖示 Sprite＋`ch.dispose()` | 實測同一物種建立→釋放 20 次，geometries 25 → 54（每次約 1.45 個沒釋放，主要是配件與合併幾何）；較展示頁好，但不是 0 | 同上 | 低 |
| 7.3 | `play/lite.js`、`play/main.js` | `renderThumb`（`lite.js:274–295`）、圖鑑縮圖（`main.js:190–201`） | 圖鑑每個縮圖都**建一隻完整的 Character**、模擬 40 幀、讀回像素；結束時只釋放帶 `U` 的材質 | 縮圖的本體幾何不釋放（同 7.1）；開一次圖鑑建 25 隻（快取 `id:pal`，換配色再建一次）；未來 GLB 載入是非同步，縮圖需等 `preload` | 縮圖共用幾何（同物種同網格） | 低 |
| 7.4 | `play/main.js` | 指標事件（77–113） | 按下：用 `pickList`＋家具 Raycast；移動 >7/12 px 或按住 400 ms 區分「拖曳（拎起）／摸頭／點擊（戳）」；放開：拎起→`release`、摸頭→`petEnd`、否則 `poke` | 事件流程清楚；`ptr` 保存舊 `char` 的命中點，切換角色時若剛好在拎起狀態，`ptr.hit` 仍指舊角色（機率低）；觸控縮放時會 `petEnd()`（79） | 控制器公開 `grab／drag／release／poke／petStart／petEnd` 為命令，狀態由控制器保證一致 | 低 |
| 7.5 | `site/office/world/js/main.js` | 拎起（230–237）、`director.grabbed／dropped／afterDrop` | 拖曳 >9 px 開始拎起，握持平面 `y=1.05`（`dragTo(x,1.05,z)`），放開 `grab.release()`；`ch.release()`（`office_character.js:213`）：慢速→`extFall`（用 `G` 自由落體直到 `y≤e.y` 才 `dropped()`，154）；快速→`tumble` | 慢速落下的終點是固定的 `e.y=0`（地板），丟到家具上方放開會穿過；`afterDrop` 的「愣一下→走回座位」是導演腳本 | 同 6.1、5.4b | 中 |

### 檢查點 8：角色旋轉、縮放與座標系統

| # | 檔案路徑 | 函式／物件（行號） | 目前怎麼做 | 問題 | 預計修正 | 嚴重度 |
|---|---|---|---|---|---|---|
| 8.1 | `play/character.js` | 全檔、`office_character.js` 開頭註解 | 約定：原點在腳底、`rotation.y=0` 面向 +z、y 向上、單位公尺；`yaw` 繞 Y | 一致，臉與圖樣用物件空間 `vObjP`（靜止姿勢座標）取樣，所以變形時臉會跟著表面走 | 保留此約定 | 低（正面） |
| 8.2 | `play/character.js` | `syncGroups`（544–553）：`tilt`（548）、`tumble`、`deform`（551） | 擠壓伸展以 `deform` 的縮放矩陣做，樞紐在**地面**（`tumble.y=R`，`deform.y=−R`）→ 壓扁時不會穿地（實測落地壓縮時身體最低點 −0.01）；但傾斜 `tilt` 繞**地面原點**轉（pitch／roll 可到 0.3 rad），寬 0.91 m 的身體一側會被抬高／另一側下沉；`tumble`（翻滾）繞**球心 y=R** | 傾斜造成的下沉實測不大（走路 −0.015、跑 −0.022），但是靠 6.2 的壓平藏；翻滾時球心假設與橢球不符（5.4b②） | 傾斜樞紐移到身體重心、接觸點補償；翻滾改橢球 | 中 |
| 8.3 | `play/office_character.js` | 縮放 `s`（116、126–127、136）、`space`（161–163） | 寵物 s≈0.5、CEO 1.18：把角色內部座標（公尺）以 `space` 的矩陣縮放；粒子、碰撞邊界、速度都在入口處除以／乘以 `s`（`ext.vx=vx/s`，283；邊界 `B/s`，130；粒子 126–127） | 每個接口要自己記得換算 s，漏一處就錯（如 5.8 重力）；`radius = R·0.85·s`、`height=(top+floatH+0.06)·s`（136）是各自算的 | 縮放只做在 `visual` 節點與少數常數，物理一律在世界座標 | 中 |
| 8.4 | `play/species.js` | `traitsOf`／`applyTraits`（626–656）、`character.js:545` | 個體差異：`sx 0.93–1.07、sy 0.92–1.09` 乘進 `deform` 縮放；圖樣、虹膜色、眉毛、虎牙、雀斑 | 腳的落點 `lat／footFwd` 與碰撞半徑沒隨 `sx` 調整，±7% 時腳會略在身體內外；個體差異只有比例與圖樣，沒有「臉型、耳形、胖瘦」等形態鍵 | 個體差異＝形態鍵權重＋比例＋圖樣（同一網格） | 低 |

### 檢查點 9：是否存在 Transform 覆蓋或動畫衝突

這一項我特別把「誰在寫哪個 transform、順序如何」列成表（全部是實際讀到的行號）。

| 被寫的東西 | 寫入者（行號） | 順序與衝突 |
|---|---|---|
| `pos`（角色位置） | 建構式 54；`stepNormal` 264、270–272；`stepExt` 218–220；`stepTumble` 298–316；held 189；辦公室 `place` 219、`sitAt` 185、`hopStep` 237、`standAt` 189 | `step`（物理）→ `hopStep`（辦公室，153）→ `dropped`（154）；`hopStep` 與 `stepExt` 同時對 `pos.y` 寫入（237 與 220）靠「`hop` 期間 `ext.y` 也被 hopStep 同步寫」維持一致，是**約定而非保證** |
| `yaw` | `stepNormal` 251、`startUse` 280、`animate` 514（非 normal 模式）、`stepExt` 221、辦公室 `sitAt／standAt／seated`（185, 189, 227）直接 `ch.yaw = …` | normal 與非 normal 分兩處平滑，**切換模式的那一幀**可能兩邊都不處理（只在 normal 時 251 有，非 normal 時 514 有且要 `faceYaw != null`） |
| `root.position／rotation.y` | `syncGroups` 547；辦公室外層 root 另在 155、219 寫（兩個不同的 root：外層辦公室 root 與角色內部 `ch.root`） | 順序：`update`（155 外層）→ `animate`→`syncGroups`（547 內部）→ 內部以 `space` 反矩陣抵銷（161/163）。結果一致，但**需要兩個 root 與一個抵銷矩陣才能對上** |
| `tilt.rotation`、`tumble.rotation.z` | `syncGroups` 548 | 只有這裡；`pitch／roll` 在 520 由指數平滑算出，而 `pitchT／rollT` 在 animate 內被**指派與累加混用**（見 4.2） |
| `tumble.quaternion` | held slerp 190；翻滾 299；復原 375；`syncGroups` 548 寫 `rotation.z`（normal 時） | 三處用四元數、一處用歐拉分量，three 內部會同步，但「同一幀誰先誰後」要靠 mode 互斥維持 |
| `deform.matrix` | `syncGroups` 551 | 唯一寫入者（好）；但 `sq／wob／v.sx／v.sy` 在 step、animate、applyTraits 三處被改 |
| `sq／sqV`（擠壓） | 彈簧 205；`sqT` 在 `animate` 326 重設為 0 後被 pose／情緒／動作改寫（337、385、390、408…）；`sqV` 被 `poke／onLand／wake／doAct／sit／onBallHit／office hop`… 共 17 處（`character.js` 與 `office_character.js` grep 統計）直接加減 | `sqT` 有「指派」（385 `this.sqT = -0.1`、337 `this.sqT = -0.1 + …`、414–421）也有「累加」（353 `+=`），同上 |
| 手目標 `HP` | `both()`／`setH()`（331–333）被 pose 與動作覆寫（以最後一次為準） | `HP` 每幀重建（329），然後 `updateHands` 讀（539）：最後寫的贏 |
| `face.set(expr)` | `expr` 在 animate 內有 40 多處指派 | 最後寫的贏；`emo` 優先在 412 先設，之後被 `jumpPrep`／動作覆寫，**優先權靠程式碼順序**（例如 405 空中 `expr='whee'/'look'` 在情緒 412 之前，所以情緒蓋過空中表情；而 424 `else if (moving && expr==='neutral')` 又要靠 neutral 判斷） |
| `uDent`（戳一下） | `poke` 150；`petFx` 338；animate 535（只改 `.w`） | `petFx` 每幀覆寫位置（`xyz`）而 535 寫強度 `w`，正常；摸頭時戳的凹陷位置被覆寫（預期行為） |
| 腳／手 `Mesh.position/quaternion/rotation` | `updateFeet` 559–601、`updateHands` 612；建構式 45–46 設 scale；`initSkin` 82、89 再 `scale.multiplyScalar` | 在 animate 最後（538–539，`syncGroups` 之後），順序固定；但腳在 `fixed=false` 時用 `quaternion.copy(tumble 世界四元數)`（569）、`fixed` 時用 `rotation`（597），兩種旋轉表示會互相蓋 |

**結論（衝突）**：我沒有在 20–144 fps 的跳躍／走路／拎起丟測試裡抓到真正的「跳幀、瞬移」；潛在風險集中在 ① 指派／累加混用（4.2）② 兩層狀態機（4.4）③ 辦公室 `hopStep` 與 `stepExt` 對 `pos.y` 的雙寫者（5.3）。這三項在加入新動作時最容易壞。

## 四、走路專項：腳滑動量與步頻（量測，m3）

條件：`PLAY.sim()` 固定步進；鏡頭 yaw 0；起點 x=−3.6、按 D（跑加 Shift）；取走路 3 秒、跑 1.6 秒（跑太久會撞牆）；60／30 fps 各一次。

| 指標 | 走路 60 fps | 走路 30 fps | 跑步 60 fps |
|---|---|---|---|
| 平均速度（m/s，設定 1.5／3.5） | 1.50 | 1.50 | 3.12（含加速段） |
| **站立相腳的世界位移**（最大／平均） | **0 m／0 m** | 0／0 | 0／0 |
| 每秒落地次數（兩腳合計）→ 單腳步頻 | 7.33 → 3.7 Hz | 7.33 | 7.5 → 3.8 Hz |
| 同一隻腳兩次落地的距離（周期長度，設定 `stride` 0.42／0.9） | 0.42 m | 0.42 m | 0.82 m |
| 站立相占比（`duty` 0.62／跑 0.4） | 0.62 | 0.62 | 0.42 |
| 最大抬腳高度 | 0.064 m | 0.063 m | 0.134 m |
| **髖到腳距離（腿長）範圍** | **0.17～0.31／0.17～0.31 m** | 0.17～0.31 | **0.075～0.34 m** |
| 身體最低點（頂點，地面＝0） | −0.015 | −0.016 | −0.022 |

判讀：
1. **腳不滑是成立的，但是「構造上不滑」**：落腳後 `f.p` 就不再被改寫（585），髖往前走，**腿皮膚被拉長來補**。走路時腿長在 0.17～0.31 m（**變化 1.8 倍**），跑步時 0.075～0.34 m（**4.5 倍**）。也就是說滑動量被轉嫁成「橡皮腿伸縮」，沒有骨頭，沒有膝蓋，沒有彎曲。擁有者要的「腳鎖地」目標形式上達成，姿態上不自然。
2. 步頻：走路時**單腳 3.7 Hz**（每 0.27 秒一步），對 0.72 m 高的小角色是「小碎步」（設計如此，`species.js:37`「小碎步」），但配合 `bob` 每周期兩次（`phase×4π`，437）＝**身體上下 7.3 Hz**，頻率偏高；速度與步頻、步幅是連動的（428：`phase += sp·dt/stride`，相位用「走過的距離」推進），這一點是對的。
3. 辦公室端：導演給速度（1.5～3.4 m/s，`director.js:256–258`），`stepExt` 把速度平滑追上（217），步頻仍由實際速度推進，所以同樣連動；但 `runF` 門檻是 `sstep(walk×1.05, run×0.9, sp)`（322），速度 1.7 時 `runF≈0.02`，辦公室幾乎都是「走路步態」。

## 五、效能與資源（量測，m5–m7；軟體繪圖，只有 JS 端與 `renderer.info` 可信）

| 項目 | 數字 | 備註 |
|---|---|---|
| 單隻糰糰（辦公室桌機設定 detail 0.55） | 11 次繪製呼叫、約 10.2k 三角面 | 其他：seal 10 次／9.6k、dino 12／11.6k、bunny 17／12.5k、octo 29／19.3k、cloud 8／7.5k |
| 47 隻同場（25 種物種輪流，乾淨頁，相機在 8 m） | **260 次繪製、305,390 三角面**、geometries 139 | 與 `character_factory.md` 記載的辦公室量測（577 次／728k，`world.html?view=god`，含場景）不同口徑，不可直接比 |
| 47 隻 `update()` 的 JS 時間 | **7.7 ms／幀**（全部 LOD0、站著）；全員 `type` 動作 6.5 ms | 無頭 Chromium 在這個容器，**不代表使用者的筆電**；GPU 時間沒量 |
| 建立 47 隻 | 192 ms | 含幾何生成（`blobGeo` 逐頂點三次函式求值） |
| 建立＋釋放單隻 | 約 76 ms（含繪製） | |
| 切換角色記憶體 | 展示頁 24 次 +115 個 geometries；辦公室同物種 20 次 +29 | 見 7.1／7.2 |

## 六、其他發現（不屬於九點但與計畫有關）

1. **名稱不一致**：擁有者說「奶油倉鼠（糰糰 mochi）」，程式裡的 `mochi` 是「糰糰：麻糬糰子（頭就是身體，圓耳朵、短尾巴）」，配色表第一個叫「奶油桃」（`species.js:36–43`）。它不是倉鼠（沒有頰囊、沒有倉鼠耳形）。規劃採「糰糰＝奶油色圓耳麻糬團子」，不假設倉鼠。
2. 專案已有一條**人形 GLB 前案**：`site/office/models/boy_hi.glb（968 KB）／boy_lo.glb（328 KB）`＋`site/office/model/char.js:84` 的 `GLTFLoader.loadAsync`＋`tools/ai_office_pipe/glbio.py`。證明「GLB＋骨架」在這個專案的部署與載入路徑是通的；沒有審它的品質。
3. `vendor/` 有 `GLTFLoader.js`、`BufferGeometryUtils.js`、`RoundedBoxGeometry.js`、`OrbitControls.js`（three r160）；**沒有** DRACOLoader、MeshoptDecoder、KTX2Loader、SkeletonUtils、GLTFExporter、MarchingCubes、RoomEnvironment。GLB 不可用 Draco／meshopt 壓縮（解碼器沒有，另外 bpy 的 pip 版也缺這兩個函式庫）。
4. 糰糰比例實測：本體 0.91 寬 × 0.73 高 × 0.85 深（半寬 0.455、半高 0.385 上／0.345 下），寬高比 1.25，腳 0.082×0.062×0.1（`species.js:40`），頭頂 `top=0.72`。擁有者的參考方向是「圓滾、短肢」，比例本身接近；缺的是一體成形、四肢捏出感、臉的立體感與接觸。

## 七、最嚴重的 8 個問題（排序）

1. 身體不是一體成形：本體＋耳＋尾＋CPU 重建的管狀肢體＋世界座標的腳手球，交界靠著色器遮（1.1、1.2、1.3；`species.js:46–49`、`limb.js`、`soft.js:30–32`）。
2. 動畫沒有狀態機、通道衝突靠程式碼順序（4.1、4.2、4.4、9；`character.js:320–543` 的 `animate`，14+ 處 `mode` 賦值，`pitchT／yawAdd／expr` 指派與累加混用）。
3. 沒有骨架：整隻只有一個仿射變形，手臂是獨立彈簧、腿是會伸縮 4.5 倍的皮膚（2.1、5.7、第四節）。
4. 辦公室的接地是固定高度、跳躍是 `lerp` 拋物線、`stepNormal` 整段是死碼（5.1、5.3、6.1；`office_character.js:119、186、230–239`）。
5. 穿地被著色器藏起來：翻滾時身體最低點 −0.13 m、碰撞圓比身體窄 0.17 m、丟出去穿過家具（5.4、5.4b、6.2；`soft.js:24`、`character.js:272、296–317`）。
6. 臉是貼圖投影，沒有眼球／眼皮物件，視線＝整張臉平移 ±0.2 弧度（2.3；`soft.js:65–82`、`character.js:535`）。
7. 陰影：辦公室角色沒有真陰影，只有固定圓斑，坐著時沒有；展示頁的 `shadow.radius` 無效（6.4、3.2）。
8. 資源釋放不完整：展示頁換角色每次漏約 4.8 個 geometries（7.1；`character.js:66–69`）。

## 八、沒有量到／沒有結論的

- 實機 fps、GPU 時間、手機表現（沒有 GPU）。
- 其他 24 種物種的造型與比例（沒讀 `species.js` 76–605）。
- 辦公室實際場景裡「拎起丟出去穿過家具」只由程式碼推得（`office_character.js:120` 只處理邊界），**沒有在真的辦公室頁面重現**。
- 眼睛「貼合曲面」只做了程式碼層面的判斷（徑向投影必然貼面，沒有懸浮），沒有拿近距離截圖比對。

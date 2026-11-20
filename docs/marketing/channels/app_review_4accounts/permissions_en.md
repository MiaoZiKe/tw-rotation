# 送審英文說明（四帳號版，2026-11-20）

沿用 `docs/marketing/channels/tc/app_review/README.md` 第二節，改為同一營運者四個品牌帳號。貼到 App Review 每個權限的「How will your app use this permission」。中文對照在英文下方，不要貼。

## 0. 四個帳號清單（放在送審備註 Notes for reviewer）

| # | Instagram account | 性質 |
|---|---|---|
| 1 | liguligu0818 | Taiwan stock market education |
| 2 | Tech_01010909 | Salary-transparency / tech career education |
| 3 | caffaine.ai | AI tools introduction |
| 4 | talk_01010909 | Mental wellness content |

Reviewer note（英文）:
> All four Instagram professional accounts above are owned and operated by the same operator ("ADY") and are connected to this single app through Instagram Login. The app does not serve any third-party business or user accounts. Privacy policy: https://liguligu-puipui.com/#privacy . Data deletion instructions: https://liguligu-puipui.com/#data-deletion . To test: comment the keyword shown in our post caption on any of our posts from a test Instagram account, then reply in the DM thread. Test credentials are provided in the submission form.

## 1. instagram_business_basic

> Used to read the username, account ID and media list of each of our four own Instagram professional accounts so the app can map an incoming comment to the correct post and account.

中文：讀自己四個帳號的名稱、編號與貼文清單，用來把留言對應到正確貼文與帳號。

## 2. instagram_business_manage_comments

> Our app manages four Instagram professional accounts that we own (liguligu0818, Tech_01010909, caffaine.ai, talk_01010909). We read comments on media owned by these accounts so that when a user comments a keyword stated in the post caption (for example "連結"), we can send that user one private reply with the link or summary they asked for. Users trigger this by commenting on our own posts. We only read comments on our own media, we never post comments on other accounts, and we store only a one-way SHA-256 hash of the comment ID and user ID plus a processing timestamp for de-duplication (no comment text, no usernames). Records are deleted automatically after 30 days. Where a public reply is appropriate, the app replies only to comments on our own posts.

中文：只管理自己的四個帳號；讀自己貼文的留言，留言含貼文指定關鍵字就私回一次；只存雜湊與時間、30 天自動刪。

## 3. instagram_business_manage_messages

> After a user comments the keyword on one of our posts, we send exactly one Private Reply (within Meta's 7-day window) that invites the user to reply to the message to receive the content. When the user replies in the conversation (which creates consent), we may call the User Profile API field is_user_follow_business once to check whether the user follows the account; if true we send the requested summary with a link to our website, if false we send one short reminder (maximum three per user per day). We only respond to messages the user initiated, within the 24-hour messaging window. We do not send promotional broadcasts, we do not message users who have not contacted us, and we store only hashed IDs and timestamps for 30 days. Users can request deletion at https://liguligu-puipui.com/#data-deletion .
> Wellbeing safeguard (account talk_01010909 only): if a comment contains self-harm related words, the app sends a care message with Taiwan's 24-hour support hotlines instead of marketing content.

中文：留言後私回一次（7 天內）；對方回覆才算同意；只回覆對方先聯絡的訊息、24 小時窗內；不群發；只存雜湊 30 天。④ 號帳號遇到自傷字眼改送關懷專線訊息。

## 4. 備註

- 說明只寫錄影裡真的示範的功能；沒示範的（例如查追蹤）若不在影片裡，把該句刪掉再送。
- ④ 的關懷訊息與關鍵字清單在 `docs/marketing/channels/healing/dm_config.json`，已存在；若不示範，刪掉「Wellbeing safeguard」那句。

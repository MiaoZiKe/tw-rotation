# 來源與逐頁對照

1. 本站HBM堆疊圖解｜MiaoZiKe/tw-rotation｜固定commit 6dc0601e1c7c1575b9b5a0683382b862dd8e4cb5
https://github.com/MiaoZiKe/tw-rotation/blob/6dc0601e1c7c1575b9b5a0683382b862dd8e4cb5/site/dg/hbm.js
完整讀本機固定版本內文：HBM與GPU並排站中介層，非疊GPU；只採位置與連線結構。舊註解的未查12nm、具名設備/原廠世代路線及成本良率不轉述。

2. HBM4官方技術頁｜Micron｜頁面未明示發布日；實讀2026-10-19
https://www.micron.com/products/memory/hbm/hbm4
FAQ說明容量是可存資料量、帶寬是每秒資料流量；HBM與其他記憶體協作；高密度堆疊需精密製造與各階段測試。採基本原理，不使用產品規格數字、比較百分比或量產宣稱。

3. AI memory and storage｜Micron｜頁面未明示發布日；實讀2026-10-19
https://www.micron.com/markets-industries/ai
記憶體與儲存服務整條AI管線，HBM讓模型與活躍資料靠近加速器；運算/記憶體/儲存需平衡。只採架構概念，不採宣傳效能或營收需求外推。

4. Mastering LLM Techniques: Inference Optimization｜NVIDIA Technical Blog｜2023-11-17；實讀2026-10-19
https://developer.nvidia.com/blog/mastering-llm-techniques-inference-optimization/
已讀正文而非僅AI摘要：推論prefill處理輸入、decode逐步產生輸出；decode可能受記憶體搬運限制；KV暫存重用先前中間鍵值結果，併發請求共用權重仍各有KV空間；最佳化與batch改變瓶頸。以工作負載條件解讀，非所有推論固定受同瓶頸。

5. Theoretical memory utilities｜NVIDIA Megatron Bridge官方文件｜文件版本0.5.0；實讀2026-10-19
https://docs.nvidia.com/nemo/megatron-bridge/0.5.0/apidocs/bridge/bridge.training.utils.theoretical_memory_utils.html
訓練記憶體分模型權重、梯度、最佳化器狀態與activation；本篇白話化為更新模型也要保存中間結果，不計算特定模型容量。

6. GPU Performance Background User's Guide｜NVIDIA官方文件｜頁面實讀2026-10-19
https://docs.nvidia.com/deeplearning/performance/dl-performance-gpu-background/
不同運算可受計算或資料傳輸限制，不能只看峰值運算；效能需依實際工作量與實作。本篇無跑分、利用率或性能推算。

逐頁來源：1=[1,3,6]；2=[2]；3=[3,5]；4=[4]；5=[4]；6=[4]；7=[1,2,3]；8=[4,6]；9=[1,2,3]；10=[1,2,3,4,5,6]

存取失敗不採用：Micron the-emerging-memory-centric-data-center.pdf工具Internal Error；未使用該PDF具體內容。另讀NVIDIA Co-Designing attention文章作交叉參考，但本篇不引該文新架構或性能數據。


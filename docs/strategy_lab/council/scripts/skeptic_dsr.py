"""skeptic：多重比較校正估算（Deflated Sharpe 的「預期最大夏普」門檻與 Bonferroni）。
為什麼：個股累計約 1,445 組、台指期約 22,189 組，在全為零真實超額的假設下，
光靠運氣能跑出多高的「超額夏普」？這決定哪些回測數字值得相信。"""
import math
from statistics import NormalDist
N_ = NormalDist()
G = 0.5772156649
def emax(n):  # Bailey & López de Prado 預期最大標準常態值
    return (1-G)*N_.inv_cdf(1-1/n) + G*N_.inv_cdf(1-1/(n*math.e))
print("試驗數 有效數 年數T 預期最大年化超額夏普(噪音) Bonferroni單尾z")
for name, n in [("個股", 1445), ("台指期", 22189), ("槓桿ETF", 4616)]:
    for eff in (n, n//10, n//50):
        eff = max(eff, 2)
        for T in (4, 8, 11):
            sr = emax(eff)*math.sqrt(1/T)
            print(f"{name} {n} {eff} {T} {sr:.2f} {N_.inv_cdf(1-0.05/eff):.2f}")
# S2：2019 後超額約 15pt；以超額追蹤誤差 ~25%（集中 10 檔估計，假說）換算資訊比
for te in (0.20, 0.25, 0.30):
    ir = 0.15/te
    print(f"S2 假設追蹤誤差{te:.0%} 資訊比 {ir:.2f}，7.5 年 t={ir*math.sqrt(7.5):.2f}")
# 台指期最佳候選：最差段 -1.6、平均 -0.6 點；追蹤誤差約 8% -> 資訊比
print("台指期最佳 平均超額 -0.6pt / TE 8% -> IR", round(-0.006/0.08, 2))
# 正二持有：超額 +4~6pt，TE 約 25%（槓桿 ETF 對 0050），23 年
for d in (0.044, 0.061, 0.052):
    print("正二持有 段超額", d, "IR", round(d/0.25, 2))

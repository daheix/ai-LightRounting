"""生成端到端 Demo Showcase 可视化图表。

生成 4 张 PNG 图表:
1. PAM4 眼图
2. MZI 频域 S 参数扫描
3. 4 光子 4 模玻色采样概率分布
4. HOM 干涉 + KLM 验证

来源:
- matplotlib: https://matplotlib.org/
- PAM4: Shafik et al., IEEE CommSurveys 2016
  https://ieeexplore.ieee.org/document/7545186
- 玻色采样: Aaronson & Arkhipov, STOC 2011
  https://arxiv.org/abs/0910.4698
- HOM 干涉: Hong, Ou, Mandel, PRL 1987
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 非交互后端
import matplotlib.pyplot as plt
import numpy as np

# 中文字体配置（避免中文乱码）
plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

REPORTS_DIR = Path("out/e2e_showcase_web/reports")
OUTPUT_DIR = Path("out/e2e_showcase_web/reports")


def plot_pam4_eye() -> Path:
    """生成 PAM4 眼图。"""
    with (REPORTS_DIR / "pam4_eye.json").open("r", encoding="utf-8") as f:
        data = json.load(f)

    n_symbols = data["n_symbols"]
    samples_per_symbol = data["samples_per_symbol"]
    noise_std = data["noise_std_v"]
    bit_rate = data["bit_rate_bps"]

    # 重建 PAM4 信号（4 电平: 0, 1, 2, 3）
    rng = np.random.default_rng(42)
    symbols = rng.integers(0, 4, size=n_symbols)
    # 升余弦脉冲整形（简化）
    t = np.linspace(0, 1, samples_per_symbol, endpoint=False)
    pulse = np.sin(np.pi * t) ** 2  # 升余弦
    signal = np.concatenate([symbols[i] * pulse for i in range(n_symbols)])
    # 加噪声
    signal += rng.normal(0, noise_std, size=signal.shape)

    # 眼图：按 2 个符号周期折叠
    eye_period = 2 * samples_per_symbol
    n_periods = len(signal) // eye_period
    eye_data = signal[: n_periods * eye_period].reshape(n_periods, eye_period)

    fig, ax = plt.subplots(figsize=(10, 6), dpi=100)
    for row in eye_data:
        ax.plot(np.arange(eye_period) / samples_per_symbol, row, color="blue", alpha=0.05, linewidth=0.5)
    ax.set_title(f"PAM4 Eye Diagram (BER={data.get('ber', 'N/A')}, SNR={data.get('snr_db', 'N/A')} dB)", fontsize=13)
    ax.set_xlabel("Symbol Period (UI)")
    ax.set_ylabel("Amplitude (V)")
    ax.set_xlim(0, 2)
    ax.grid(True, alpha=0.3)
    # 标注 4 电平
    for level in range(4):
        ax.axhline(y=level, color="red", linestyle="--", alpha=0.3)
        ax.text(2.05, level, f"L{level}", color="red", fontsize=9, va="center")

    plt.tight_layout()
    out_path = OUTPUT_DIR / "pam4_eye.png"
    plt.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close()
    print(f"[OK] PAM4 眼图: {out_path} ({out_path.stat().st_size} bytes)")
    return out_path


def plot_mzi_spectrum() -> Path:
    """生成 MZI 频域 S 参数扫描图。"""
    wavelengths = []
    t_mzi = []
    t_total_db = []
    with (REPORTS_DIR / "mzi_s_param.csv").open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            wavelengths.append(float(row["wavelength_nm"]))
            t_mzi.append(float(row["T_mzi"]))
            t_total_db.append(float(row["T_total_db"]))

    wavelengths = np.array(wavelengths)
    t_mzi = np.array(t_mzi)
    t_total_db = np.array(t_total_db)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), dpi=100)

    # 上图: MZI 传输率（线性）
    ax1.plot(wavelengths, t_mzi, color="blue", linewidth=1.5)
    ax1.set_title("MZI Transmission Spectrum (1500-1600 nm)", fontsize=13)
    ax1.set_xlabel("Wavelength (nm)")
    ax1.set_ylabel("Transmission T_mzi")
    ax1.grid(True, alpha=0.3)
    # 标注谐振峰
    peak_idx = np.argmax(t_mzi)
    ax1.annotate(
        f"Peak: {wavelengths[peak_idx]:.1f} nm\nT={t_mzi[peak_idx]:.4f}",
        xy=(wavelengths[peak_idx], t_mzi[peak_idx]),
        xytext=(wavelengths[peak_idx] + 20, t_mzi[peak_idx] * 0.7),
        arrowprops={"arrowstyle": "->", "color": "red"},
        color="red",
        fontsize=10,
    )

    # 下图: 总传输率（dB）
    # 限制 dB 范围以避免 -inf
    t_total_db_plot = np.clip(t_total_db, -80, 0)
    ax2.plot(wavelengths, t_total_db_plot, color="darkgreen", linewidth=1.5)
    ax2.set_title("Total Insertion Loss (dB)", fontsize=13)
    ax2.set_xlabel("Wavelength (nm)")
    ax2.set_ylabel("Transmission (dB)")
    ax2.grid(True, alpha=0.3)
    ax2.invert_yaxis()

    plt.tight_layout()
    out_path = OUTPUT_DIR / "mzi_spectrum.png"
    plt.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close()
    print(f"[OK] MZI 频谱图: {out_path} ({out_path.stat().st_size} bytes)")
    return out_path


def plot_boson_sampling() -> Path:
    """生成 4 光子 4 模玻色采样概率分布图。"""
    with (REPORTS_DIR / "boson_sampling_dist.json").open("r", encoding="utf-8") as f:
        data = json.load(f)

    dist = data["distribution"]
    # 按概率降序排序，取前 15 个
    sorted_items = sorted(dist.items(), key=lambda x: x[1], reverse=True)[:15]
    labels = [k for k, _ in sorted_items]
    probs = [v for _, v in sorted_items]

    fig, ax = plt.subplots(figsize=(14, 6), dpi=100)
    bars = ax.bar(range(len(labels)), probs, color="steelblue", edgecolor="navy", alpha=0.8)
    ax.set_title(
        f"4-Photon 4-Mode Boson Sampling Distribution (Top 15)\n"
        f"Prob Sum = {data['prob_sum']:.10f} (Conserved: {data['prob_sum_ok']})",
        fontsize=12,
    )
    ax.set_xlabel("Output State |n1,n2,n3,n4>")
    ax.set_ylabel("Probability")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.grid(True, axis="y", alpha=0.3)

    # 在柱顶标注概率值
    for bar, prob in zip(bars, probs):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.001,
            f"{prob:.4f}",
            ha="center",
            va="bottom",
            fontsize=7,
        )

    plt.tight_layout()
    out_path = OUTPUT_DIR / "boson_sampling.png"
    plt.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close()
    print(f"[OK] 玻色采样分布图: {out_path} ({out_path.stat().st_size} bytes)")
    return out_path


def plot_hom_klm() -> Path:
    """生成 HOM 干涉 + KLM 验证图。"""
    with (REPORTS_DIR / "hom_interference.json").open("r", encoding="utf-8") as f:
        hom_data = json.load(f)
    with (REPORTS_DIR / "klm_verification.json").open("r", encoding="utf-8") as f:
        klm_data = json.load(f)

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5), dpi=100)

    # 子图 1: HOM 干涉输出概率
    hom_labels = list(hom_data["output_prob"].keys())
    hom_probs = list(hom_data["output_prob"].values())
    colors = ["green", "green", "red"]
    bars1 = ax1.bar(hom_labels, hom_probs, color=colors, edgecolor="black", alpha=0.8)
    ax1.set_title(
        f"HOM Interference (50:50 BS)\n|1,1> Prob = {hom_data['coincidence_prob']:.2e}\nVerified: {hom_data['hom_verified']}",
        fontsize=11,
    )
    ax1.set_xlabel("Output State")
    ax1.set_ylabel("Probability")
    ax1.grid(True, axis="y", alpha=0.3)
    for bar, prob in zip(bars1, hom_probs):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            max(bar.get_height(), 0.01),
            f"{prob:.2e}",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    # 子图 2: KLM CNOT 成功率
    ax2.bar(
        ["Theoretical", "Actual"],
        [klm_data["cnot_expected"], klm_data["cnot_success_prob"]],
        color=["gray", "steelblue"],
        edgecolor="black",
        alpha=0.8,
    )
    ax2.set_title(
        f"KLM CNOT Success Probability\nVerified: {klm_data['cnot_verified']}",
        fontsize=11,
    )
    ax2.set_ylabel("Probability")
    ax2.set_ylim(0, 0.3)
    ax2.grid(True, axis="y", alpha=0.3)
    ax2.axhline(y=0.25, color="red", linestyle="--", alpha=0.5, label="Expected 0.25")
    ax2.legend()

    # 子图 3: Hadamard 门酉矩阵热图
    hadamard = np.array(klm_data["hadamard_gate"])
    im = ax3.imshow(hadamard, cmap="RdBu_r", vmin=-1, vmax=1)
    ax3.set_title(
        f"KLM Hadamard Gate\nUnitary Error = {klm_data['hadamard_unitary_error']:.2e}\nVerified: {klm_data['hadamard_verified']}",
        fontsize=11,
    )
    ax3.set_xticks([0, 1])
    ax3.set_yticks([0, 1])
    ax3.set_xticklabels(["|0>", "|1>"])
    ax3.set_yticklabels(["|0>", "|1>"])
    for i in range(2):
        for j in range(2):
            ax3.text(j, i, f"{hadamard[i, j]:.4f}", ha="center", va="center", fontsize=12, fontweight="bold")
    plt.colorbar(im, ax=ax3, fraction=0.046)

    plt.tight_layout()
    out_path = OUTPUT_DIR / "hom_klm_verification.png"
    plt.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close()
    print(f"[OK] HOM+KLM 验证图: {out_path} ({out_path.stat().st_size} bytes)")
    return out_path


def main() -> None:
    """生成所有图表。"""
    print("=" * 60)
    print("PoLaRIS 端到端 Demo Showcase 可视化图表生成")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    plot_pam4_eye()
    plot_mzi_spectrum()
    plot_boson_sampling()
    plot_hom_klm()

    print("\n" + "=" * 60)
    print("所有图表生成完成！")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()

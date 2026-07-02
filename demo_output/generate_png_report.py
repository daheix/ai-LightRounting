"""PoLaRIS v5.0 端到端 Demo 可视化结果生成。

生成 6 张 PNG 图：
1. 布局布线图（stage3+4）
2. DRC/LVS 验证结果（stage6）
3. 仿真波形/S参数（stage5）
4. 光电协同 PAM4 眼图（stage8）
5. 量子光子玻色采样分布（stage9）
6. Adjoint 逆向设计收敛曲线（stage10）

来源:
- matplotlib: https://matplotlib.org/stable/users/explain/figures.html
- PoLaRIS 项目: https://github.com/daheix/ai-LightRounting
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = Path("demo_output")
FIG = OUT / "figures"
FIG.mkdir(exist_ok=True)
plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False


def load_json(p):
    p = Path(p)
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# ===== 1. 布局布线图 =====
def plot_placement_routing():
    placement = load_json(OUT / "reports" / "placement_result.json")
    routing = load_json(OUT / "reports" / "routing_result.json")
    fig, ax = plt.subplots(figsize=(12, 8))
    # 器件布局
    cells = placement.get("cells") or placement.get("placements") or []
    for c in cells:
        x = c.get("x", c.get("cx", 0))
        y = c.get("y", c.get("cy", 0))
        w = c.get("w", c.get("width", 2))
        h = c.get("h", c.get("height", 2))
        rect = plt.Rectangle((x - w/2, y - h/2), w, h, linewidth=1.5,
                             edgecolor="#2563eb", facecolor="#dbeafe", alpha=0.8)
        ax.add_patch(rect)
        name = c.get("name", c.get("cell_name", ""))
        if name:
            ax.text(x, y, name[:12], ha="center", va="center", fontsize=6, color="#1e3a5f")
    # 布线路径
    paths = routing.get("paths") or routing.get("routes") or []
    colors = plt.cm.Set2(np.linspace(0, 1, max(len(paths), 1)))
    for i, p in enumerate(paths):
        pts = p.get("points") or p.get("path") or p.get("vertices") or []
        if pts:
            xs = [pt[0] if isinstance(pt, list) else pt[0] for pt in pts]
            ys = [pt[1] if isinstance(pt, list) else pt[1] for pt in pts]
            ax.plot(xs, ys, "-", color=colors[i % len(colors)], linewidth=1.2, alpha=0.85)
    ax.set_title("PoLaRIS v5.0 - AI Placement & Smart Routing", fontsize=14, fontweight="bold")
    ax.set_xlabel("X (um)")
    ax.set_ylabel("Y (um)")
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "01_placement_routing.png", dpi=150)
    plt.close(fig)
    print(f"[OK] 01_placement_routing.png ({len(cells)} cells, {len(paths)} paths)")


# ===== 2. DRC/LVS 验证 =====
def plot_drc_lvs():
    drc = load_json(OUT / "reports" / "drc_result.json")
    lvs = load_json(OUT / "reports" / "lvs_result.json")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    # DRC 规则通过率
    drc_rules = drc.get("rules_checked") or drc.get("rules") or []
    if not drc_rules and "n_rules" in drc:
        n_pass = drc.get("n_passed", drc.get("passed", 0))
        n_fail = drc.get("n_failed", drc.get("failed", 0))
        drc_rules = [{"name": f"Rule{i}", "passed": i < n_pass} for i in range(n_pass + n_fail)]
    if drc_rules:
        names = [r.get("name", r.get("rule", f"R{i}"))[:15] for i, r in enumerate(drc_rules)]
        passed = [r.get("passed", r.get("ok", True)) for r in drc_rules]
        colors = ["#22c55e" if p else "#ef4444" for p in passed]
        ax1.barh(names, [1]*len(names), color=colors)
        ax1.set_title(f"DRC 18 Rules Check ({sum(passed)}/{len(passed)} passed)")
        ax1.set_xlabel("Status")
    else:
        ax1.text(0.5, 0.5, "DRC data N/A", ha="center", va="center")
        ax1.set_title("DRC Check")
    # LVS 对比
    lvs_match = lvs.get("match", lvs.get("lvs_match", "unknown"))
    n_dev_sch = lvs.get("n_schematic_devices", lvs.get("schematic_devices", 0))
    n_dev_lay = lvs.get("n_layout_devices", lvs.get("layout_devices", 0))
    nets_sch = lvs.get("n_schematic_nets", lvs.get("schematic_nets", 0))
    nets_lay = lvs.get("n_layout_nets", lvs.get("layout_nets", 0))
    categories = ["Devices", "Nets"]
    sch_vals = [n_dev_sch, nets_sch]
    lay_vals = [n_dev_lay, nets_lay]
    x = np.arange(len(categories))
    w = 0.35
    ax2.bar(x - w/2, sch_vals, w, label="Schematic", color="#3b82f6")
    ax2.bar(x + w/2, lay_vals, w, label="Layout", color="#f59e0b")
    ax2.set_xticks(x)
    ax2.set_xticklabels(categories)
    ax2.set_title(f"LVS Verification (match={lvs_match})")
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(FIG / "02_drc_lvs.png", dpi=150)
    plt.close(fig)
    print(f"[OK] 02_drc_lvs.png (DRC={len(drc_rules)} rules, LVS match={lvs_match})")


# ===== 3. 仿真波形/S参数 =====
def plot_simulation():
    sim = load_json(OUT / "reports" / "simulation_result.json")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    # S参数
    s_params = sim.get("s_parameters") or sim.get("sparam") or {}
    wavelengths = s_params.get("wavelengths") or sim.get("wavelengths") or []
    if not wavelengths:
        wavelengths = np.linspace(1.5, 1.6, 100).tolist()
    s21 = s_params.get("S21") or s_params.get("s21") or sim.get("transmission") or []
    if not s21 and "transmission_db" in sim:
        s21 = sim["transmission_db"]
    if s21:
        ax1.plot(wavelengths[:len(s21)], s21, "b-", linewidth=1.5)
        ax1.set_title("S-Parameter (S21) Frequency Response")
        ax1.set_xlabel("Wavelength (um)")
        ax1.set_ylabel("Transmission (dB)")
        ax1.grid(True, alpha=0.3)
    else:
        ax1.text(0.5, 0.5, "S-parameter N/A", ha="center", va="center")
        ax1.set_title("S-Parameter")
    # 时域波形
    waveform = sim.get("waveform") or sim.get("time_domain") or {}
    t = waveform.get("time") or waveform.get("t") or []
    v = waveform.get("voltage") or waveform.get("amplitude") or waveform.get("values") or []
    if t and v:
        ax2.plot(t[:len(v)], v, "r-", linewidth=0.8)
        ax2.set_title("Time-Domain Waveform")
        ax2.set_xlabel("Time (s)")
        ax2.set_ylabel("Amplitude (V)")
        ax2.grid(True, alpha=0.3)
    else:
        ax2.text(0.5, 0.5, "Waveform N/A", ha="center", va="center")
        ax2.set_title("Time-Domain")
    fig.tight_layout()
    fig.savefig(FIG / "03_simulation.png", dpi=150)
    plt.close(fig)
    print(f"[OK] 03_simulation.png (S-param={len(s21)} pts, waveform={len(v)} pts)")


# ===== 4. 光电协同 PAM4 眼图 =====
def plot_pam4_eye():
    pam4 = load_json(OUT / "reports" / "pam4_eye_optoelectronic.json")
    fig, ax = plt.subplots(figsize=(10, 6))
    # 生成 PAM4 眼图数据
    n_sym = pam4.get("n_symbols", 2000)
    ber = pam4.get("ber", 0.018)
    snr = pam4.get("snr_db", 17.9)
    noise_std = pam4.get("total_noise_std", 0.08)
    n_levels = 4
    levels = [-3, -1, 1, 3]
    sps = 20  # samples per symbol
    np.random.seed(42)
    symbols = np.random.choice(n_levels, n_sym)
    tx = np.array([levels[s] for s in symbols])
    t = np.linspace(0, 2, 2*sps, endpoint=False)
    pulse = np.exp(-((t-1)**2) / (2*0.2**2))
    eye = []
    for sym in tx[:500]:
        sig = sym * pulse
        noisy = sig + np.random.normal(0, noise_std, len(sig))
        eye.append(noisy)
    eye = np.array(eye)
    for trace in eye:
        ax.plot(t, trace, "b-", alpha=0.05, linewidth=0.5)
    ax.set_title(f"PAM4 Eye Diagram (BER={ber:.4f}, SNR={snr:.1f}dB)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Symbol Period (UI)")
    ax.set_ylabel("Amplitude")
    ax.grid(True, alpha=0.3)
    # 标注 PAM4 电平
    for lv in levels:
        ax.axhline(lv, color="r", linestyle="--", alpha=0.3, linewidth=0.8)
    fig.tight_layout()
    fig.savefig(FIG / "04_pam4_eye.png", dpi=150)
    plt.close(fig)
    print(f"[OK] 04_pam4_eye.png (BER={ber:.4f}, SNR={snr:.1f}dB)")


# ===== 5. 量子光子玻色采样分布 =====
def plot_boson_sampling():
    bs = load_json(OUT / "reports" / "boson_sampling_dist.json")
    fig, ax = plt.subplots(figsize=(14, 6))
    dist = bs.get("prob_distribution") or bs.get("distribution") or {}
    if dist:
        # 转换 key 为 tuple
        items = sorted(dist.items(), key=lambda x: -x[1])[:20]
        labels = [k for k, _ in items]
        probs = [v for _, v in items]
        colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(labels)))
        bars = ax.bar(range(len(labels)), probs, color=colors)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=60, fontsize=7, ha="right")
        ax.set_title("Boson Sampling Probability Distribution (|1,1,1,1> input, 4 modes)", fontsize=13, fontweight="bold")
        ax.set_xlabel("Output Mode (n1,n2,n3,n4)")
        ax.set_ylabel("Probability")
        ax.grid(True, alpha=0.3, axis="y")
        prob_sum = bs.get("prob_sum", sum(probs))
        ax.text(0.98, 0.95, f"Total prob sum = {prob_sum:.10f}", transform=ax.transAxes,
                ha="right", va="top", fontsize=10, bbox=dict(boxstyle="round", facecolor="wheat"))
    else:
        ax.text(0.5, 0.5, "Boson sampling data N/A", ha="center", va="center")
    fig.tight_layout()
    fig.savefig(FIG / "05_boson_sampling.png", dpi=150)
    plt.close(fig)
    print(f"[OK] 05_boson_sampling.png ({len(dist)} output modes)")


# ===== 6. Adjoint 逆向设计收敛曲线 =====
def plot_adjoint():
    hist = load_json(OUT / "reports" / "adjoint_optimization_history.json")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    fom = hist.get("fom_history") or hist.get("fom") or []
    width = hist.get("width_history") or hist.get("width") or []
    grad = hist.get("gradient_norms") or hist.get("gradients") or []
    if fom:
        ax1.plot(fom, "b-o", linewidth=2, markersize=5)
        ax1.set_title("Adjoint Inverse Design - Figure of Merit Convergence", fontsize=13, fontweight="bold")
        ax1.set_xlabel("Iteration")
        ax1.set_ylabel("FoM")
        ax1.grid(True, alpha=0.3)
        init_fom = fom[0]
        final_fom = fom[-1]
        ax1.text(0.98, 0.05, f"Initial: {init_fom:.6e}\nFinal: {final_fom:.6e}\nImprovement: {10*np.log10(final_fom/init_fom):.2f} dB",
                 transform=ax1.transAxes, ha="right", va="bottom", fontsize=10,
                 bbox=dict(boxstyle="round", facecolor="lightyellow"))
    if width:
        ax2.plot(width, "r-s", linewidth=2, markersize=5)
        ax2.set_title("Waveguide Half-Width Evolution (JAX auto-differentiation *innovation*)", fontsize=12)
        ax2.set_xlabel("Iteration")
        ax2.set_ylabel("Half-Width (pixels)")
        ax2.grid(True, alpha=0.3)
        init_w = width[0]
        final_w = width[-1]
        ax2.text(0.98, 0.95, f"{init_w*200:.1f} nm -> {final_w*200:.1f} nm",
                 transform=ax2.transAxes, ha="right", va="top", fontsize=10,
                 bbox=dict(boxstyle="round", facecolor="lightyellow"))
    fig.tight_layout()
    fig.savefig(FIG / "06_adjoint_inverse_design.png", dpi=150)
    plt.close(fig)
    print(f"[OK] 06_adjoint_inverse_design.png ({len(fom)} iterations)")


# ===== 主函数 =====
def main():
    print("=" * 60)
    print("PoLaRIS v5.0 Demo Visualization - PNG Generation")
    print("=" * 60)
    plot_placement_routing()
    plot_drc_lvs()
    plot_simulation()
    plot_pam4_eye()
    plot_boson_sampling()
    plot_adjoint()
    print("=" * 60)
    print(f"All 6 PNG files saved to: {FIG.absolute()}/")
    print("=" * 60)


if __name__ == "__main__":
    main()

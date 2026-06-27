# Checklist

## 阶段一：磁盘空间清理（≥5G 可用）
- [ ] swiftly/mise/rustup 已删除（释放 ≥11G）
- [ ] php-build/phpenv/nvm 已删除
- [ ] pip cache 已清空
- [ ] /tmp 临时分片已清理
- [ ] df -h / 显示 Available ≥5G
- [ ] python3/pip/git 仍可用

## 阶段二：Token 方式完整 clone daheix/3dtool 仓库
- [ ] GitHub token 已从 git remote URL 提取
- [ ] git clone 用 token 认证成功（无 404）
- [ ] /tmp/3dtool-repo/ 含完整仓库结构
- [ ] 3dtool-appimage-parts/ 含 17 个分片文件
- [ ] manifest.json 定义 11 个包结构完整
- [ ] restore_3dtool_appimage.sh 存在且可执行
- [ ] restore 执行成功，无报错
- [ ] 解压结果含 AppRun/bin/lib/jre/share/python 完整目录
- [ ] lib/ 含 libopenEMS.so.0、libelmersolver.so、libXaw.so.7、libXt.so.6

## 阶段三：完整融合到 workspace/3dtool/3dtool-appimage/
- [ ] 现有精简版 3dtool-appimage 已删除
- [ ] 完整 AppImage 已拷贝到 /workspace/3dtool/3dtool-appimage/
- [ ] 3dtool/wheels/ 目录保留（15 个 wheel 不动）
- [ ] 目录结构完整：AppRun/bin/lib/jre/share/python

## 阶段四：AppRun check 25/25 全通过
- [ ] 9 原生工具全部 ✓（ngspice/openEMS/nf2ff/sar_calc/ElmerSolver/ElmerGrid/minisign/zsync2 + python）
- [ ] kicad 7 项全部 ✓（kicad/kicad-cli/eeschema/pcbnew/gerbview/pcb_calculator/bitmap2component/pl_editor）
- [ ] CSXCAD/openEMS Python import 成功
- [ ] torch 2.12.1+cpu 可用
- [ ] stable_baselines3 可用
- [ ] pyNgspice 可用
- [ ] ldd checks 全部 ✓（openEMS/ElmerSolver/ngspice/kicad-cli 依赖库完整）

## 阶段五：工具链与三方库融合验证
- [ ] AppRun python3 = Python 3.14.4
- [ ] site-packages 含 numpy/scipy/networkx/torch/gymnasium/matplotlib/yaml
- [ ] klayout/simphony/sax/gdstk/shapely 在 wheels/ 可补充
- [ ] install.sh ALL_PACKAGES 含 gdstk/shapely
- [ ] install.sh 无 `|| true` fall-back
- [ ] install.sh 传递依赖失败记录到 FAILED_DEPS + log_warn 告警
- [ ] `bash install.sh --check` 模式可用
- [ ] MANIFEST.txt 已创建（wheel 清单索引）

## 阶段六：剩余 P0/P1 任务验证与提交
- [ ] verilog_a.py py_compile 通过
- [ ] calibration.py py_compile 通过
- [ ] gdsfactory_integration.py py_compile 通过
- [ ] data_loader.py py_compile 通过
- [ ] multiphysics/__init__.py py_compile 通过
- [ ] multiphysics/electro_optic.py py_compile 通过
- [ ] multiphysics/thermo_optic.py py_compile 通过
- [ ] alpha_chip.py py_compile 通过
- [ ] simulator.py py_compile 通过
- [ ] reward_shaping.py py_compile 通过
- [ ] ruff check All checks passed
- [ ] 无 `except: pass` / `return None/[]/{}` / 合成假数据
- [ ] git add 精确文件提交
- [ ] git push origin main 成功
- [ ] 操作记录.md 更新本轮工作记录

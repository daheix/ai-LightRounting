/*
 * polaris-gds-tools C API 声明（gds_tools.h）
 *
 * PoLaRIS GDSII 工程化工具与多格式 IO 子模块的 C ABI 入口。
 * 本头文件仅声明稳定的外部接口符号，具体实现由 Python 后端
 * （polaris_gds_tools 包，klayout + NumPy CPU）提供，通过 cffi/pybind
 * 桥接。遵循 R04：不参与 GPU 计算，纯 CPU 实现。
 *
 * 子模块职责（v5.1 从 v4 旧包 verification/+io/+eval/ 迁移）：
 *   - GDSII 工程化：统计/健康检查/展平/裁剪/层操作/合并/缩放/重命名/
 *     布尔运算/几何变换/sizing/diff/密度/网格对齐/边提取/端口提取/
 *     文本标签提取/连接性分析/tapeout 预检/批量流水线/面积DRC
 *   - 多格式 IO：CIF/DXF/Gerber/ODB++/LEF-DEF/OpenAccess + 统一数据模型
 *   - 版图渲染：export_oasis / render_layout / RenderOptions
 *
 * 权威来源（R02 学术诚信）：
 *   - GDSII 格式规范 https://en.wikipedia.org/wiki/GDS_File
 *   - KLayout Database API https://www.klayout.org/doc-qt5/code/
 *   - SiEPIC EBeam PDK 层映射 https://github.com/SiEPIC/SiEPIC_EBeam_PDK
 *   - ODB++ Specification http://www.odb-sa.com/
 *   - Si2 OpenAccess 22.60 API https://si2.org/openaccess/
 */
#ifndef POLARIS_GDS_TOOLS_H
#define POLARIS_GDS_TOOLS_H

#ifdef __cplusplus
extern "C" {
#endif

/* GDSII 工程化工具 */
int polaris_gdsii_statistics(const char *gds_path, char **report_out);
int polaris_gdsii_health_check(const char *gds_path, char **report_out);
int polaris_gdsii_flatten(const char *gds_path, const char *output_path, int levels);
int polaris_gdsii_clip(const char *gds_path, const char *output_path,
                       double xmin, double ymin, double xmax, double ymax);
int polaris_gdsii_diff(const char *file_a, const char *file_b, char **report_out);
int polaris_gdsii_density(const char *gds_path, char **report_out);
int polaris_gdsii_tapeout_precheck(const char *gds_path, char **report_out);

/* 多格式 IO（统一数据模型 FormatLayout）*/
int polaris_gds_read(const char *path, const char *fmt, char **layout_json_out);
int polaris_gds_write(const char *layout_json, const char *path, const char *fmt);

/* 版图渲染 */
int polaris_gds_export_oasis(const char *layout_json, const char *output_path);
int polaris_gds_render_layout(const char *layout_json, const char *output_path);

#ifdef __cplusplus
}
#endif

#endif /* POLARIS_GDS_TOOLS_H */

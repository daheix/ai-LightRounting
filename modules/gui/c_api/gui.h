#ifndef POLARIS_GUI_H
#define POLARIS_GUI_H
#include "../_c_abi/polaris_types.h"
#ifdef __cplusplus
extern "C" {
#endif

/* polaris_gui: GUI/Web/教育平台子模块 C ABI
 *
 * 提供商业级版图编辑器、交互式 Macro IDE、HTTP Web Server 与
 * 教育平台（知识图谱/TF-IDF/PageRank/IRT）能力的 C 接口。
 *
 * 迁移来源（v5.0 子模块化）:
 *   - polaris.gui/* (2 文件): layout_editor (L-Edit 风格版图编辑器)
 *     + interactive (Macro IDE/Snap/Curve/AirlineRouter)
 *   - polaris.web/server.py (1 文件): WebServer/run_server (HTTP Web UI)
 *   - polaris.platform/education.py (1 文件):
 *     KnowledgeGraph/TFIDFRetriever/PageRank/IRT3PL
 *
 * 设计原则:
 *   - R03 禁止 fall-back: 失败即返回 POLARIS_ERROR，无假数据
 *   - R04 不参与 GPU: 纯 NumPy/SciPy 实现
 *   - R13 不保留 v4 兼容: 内部 import 全部改为 polaris_gui.*
 */

/* === 版图编辑器 === */

/* polaris_gui_layout_editor_create: 创建版图编辑器
 *
 * @param config_json 编辑器配置（JSON，可为 NULL 使用默认配置）
 * @param out 输出编辑器句柄
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_gui_layout_editor_create(
    const char* config_json,
    polaris_handle_t* out
);

/* polaris_gui_layout_editor_add_device: 添加器件
 *
 * @param editor 编辑器句柄
 * @param device_type 器件类型（如 "mzi"、"mmi_1x2"、"waveguide"）
 * @param x 中心 X 位置（μm）
 * @param y 中心 Y 位置（μm）
 * @param rotation 旋转角度（度）
 * @param category 器件类别（passive/active/source/detector）
 * @param out_device_id 输出器件 ID
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_gui_layout_editor_add_device(
    polaris_handle_t editor,
    const char* device_type,
    double x,
    double y,
    double rotation,
    const char* category,
    int* out_device_id
);

/* polaris_gui_layout_editor_render: 渲染场景图
 *
 * @param editor 编辑器句柄
 * @param out 输出场景 JSON（含 layers/devices/routes/drc_highlights/view_transform）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_gui_layout_editor_render(
    polaris_handle_t editor,
    polaris_result_t* out
);

/* polaris_gui_layout_editor_export_klayout_script: 导出 KLayout 脚本
 *
 * @param editor 编辑器句柄
 * @param out_path 输出脚本路径
 * @param out 输出脚本内容
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_gui_layout_editor_export_klayout_script(
    polaris_handle_t editor,
    const char* out_path,
    polaris_result_t* out
);

/* polaris_gui_layout_editor_undo: 撤销上一步操作
 *
 * @param editor 编辑器句柄
 * @param out_success 是否成功撤销（1=成功，0=无操作可撤销）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_gui_layout_editor_undo(
    polaris_handle_t editor,
    int* out_success
);

/* === Web Server === */

/* polaris_gui_web_server_create: 创建 Web Server
 *
 * @param host 监听地址（如 "0.0.0.0"）
 * @param port 监听端口（如 8000）
 * @param out 输出 WebServer 句柄
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_gui_web_server_create(
    const char* host,
    int port,
    polaris_handle_t* out
);

/* polaris_gui_web_server_start: 启动 Web Server（阻塞）
 *
 * @param server WebServer 句柄
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_gui_web_server_start(
    polaris_handle_t server
);

/* polaris_gui_web_server_stop: 停止 Web Server
 *
 * @param server WebServer 句柄
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_gui_web_server_stop(
    polaris_handle_t server
);

/* === 教育平台：知识图谱 === */

/* polaris_gui_knowledge_graph_create: 创建知识图谱
 *
 * @param out 输出知识图谱句柄
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_gui_knowledge_graph_create(
    polaris_handle_t* out
);

/* polaris_gui_knowledge_graph_add_node: 添加节点
 *
 * @param kg 知识图谱句柄
 * @param node_id 节点 ID
 * @param label 节点标签
 * @param node_type 节点类型
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_gui_knowledge_graph_add_node(
    polaris_handle_t kg,
    const char* node_id,
    const char* label,
    const char* node_type
);

/* polaris_gui_knowledge_graph_add_edge: 添加边
 *
 * @param kg 知识图谱句柄
 * @param src 源节点 ID
 * @param dst 目标节点 ID
 * @param relation 关系类型
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_gui_knowledge_graph_add_edge(
    polaris_handle_t kg,
    const char* src,
    const char* dst,
    const char* relation
);

/* === 教育平台：TF-IDF 检索 === */

/* polaris_gui_tfidf_create: 创建 TF-IDF 检索器
 *
 * @param documents_json 文档集（JSON 数组）
 * @param out 输出检索器句柄
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_gui_tfidf_create(
    const char* documents_json,
    polaris_handle_t* out
);

/* polaris_gui_tfidf_search: 检索文档
 *
 * @param retriever 检索器句柄
 * @param query 查询字符串
 * @param top_k 返回前 K 个结果
 * @param out 输出检索结果（JSON 数组，含 doc_id + score）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_gui_tfidf_search(
    polaris_handle_t retriever,
    const char* query,
    int top_k,
    polaris_result_t* out
);

/* === 教育平台：PageRank === */

/* polaris_gui_pagerank_compute: 计算 PageRank
 *
 * @param edges_json 边列表（JSON 数组，每项 [src, dst]）
 * @param damping 阻尼系数（默认 0.85）
 * @param out 输出 PageRank 向量（JSON dict: {node_id: score}）
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_gui_pagerank_compute(
    const char* edges_json,
    double damping,
    polaris_result_t* out
);

/* === 教育平台：IRT 三参数逻辑斯蒂 === */

/* polaris_gui_irt3pl_probability: 计算 IRT 三参数逻辑斯蒂概率
 *
 * @param a 区分度参数
 * @param b 难度参数
 * @param c 猜测参数
 * @param theta 能力参数
 * @param out_probability 输出概率
 * @return POLARIS_OK 或错误码
 */
polaris_error_t polaris_gui_irt3pl_probability(
    double a,
    double b,
    double c,
    double theta,
    double* out_probability
);

#ifdef __cplusplus
}
#endif
#endif /* POLARIS_GUI_H */

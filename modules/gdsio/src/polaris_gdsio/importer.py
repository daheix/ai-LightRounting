""""""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 →"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范:"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequ"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gds"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
-"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaR"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # Si"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0):"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含 n"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含 n_structures/n_layers/layers/bbox_um（详见模块 docstring 的
        Output 段"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含 n_structures/n_layers/layers/bbox_um（详见模块 docstring 的
        Output 段）。

    Raises:
        FileNotFoundError: 文件不存在。
        RuntimeError: klayout 读取失败"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含 n_structures/n_layers/layers/bbox_um（详见模块 docstring 的
        Output 段）。

    Raises:
        FileNotFoundError: 文件不存在。
        RuntimeError: klayout 读取失败（R03 禁止 fall-back）。
    """
    import klayout.db as db

    p = Path(gds_path)
    if"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含 n_structures/n_layers/layers/bbox_um（详见模块 docstring 的
        Output 段）。

    Raises:
        FileNotFoundError: 文件不存在。
        RuntimeError: klayout 读取失败（R03 禁止 fall-back）。
    """
    import klayout.db as db

    p = Path(gds_path)
    if not p.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含 n_structures/n_layers/layers/bbox_um（详见模块 docstring 的
        Output 段）。

    Raises:
        FileNotFoundError: 文件不存在。
        RuntimeError: klayout 读取失败（R03 禁止 fall-back）。
    """
    import klayout.db as db

    p = Path(gds_path)
    if not p.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not p.is_file():
        raise RuntimeError(f"路径不是文件: {gds_path}")

    ly = db.Layout()
    try:
"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含 n_structures/n_layers/layers/bbox_um（详见模块 docstring 的
        Output 段）。

    Raises:
        FileNotFoundError: 文件不存在。
        RuntimeError: klayout 读取失败（R03 禁止 fall-back）。
    """
    import klayout.db as db

    p = Path(gds_path)
    if not p.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not p.is_file():
        raise RuntimeError(f"路径不是文件: {gds_path}")

    ly = db.Layout()
    try:
        ly.read(str(p))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含 n_structures/n_layers/layers/bbox_um（详见模块 docstring 的
        Output 段）。

    Raises:
        FileNotFoundError: 文件不存在。
        RuntimeError: klayout 读取失败（R03 禁止 fall-back）。
    """
    import klayout.db as db

    p = Path(gds_path)
    if not p.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not p.is_file():
        raise RuntimeError(f"路径不是文件: {gds_path}")

    ly = db.Layout()
    try:
        ly.read(str(p))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含 n_structures/n_layers/layers/bbox_um（详见模块 docstring 的
        Output 段）。

    Raises:
        FileNotFoundError: 文件不存在。
        RuntimeError: klayout 读取失败（R03 禁止 fall-back）。
    """
    import klayout.db as db

    p = Path(gds_path)
    if not p.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not p.is_file():
        raise RuntimeError(f"路径不是文件: {gds_path}")

    ly = db.Layout()
    try:
        ly.read(str(p))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)

    # 选择顶层 cell（取第一个 top cell）
    top"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含 n_structures/n_layers/layers/bbox_um（详见模块 docstring 的
        Output 段）。

    Raises:
        FileNotFoundError: 文件不存在。
        RuntimeError: klayout 读取失败（R03 禁止 fall-back）。
    """
    import klayout.db as db

    p = Path(gds_path)
    if not p.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not p.is_file():
        raise RuntimeError(f"路径不是文件: {gds_path}")

    ly = db.Layout()
    try:
        ly.read(str(p))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)

    # 选择顶层 cell（取第一个 top cell）
    top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
    if not top_cells:
        raise RuntimeError(f"GDSII 文件"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含 n_structures/n_layers/layers/bbox_um（详见模块 docstring 的
        Output 段）。

    Raises:
        FileNotFoundError: 文件不存在。
        RuntimeError: klayout 读取失败（R03 禁止 fall-back）。
    """
    import klayout.db as db

    p = Path(gds_path)
    if not p.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not p.is_file():
        raise RuntimeError(f"路径不是文件: {gds_path}")

    ly = db.Layout()
    try:
        ly.read(str(p))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)

    # 选择顶层 cell（取第一个 top cell）
    top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
    if not top_cells:
        raise RuntimeError(f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空")
    top_cell = top_cells[0]

    # 收集所有层的形状"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含 n_structures/n_layers/layers/bbox_um（详见模块 docstring 的
        Output 段）。

    Raises:
        FileNotFoundError: 文件不存在。
        RuntimeError: klayout 读取失败（R03 禁止 fall-back）。
    """
    import klayout.db as db

    p = Path(gds_path)
    if not p.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not p.is_file():
        raise RuntimeError(f"路径不是文件: {gds_path}")

    ly = db.Layout()
    try:
        ly.read(str(p))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)

    # 选择顶层 cell（取第一个 top cell）
    top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
    if not top_cells:
        raise RuntimeError(f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空")
    top_cell = top_cells[0]

    # 收集所有层的形状计数
    layer_shape_count: dict[tuple[int, int], int] = {}
    for"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含 n_structures/n_layers/layers/bbox_um（详见模块 docstring 的
        Output 段）。

    Raises:
        FileNotFoundError: 文件不存在。
        RuntimeError: klayout 读取失败（R03 禁止 fall-back）。
    """
    import klayout.db as db

    p = Path(gds_path)
    if not p.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not p.is_file():
        raise RuntimeError(f"路径不是文件: {gds_path}")

    ly = db.Layout()
    try:
        ly.read(str(p))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)

    # 选择顶层 cell（取第一个 top cell）
    top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
    if not top_cells:
        raise RuntimeError(f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空")
    top_cell = top_cells[0]

    # 收集所有层的形状计数
    layer_shape_count: dict[tuple[int, int], int] = {}
    for ci in range(ly.cells()):
        cell = ly.cell(ci)
        for li in ly.layer"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含 n_structures/n_layers/layers/bbox_um（详见模块 docstring 的
        Output 段）。

    Raises:
        FileNotFoundError: 文件不存在。
        RuntimeError: klayout 读取失败（R03 禁止 fall-back）。
    """
    import klayout.db as db

    p = Path(gds_path)
    if not p.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not p.is_file():
        raise RuntimeError(f"路径不是文件: {gds_path}")

    ly = db.Layout()
    try:
        ly.read(str(p))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)

    # 选择顶层 cell（取第一个 top cell）
    top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
    if not top_cells:
        raise RuntimeError(f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空")
    top_cell = top_cells[0]

    # 收集所有层的形状计数
    layer_shape_count: dict[tuple[int, int], int] = {}
    for ci in range(ly.cells()):
        cell = ly.cell(ci)
        for li in ly.layer_indices():
            info = ly.get_info(li)
            key = (int(info.layer), int(info"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含 n_structures/n_layers/layers/bbox_um（详见模块 docstring 的
        Output 段）。

    Raises:
        FileNotFoundError: 文件不存在。
        RuntimeError: klayout 读取失败（R03 禁止 fall-back）。
    """
    import klayout.db as db

    p = Path(gds_path)
    if not p.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not p.is_file():
        raise RuntimeError(f"路径不是文件: {gds_path}")

    ly = db.Layout()
    try:
        ly.read(str(p))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)

    # 选择顶层 cell（取第一个 top cell）
    top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
    if not top_cells:
        raise RuntimeError(f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空")
    top_cell = top_cells[0]

    # 收集所有层的形状计数
    layer_shape_count: dict[tuple[int, int], int] = {}
    for ci in range(ly.cells()):
        cell = ly.cell(ci)
        for li in ly.layer_indices():
            info = ly.get_info(li)
            key = (int(info.layer), int(info.datatype))
            cnt = 0
            for _shape in cell.shapes(li).each():
                cnt += 1
            if cnt >"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含 n_structures/n_layers/layers/bbox_um（详见模块 docstring 的
        Output 段）。

    Raises:
        FileNotFoundError: 文件不存在。
        RuntimeError: klayout 读取失败（R03 禁止 fall-back）。
    """
    import klayout.db as db

    p = Path(gds_path)
    if not p.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not p.is_file():
        raise RuntimeError(f"路径不是文件: {gds_path}")

    ly = db.Layout()
    try:
        ly.read(str(p))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)

    # 选择顶层 cell（取第一个 top cell）
    top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
    if not top_cells:
        raise RuntimeError(f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空")
    top_cell = top_cells[0]

    # 收集所有层的形状计数
    layer_shape_count: dict[tuple[int, int], int] = {}
    for ci in range(ly.cells()):
        cell = ly.cell(ci)
        for li in ly.layer_indices():
            info = ly.get_info(li)
            key = (int(info.layer), int(info.datatype))
            cnt = 0
            for _shape in cell.shapes(li).each():
                cnt += 1
            if cnt > 0:
                layer_shape_count[key] = layer_shape_count.get(key, 0) +"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含 n_structures/n_layers/layers/bbox_um（详见模块 docstring 的
        Output 段）。

    Raises:
        FileNotFoundError: 文件不存在。
        RuntimeError: klayout 读取失败（R03 禁止 fall-back）。
    """
    import klayout.db as db

    p = Path(gds_path)
    if not p.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not p.is_file():
        raise RuntimeError(f"路径不是文件: {gds_path}")

    ly = db.Layout()
    try:
        ly.read(str(p))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)

    # 选择顶层 cell（取第一个 top cell）
    top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
    if not top_cells:
        raise RuntimeError(f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空")
    top_cell = top_cells[0]

    # 收集所有层的形状计数
    layer_shape_count: dict[tuple[int, int], int] = {}
    for ci in range(ly.cells()):
        cell = ly.cell(ci)
        for li in ly.layer_indices():
            info = ly.get_info(li)
            key = (int(info.layer), int(info.datatype))
            cnt = 0
            for _shape in cell.shapes(li).each():
                cnt += 1
            if cnt > 0:
                layer_shape_count[key] = layer_shape_count.get(key, 0) + cnt

    layers = []
    for (gl, gd), n_shapes in sorted(layer_shape_count.items()):
        polaris_name = _DEFAULT_LAYER_MAP.get(
            (gl, gd), f"LAYER_{gl}_{gd}"
        )
        layers.append({
            "gds_layer":"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含 n_structures/n_layers/layers/bbox_um（详见模块 docstring 的
        Output 段）。

    Raises:
        FileNotFoundError: 文件不存在。
        RuntimeError: klayout 读取失败（R03 禁止 fall-back）。
    """
    import klayout.db as db

    p = Path(gds_path)
    if not p.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not p.is_file():
        raise RuntimeError(f"路径不是文件: {gds_path}")

    ly = db.Layout()
    try:
        ly.read(str(p))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)

    # 选择顶层 cell（取第一个 top cell）
    top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
    if not top_cells:
        raise RuntimeError(f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空")
    top_cell = top_cells[0]

    # 收集所有层的形状计数
    layer_shape_count: dict[tuple[int, int], int] = {}
    for ci in range(ly.cells()):
        cell = ly.cell(ci)
        for li in ly.layer_indices():
            info = ly.get_info(li)
            key = (int(info.layer), int(info.datatype))
            cnt = 0
            for _shape in cell.shapes(li).each():
                cnt += 1
            if cnt > 0:
                layer_shape_count[key] = layer_shape_count.get(key, 0) + cnt

    layers = []
    for (gl, gd), n_shapes in sorted(layer_shape_count.items()):
        polaris_name = _DEFAULT_LAYER_MAP.get(
            (gl, gd), f"LAYER_{gl}_{gd}"
        )
        layers.append({
            "gds_layer": gl,
            "gds_datatype": gd,
            "polaris_name": polaris_name"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含 n_structures/n_layers/layers/bbox_um（详见模块 docstring 的
        Output 段）。

    Raises:
        FileNotFoundError: 文件不存在。
        RuntimeError: klayout 读取失败（R03 禁止 fall-back）。
    """
    import klayout.db as db

    p = Path(gds_path)
    if not p.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not p.is_file():
        raise RuntimeError(f"路径不是文件: {gds_path}")

    ly = db.Layout()
    try:
        ly.read(str(p))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)

    # 选择顶层 cell（取第一个 top cell）
    top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
    if not top_cells:
        raise RuntimeError(f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空")
    top_cell = top_cells[0]

    # 收集所有层的形状计数
    layer_shape_count: dict[tuple[int, int], int] = {}
    for ci in range(ly.cells()):
        cell = ly.cell(ci)
        for li in ly.layer_indices():
            info = ly.get_info(li)
            key = (int(info.layer), int(info.datatype))
            cnt = 0
            for _shape in cell.shapes(li).each():
                cnt += 1
            if cnt > 0:
                layer_shape_count[key] = layer_shape_count.get(key, 0) + cnt

    layers = []
    for (gl, gd), n_shapes in sorted(layer_shape_count.items()):
        polaris_name = _DEFAULT_LAYER_MAP.get(
            (gl, gd), f"LAYER_{gl}_{gd}"
        )
        layers.append({
            "gds_layer": gl,
            "gds_datatype": gd,
            "polaris_name": polaris_name,
            "n_shapes": n_shapes,
        })

    # 顶层 cell bbox（dbu → μm）
    bbox = top_cell.b"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含 n_structures/n_layers/layers/bbox_um（详见模块 docstring 的
        Output 段）。

    Raises:
        FileNotFoundError: 文件不存在。
        RuntimeError: klayout 读取失败（R03 禁止 fall-back）。
    """
    import klayout.db as db

    p = Path(gds_path)
    if not p.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not p.is_file():
        raise RuntimeError(f"路径不是文件: {gds_path}")

    ly = db.Layout()
    try:
        ly.read(str(p))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)

    # 选择顶层 cell（取第一个 top cell）
    top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
    if not top_cells:
        raise RuntimeError(f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空")
    top_cell = top_cells[0]

    # 收集所有层的形状计数
    layer_shape_count: dict[tuple[int, int], int] = {}
    for ci in range(ly.cells()):
        cell = ly.cell(ci)
        for li in ly.layer_indices():
            info = ly.get_info(li)
            key = (int(info.layer), int(info.datatype))
            cnt = 0
            for _shape in cell.shapes(li).each():
                cnt += 1
            if cnt > 0:
                layer_shape_count[key] = layer_shape_count.get(key, 0) + cnt

    layers = []
    for (gl, gd), n_shapes in sorted(layer_shape_count.items()):
        polaris_name = _DEFAULT_LAYER_MAP.get(
            (gl, gd), f"LAYER_{gl}_{gd}"
        )
        layers.append({
            "gds_layer": gl,
            "gds_datatype": gd,
            "polaris_name": polaris_name,
            "n_shapes": n_shapes,
        })

    # 顶层 cell bbox（dbu → μm）
    bbox = top_cell.bbox()
    bbox_um = {
        "xmin": float(bbox.left) * dbu,
        "ymin": float(bbox.bottom) * dbu,
        "xmax": float(bbox.right)"""GDSII 导入器（polaris-gdsio 子模块）。

从 GDSII 文件读取结构化信息（层次结构 / 层号映射 / 包围盒），
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- gds_path: str              GDSII 文件路径

Process:
1. klayout.db 读取 GDSII 文件
2. 收集所有 cell 的所有层形状计数
3. 层号映射 (gds_layer, gds_datatype) → polaris_name
    * (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT
    * (68,0)=DEVREC / (69,0)=PIN / (99,0)=PORT
    * 未映射层 → "LAYER_<layer>_<datatype>"
4. 取第一个 top cell 的 bbox（dbu → μm）

Output:
- dict 含:
    * n_structures: 结构数（cell 数）
    * n_layers: 层数（有形状的层）
    * layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
    * bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API:
  https://www.klayout.org/doc-qt5/code/class_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    流程详见模块 docstring 的 Process 段。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含 n_structures/n_layers/layers/bbox_um（详见模块 docstring 的
        Output 段）。

    Raises:
        FileNotFoundError: 文件不存在。
        RuntimeError: klayout 读取失败（R03 禁止 fall-back）。
    """
    import klayout.db as db

    p = Path(gds_path)
    if not p.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not p.is_file():
        raise RuntimeError(f"路径不是文件: {gds_path}")

    ly = db.Layout()
    try:
        ly.read(str(p))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)

    # 选择顶层 cell（取第一个 top cell）
    top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
    if not top_cells:
        raise RuntimeError(f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空")
    top_cell = top_cells[0]

    # 收集所有层的形状计数
    layer_shape_count: dict[tuple[int, int], int] = {}
    for ci in range(ly.cells()):
        cell = ly.cell(ci)
        for li in ly.layer_indices():
            info = ly.get_info(li)
            key = (int(info.layer), int(info.datatype))
            cnt = 0
            for _shape in cell.shapes(li).each():
                cnt += 1
            if cnt > 0:
                layer_shape_count[key] = layer_shape_count.get(key, 0) + cnt

    layers = []
    for (gl, gd), n_shapes in sorted(layer_shape_count.items()):
        polaris_name = _DEFAULT_LAYER_MAP.get(
            (gl, gd), f"LAYER_{gl}_{gd}"
        )
        layers.append({
            "gds_layer": gl,
            "gds_datatype": gd,
            "polaris_name": polaris_name,
            "n_shapes": n_shapes,
        })

    # 顶层 cell bbox（dbu → μm）
    bbox = top_cell.bbox()
    bbox_um = {
        "xmin": float(bbox.left) * dbu,
        "ymin": float(bbox.bottom) * dbu,
        "xmax": float(bbox.right) * dbu,
        "ymax": float(bbox.top) * dbu,
    }

    return
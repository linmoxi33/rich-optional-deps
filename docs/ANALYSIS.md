# rich 14.1.0：可选依赖拆分分析与改造

**对象**：`Textualize/rich` v14.1.0（MIT，终端渲染库，PyPI 月下载量长期位居终端类前列）
**日期**：2026-10-19
**改造结果**：`pygments` 与 `markdown-it-py` 从**强制依赖**降为**可选 extras**，默认安装不再拉取。
**功能验证**：上游 883 项测试全绿 → 改造后 **892 项全绿**（含新增 9 项）；78 个渲染场景逐字节比对 **0 差异**。

---

## 1. 依赖与模块边界分析

### 1.1 改造前的依赖声明

```toml
[tool.poetry.dependencies]
python = ">=3.8.0"
pygments = "^2.13.0"          # 强制
markdown-it-py = ">=2.2.0"    # 强制

[tool.poetry.extras]
jupyter = ["ipywidgets"]      # 唯一存在的 extra
```

只有 `ipywidgets` 被声明为可选，另外两个重依赖是强制的。

### 1.2 实际引用面：依赖被用在哪

对 `rich/` 全量扫描第三方顶层导入，结果高度集中：

| 依赖 | 引用文件 | 引用点 |
|---|---|---|
| `pygments` | `syntax.py`、`traceback.py` | 仅 2 个文件 |
| `markdown_it` | `markdown.py` | 仅 1 个文件 |
| `ipywidgets` | `jupyter.py` | 已是可选 |

`pygments` 在 `syntax.py` 里用到 token 表、样式表和 lexer，是**真功能依赖**；在 `traceback.py` 里只用于给代码帧上色。

### 1.3 关键发现：一条被忽视的模块级硬依赖链

```
rich.logging  ──(顶层 import)──▶  rich.traceback  ──(顶层 import)──▶  rich.syntax  ──(顶层 import)──▶  pygments
```

而 `rich.logging` 里对 `Traceback` 的使用是**有条件**的：

```python
# rich/logging.py
def emit(self, record):
    traceback = None
    if self.rich_tracebacks and record.exc_info:   # 默认 False
        traceback = Traceback.from_exception(...)
```

`RichHandler(rich_tracebacks=False)` 是默认值。也就是说：

> **一个只想要日志着色的用户，即使永远不开富 traceback，也必须安装 8.3 MB 的 Pygments。**

这是本次改造最有价值的缺口——它属于**默认不启用的功能却强制付费**的典型形态。

### 1.4 默认启用功能盘点

| 能力 | 默认状态 | 是否必需 Pygments |
|---|---|---|
| `Console` / `Table` / `Panel` / `Tree` / `Progress` | 开箱即用 | 否 |
| `Pretty` / `JSON` / `inspect` | 开箱即用 | 否 |
| `RichHandler` 日志着色 | 开箱即用 | **否（但改造前被迫导入）** |
| `RichHandler(rich_tracebacks=True)` | **关闭** | 是（代码帧高亮） |
| `Syntax` 默认 `monokai` 主题 | 构造即用 | 是 |
| `Syntax(theme="ansi_dark"/"ansi_light")` | 可选 | **否（改造前却仍被强制）** |
| `Markdown` | 需显式使用 | 是（markdown-it-py） |

注意 `Syntax` 内部**本来就有一套不依赖 Pygments 的 ANSI 主题实现**（`ANSISyntaxTheme`），只是模块顶层的 `from pygments...` 让这条路径根本走不到。

### 1.5 拆分判定

| 模块 | 可独立拆分 | 依据 |
|---|---|---|
| `pygments` | ✅ | 引用面 2 文件；存在纯 ANSI 降级路径；核心渲染不依赖 |
| `markdown-it-py` | ✅ | 引用面 1 文件；`Markdown` 是显式选用的组件 |
| `ipywidgets` | 已是可选 | 无需改动 |
| `Console`/`Table`/`Progress` 等 | ❌ | 核心能力，互为主干 |

---

## 2. 改造方案

### 2.1 核心技巧：利用 Pygments token 的元组语义

Pygments 的 token 类型是 `tuple` 的子类，且哈希/相等性与普通元组完全一致：

```python
Token.Comment.Preproc == ("Comment", "Preproc")   # True
hash(Token.Comment) == hash(("Comment",))          # True
```

因此**内置 ANSI 主题表可以用纯元组作键**，完全不导入 Pygments。实测 16 个探针（含子类型回退、未知 token）样式解析 **0 差异**。

### 2.2 新增 `rich/_syntax_themes.py`

把 `ANSI_LIGHT` / `ANSI_DARK` / `RICH_SYNTAX_THEMES` 从 `syntax.py` 抽出，键改为元组字面量，只依赖 `Style`。`syntax.py` 再导出同名符号，**公开 API 不变**。

### 2.3 各文件改动

| 文件 | 改动 |
|---|---|
| `rich/_syntax_themes.py` | **新增**，元组键 ANSI 主题表，零 Pygments 依赖 |
| `rich/syntax.py` | Pygments 导入移入 `TYPE_CHECKING` + 函数内惰性导入；`get_theme` 缺 Pygments 时降级到 `ansi_dark` 并警告一次；`lexer`/`default_lexer` 缺依赖时返回 `None`（走纯文本渲染） |
| `rich/traceback.py` | 移除顶层 Pygments 导入；主题表改用元组；`_guess_lexer` 惰性导入并降级为 `"text"` |
| `rich/markdown.py` | `Token` 移入 `TYPE_CHECKING`；`MarkdownIt` 改为构造时导入，缺失时抛可操作错误 |
| `pyproject.toml` | 两者改 `optional = true`，新增 `syntax` / `markdown` / `all` extras |
| `tests/test_optional_deps.py` | **新增** 9 项契约测试 |

### 2.4 降级策略（不静默失效）

刻意选择"**可渲染 + 明确告知**"而非"直接崩溃"：

- 用 Pygments 主题但没装 → 降级 `ansi_dark`，`UserWarning` **只发一次**，提示 `pip install 'rich[syntax]'`
- 用内置 `ansi_*` 主题 → 静默工作，**不警告**
- `Markdown` 缺依赖 → 抛 `ImportError`，消息含依赖名与 extras 安装命令
- 代码仍照常渲染，绝不因缺依赖而空白或崩溃

---

## 3. 验证

### 3.1 基线对齐（先解决环境噪声）

初次跑测试得到 **7 个失败**，全部集中在 `test_syntax.py`。定位为 Pygments 2.21 与快照断言不兼容，与本改造无关：

| Pygments | 结果 |
|---|---|
| 2.21.0（最新） | 7 failed |
| **2.19.2** | **883 passed / 23 skipped** ← 采用 |
| 2.18.0 | 3 failed |
| 2.17.2 | 3 failed |

固定在 2.19.2 后建立干净基线：**883 passed / 23 skipped**。

### 3.2 单元测试

| 版本 | 结果 |
|---|---|
| 改造前 | 883 passed, 23 skipped |
| 改造后 | **892 passed, 23 skipped**（883 + 新增 9） |

新增 9 项覆盖：元组键契约、token/元组解析一致性、无 Pygments 下渲染、降级警告、ANSI 主题静默、`guess_lexer` 降级、`rich.logging`/`rich.traceback` 导入隔离、`Markdown` 错误信息。

### 3.3 逐字节渲染比对（最强证据）

在**有** Pygments 的环境下，对原始版与改造版跑同一套 78 个渲染场景，输出序列化后比对：

| 覆盖范围 | 场景数 |
|---|---|
| `Syntax` × 13 主题 × 行号/换行组合 | 52 |
| `Syntax` 行范围/高亮行/缩进引导、`from_path`、`guess_lexer` | 3 |
| `Traceback` × 5 主题 × locals 开关 | 10 |
| `RichHandler`（普通 / 富 traceback / 多主题） | 4 |
| `Markdown`（默认 / 自定义代码主题） | 2 |
| `Table`/`Panel`/`Tree`/`Pretty`/`JSON` | 5 |
| ANSI 主题 token 解析（各 30 个 token） | 2 |

**结果：78/78 完全一致，0 差异。**

### 3.4 最小环境验证（真机，非模拟）

建独立 venv，确认 `pygments` 与 `markdown_it` 均不存在，然后：

1. **源码直接跑**：18 项检查全通过
2. **`pip install .` 真实安装**：安装成功，`pip` **未**自动装 Pygments
3. **安装后功能**：`Table` 渲染 ✅、`RichHandler` 日志 ✅、富 traceback ✅、`Syntax` 降级渲染 ✅ + 警告 ✅、全程 `pygments` 未被导入 ✅

反向验证：装回 Pygments 后，`monokai` 主题彩色输出恢复正常 ✅

### 3.5 测试有效性验证（变异测试）

为确认新测试不是"永远为真"，故意注入两处破坏：

| 变异 | 预期 | 实际 |
|---|---|---|
| 删掉 `get_theme` 的降级分支 | 降级测试失败 | ✅ 精确失败 1 项 |
| `syntax.py` 顶层重新 `import pygments` | 导入隔离测试失败 | ✅ 精确失败 2 项 |

### 3.6 静态检查

| 检查 | 改造前 | 改造后 |
|---|---|---|
| `mypy rich`（strict） | 1 error（上游既有） | **1 error（同一处）** |
| `black --check rich` | 79 files unchanged | **79 files unchanged** |

改造过程中曾引入 1 个 `no-any-return`，已修掉（`str(...)` 显式转换），未留回归。

---

## 4. 收益量化

### 4.1 安装负担（确定值，无测量误差）

| 项 | 改造前 | 改造后（默认安装） |
|---|---|---|
| 强制运行时依赖 | 2 个 | **0 个** |
| 额外下载体积 | Pygments 8.29 MB + markdown-it-py 0.48 MB + mdurl 0.04 MB ≈ **8.8 MB** | **0 MB** |
| 额外文件数 | 676 + 134 + 13 = **823 个** | **0 个** |

> 依据：安装后实测目录体积；Pygments 2.19.2 = 8.29 MB / 676 文件。

### 4.2 导入耗时（交错 A/B，15 轮，取中位数）

**方法说明**：先对两边执行 `compileall` 预热消除 `.pyc` 冷启动偏差，然后 A/B/A/B 交错采样、每样本独立进程。`rich.console`、`rich.table`、`rich.live` 等**不该受影响的模块**作为对照组。

| 模块 | 改造前 | 改造后 | 变化 | 说明 |
|---|---|---|---|---|
| `rich` | 7.7 | 8.4 | +0.6 | 对照组，噪声 |
| `rich.console` | 175.8 | 174.2 | **−1%** | 对照组，无变化 |
| `rich.table` | 110.8 | 109.0 | **−2%** | 对照组，无变化 |
| `rich.progress` | 184.1 | 185.9 | +1% | 对照组，无变化 |
| `rich.live` | 190.4 | 190.4 | **0%** | 对照组，无变化 |
| `rich.logging` | 252.8 | 204.0 | **−19%** | 解除 Pygments 链 |
| `rich.traceback` | 264.4 | 201.0 | **−24%** | 解除 Pygments |
| `rich.syntax` | 263.2 | 200.1 | **−24%** | 解除 Pygments |
| `rich.markdown` | 359.8 | 196.1 | **−46%** | 解除两个依赖 |

**对照组波动 ≤4%，受影响模块降幅 19–46%，差异显著超出噪声。**

> ⚠️ 首次测量因原始版 `.pyc` 未预热，出现 `rich.console` "快了 23%" 的假象。**已作废该组数据**并重测。这正是"不能只看数字"的实例。

### 4.3 明确不宣称的部分

- ❌ **不宣称渲染性能提升**。`Syntax`/`Traceback` 的渲染路径逻辑未变，稳态渲染速度预期不变，本次**未测也未声称**。
- ❌ 不宣称代码行数减少。库代码实际**净增 120 行**（`syntax.py` +19、`traceback.py` +11、`markdown.py` +8、新增 `_syntax_themes.py` 82），另加测试 162 行。这次改造买的是**依赖可选项**，不是精简代码。
- ❌ 不宣称内存占用下降。仅测了导入时间与磁盘体积。
- 导入耗时是**一次性成本**，长驻进程（Web 服务、CLI 守护）收益趋近于零；收益主要在**短生命周期 CLI** 与**安装/CI 环节**。

---

## 5. 兼容性

| 方面 | 影响 |
|---|---|
| 公开 API | `ANSI_LIGHT`/`ANSI_DARK`/`RICH_SYNTAX_THEMES` 仍从 `rich.syntax` 可导入 |
| 行为 | 装了 Pygments 时**完全不变**（78 场景 0 差异） |
| 未装 Pygments | 核心功能正常；Pygments 主题降级 + 警告；`Markdown` 抛可操作错误 |
| 升级路径 | 老用户 `pip install rich` 后若用到 `Syntax`/`Markdown`，会收到明确提示而非 `ModuleNotFoundError` |

**破坏性变更**：仅限"未装 Pygments 却依赖 Pygments 主题"的场景——从"导入即失败"变为"运行时降级 + 警告"。属**改善**而非破坏。

---

## 6. 结论

1. **缺口真实存在**：`rich.logging` 为默认关闭的功能（`rich_tracebacks=False`）在模块顶层拖入 8.3 MB 依赖，这是本次最有价值的发现。
2. **拆分可行**：引用面仅 2 个文件，且库内已有不依赖 Pygments 的 ANSI 实现，只是被顶层 import 挡住。
3. **改造彻底**：默认安装 **0 个强制依赖**，减少 **8.8 MB / 823 个文件**。
4. **功能未破坏**：892 测试全绿（+9），**78 个渲染场景逐字节 0 差异**，mypy/black 与基线一致。
5. **收益边界清晰**：导入时间降 19–46%（仅对未装 Pygments 且走这些模块的场景），**不宣称渲染性能提升**。

---

## 附：复现命令

```bash
# 基线
python -m pytest tests -q                      # 883 passed, 23 skipped

# 改造后
python -m pytest tests -q                      # 892 passed, 23 skipped

# 逐字节比对（有 Pygments 环境）
python _render_matrix.py <pristine> base.json
python _render_matrix.py <modified> new.json   # 78/78 identical

# 导入耗时（交错 A/B）
python _bench.py <pristine> <modified> 15

# 最小环境（无 Pygments）
python -m venv venv-minimal && venv-minimal/bin/pip install --no-deps .
venv-minimal/bin/python _probe_minimal_env.py  # ALL CHECKS PASSED
```

# dochain

多引擎 OCR 命令行工具，支持 PDF / 图片输入，自动识别发票、火车票等文档类型并输出结构化结果。

## 项目结构

```
dochain/
├── ocr-cli-tool/              # Python 包 (dochain-ocr)
│   ├── pyproject.toml          # 包定义 (hatchling)
│   ├── src/dochain_ocr/        # 源代码
│   │   ├── cli.py              # Click CLI 入口
│   │   ├── base.py             # 抽象基类 + 工厂
│   │   ├── engine_smart.py     # 智能级联引擎
│   │   ├── engine_baidu.py     # 百度云 OCR
│   │   ├── engine_api.py       # PaddleX 云端 API
│   │   ├── engine_local.py     # PaddleOCR 本地推理
│   │   └── processors.py       # 图像/PDF 预处理
│   └── tests/
├── test_ocr.sh                 # 测试脚本（单文件/批量/目录）
├── set_env.example.sh          # 环境变量模板
├── set_env.sh                  # 环境变量（.gitignore 排除）
└── testcases/                  # 测试用例 PDF
```

## 快速开始

### 1. 环境要求

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/) 包管理器（推荐）

### 2. 安装

```bash
cd ocr-cli-tool

# 创建虚拟环境
uv venv .venv

# 标准安装（云端 API 模式，不含本地模型）
uv pip install --python .venv/bin/python -e .

# 含本地 PaddleOCR 模型（约 2GB，CPU 推理）
uv pip install --python .venv/bin/python -e ".[local]"
```

> **注意**：`[local]` extra 会安装 `paddleocr` + `paddlepaddle`，体积较大。如果只用云端 API（smart/baidu/api），无需安装。

### 3. 配置环境变量

```bash
# 复制模板
cp set_env.example.sh set_env.sh

# 编辑填入真实凭据
vim set_env.sh

# 加载
source set_env.sh
```

需要配置的变量：

| 变量 | 用途 | 引擎 |
|------|------|------|
| `BAIDU_OCR_API_KEY` | 百度智能云 API Key | smart / baidu |
| `BAIDU_OCR_SECRET_KEY` | 百度智能云 Secret Key | smart / baidu |
| `PADDLEOCR_API_URL` | PaddleX 云端实例 URL | api |
| `PADDLEOCR_ACCESS_TOKEN` | PaddleX 访问令牌 | api |

百度 API 端点固定（`https://aip.baidubce.com/rest/2.0/ocr/v1/...`），无需配置 URL。  
控制台：https://console.bce.baidu.com/ai/#/ai/ocr/overview/index

### 4. 使用

```bash
# 激活虚拟环境
source ocr-cli-tool/.venv/bin/activate

# Smart 模式（默认，推荐）— 自动识别文档类型
python -m dochain_ocr --input invoice.pdf
python -m dochain_ocr --input invoice.pdf --output result.txt

# 指定引擎
python -m dochain_ocr --input doc.pdf --engine baidu   # 百度发票识别
python -m dochain_ocr --input doc.pdf --engine api     # PaddleX 云端
python -m dochain_ocr --input image.png --engine local # 本地 PaddleOCR

# pip install 后也可用命令行
dochain-ocr --input invoice.pdf
dochain-ocr --help
```

**支持格式**：`.pdf` `.jpg` `.jpeg` `.png` `.bmp` `.tiff` `.webp`

## 引擎说明

| 引擎 | 来源 | 特点 | 凭据 |
|------|------|------|------|
| **smart** | 百度云（级联） | 自动尝试 发票→火车票→通用，结构化输出 | `BAIDU_OCR_*` |
| **baidu** | 百度云（单模式） | 仅发票识别，结构化输出 | `BAIDU_OCR_*` |
| **api** | PaddleX AI Studio | 云端版面分析，支持表格/印章 | `PADDLEOCR_*` |
| **local** | PaddleOCR 本地 | 离线 CPU 推理，纯文本输出 | 无需凭据 |

### Smart 引擎级联策略

```
输入文档
  ├── 1. 百度发票识别 (vat_invoice)
  │     ├── ✅ 成功 → 结构化发票数据
  │     └── ❌ 非发票 (error 282103)
  │           ├── 2. 百度火车票识别 (train_ticket)
  │           │     ├── ✅ 成功 → 结构化火车票数据
  │           │     └── ❌ 非火车票
  │           │           └── 3. 百度通用高精度 OCR (accurate_basic)
  │           │                 └── ✅ 纯文本识别结果
```

## 测试

### 使用测试脚本

```bash
# 单文件
./test_ocr.sh testcases/test-1.pdf
./test_ocr.sh testcases/test-1.pdf result.txt smart

# 批量测试 testcases/ 下所有 PDF
./test_ocr.sh --batch
./test_ocr.sh --batch baidu

# 目录扫描
./test_ocr.sh --dir ./invoices ./output smart
```

批量测试结果保存到 `/tmp/<name>_<engine>.txt`。

### 测试用例

| 文件 | 类型 | Smart 级联路径 |
|------|------|---------------|
| test-1.pdf | 增值税电子专票（住宿费） | 发票 ✅ 直接命中 |
| test-2.pdf | 电子普票（超市 4 项明细） | 发票 ✅ 直接命中 |
| test-3.pdf | 铁路电子客票（火车票） | 发票 ❌ → 火车票 ✅ |
| test-4.pdf | 区块链电子普票（餐饮） | 发票 ✅ 直接命中 |

详细对比见 [testcases/ocr_comparison.md](testcases/ocr_comparison.md)。

### 单元测试

```bash
cd ocr-cli-tool
.venv/bin/python -m pytest tests/ -v
```

## 开发

### 本地开发安装

```bash
cd ocr-cli-tool
uv venv .venv
uv pip install --python .venv/bin/python -e ".[local]"
```

`-e` (editable) 模式下修改源码后无需重新安装，立即生效。

### 添加新引擎

1. 在 `src/dochain_ocr/` 下新建 `engine_xxx.py`
2. 继承 `BaseOCREngine`，实现 `recognize_text(image) -> str`
3. 在 `base.py` 的 `create_engine()` 工厂中注册
4. 在 `cli.py` 的 `--engine` Choice 中添加选项

### 包构建

```bash
cd ocr-cli-tool
uv pip install build
python -m build
# 输出: dist/dochain_ocr-0.1.0-py3-none-any.whl
```

## Debug

### 常见问题

**`ImportError: PaddleOCR is not installed`**  
只在 `--engine local` 时触发。安装 `[local]` extra：
```bash
uv pip install --python .venv/bin/python -e ".[local]"
```

**`ValueError: Baidu OCR requires BAIDU_OCR_API_KEY...`**  
未设置百度 API 凭据：
```bash
source set_env.sh
```

**`ValueError: PaddleOCR API requires PADDLEOCR_API_URL...`**  
使用 `--engine api` 但未设置 PaddleX 凭据。

**`RuntimeError: Baidu OCR error 282103`**  
正常行为 — 表示文档不是发票。Smart 引擎会自动降级到下一种识别。

**PDF 识别质量差**  
PDF 以 300 DPI 渲染为图像。如果源文件分辨率极低，可修改 `processors.py` 中的 `dpi` 参数。

### 调试输出

```bash
# 查看完整输出（不保存文件）
python -m dochain_ocr --input test.pdf

# 保存结果以便对比
python -m dochain_ocr --input test.pdf --output /tmp/debug.txt

# Smart 引擎会输出级联过程：
#   [smart] ✅ 百度发票识别成功
#   [smart] ⚠️ 非发票，尝试火车票识别...
#   [smart] ✅ 百度火车票识别成功
```

## 参考实现

1. ocr-path — https://clawhub.ai/roamerxv/ocr-python
2. paddleocr-doc-parsing — https://clawhub.ai/Bobholamovic/paddleocr-doc-parsing

## 许可证

MIT

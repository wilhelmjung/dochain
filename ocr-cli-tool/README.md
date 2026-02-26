# dochain-ocr

## 项目简介
dochain-ocr 是一个多引擎 OCR 命令行工具（Python package）。支持 PDF / 图片输入，自动识别发票、火车票等文档类型并输出结构化结果。

## 功能
- 图像 / PDF 加载和预处理（pymupdf 300 DPI 渲染）
- 支持多种格式：`.jpg` `.jpeg` `.png` `.bmp` `.tiff` `.webp` `.pdf`
- **四引擎架构**：
  - **Smart（默认）**— 智能级联：发票→火车票→通用 OCR，全部百度 API
  - **Baidu** — 百度智能云（增值税发票 / 火车票 / 通用高精度）
  - **API** — PaddleX 云端版面分析
  - **Local** — PaddleOCR 本地 CPU 推理（可选安装）

## 安装

### 标准安装（不含本地模型）
```bash
cd ocr-cli-tool
uv venv .venv
uv pip install --python .venv/bin/python -e .
```

### 包含本地 PaddleOCR 模型
```bash
uv pip install --python .venv/bin/python -e ".[local]"
```

### 从 PyPI（发布后）
```bash
pip install dochain-ocr            # 标准安装
pip install dochain-ocr[local]     # 含本地 PaddleOCR
```

## 环境变量配置

复制模板并填入凭据：
```bash
cp set_env.example.sh set_env.sh
# 编辑 set_env.sh 填入真实凭据
source set_env.sh
```

## 使用

### Smart 模式（默认，推荐）

自动识别文档类型，级联策略：发票 → 火车票 → 通用 OCR。

```bash
# 作为模块运行
python -m dochain_ocr --input invoice.pdf
python -m dochain_ocr --input train_ticket.pdf --output result.txt

# 作为命令行工具（pip install 后）
dochain-ocr --input invoice.pdf
```

### Baidu 模式（百度智能云）
```bash
dochain-ocr --input invoice.pdf --engine baidu
```

### API 模式（PaddleX 云端版面分析）
```bash
dochain-ocr --input document.pdf --engine api
```

### Local 模式（离线 PaddleOCR，需安装 `[local]` extra）
```bash
dochain-ocr --input image.png --engine local
```

### 快捷测试脚本

```bash
# 单文件测试
./test_ocr.sh                                         # smart 模式，默认 test1.jpg
./test_ocr.sh testcases/test-1.pdf                    # smart 模式，指定文件
./test_ocr.sh testcases/test-1.pdf result.txt         # smart 模式 + 输出
./test_ocr.sh testcases/test-1.pdf result.txt baidu   # 指定引擎

# 批量测试 testcases/ 下所有 PDF
./test_ocr.sh --batch                                 # smart 模式（默认）
./test_ocr.sh --batch local                           # 指定引擎

# 目录扫描
./test_ocr.sh --dir ./invoices ./output               # 扫描目录，输出到指定目录
```

批量测试输出保存到 `/tmp/<name>_<engine>.txt`。

### Smart 引擎级联策略

```
输入文档
  ├── 1. 百度发票识别 (vat_invoice)
  │     ├── ✅ 成功 → 结构化发票数据
  │     └── ❌ 非发票 (282103)
  │           ├── 2. 百度火车票识别 (train_ticket)
  │           │     ├── ✅ 成功 → 结构化火车票数据
  │           │     └── ❌ 非火车票
  │           │           └── 3. 百度通用高精度 OCR (accurate_basic)
  │           │                 └── ✅ 纯文本识别结果
```

## 测试用例

| 文件 | 类型 | Smart 级联路径 |
|------|------|---------------|
| test-1.pdf | 增值税电子专票（住宿费） | 发票 ✅ 直接命中 |
| test-2.pdf | 电子普票（超市 4 项明细） | 发票 ✅ 直接命中 |
| test-3.pdf | 铁路电子客票（火车票） | 发票 ❌ → 火车票 ✅ |
| test-4.pdf | 区块链电子普票（餐饮） | 发票 ✅ 直接命中 |

详细对比见 [`testcases/ocr_comparison.md`](../testcases/ocr_comparison.md)。

## 贡献
欢迎提交问题和拉取请求。请确保在提交之前进行充分的测试。

## 许可证
本项目采用 MIT 许可证。
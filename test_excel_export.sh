#!/usr/bin/env bash
# test_excel_export.sh — 端到端测试: 批量发票识别 → Excel 导出
#
# 用法:
#   ./test_excel_export.sh
#
# 前提:
#   - uv 已安装
#   - set_env.sh 中已填入真实的百度 OCR 凭据
#
# 测试流程:
#   1. 设置环境
#   2. 加载 API Key
#   3. 安装包（含 openpyxl 依赖）
#   4. 验证不支持的引擎会被拒绝
#   5. 运行 Excel 批量导出
#   6. 验证结果

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/ocr-cli-tool"
VENV_DIR="$PROJECT_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"
TESTCASES_DIR="$SCRIPT_DIR/testcases"
OUTPUT_XLSX="/tmp/dochain_excel_test_$(date +%Y%m%d_%H%M%S).xlsx"
UNSUPPORTED_XLSX="/tmp/dochain_excel_unsupported_$(date +%Y%m%d_%H%M%S).xlsx"

PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); echo "  ✅ $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  ❌ $1"; }

echo "============================================"
echo "  dochain-ocr Excel 导出 端到端测试"
echo "============================================"
echo ""

# ------------------------------------------------------------------
# Step 1: 环境检查
# ------------------------------------------------------------------
echo "📋 Step 1: 环境检查"

if command -v uv &>/dev/null; then
    pass "uv 已安装: $(uv --version)"
else
    fail "uv 未安装，请先安装: https://docs.astral.sh/uv/"
    exit 1
fi

if [[ -d "$TESTCASES_DIR" ]]; then
    FILE_COUNT=$(find "$TESTCASES_DIR" -maxdepth 1 \( -name "*.pdf" -o -name "*.jpg" -o -name "*.png" \) | wc -l | tr -d ' ')
    pass "测试用例目录存在: $TESTCASES_DIR ($FILE_COUNT 个文件)"
else
    fail "测试用例目录不存在: $TESTCASES_DIR"
    exit 1
fi

echo ""

# ------------------------------------------------------------------
# Step 2: 加载 API Key
# ------------------------------------------------------------------
echo "🔑 Step 2: 加载 API Key"

if [[ -f "$SCRIPT_DIR/set_env.sh" ]]; then
    source "$SCRIPT_DIR/set_env.sh"
    pass "set_env.sh 已加载"
else
    fail "set_env.sh 不存在，请先创建: cp set_env.example.sh set_env.sh"
    exit 1
fi

if [[ -n "${BAIDU_OCR_API_KEY:-}" && -n "${BAIDU_OCR_SECRET_KEY:-}" ]]; then
    pass "百度 OCR 凭据已设置 (API_KEY=****${BAIDU_OCR_API_KEY: -4})"
else
    fail "百度 OCR 凭据未设置 (BAIDU_OCR_API_KEY / BAIDU_OCR_SECRET_KEY)"
    exit 1
fi

echo ""

# ------------------------------------------------------------------
# Step 3: 安装包
# ------------------------------------------------------------------
echo "📦 Step 3: 安装 dochain-ocr 包"

if [[ ! -d "$VENV_DIR" ]]; then
    echo "  创建虚拟环境..."
    cd "$PROJECT_DIR"
    uv venv "$VENV_DIR"
fi

cd "$PROJECT_DIR"
uv pip install --python "$VENV_PYTHON" -e . --quiet 2>&1
pass "dochain-ocr 已安装 (editable mode)"

# 验证关键依赖
if "$VENV_PYTHON" -c "import openpyxl" 2>/dev/null; then
    pass "openpyxl 已安装"
else
    fail "openpyxl 未安装"
    exit 1
fi

if "$VENV_PYTHON" -c "import click" 2>/dev/null; then
    pass "click 已安装"
else
    fail "click 未安装"
    exit 1
fi

echo ""

# ------------------------------------------------------------------
# Step 4: 验证不支持的引擎会被拒绝
# ------------------------------------------------------------------
echo "🧪 Step 4: 验证不支持的引擎会被拒绝"
echo "  输入目录: $TESTCASES_DIR"
echo "  输出文件: $UNSUPPORTED_XLSX"
echo "  引擎: api"
echo ""

cd "$PROJECT_DIR"
set +e
UNSUPPORTED_OUTPUT=$("$VENV_PYTHON" -m dochain_ocr \
    --input "$TESTCASES_DIR" \
    --excel "$UNSUPPORTED_XLSX" \
    --engine api 2>&1)
UNSUPPORTED_EXIT=$?
set -e

if [[ $UNSUPPORTED_EXIT -ne 0 ]]; then
    pass "api 引擎已被正确拒绝 (exit=$UNSUPPORTED_EXIT)"
else
    fail "api 引擎未被拒绝，预期应 fail fast"
fi

if [[ "$UNSUPPORTED_OUTPUT" == *"does not support structured Excel export"* ]]; then
    pass "错误信息正确: 不支持 Excel 结构化导出"
else
    fail "错误信息不符合预期: $UNSUPPORTED_OUTPUT"
fi

if [[ ! -f "$UNSUPPORTED_XLSX" ]]; then
    pass "不支持的引擎未生成 Excel 文件"
else
    fail "不支持的引擎错误生成了 Excel 文件: $UNSUPPORTED_XLSX"
fi

echo ""

# ------------------------------------------------------------------
# Step 5: 运行 Excel 批量导出
# ------------------------------------------------------------------
echo "🚀 Step 5: 运行 Excel 批量导出"
echo "  输入目录: $TESTCASES_DIR"
echo "  输出文件: $OUTPUT_XLSX"
echo "  引擎: smart"
echo ""

cd "$PROJECT_DIR"
"$VENV_PYTHON" -m dochain_ocr \
    --input "$TESTCASES_DIR" \
    --excel "$OUTPUT_XLSX" \
    --engine smart

echo ""

# ------------------------------------------------------------------
# Step 6: 验证结果
# ------------------------------------------------------------------
echo "🔍 Step 6: 验证结果"

# 6a. Excel 文件是否生成
if [[ -f "$OUTPUT_XLSX" ]]; then
    FILE_SIZE=$(stat -f%z "$OUTPUT_XLSX" 2>/dev/null || stat --format=%s "$OUTPUT_XLSX" 2>/dev/null || echo "unknown")
    pass "Excel 文件已生成: $OUTPUT_XLSX ($FILE_SIZE bytes)"
else
    fail "Excel 文件未生成: $OUTPUT_XLSX"
fi

# 6b. 用 Python 读取 Excel 验证内容
"$VENV_PYTHON" - "$OUTPUT_XLSX" << 'PYEOF'
import sys
from openpyxl import load_workbook

xlsx_path = sys.argv[1]
wb = load_workbook(xlsx_path, read_only=True)
ws = wb.active

# 读取表头
headers = [cell.value for cell in ws[1]]
rows = list(ws.iter_rows(min_row=2, values_only=True))

errors = []

# 6b-1: 检查列数
EXPECTED_COLS = ["序号", "数电发票号码", "发票代码", "发票号码", "开票日期",
                 "金额", "票面税额", "有效抵扣税额", "购买方识别号",
                 "销售方纳税人名称", "销售方纳税人识别号", "发票来源",
                 "票种", "货物或劳务名称", "旅客姓名", "出行日期",
                 "乘客姓名", "乘机日期", "座位类型"]

if headers == EXPECTED_COLS:
    print(f"  ✅ 列头正确: {len(headers)} 列")
else:
    missing = set(EXPECTED_COLS) - set(headers)
    extra = set(headers) - set(EXPECTED_COLS)
    errors.append(f"列头不匹配: 缺少{missing}, 多余{extra}")
    print(f"  ❌ 列头不匹配")

# 6b-2: 检查行数 (testcases/ 下有 5 个文件)
if len(rows) >= 4:
    print(f"  ✅ 数据行数: {len(rows)} 条记录")
else:
    errors.append(f"数据行数不足: {len(rows)}")
    print(f"  ❌ 数据行数不足: {len(rows)}")

# 6b-3: 检查必填字段不为空 (开票日期, 金额, 票种)
COL_IDX = {h: i for i, h in enumerate(headers)}
required_fields = ["开票日期", "金额", "票种"]
empty_count = 0
for row_idx, row in enumerate(rows, start=1):
    for field in required_fields:
        val = row[COL_IDX[field]]
        if not val or str(val).strip() == "":
            empty_count += 1
            errors.append(f"第{row_idx}行 {field} 为空")

if empty_count == 0:
    print(f"  ✅ 必填字段完整: 开票日期, 金额, 票种 均有值")
else:
    print(f"  ❌ {empty_count} 个必填字段为空")

# 6b-4: 检查票种枚举值，确保未把 general fallback 导出成“未知”
VALID_TYPES = {
    "数电发票（铁路电子客票）",
    "数电发票（增值税专用发票）",
    "数电发票（普通发票）",
    "数电发票（航空运输电子客票行程单）",
    "数电发票（通行费发票）",
    "区块链发票",
}
invoice_types = set()
for row in rows:
    t = row[COL_IDX["票种"]]
    if t:
        invoice_types.add(str(t))

invalid_types = invoice_types - VALID_TYPES
if not invalid_types:
    print(f"  ✅ 票种枚举合法: {invoice_types}")
else:
    errors.append(f"非法票种: {invalid_types}")
    print(f"  ❌ 非法票种: {invalid_types}")

# 6b-5: 打印摘要表
print("")
print("  ┌──────────────────────────────────────────────────────────────────┐")
print(f"  │ {'序号':^4} │ {'发票来源':^14} │ {'票种':^20} │ {'金额':^10} │")
print("  ├──────────────────────────────────────────────────────────────────┤")
for row in rows:
    seq = row[COL_IDX["序号"]]
    src = str(row[COL_IDX["发票来源"]] or "")[:14]
    typ = str(row[COL_IDX["票种"]] or "")[:20]
    amt = str(row[COL_IDX["金额"]] or "")[:10]
    print(f"  │ {seq:^4} │ {src:<14} │ {typ:<20} │ {amt:>10} │")
print("  └──────────────────────────────────────────────────────────────────┘")

wb.close()

if errors:
    print(f"\n  ⚠️  共 {len(errors)} 个问题:")
    for e in errors:
        print(f"    - {e}")
    sys.exit(1)
PYEOF

VERIFY_EXIT=$?
if [[ $VERIFY_EXIT -eq 0 ]]; then
    pass "Excel 内容验证通过"
else
    fail "Excel 内容验证失败"
fi

echo ""

# ------------------------------------------------------------------
# 汇总
# ------------------------------------------------------------------
TOTAL=$((PASS + FAIL))
echo "============================================"
if [[ $FAIL -eq 0 ]]; then
    echo "  🎉 全部通过! ($PASS/$TOTAL)"
else
    echo "  ⚠️  $FAIL/$TOTAL 项失败"
fi
echo "  📄 Excel: $OUTPUT_XLSX"
echo "============================================"

exit $FAIL

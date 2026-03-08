#!/usr/bin/env bash
# OCR CLI 快速测试脚本
#
# 用法:
#   ./test_ocr.sh                                         # smart 模式，默认 test1.jpg
#   ./test_ocr.sh myimage.png                             # smart 模式，指定文件
#   ./test_ocr.sh myimage.png result.txt                  # smart 模式 + 输出文件
#   ./test_ocr.sh myimage.png result.txt api              # 指定引擎模式
#   ./test_ocr.sh --batch                                 # 批量测试 testcases/ 下所有文件
#   ./test_ocr.sh --batch local                           # 批量测试，指定引擎
#   ./test_ocr.sh --dir <输入目录> <输出目录>              # 目录扫描，结果输出到指定目录
#   ./test_ocr.sh --dir ./invoices ./results smart        # 目录扫描，指定引擎
#   ./test_ocr.sh --excel <输入目录> <输出.xlsx>           # 批量识别 → Excel
#   ./test_ocr.sh --excel ./invoices ./out.xlsx smart     # 批量识别 → Excel，指定引擎
#
# 引擎模式:
#   smart  — 智能级联（默认）：发票→火车票→通用 OCR，全部使用百度 API
#   baidu  — 百度增值税发票识别（仅发票）
#   api    — PaddleX 云端版面分析
#   local  — PaddleOCR 本地 CPU 推理
#
# 使用 API/Baidu/Smart 模式前，请先设置环境变量：
#   source set_env.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/ocr-cli-tool"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
TESTCASES_DIR="$SCRIPT_DIR/testcases"
SUPPORTED_EXTS="pdf jpg jpeg png bmp tiff webp"

# 检查虚拟环境
if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "❌ 虚拟环境不存在，正在创建..."
    cd "$PROJECT_DIR"
    uv venv .venv
    uv pip install --python .venv/bin/python -e ".[local]"
    echo "✅ 虚拟环境已创建并安装依赖"
fi

# ---------------------------------------------------------------------------
# 加载环境变量（按需）
# ---------------------------------------------------------------------------
load_env() {
    local engine="$1"
    local NEED_ENV=false
    if [[ "$engine" == "api" && ( -z "${PADDLEOCR_API_URL:-}" || -z "${PADDLEOCR_ACCESS_TOKEN:-}" ) ]]; then
        NEED_ENV=true
    fi
    if [[ ("$engine" == "baidu" || "$engine" == "smart") && ( -z "${BAIDU_OCR_API_KEY:-}" || -z "${BAIDU_OCR_SECRET_KEY:-}" ) ]]; then
        NEED_ENV=true
    fi
    if [[ "$NEED_ENV" == true ]]; then
        if [[ -f "$SCRIPT_DIR/set_env.sh" ]]; then
            echo "🔑 加载 set_env.sh 环境变量..."
            source "$SCRIPT_DIR/set_env.sh"
        else
            echo "❌ 需要设置环境变量，请先运行: source set_env.sh"
            exit 1
        fi
    fi
}

# ---------------------------------------------------------------------------
# 单文件识别
# ---------------------------------------------------------------------------
run_single() {
    local input="$1"
    local output="${2:-}"
    local engine="${3:-smart}"

    if [[ ! -f "$input" ]]; then
        echo "❌ 文件不存在: $input"
        echo "用法: $0 [文件路径] [输出文件路径] [local|api|baidu|smart]"
        exit 1
    fi

    load_env "$engine"

    echo "📷 输入文件: $input"
    echo "🔧 引擎模式: $engine"

    local CMD=("$VENV_PYTHON" -m dochain_ocr --input "$input" --engine "$engine")
    if [[ -n "$output" ]]; then
        CMD+=(--output "$output")
        echo "📄 输出文件: $output"
    fi

    echo "⏳ 正在识别..."
    echo "---"
    cd "$PROJECT_DIR"
    "${CMD[@]}"
    echo "---"
    if [[ -n "$output" && -f "$output" ]]; then
        echo "✅ 结果已保存到: $output"
    fi
    echo "✅ 完成"
}

# ---------------------------------------------------------------------------
# 批量测试 testcases/ 目录
# ---------------------------------------------------------------------------
run_batch() {
    local engine="${1:-smart}"
    load_env "$engine"

    echo "🚀 批量测试模式 — 引擎: $engine"
    echo "📁 测试目录: $TESTCASES_DIR"
    echo "==========================================="

    local total=0
    local success=0
    local fail=0

    for f in "$TESTCASES_DIR"/test-*.pdf; do
        [[ -f "$f" ]] || continue
        local name
        name="$(basename "$f" .pdf)"
        local outfile="/tmp/${name}_${engine}.txt"
        total=$((total + 1))

        echo ""
        echo "--- [$name] ($engine) ---"
        cd "$PROJECT_DIR"
        if "$VENV_PYTHON" -m dochain_ocr --input "$f" --output "$outfile" --engine "$engine" 2>&1; then
            success=$((success + 1))
            echo "  → 保存到 $outfile"
        else
            fail=$((fail + 1))
            echo "  ❌ 识别失败"
        fi
    done

    echo ""
    echo "==========================================="
    echo "📊 批量测试结果: 共 $total 个文件, ✅ $success 成功, ❌ $fail 失败"
    echo "📂 输出目录: /tmp/*_${engine}.txt"
}

# ---------------------------------------------------------------------------
# 目录扫描模式
# ---------------------------------------------------------------------------
run_dir() {
    local input_dir="$1"
    local output_dir="$2"
    local engine="${3:-smart}"

    if [[ ! -d "$input_dir" ]]; then
        echo "❌ 输入目录不存在: $input_dir"
        exit 1
    fi

    # 转为绝对路径
    input_dir="$(cd "$input_dir" && pwd)"
    mkdir -p "$output_dir"
    output_dir="$(cd "$output_dir" && pwd)"

    load_env "$engine"

    echo "🚀 目录扫描模式 — 引擎: $engine"
    echo "📂 输入目录: $input_dir"
    echo "📂 输出目录: $output_dir"
    echo "=========================================="

    local total=0
    local success=0
    local fail=0

    for ext in $SUPPORTED_EXTS; do
        for f in "$input_dir"/*.$ext "$input_dir"/*."$(echo "$ext" | tr '[:lower:]' '[:upper:]')"; do
            [[ -f "$f" ]] || continue
            local basename
            basename="$(basename "$f")"
            local name="${basename%.*}"
            local outfile="$output_dir/${name}.txt"
            total=$((total + 1))

            echo ""
            echo "--- [$basename] ($engine) ---"
            cd "$PROJECT_DIR"
            if "$VENV_PYTHON" -m dochain_ocr --input "$f" --output "$outfile" --engine "$engine" 2>&1; then
                success=$((success + 1))
                echo "  → $outfile"
            else
                fail=$((fail + 1))
                echo "  ❌ 识别失败"
            fi
        done
    done

    if [[ $total -eq 0 ]]; then
        echo "⚠️  未找到支持的文件（支持: $SUPPORTED_EXTS）"
    else
        echo ""
        echo "=========================================="
        echo "📊 处理结果: 共 $total 个文件, ✅ $success 成功, ❌ $fail 失败"
        echo "📂 输出目录: $output_dir"
    fi
}

# ---------------------------------------------------------------------------
# Excel 批量导出模式
# ---------------------------------------------------------------------------
run_excel() {
    local input_dir="$1"
    local output_xlsx="$2"
    local engine="${3:-smart}"

    if [[ ! -d "$input_dir" ]]; then
        echo "❌ 输入目录不存在: $input_dir"
        exit 1
    fi

    # 转为绝对路径
    input_dir="$(cd "$input_dir" && pwd)"
    # 输出文件: 如果是相对路径，基于当前工作目录
    if [[ "$output_xlsx" != /* ]]; then
        output_xlsx="$(pwd)/$output_xlsx"
    fi
    mkdir -p "$(dirname "$output_xlsx")"

    load_env "$engine"

    echo "📊 Excel 批量导出模式 — 引擎: $engine"
    echo "📂 输入目录: $input_dir"
    echo "📄 输出文件: $output_xlsx"
    echo "=========================================="

    cd "$PROJECT_DIR"
    "$VENV_PYTHON" -m dochain_ocr --input "$input_dir" --excel "$output_xlsx" --engine "$engine"
}

# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
case "${1:-}" in
    --batch)
        run_batch "${2:-smart}"
        ;;
    --dir)
        if [[ -z "${2:-}" || -z "${3:-}" ]]; then
            echo "用法: $0 --dir <输入目录> <输出目录> [local|api|baidu|smart]"
            exit 1
        fi
        run_dir "$2" "$3" "${4:-smart}"
        ;;
    --excel)
        if [[ -z "${2:-}" || -z "${3:-}" ]]; then
            echo "用法: $0 --excel <输入目录> <输出.xlsx> [local|api|baidu|smart]"
            exit 1
        fi
        run_excel "$2" "$3" "${4:-smart}"
        ;;
    *)
        run_single "${1:-$SCRIPT_DIR/test1.jpg}" "${2:-}" "${3:-smart}"
        ;;
esac

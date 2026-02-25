#!/usr/bin/env bash
# PaddleOCR & 百度智能云 OCR 环境变量配置模板
#
# 用法:
#   1. 复制本文件: cp set_env.example.sh set_env.sh
#   2. 填入真实凭据
#   3. 加载: source set_env.sh
#
# 注意: set_env.sh 已在 .gitignore 中排除，请勿提交真实凭据

# PaddleX 云端版面分析 API（AI Studio 部署实例）
export PADDLEOCR_API_URL="https://your-instance.aistudio-app.com/layout-parsing"
export PADDLEOCR_ACCESS_TOKEN="your_paddlex_access_token"

# 百度智能云 OCR（增值税发票 / 火车票 / 通用高精度）
# API 端点固定，无需配置 URL：https://aip.baidubce.com/rest/2.0/ocr/v1/...
# 控制台：https://console.bce.baidu.com/ai/#/ai/ocr/overview/index
export BAIDU_OCR_API_KEY="your_baidu_api_key"
export BAIDU_OCR_SECRET_KEY="your_baidu_secret_key"

echo "✅ PaddleOCR API 环境变量已设置"
echo "   PADDLEOCR_API_URL=$PADDLEOCR_API_URL"
echo "   PADDLEOCR_ACCESS_TOKEN=****${PADDLEOCR_ACCESS_TOKEN: -8}"
echo "✅ 百度智能云 OCR 环境变量已设置"
echo "   BAIDU_OCR_API_KEY=****${BAIDU_OCR_API_KEY: -8}"

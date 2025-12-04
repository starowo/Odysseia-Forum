#!/bin/bash

# Odysseia-Forum Discord Bot 一键启动脚本
# 作者: AI Assistant
# 用途: 自动设置Python环境并启动Discord机器人

set -e # 如果任何命令以非零状态退出，则立即退出脚本

# --- 颜色定义 ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

# --- 日志函数 ---
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# --- 辅助函数 ---
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# --- 核心功能函数 ---

# 1. 检查并准备所有必需的系统和Python依赖项
check_and_prepare_dependencies() {
    log_info "正在检查依赖项..."

    # 检查 uv，如果缺失则尝试使用 pip 安装
    if ! command_exists uv; then
        log_warning "未找到 'uv' 命令。正在尝试使用 pip 安装..."
        if command_exists pip3; then
            pip3 install uv
        elif command_exists pip; then
            pip install uv
        else
            log_error "未找到 'pip'。请先安装 Python 和 pip，然后手动安装 uv ('pip install uv')。"
            exit 1
        fi
        log_success "uv 安装成功。"
    fi

    # 检查并尝试自动安装 Jemalloc
    JEMALLOC_PATH=$(find /usr/lib /usr/local/lib -name "libjemalloc.so" -print -quit 2>/dev/null)
    if [ -z "$JEMALLOC_PATH" ]; then
        log_warning "未找到 Jemalloc。为了获得更佳的性能，建议安装它。"
        if command_exists sudo; then
            read -p "是否尝试使用 sudo 自动安装 Jemalloc? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                if command_exists apt-get; then
                    sudo apt-get update && sudo apt-get install -y libjemalloc-dev
                elif command_exists yum; then
                    sudo yum install -y jemalloc-devel
                elif command_exists pacman; then
                    sudo pacman -S --noconfirm jemalloc
                else
                    log_error "未知的包管理器。请手动安装 Jemalloc。"
                    USE_JEMALLOC=false
                    return
                fi
                log_success "Jemalloc 安装成功。"
                # 重新查找路径
                JEMALLOC_PATH=$(find /usr/lib /usr/local/lib -name "libjemalloc.so" -print -quit 2>/dev/null)
            else
                log_info "已跳过 Jemalloc 安装。"
            fi
        else
            log_warning "未找到 'sudo' 命令，无法自动安装 Jemalloc。请手动安装。"
        fi
    fi

    if [ -n "$JEMALLOC_PATH" ]; then
        log_info "发现 Jemalloc: $JEMALLOC_PATH"
        USE_JEMALLOC=true
    else
        USE_JEMALLOC=false
    fi
}

# 2. 设置 Python 虚拟环境并将项目以可编辑模式安装
setup_environment() {
    log_info "正在使用 uv 设置 Python 环境..."
    if [ ! -d ".venv" ]; then
        log_info "正在创建虚拟环境..."
        uv venv
        log_success "虚拟环境创建成功。"
    else
        log_info "检测到已存在的虚拟环境。"
    fi

    if [ -f "pyproject.toml" ]; then
        log_info "正在以可编辑模式安装项目及其依赖..."
        uv pip install -e .
        log_success "项目安装完成。"
    else
        log_error "关键文件 'pyproject.toml' 未找到。无法继续安装。"
        exit 1
    fi
}

# 3. 启动 Discord 机器人
start_bot() {
    log_info "正在启动 Odysseia-Forum Discord Bot..."
    if [ ! -f "config.json" ]; then
        log_error "配置文件 'config.json' 未找到。请从 'config.example.json' 创建并填入您的 Bot Token。"
        exit 1
    fi

    LAUNCH_CMD="uv run python bot_main.py"
    if [ "$USE_JEMALLOC" = true ]; then
        LAUNCH_CMD="LD_PRELOAD=$JEMALLOC_PATH $LAUNCH_CMD"
        log_info "将使用 Jemalloc 启动以优化内存。"
    else
        log_warning "将在没有 Jemalloc 的情况下启动。可能会有更高的内存占用。"
    fi

    log_info "执行启动命令: $LAUNCH_CMD"
    echo "=========================================="
    log_info "机器人正在运行... 按 Ctrl+C 停止。"
    trap 'echo -e "\n${YELLOW}正在停止机器人...${NC}"; exit 0' SIGINT SIGTERM
    eval $LAUNCH_CMD
}

# 显示帮助信息
show_help() {
    echo "Odysseia-Forum Discord Bot 启动脚本"
    echo ""
    echo "用法: ./start.sh [命令]"
    echo ""
    echo "可用命令:"
    echo "  (无命令)    - 启动机器人（如果需要，会先进行设置）。"
    echo "  setup       - 仅设置环境（安装依赖），不启动机器人。"
    echo "  restart     - 重启机器人（停止现有进程后重新启动）。"
    echo "  --help, -h  - 显示此帮助信息。"
    echo ""
}

# --- 脚本主逻辑 ---
main() {
    if [ ! -f "bot_main.py" ]; then
        log_error "未找到 'bot_main.py'。请确保您在项目根目录下运行此脚本。"
        exit 1
    fi

    # 处理命令行参数
    case "$1" in
        setup)
            log_info "执行仅设置模式..."
            check_and_prepare_dependencies
            setup_environment
            log_success "环境设置完成！现在可以运行 './start.sh' 来启动机器人。"
            ;;
        restart)
            log_info "正在重启机器人..."
            # 尝试停止现有机器人进程
            pkill -f "uv run python bot_main.py" || true
            sleep 2
            # 执行默认启动流程
            check_and_prepare_dependencies
            setup_environment
            start_bot
            ;;
        --help|-h)
            show_help
            ;;
        *)
            # 默认流程：检查、设置并启动
            check_and_prepare_dependencies
            setup_environment
            start_bot
            ;;
    esac
}

# 执行主函数，并传递所有脚本参数
main "$@"
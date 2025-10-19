#!/bin/bash

# =============================================================================
# 🧹 COMPLETE CLEANUP SCRIPT FOR ALICE CHESS PROJECT
# =============================================================================
#
# This script safely removes all components of the Alice Chess project:
# - Project directories and files
# - Virtual environments
# - Running processes
# - Optionally: Stockfish and Homebrew cleanup
#
# USAGE: ./cleanup_alice_chess.sh [OPTIONS]
#
# OPTIONS:
#   --full          : Full cleanup including Stockfish removal
#   --dry-run       : Show what would be removed without deleting
#   --help          : Show this help message
#
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default settings
DRY_RUN=false
FULL_CLEANUP=false

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

print_header() {
    echo -e "${BLUE}================================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================================================${NC}"
}

print_step() {
    echo -e "${GREEN}➤ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  WARNING: $1${NC}"
}

print_error() {
    echo -e "${RED}❌ ERROR: $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

confirm_action() {
    local message="$1"
    local default="${2:-n}"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would ask: $message${NC}"
        return 0
    fi

    echo -e "${YELLOW}$message${NC}"
    read -p "(y/N): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping..."
        return 1
    fi
    return 0
}

safe_remove() {
    local path="$1"
    local description="$2"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would remove: $description ($path)${NC}"
        return 0
    fi

    if [ -e "$path" ]; then
        echo "Removing $description..."
        rm -rf "$path"
        echo -e "${GREEN}✅ Removed: $description${NC}"
    else
        echo -e "${BLUE}ℹ️  Already removed: $description${NC}"
    fi
}

# =============================================================================
# CLEANUP FUNCTIONS
# =============================================================================

stop_processes() {
    print_step "Stopping running processes..."

    # Find and stop Flask/Alice Chess servers
    local flask_pids=$(ps aux | grep -E "(flask)" | grep -v grep | awk '{print $2}' || true)
    if [ -n "$flask_pids" ]; then
        echo "Stopping Flask servers (PIDs: $flask_pids)..."
        if [ "$DRY_RUN" = false ]; then
            kill -9 $flask_pids 2>/dev/null || true
        else
            echo -e "${YELLOW}[DRY RUN] Would stop Flask servers${NC}"
        fi
    fi

    # Find and stop Chess API servers
    local chessapi_pids=$(ps aux | grep -E "(uvicorn|chessapi)" | grep -v grep | awk '{print $2}' || true)
    if [ -n "$chessapi_pids" ]; then
        echo "Stopping Chess API servers (PIDs: $chessapi_pids)..."
        if [ "$DRY_RUN" = false ]; then
            kill -9 $chessapi_pids 2>/dev/null || true
        else
            echo -e "${YELLOW}[DRY RUN] Would stop Chess API servers${NC}"
        fi
    fi

    echo -e "${GREEN}✅ Processes stopped${NC}"
}

cleanup_projects() {
    print_step "Removing project directories..."

    # Alice Chess project (current directory or specified path)
    local alice_chess_dir="${ALICE_CHESS_DIR:-$(pwd)}"
    safe_remove "$alice_chess_dir" "Alice Chess project directory"

    # Chess API project (sibling directory or specified path)
    local chessapi_dir="${CHESSAPI_DIR:-$(dirname "$alice_chess_dir")/chessapi}"
    safe_remove "$chessapi_dir" "Chess API project directory"
}

cleanup_stockfish() {
    if [ "$FULL_CLEANUP" = true ]; then
        print_step "Removing Stockfish (full cleanup mode)..."

        if command -v stockfish >/dev/null 2>&1; then
            print_warning "This will attempt to remove Stockfish using your system's package manager."
            if confirm_action "Remove Stockfish?"; then
                if [ "$DRY_RUN" = false ]; then
                    # Try different package managers
                    if command -v brew >/dev/null 2>&1; then
                        echo "Using Homebrew to remove Stockfish..."
                        brew uninstall stockfish
                        brew cleanup stockfish
                    elif command -v apt >/dev/null 2>&1; then
                        echo "Using apt to remove Stockfish..."
                        sudo apt remove -y stockfish
                    elif command -v yum >/dev/null 2>&1; then
                        echo "Using yum to remove Stockfish..."
                        sudo yum remove -y stockfish
                    elif command -v dnf >/dev/null 2>&1; then
                        echo "Using dnf to remove Stockfish..."
                        sudo dnf remove -y stockfish
                    elif command -v pacman >/dev/null 2>&1; then
                        echo "Using pacman to remove Stockfish..."
                        sudo pacman -R stockfish
                    else
                        print_warning "No supported package manager found. Stockfish removal skipped."
                        echo "You may need to manually remove Stockfish from your system."
                        return 0
                    fi
                    echo -e "${GREEN}✅ Stockfish removal attempted${NC}"
                else
                    echo -e "${YELLOW}[DRY RUN] Would remove Stockfish${NC}"
                fi
            fi
        else
            echo -e "${BLUE}ℹ️  Stockfish not found or already removed${NC}"
        fi
    fi
}

cleanup_package_manager() {
    if [ "$FULL_CLEANUP" = true ]; then
        print_step "Cleaning up package manager (optional)..."

        print_warning "This will remove unused package dependencies. This is generally safe but may affect other projects."
        if confirm_action "Run package manager cleanup?"; then
            if [ "$DRY_RUN" = false ]; then
                # Try different package managers
                if command -v brew >/dev/null 2>&1; then
                    echo "Using Homebrew cleanup..."
                    brew autoremove
                    brew cleanup --prune=all
                elif command -v apt >/dev/null 2>&1; then
                    echo "Using apt cleanup..."
                    sudo apt autoremove -y
                    sudo apt autoclean
                elif command -v yum >/dev/null 2>&1; then
                    echo "Using yum cleanup..."
                    sudo yum autoremove -y
                    sudo yum clean all
                elif command -v dnf >/dev/null 2>&1; then
                    echo "Using dnf cleanup..."
                    sudo dnf autoremove -y
                    sudo dnf clean all
                elif command -v pacman >/dev/null 2>&1; then
                    echo "Using pacman cleanup..."
                    sudo pacman -Qdtq | sudo pacman -Rns -
                else
                    print_warning "No supported package manager found. Cleanup skipped."
                    return 0
                fi
                echo -e "${GREEN}✅ Package manager cleaned up${NC}"
            else
                echo -e "${YELLOW}[DRY RUN] Would clean up package manager${NC}"
            fi
        fi
    fi
}

verify_cleanup() {
    print_step "Verifying cleanup..."

    local issues_found=false
    local alice_chess_dir="${ALICE_CHESS_DIR:-$(pwd)}"
    local chessapi_dir="${CHESSAPI_DIR:-$(dirname "$alice_chess_dir")/chessapi}"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${BLUE}ℹ️  Dry run - checking current state${NC}"
    fi

    # Check if directories still exist
    if [ -d "$alice_chess_dir" ]; then
        if [ "$DRY_RUN" = true ]; then
            echo -e "${YELLOW}ℹ️  Alice Chess directory exists (would be removed)${NC}"
        else
            echo -e "${RED}❌ Alice Chess directory still exists${NC}"
            issues_found=true
        fi
    else
        echo -e "${GREEN}✅ Alice Chess directory removed${NC}"
    fi

    if [ -d "$chessapi_dir" ]; then
        if [ "$DRY_RUN" = true ]; then
            echo -e "${YELLOW}ℹ️  Chess API directory exists (would be removed)${NC}"
        else
            echo -e "${RED}❌ Chess API directory still exists${NC}"
            issues_found=true
        fi
    else
        echo -e "${GREEN}✅ Chess API directory removed${NC}"
    fi

    # Check for running processes
    local running_processes=$(ps aux | grep -E "(flask|uvicorn|chessapi)" | grep -v grep | wc -l 2>/dev/null || echo "0")
    if [ "$running_processes" -gt 0 ]; then
        if [ "$DRY_RUN" = true ]; then
            echo -e "${YELLOW}ℹ️  $running_processes related processes running (would be stopped)${NC}"
        else
            echo -e "${RED}❌ $running_processes processes still running${NC}"
            issues_found=true
        fi
    else
        echo -e "${GREEN}✅ No related processes running${NC}"
    fi

    # Check ports
    if lsof -i :5000 >/dev/null 2>&1; then
        if [ "$DRY_RUN" = true ]; then
            echo -e "${YELLOW}ℹ️  Port 5000 in use (would be freed)${NC}"
        else
            echo -e "${RED}❌ Port 5000 still in use${NC}"
            issues_found=true
        fi
    else
        echo -e "${GREEN}✅ Port 5000 free${NC}"
    fi

    if lsof -i :8000 >/dev/null 2>&1; then
        if [ "$DRY_RUN" = true ]; then
            echo -e "${YELLOW}ℹ️  Port 8000 in use (would be freed)${NC}"
        else
            echo -e "${RED}❌ Port 8000 still in use${NC}"
            issues_found=true
        fi
    else
        echo -e "${GREEN}✅ Port 8000 free${NC}"
    fi

    if [ "$FULL_CLEANUP" = true ]; then
        if command -v stockfish >/dev/null 2>&1; then
            if [ "$DRY_RUN" = true ]; then
                echo -e "${YELLOW}ℹ️  Stockfish installed (would be removed)${NC}"
            else
                echo -e "${RED}❌ Stockfish still installed${NC}"
                issues_found=true
            fi
        else
            echo -e "${GREEN}✅ Stockfish removed${NC}"
        fi
    fi

    if [ "$DRY_RUN" = true ]; then
        echo -e "${BLUE}ℹ️  Dry run verification complete${NC}"
        return 0
    elif [ "$issues_found" = true ]; then
        echo -e "${RED}❌ Cleanup incomplete - some components may still exist${NC}"
        return 1
    else
        echo -e "${GREEN}✅ Cleanup completed successfully${NC}"
        return 0
    fi
}

show_summary() {
    print_header "CLEANUP SUMMARY"

    local alice_chess_dir="${ALICE_CHESS_DIR:-$(pwd)}"
    local chessapi_dir="${CHESSAPI_DIR:-$(dirname "$alice_chess_dir")/chessapi}"

    echo "Removed components:"
    echo "  ✅ Alice Chess project ($alice_chess_dir/)"
    echo "  ✅ Chess API project ($chessapi_dir/)"
    echo "  ✅ Running processes (Flask and Uvicorn servers)"
    echo "  ✅ Virtual environments"

    if [ "$FULL_CLEANUP" = true ]; then
        echo "  ✅ Stockfish engine (if installed via package manager)"
        echo "  ✅ Unused packages (if supported by package manager)"
    fi

    echo ""
    echo "Preserved components:"
    echo "  ✅ System Python installation"
    echo "  ✅ Package manager installation"
    echo "  ✅ Other packages (if not full cleanup)"
    echo "  ✅ Other user projects and files"

    echo ""
    echo -e "${GREEN}🎉 Cleanup completed!${NC}"
}

# =============================================================================
# MAIN SCRIPT
# =============================================================================

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --full)
                FULL_CLEANUP=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                print_warning "DRY RUN MODE - No actual changes will be made"
                shift
                ;;
            --help)
                echo "Complete Cleanup Script for Alice Chess Project"
                echo ""
                echo "USAGE: $0 [OPTIONS]"
                echo ""
                echo "OPTIONS:"
                echo "  --full          : Full cleanup including Stockfish removal"
                echo "  --dry-run       : Show what would be removed without deleting"
                echo "  --help          : Show this help message"
                echo ""
                echo "ENVIRONMENT VARIABLES:"
                echo "  ALICE_CHESS_DIR : Path to Alice Chess project directory (default: current directory)"
                echo "  CHESSAPI_DIR    : Path to Chess API project directory (default: ../chessapi relative to Alice Chess)"
                echo ""
                echo "EXAMPLES:"
                echo "  $0                           # Standard cleanup of current directory"
                echo "  $0 --dry-run                # Preview what would be removed"
                echo "  $0 --full                   # Full cleanup including Stockfish"
                echo "  ALICE_CHESS_DIR=/path/to/alice-chess $0  # Specify custom Alice Chess directory"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    print_header "🧹 ALICE CHESS PROJECT CLEANUP"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}🔍 DRY RUN MODE - Previewing cleanup actions${NC}"
    else
        echo -e "${RED}⚠️  WARNING: This will permanently delete project files!${NC}"
        echo -e "${RED}   Make sure you have backups if needed.${NC}"
        echo ""
        if ! confirm_action "Continue with cleanup?"; then
            echo "Cleanup cancelled."
            exit 0
        fi
    fi

    if [ "$FULL_CLEANUP" = true ]; then
        print_warning "FULL CLEANUP MODE - This will also remove Stockfish and clean Homebrew"
    fi

    echo ""

    # Execute cleanup steps
    stop_processes
    echo ""

    cleanup_projects
    echo ""

    cleanup_stockfish
    echo ""

    cleanup_package_manager
    echo ""

    verify_cleanup
    local verify_result=$?

    echo ""
    show_summary

    if [ "$DRY_RUN" = true ]; then
        echo ""
        echo -e "${BLUE}ℹ️  This was a dry run. Run without --dry-run to perform actual cleanup.${NC}"
    fi

    return $verify_result
}

# =============================================================================
# SCRIPT ENTRY POINT
# =============================================================================

# Run main function
main "$@"
exit $?

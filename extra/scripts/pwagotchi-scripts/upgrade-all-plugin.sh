#!/usr/bin/env bash

#############################################################################
# Pwnagotchi Plugin Upgrade Script
# Description: Updates all installed pwnagotchi plugins with status tracking
# Usage: 
#   sudo ./upgrade-all-plugin.sh                    # Upgrade all detected plugins
#   sudo ./upgrade-all-plugin.sh plugin1 plugin2    # Upgrade specific plugins
#   PLUGINS_OVERRIDE="plugin1 plugin2" sudo ./upgrade-all-plugin.sh
#############################################################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Emoji/Status symbols
CHECK="✓"
CROSS="✗"
ARROW="→"
INFO="ℹ"

# Counters
SUCCESS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0
TOTAL_COUNT=0

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}${CROSS} Please run as root or with sudo${NC}"
    exit 1
fi

# Log file
LOG_FILE="/var/log/pwnagotchi-plugin-upgrade-$(date +%Y%m%d-%H%M%S).log"
echo "Logging to: $LOG_FILE"
echo ""

# Function to log messages
log_message() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Function to get list of installed plugins
get_installed_plugins() {
    local plugins=()
    
    # Method 1: Find all .py plugin files in standard locations
    local plugin_dirs=(
        "/usr/local/lib/python3*/dist-packages/pwnagotchi/plugins/default"
        "/usr/local/lib/python3*/dist-packages/pwnagotchi/plugins"
        "/usr/local/share/pwnagotchi/custom-plugins"
        "/usr/local/share/pwnagotchi/available-plugins"
        "/etc/pwnagotchi/plugins"
        "/opt/pwnagotchi/plugins"
    )
    
    for dir_pattern in "${plugin_dirs[@]}"; do
        for plugin_dir in $dir_pattern; do
            if [ -d "$plugin_dir" ]; then
                # Find all .py files that are not __init__.py
                while IFS= read -r plugin_file; do
                    if [ -f "$plugin_file" ]; then
                        local plugin_name=$(basename "$plugin_file" .py)
                        # Skip __init__ and other special files
                        if [[ ! "$plugin_name" =~ ^__ ]] && [[ ! "$plugin_name" =~ ^test_ ]]; then
                            plugins+=("$plugin_name")
                        fi
                    fi
                done < <(find "$plugin_dir" -maxdepth 1 -type f -name "*.py" 2>/dev/null)
            fi
        done
    done
    
    # Method 2: Parse config.toml for enabled plugins
    if [ -f /etc/pwnagotchi/config.toml ]; then
        while IFS= read -r plugin_name; do
            if [ -n "$plugin_name" ]; then
                plugins+=("$plugin_name")
            fi
        done < <(grep -oP 'main\.plugins\.\K[^.]+(?=\.enabled\s*=\s*true)' /etc/pwnagotchi/config.toml 2>/dev/null)
    fi
    
    # Method 3: Try to use pwnagotchi CLI if it has a search/list command
    # Note: This may not work on all versions but we'll try
    if command -v pwnagotchi &> /dev/null; then
        # Try to get available plugins from search output
        local search_output=$(pwnagotchi plugins search "" 2>/dev/null | grep -oP '^\s*\K[a-z_-]+(?=\s)' || true)
        if [ -n "$search_output" ]; then
            while IFS= read -r plugin_name; do
                [ -n "$plugin_name" ] && plugins+=("$plugin_name")
            done <<< "$search_output"
        fi
    fi
    
    # Remove duplicates and sort
    if [ ${#plugins[@]} -gt 0 ]; then
        printf '%s\n' "${plugins[@]}" | sort -u
    fi
}

# Function to upgrade a single plugin
upgrade_plugin() {
    local plugin_name=$1
    local start_time=$(date +%s)
    
    log_message "${CYAN}${ARROW} Upgrading plugin: ${plugin_name}${NC}"
    
    # Attempt to upgrade the plugin
    if pwnagotchi plugins upgrade "$plugin_name" >> "$LOG_FILE" 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_message "${GREEN}${CHECK} Successfully upgraded ${plugin_name} (${duration}s)${NC}"
        ((SUCCESS_COUNT++))
        return 0
    else
        local exit_code=$?
        log_message "${RED}${CROSS} Failed to upgrade ${plugin_name} (exit code: ${exit_code})${NC}"
        ((FAIL_COUNT++))
        return 1
    fi
}

# Main script
main() {
    log_message "${BLUE}════════════════════════════════════════════════════════${NC}"
    log_message "${BLUE}     Pwnagotchi Plugin Upgrade Script${NC}"
    log_message "${BLUE}     Started: $(date)${NC}"
    log_message "${BLUE}════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Step 1: Update plugin repositories
    log_message "${YELLOW}${INFO} Step 1/3: Updating plugin repositories...${NC}"
    if pwnagotchi plugins update >> "$LOG_FILE" 2>&1; then
        log_message "${GREEN}${CHECK} Plugin repositories updated successfully${NC}"
    else
        log_message "${RED}${CROSS} Failed to update plugin repositories${NC}"
        log_message "${YELLOW}Continuing anyway...${NC}"
    fi
    echo ""
    
    # Step 2: Get list of installed/enabled plugins
    log_message "${YELLOW}${INFO} Step 2/3: Finding installed plugins...${NC}"
    
    # Check if plugins were specified as command-line arguments
    if [ $# -gt 0 ]; then
        PLUGINS=("$@")
        log_message "${CYAN}Using command-line specified plugins: ${PLUGINS[*]}${NC}"
    # Check if PLUGINS_OVERRIDE environment variable is set
    elif [ -n "${PLUGINS_OVERRIDE:-}" ]; then
        IFS=' ' read -r -a PLUGINS <<< "$PLUGINS_OVERRIDE"
        log_message "${GREEN}Using environment specified plugins: ${PLUGINS[*]}${NC}"
    else
        # Dynamically detect installed plugins
        mapfile -t PLUGINS < <(get_installed_plugins)
        
        # If no plugins found, show warning
        if [ ${#PLUGINS[@]} -eq 0 ]; then
            log_message "${YELLOW}${INFO} No plugins detected automatically${NC}"
            log_message "${YELLOW}${INFO} Possible reasons:${NC}"
            log_message "  - Pwnagotchi is not installed"
            log_message "  - Plugin directories don't exist yet"
            log_message "  - No plugins are currently installed"
            log_message ""
            log_message "${CYAN}${INFO} You can specify plugins to upgrade:${NC}"
            log_message "${CYAN}  sudo $0 plugin1 plugin2 plugin3${NC}"
            log_message "${CYAN}  PLUGINS_OVERRIDE='plugin1 plugin2' sudo $0${NC}"
            log_message "${RED}${CROSS} No plugins to upgrade${NC}"
            exit 0
        else
            log_message "${CYAN}Auto-detected ${#PLUGINS[@]} plugin(s):${NC}"
            printf '  - %s\n' "${PLUGINS[@]}" | tee -a "$LOG_FILE"
        fi
    fi
    
    TOTAL_COUNT=${#PLUGINS[@]}
    echo ""
    
    # Step 3: Upgrade each plugin
    log_message "${YELLOW}${INFO} Step 3/3: Upgrading plugins...${NC}"
    echo ""
    
    for plugin in "${PLUGINS[@]}"; do
        # Skip empty entries
        [ -z "$plugin" ] && continue
        
        upgrade_plugin "$plugin"
        echo ""
    done
    
    # Summary
    log_message "${BLUE}════════════════════════════════════════════════════════${NC}"
    log_message "${BLUE}     Upgrade Summary${NC}"
    log_message "${BLUE}════════════════════════════════════════════════════════${NC}"
    log_message "Total plugins processed: ${TOTAL_COUNT}"
    log_message "${GREEN}Successfully upgraded:   ${SUCCESS_COUNT}${NC}"
    log_message "${RED}Failed upgrades:         ${FAIL_COUNT}${NC}"
    log_message "${YELLOW}Skipped:                 ${SKIP_COUNT}${NC}"
    log_message ""
    log_message "Completed: $(date)"
    log_message "Full log available at: ${LOG_FILE}"
    log_message "${BLUE}════════════════════════════════════════════════════════${NC}"
    
    # Exit with appropriate code
    if [ $FAIL_COUNT -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

# Run main function
main

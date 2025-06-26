#!/bin/bash

# LetsGoal Firewall Configuration Script
# Configures UFW firewall for secure LetsGoal deployment

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Default configuration
DEPLOYMENT_TYPE=""
ALLOW_SSH=true
ALLOW_HTTP=true
ALLOW_HTTPS=true
ALLOW_APP_PORT=false
APP_PORT=5001
SSH_PORT=22
ADMIN_IPS=()
BLOCKED_COUNTRIES=()
RATE_LIMIT_ENABLED=false

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${PURPLE}"
    echo "================================================================================"
    echo "                      LetsGoal Firewall Configuration"
    echo "================================================================================"
    echo -e "${NC}"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_ufw() {
    if ! command -v ufw &> /dev/null; then
        log_info "Installing UFW firewall..."
        apt-get update -y
        apt-get install -y ufw
    fi
    
    log_info "UFW firewall is available"
}

load_config() {
    local config_file="/opt/letsgoal/.env"
    
    if [[ -f "$config_file" ]]; then
        log_info "Loading configuration from $config_file..."
        
        # Source the environment file
        set -a
        source "$config_file"
        set +a
        
        # Update configuration from environment
        DEPLOYMENT_TYPE="${DEPLOYMENT_TYPE:-local}"
        
        if [[ "$DEPLOYMENT_TYPE" == "local" ]]; then
            ALLOW_APP_PORT=true
        else
            ALLOW_APP_PORT=false
        fi
    else
        log_warning "Configuration file not found, using defaults"
    fi
}

reset_firewall() {
    log_info "Resetting UFW to defaults..."
    
    # Reset UFW rules
    ufw --force reset
    
    # Set default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    log_success "Firewall reset to defaults"
}

configure_ssh_access() {
    if [[ "$ALLOW_SSH" == true ]]; then
        log_info "Configuring SSH access..."
        
        # Allow SSH on specified port
        ufw allow "$SSH_PORT/tcp" comment "SSH access"
        
        # If admin IPs are specified, limit SSH to those IPs
        if [[ ${#ADMIN_IPS[@]} -gt 0 ]]; then
            # First deny SSH from everywhere
            ufw delete allow "$SSH_PORT/tcp" 2>/dev/null || true
            
            # Then allow only from admin IPs
            for admin_ip in "${ADMIN_IPS[@]}"; do
                log_info "Allowing SSH from admin IP: $admin_ip"
                ufw allow from "$admin_ip" to any port "$SSH_PORT" proto tcp comment "SSH from admin"
            done
        fi
        
        log_success "SSH access configured on port $SSH_PORT"
    else
        log_warning "SSH access is disabled - ensure you have alternative access!"
    fi
}

configure_web_access() {
    if [[ "$ALLOW_HTTP" == true ]]; then
        log_info "Allowing HTTP traffic (port 80)..."
        ufw allow 80/tcp comment "HTTP web traffic"
    fi
    
    if [[ "$ALLOW_HTTPS" == true ]]; then
        log_info "Allowing HTTPS traffic (port 443)..."
        ufw allow 443/tcp comment "HTTPS web traffic"
    fi
    
    if [[ "$ALLOW_APP_PORT" == true ]]; then
        log_info "Allowing application port $APP_PORT for local access..."
        ufw allow "$APP_PORT/tcp" comment "LetsGoal application port"
    fi
}

configure_rate_limiting() {
    if [[ "$RATE_LIMIT_ENABLED" == true ]]; then
        log_info "Configuring rate limiting..."
        
        # SSH rate limiting
        ufw limit "$SSH_PORT/tcp" comment "SSH rate limiting"
        
        # HTTP rate limiting (basic)
        ufw limit 80/tcp comment "HTTP rate limiting"
        ufw limit 443/tcp comment "HTTPS rate limiting"
        
        log_success "Rate limiting configured"
    fi
}

configure_country_blocking() {
    if [[ ${#BLOCKED_COUNTRIES[@]} -gt 0 ]]; then
        log_info "Configuring country-based blocking..."
        
        # Note: This requires additional tools like ipset and iptables
        # UFW doesn't directly support country blocking
        log_warning "Country blocking requires additional setup with ipset/iptables"
        log_warning "Consider using external services like Cloudflare for geo-blocking"
    fi
}

configure_application_specific() {
    log_info "Configuring application-specific rules..."
    
    # Allow internal Docker communication
    ufw allow from 172.16.0.0/12 comment "Docker internal network"
    ufw allow from 10.0.0.0/8 comment "Private network A"
    ufw allow from 192.168.0.0/16 comment "Private network B"
    
    # Block common attack ports
    local attack_ports=("23" "135" "139" "445" "1433" "3389" "5432" "5900")
    for port in "${attack_ports[@]}"; do
        ufw deny "$port" comment "Block common attack port $port"
    done
    
    # Allow outbound email (if email notifications are used)
    ufw allow out 25/tcp comment "SMTP outbound"
    ufw allow out 587/tcp comment "SMTP submission"
    ufw allow out 465/tcp comment "SMTPS"
    
    # Allow outbound DNS
    ufw allow out 53/udp comment "DNS outbound"
    ufw allow out 53/tcp comment "DNS TCP outbound"
    
    # Allow outbound NTP
    ufw allow out 123/udp comment "NTP outbound"
    
    # Allow outbound HTTP/HTTPS for updates and external APIs
    ufw allow out 80/tcp comment "HTTP outbound"
    ufw allow out 443/tcp comment "HTTPS outbound"
}

apply_security_hardening() {
    log_info "Applying security hardening rules..."
    
    # Drop invalid packets
    ufw --force enable
    
    # Configure logging
    ufw logging on
    
    # Block new connections that aren't explicitly allowed
    ufw default deny incoming
    ufw default allow outgoing
    
    # Protection against SYN flood attacks (basic)
    echo "net.ipv4.tcp_syncookies = 1" >> /etc/sysctl.conf
    echo "net.ipv4.tcp_max_syn_backlog = 2048" >> /etc/sysctl.conf
    echo "net.ipv4.tcp_synack_retries = 3" >> /etc/sysctl.conf
    
    # Apply sysctl changes
    sysctl -p
    
    log_success "Security hardening applied"
}

show_firewall_status() {
    print_header
    
    echo -e "${BLUE}Firewall Status${NC}"
    echo "----------------------------------------"
    
    # Show UFW status
    ufw status verbose
    echo ""
    
    # Show listening ports
    echo -e "${BLUE}Listening Ports${NC}"
    echo "----------------------------------------"
    netstat -tulpn 2>/dev/null | grep LISTEN || ss -tulpn | grep LISTEN
    echo ""
    
    # Show recent firewall logs
    echo -e "${BLUE}Recent Firewall Activity${NC}"
    echo "----------------------------------------"
    tail -n 10 /var/log/ufw.log 2>/dev/null || echo "No UFW logs found"
}

interactive_setup() {
    print_header
    
    echo -e "${WHITE}Interactive Firewall Setup${NC}"
    echo "This will configure the firewall for your LetsGoal installation."
    echo ""
    
    # Get deployment type
    echo "What type of deployment is this?"
    echo "1) Local network only"
    echo "2) Internet-facing with domain"
    echo ""
    read -p "Enter choice (1-2): " deploy_choice
    
    case $deploy_choice in
        1)
            DEPLOYMENT_TYPE="local"
            ALLOW_APP_PORT=true
            ;;
        2)
            DEPLOYMENT_TYPE="domain"
            ALLOW_APP_PORT=false
            ;;
        *)
            log_error "Invalid choice"
            exit 1
            ;;
    esac
    
    # SSH configuration
    echo ""
    if [[ -n "${SSH_CLIENT:-}" ]]; then
        local current_ssh_ip
        current_ssh_ip=$(echo "$SSH_CLIENT" | cut -d' ' -f1)
        echo "You're connecting from: $current_ssh_ip"
        
        if confirm "Restrict SSH access to your current IP only?" "n"; then
            ADMIN_IPS=("$current_ssh_ip")
        fi
    fi
    
    # Rate limiting
    echo ""
    if confirm "Enable rate limiting (recommended)?" "y"; then
        RATE_LIMIT_ENABLED=true
    fi
    
    # Custom SSH port
    echo ""
    if confirm "Are you using a custom SSH port?" "n"; then
        read -p "Enter SSH port (default: 22): " custom_ssh_port
        SSH_PORT="${custom_ssh_port:-22}"
    fi
    
    echo ""
    echo -e "${YELLOW}Configuration Summary:${NC}"
    echo "• Deployment type: $DEPLOYMENT_TYPE"
    echo "• SSH port: $SSH_PORT"
    echo "• Admin IPs: ${ADMIN_IPS[*]:-Any}"
    echo "• Rate limiting: $RATE_LIMIT_ENABLED"
    echo "• Application port access: $ALLOW_APP_PORT"
    echo ""
    
    if ! confirm "Apply this firewall configuration?" "y"; then
        log_info "Firewall configuration cancelled"
        exit 0
    fi
}

confirm() {
    local prompt="$1"
    local default="${2:-n}"
    local response
    
    if [[ "$default" == "y" ]]; then
        prompt="$prompt [Y/n]: "
    else
        prompt="$prompt [y/N]: "
    fi
    
    read -p "$prompt" response
    response=${response:-$default}
    
    [[ "$response" =~ ^[Yy]$ ]]
}

usage() {
    echo "LetsGoal Firewall Configuration Script"
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  setup                      Interactive firewall setup"
    echo "  apply                      Apply firewall rules based on configuration"
    echo "  reset                      Reset firewall to defaults"
    echo "  status                     Show current firewall status"
    echo "  harden                     Apply additional security hardening"
    echo ""
    echo "Options:"
    echo "  --deployment TYPE          Deployment type: local or domain"
    echo "  --ssh-port PORT           SSH port (default: 22)"
    echo "  --admin-ip IP             Admin IP address (can be used multiple times)"
    echo "  --no-ssh                  Disable SSH access (dangerous!)"
    echo "  --no-http                 Disable HTTP access"
    echo "  --no-https               Disable HTTPS access"
    echo "  --app-port PORT           Application port (default: 5001)"
    echo "  --rate-limit              Enable rate limiting"
    echo "  --config FILE             Use specific configuration file"
    echo "  --help                    Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup                               # Interactive setup"
    echo "  $0 apply --deployment local            # Apply local network rules"
    echo "  $0 apply --deployment domain --rate-limit  # Apply domain rules with rate limiting"
    echo "  $0 status                              # Show firewall status"
}

main() {
    local command=""
    local config_file=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            setup|apply|reset|status|harden)
                command="$1"
                shift
                ;;
            --deployment)
                DEPLOYMENT_TYPE="$2"
                if [[ "$DEPLOYMENT_TYPE" == "local" ]]; then
                    ALLOW_APP_PORT=true
                fi
                shift 2
                ;;
            --ssh-port)
                SSH_PORT="$2"
                shift 2
                ;;
            --admin-ip)
                ADMIN_IPS+=("$2")
                shift 2
                ;;
            --no-ssh)
                ALLOW_SSH=false
                shift
                ;;
            --no-http)
                ALLOW_HTTP=false
                shift
                ;;
            --no-https)
                ALLOW_HTTPS=false
                shift
                ;;
            --app-port)
                APP_PORT="$2"
                ALLOW_APP_PORT=true
                shift 2
                ;;
            --rate-limit)
                RATE_LIMIT_ENABLED=true
                shift
                ;;
            --config)
                config_file="$2"
                shift 2
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Check prerequisites
    check_root
    check_ufw
    
    # Load configuration if available
    if [[ -z "$config_file" ]]; then
        load_config
    else
        if [[ -f "$config_file" ]]; then
            source "$config_file"
        else
            log_error "Configuration file not found: $config_file"
            exit 1
        fi
    fi
    
    # Execute command
    case "$command" in
        setup)
            interactive_setup
            reset_firewall
            configure_ssh_access
            configure_web_access
            configure_rate_limiting
            configure_application_specific
            apply_security_hardening
            ufw --force enable
            show_firewall_status
            ;;
        apply)
            if [[ -z "$DEPLOYMENT_TYPE" ]]; then
                log_error "Deployment type must be specified"
                exit 1
            fi
            reset_firewall
            configure_ssh_access
            configure_web_access
            configure_rate_limiting
            configure_application_specific
            apply_security_hardening
            ufw --force enable
            log_success "Firewall configuration applied"
            ;;
        reset)
            reset_firewall
            log_success "Firewall reset to defaults"
            ;;
        status)
            show_firewall_status
            ;;
        harden)
            apply_security_hardening
            log_success "Security hardening applied"
            ;;
        "")
            log_error "Command required"
            usage
            exit 1
            ;;
        *)
            log_error "Unknown command: $command"
            usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
#!/usr/bin/env bash
set -euo pipefail

CLUSTER="jobedin-v3"
REGION="eu-west-2"

usage() {
    echo "Usage: $0 <command> [service]"
    echo ""
    echo "Commands:"
    echo "  on [service]    Scale service to 1 task (default: all workers)"
    echo "  off [service]   Scale service to 0 tasks (default: all workers)"
    echo "  status          Show current task count for all services"
    echo ""
    echo "Services: ai-worker, job-worker, apply-worker"
    echo "Examples:"
    echo "  $0 on              # Turn on all workers"
    echo "  $0 off             # Turn off all workers"
    echo "  $0 on ai-worker    # Turn on AI worker only"
    echo "  $0 status          # Check status of all services"
}

SERVICES=("jobedin-v3-ai-worker" "jobedin-v3-job-worker" "jobedin-v3-apply-worker")
SHORT_NAMES=("ai-worker" "job-worker" "apply-worker")

resolve_service() {
    local input="$1"
    for i in "${!SHORT_NAMES[@]}"; do
        if [ "$input" = "${SHORT_NAMES[$i]}" ]; then
            echo "${SERVICES[$i]}"
            return
        fi
    done
    echo "ERROR: Unknown service '$input'. Use: ${SHORT_NAMES[*]}" >&2
    exit 1
}

scale_service() {
    local service="$1"
    local count="$2"
    local short_name
    short_name=$(echo "$service" | sed 's/jobedin-v3-//')
    echo "Scaling $short_name to $count..."
    aws ecs update-service \
        --cluster "$CLUSTER" \
        --service "$service" \
        --desired-count "$count" \
        --region "$REGION" \
        --query 'service.serviceName' \
        --output text > /dev/null
    echo "  ✓ $short_name set to $count task(s)"
}

show_status() {
    echo "ECS Service Status (cluster: $CLUSTER)"
    echo "──────────────────────────────────────"
    for i in "${!SERVICES[@]}"; do
        local service="${SERVICES[$i]}"
        local short="${SHORT_NAMES[$i]}"
        local running desired
        running=$(aws ecs describe-services \
            --cluster "$CLUSTER" \
            --services "$service" \
            --region "$REGION" \
            --query 'services[0].runningCount' \
            --output text 2>/dev/null || echo "0")
        desired=$(aws ecs describe-services \
            --cluster "$CLUSTER" \
            --services "$service" \
            --region "$REGION" \
            --query 'services[0].desiredCount' \
            --output text 2>/dev/null || echo "0")
        local status="OFF"
        if [ "$running" -gt 0 ] 2>/dev/null; then
            status="ON ($running/$desired)"
        fi
        printf "  %-15s %s\n" "$short" "$status"
    done
    echo ""
    echo "Backend API: $(aws ecs describe-services --cluster "$CLUSTER" --services jobedin-v3-backend --region "$REGION" --query 'services[0].runningCount' --output text 2>/dev/null || echo "0") task(s) running (always on)"
}

if [ $# -lt 1 ]; then
    usage
    exit 1
fi

COMMAND="$1"
SHIFT_ARG="${2:-}"

case "$COMMAND" in
    on)
        COUNT=1
        if [ -n "$SHIFT_ARG" ]; then
            svc=$(resolve_service "$SHIFT_ARG")
            scale_service "$svc" "$COUNT"
        else
            for svc in "${SERVICES[@]}"; do
                scale_service "$svc" "$COUNT"
            done
        fi
        echo ""
        echo "Done. Use '$0 status' to verify."
        ;;
    off)
        COUNT=0
        if [ -n "$SHIFT_ARG" ]; then
            svc=$(resolve_service "$SHIFT_ARG")
            scale_service "$svc" "$COUNT"
        else
            for svc in "${SERVICES[@]}"; do
                scale_service "$svc" "$COUNT"
            done
        fi
        echo ""
        echo "Done. Use '$0 status' to verify."
        ;;
    status)
        show_status
        ;;
    *)
        usage
        exit 1
        ;;
esac

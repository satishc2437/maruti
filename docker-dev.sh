#!/bin/bash

# Maruti Docker Development Helper Script
# Usage: ./docker-dev.sh [command]

COMMAND=${1:-help}

show_help() {
    echo ""
    echo -e "\033[32mMaruti Docker Development Helper\033[0m"
    echo -e "\033[32m================================\033[0m"
    echo ""
    echo -e "\033[33mAvailable commands:\033[0m"
    echo "  build      - Build the Docker image"
    echo "  start      - Start the development container"
    echo "  stop       - Stop the development container"
    echo "  restart    - Restart the development container"
    echo "  shell      - Connect to the development container shell"
    echo "  logs       - Show container logs"
    echo "  test       - Run tests in a separate container"
    echo "  clean      - Remove containers and images"
    echo "  status     - Show container status"
    echo "  help       - Show this help message"
    echo ""
    echo -e "\033[36mExamples:\033[0m"
    echo "  ./docker-dev.sh build"
    echo "  ./docker-dev.sh start"
    echo "  ./docker-dev.sh shell"
    echo ""
}

build_image() {
    echo -e "\033[32mBuilding Maruti Docker image...\033[0m"
    docker-compose build maruti-dev
    if [ $? -eq 0 ]; then
        echo -e "\033[32m✅ Image built successfully!\033[0m"
    else
        echo -e "\033[31m❌ Image build failed!\033[0m"
        exit 1
    fi
}

start_container() {
    echo -e "\033[32mStarting Maruti development container...\033[0m"
    docker-compose up -d maruti-dev
    if [ $? -eq 0 ]; then
        echo -e "\033[32m✅ Container started successfully!\033[0m"
        echo -e "\033[33mUse './docker-dev.sh shell' to connect to the container.\033[0m"
    else
        echo -e "\033[31m❌ Container start failed!\033[0m"
        exit 1
    fi
}

stop_container() {
    echo -e "\033[32mStopping Maruti development container...\033[0m"
    docker-compose down
    if [ $? -eq 0 ]; then
        echo -e "\033[32m✅ Container stopped successfully!\033[0m"
    else
        echo -e "\033[31m❌ Container stop failed!\033[0m"
        exit 1
    fi
}

restart_container() {
    echo -e "\033[32mRestarting Maruti development container...\033[0m"
    docker-compose restart maruti-dev
    if [ $? -eq 0 ]; then
        echo -e "\033[32m✅ Container restarted successfully!\033[0m"
    else
        echo -e "\033[31m❌ Container restart failed!\033[0m"
        exit 1
    fi
}

connect_shell() {
    echo -e "\033[32mConnecting to Maruti development container...\033[0m"
    docker exec -it maruti-development bash
}

show_logs() {
    echo -e "\033[32mShowing container logs...\033[0m"
    docker-compose logs -f maruti-dev
}

run_tests() {
    echo -e "\033[32mRunning tests in container...\033[0m"
    docker-compose --profile test run --rm maruti-test
}

clean_environment() {
    echo -e "\033[32mCleaning up Docker environment...\033[0m"
    docker-compose down --remove-orphans
    docker-compose rm -f
    echo -e "\033[33mRemoving images...\033[0m"
    docker image rm maruti-maruti-dev -f 2>/dev/null || true
    echo -e "\033[32m✅ Environment cleaned!\033[0m"
}

show_status() {
    echo -e "\033[32mContainer Status:\033[0m"
    docker-compose ps
    echo ""
    echo -e "\033[32mImages:\033[0m"
    docker images | grep maruti || echo "No maruti images found"
}

# Main script logic
case "${COMMAND,,}" in
    build)
        build_image
        ;;
    start)
        start_container
        ;;
    stop)
        stop_container
        ;;
    restart)
        restart_container
        ;;
    shell)
        connect_shell
        ;;
    logs)
        show_logs
        ;;
    test)
        run_tests
        ;;
    clean)
        clean_environment
        ;;
    status)
        show_status
        ;;
    help)
        show_help
        ;;
    *)
        echo -e "\033[31mUnknown command: $COMMAND\033[0m"
        show_help
        exit 1
        ;;
esac
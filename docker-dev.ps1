# Maruti Docker Development Helper Script
# Usage: .\docker-dev.ps1 [command]

param(
    [string]$Command = "help"
)

function Show-Help {
    Write-Host ""
    Write-Host "Maruti Docker Development Helper" -ForegroundColor Green
    Write-Host "================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Available commands:" -ForegroundColor Yellow
    Write-Host "  build      - Build the Docker image"
    Write-Host "  start      - Start the development container"
    Write-Host "  stop       - Stop the development container"
    Write-Host "  restart    - Restart the development container"
    Write-Host "  shell      - Connect to the development container shell"
    Write-Host "  logs       - Show container logs"
    Write-Host "  test       - Run tests in a separate container"
    Write-Host "  clean      - Remove containers and images"
    Write-Host "  status     - Show container status"
    Write-Host "  help       - Show this help message"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Cyan
    Write-Host "  .\docker-dev.ps1 build"
    Write-Host "  .\docker-dev.ps1 start"
    Write-Host "  .\docker-dev.ps1 shell"
    Write-Host ""
}

function Build-Image {
    Write-Host "Building Maruti Docker image..." -ForegroundColor Green
    docker-compose build maruti-dev
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Image built successfully!" -ForegroundColor Green
    } else {
        Write-Host "❌ Image build failed!" -ForegroundColor Red
        exit 1
    }
}

function Start-Container {
    Write-Host "Starting Maruti development container..." -ForegroundColor Green
    docker-compose up -d maruti-dev
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Container started successfully!" -ForegroundColor Green
        Write-Host "Use '.\docker-dev.ps1 shell' to connect to the container." -ForegroundColor Yellow
    } else {
        Write-Host "❌ Container start failed!" -ForegroundColor Red
        exit 1
    }
}

function Stop-Container {
    Write-Host "Stopping Maruti development container..." -ForegroundColor Green
    docker-compose down
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Container stopped successfully!" -ForegroundColor Green
    } else {
        Write-Host "❌ Container stop failed!" -ForegroundColor Red
        exit 1
    }
}

function Restart-Container {
    Write-Host "Restarting Maruti development container..." -ForegroundColor Green
    docker-compose restart maruti-dev
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Container restarted successfully!" -ForegroundColor Green
    } else {
        Write-Host "❌ Container restart failed!" -ForegroundColor Red
        exit 1
    }
}

function Connect-Shell {
    Write-Host "Connecting to Maruti development container..." -ForegroundColor Green
    docker exec -it maruti-development bash
}

function Show-Logs {
    Write-Host "Showing container logs..." -ForegroundColor Green
    docker-compose logs -f maruti-dev
}

function Run-Tests {
    Write-Host "Running tests in container..." -ForegroundColor Green
    docker-compose --profile test run --rm maruti-test
}

function Clean-Environment {
    Write-Host "Cleaning up Docker environment..." -ForegroundColor Green
    docker-compose down --remove-orphans
    docker-compose rm -f
    Write-Host "Removing images..." -ForegroundColor Yellow
    docker image rm maruti-maruti-dev -f 2>$null
    Write-Host "✅ Environment cleaned!" -ForegroundColor Green
}

function Show-Status {
    Write-Host "Container Status:" -ForegroundColor Green
    docker-compose ps
    Write-Host ""
    Write-Host "Images:" -ForegroundColor Green
    docker images | Select-String "maruti"
}

# Main script logic
switch ($Command.ToLower()) {
    "build" { Build-Image }
    "start" { Start-Container }
    "stop" { Stop-Container }
    "restart" { Restart-Container }
    "shell" { Connect-Shell }
    "logs" { Show-Logs }
    "test" { Run-Tests }
    "clean" { Clean-Environment }
    "status" { Show-Status }
    "help" { Show-Help }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Show-Help
        exit 1
    }
}
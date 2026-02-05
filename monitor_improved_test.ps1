# Monitor improved CrewAI workflow test
# Usage: .\monitor_improved_test.ps1

$baseName = "failed_ingredients_retest_improved"

Write-Host "`n=== IMPROVED CREWAI WORKFLOW - MONITORING ===" -ForegroundColor Cyan
Write-Host ""

# Find the most recent log file
$logFiles = Get-ChildItem "${baseName}*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
if ($logFiles) {
    $latestLog = $logFiles[0]
    Write-Host "Log file: $($latestLog.Name)" -ForegroundColor Green
    Write-Host "Last modified: $($latestLog.LastWriteTime)" -ForegroundColor Gray
    
    $logContent = Get-Content $latestLog.FullName -ErrorAction SilentlyContinue
    
    # Check progress
    $progressMatch = $logContent | Select-String -Pattern "\[(\d+)/39\]" | Select-Object -Last 1
    if ($progressMatch) {
        $current = $progressMatch.Matches.Groups[1].Value
        $percent = [math]::Round([int]$current / 39 * 100, 1)
        Write-Host "`nProgress: $current/39 ingredients ($percent%)" -ForegroundColor Yellow
    }
    
    # Check for key ingredients
    Write-Host "`n=== KEY INGREDIENTS STATUS ===" -ForegroundColor Cyan
    $keyIngredients = @(
        @{name="tzatziki"; expected="Tzatziki dip"},
        @{name="guacamole"; expected="Guacamole, NFS"},
        @{name="chutney"; expected="Chutney"},
        @{name="brandy"; expected="Brandy"},
        @{name="kosher salt"; expected="Salt, table"},
        @{name="smoked paprika"; expected="Spices, paprika"},
        @{name="cinnamon sticks"; expected="Spices, cinnamon, ground"},
        @{name="sea salt"; expected="Salt, table"},
        @{name="low-moisture mozzarella"; expected="Cheese, mozzarella, low moisture"}
    )
    
    foreach ($ing in $keyIngredients) {
        $ingName = $ing.name
        $pattern = "Processing: $ingName"
        $matches = $logContent | Select-String -Pattern $pattern -Context 0,30
        
        if ($matches) {
            $context = $matches[0].Context.PostContext
            $semantic = $context | Select-String -Pattern "semantic score: (\d+\.\d+)%"
            $nutrition = $context | Select-String -Pattern "nutritional similarity: (\d+\.\d+)%"
            $success = $context | Select-String -Pattern "\[SUCCESS\]|NO_MAPPING_FOUND"
            $description = $context | Select-String -Pattern "Found:|Best.*match:" | Select-Object -First 1
            
            Write-Host "`n$ingName :" -ForegroundColor White
            if ($description) {
                Write-Host "  Matched: $($description.Line.Trim())" -ForegroundColor Green
            }
            if ($semantic) {
                $score = [float]$semantic.Matches.Groups[1].Value
                $color = if ($score -ge 90) { "Green" } elseif ($score -ge 65) { "Yellow" } else { "Red" }
                Write-Host "  Semantic Score: $score%" -ForegroundColor $color
            }
            if ($nutrition) {
                $score = [float]$nutrition.Matches.Groups[1].Value
                Write-Host "  Nutritional Score: $score%" -ForegroundColor Cyan
            }
            if ($success) {
                $status = $success.Line.Trim()
                if ($status -match "SUCCESS") {
                    Write-Host "  Status: SUCCESS" -ForegroundColor Green
                } else {
                    Write-Host "  Status: FAILED" -ForegroundColor Red
                }
            } else {
                Write-Host "  Status: Processing..." -ForegroundColor Yellow
            }
        }
    }
    
    # Summary
    Write-Host "`n=== SUMMARY ===" -ForegroundColor Cyan
    $successCount = ($logContent | Select-String -Pattern "\[SUCCESS\]").Count
    $failedCount = ($logContent | Select-String -Pattern "NO_MAPPING_FOUND").Count
    Write-Host "Successful: $successCount" -ForegroundColor Green
    Write-Host "Failed: $failedCount" -ForegroundColor Red
    
    # Check if completed
    if ($logContent | Select-String -Pattern "PROCESSING SUMMARY") {
        Write-Host "`nStatus: COMPLETED" -ForegroundColor Green
        $summary = $logContent | Select-String -Pattern "Total processed:|Successful:|Failed/Not found:" | ForEach-Object { $_.Line }
        Write-Host $summary
    } else {
        Write-Host "`nStatus: RUNNING" -ForegroundColor Yellow
    }
    
} else {
    Write-Host "No log files found" -ForegroundColor Red
}

Write-Host "`n=== END ===" -ForegroundColor Cyan
Write-Host ""

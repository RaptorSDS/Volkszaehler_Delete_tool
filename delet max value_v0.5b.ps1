function Get-JsonData {
    param ([string]$url)
    try {
        return Invoke-RestMethod -Uri $url -Method Get
    } catch {
        Write-Host "Failed to fetch JSON data: $_" -ForegroundColor Red
        return $null
    }
}

function Remove-DataEntry {
    param ([string]$url)
    try {
        Invoke-RestMethod -Uri $url -Method Get | Out-Null
        return $true
    } catch {
        Write-Host "Delete operation failed: $_" -ForegroundColor Red
        return $false
    }
}

function Test-ValidIPorDomain {
    param ([string]$value)
    $ipRegex = "^\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b$"
    $domainRegex = "^(?:(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,6}$"
    return ($value -match $ipRegex -or $value -match $domainRegex)
}

function Test-ValidUUID {
    param ([string]$value)
    $uuidRegex = '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
    return ($value -match $uuidRegex)
}

function ConvertTo-UnixTimestamp {
    param ([string]$dateTime)
    try {
        $dateTimeObject = [DateTime]::ParseExact($dateTime, "dd.MM.yyyy HH:mm", [System.Globalization.CultureInfo]::InvariantCulture)
        $unixTimestamp = $dateTimeObject.ToUniversalTime().Subtract((Get-Date "1970-01-01")).TotalMilliseconds
        return [math]::Round($unixTimestamp)
    } catch {
        Write-Host "Invalid date format. Please use dd.MM.yyyy HH:mm format." -ForegroundColor Red
        return $null
    }
}

function Test-ValidDecimal {
    param ([string]$value)
    return $value -match '^\d+\.\d{2}$'
}

function Process-DataDeletion {
    param (
        [string]$serverAddress,
        [string]$uuid,
        [long]$startTime,
        [long]$endTime,
        [decimal]$maxValue
    )

    $baseUrl = "http://$serverAddress/data/$uuid.json?from=$startTime&to=$endTime"
    $rowCount = 0
    $continueProcessing = $true

    Write-Host "Starting data deletion process..." -ForegroundColor Cyan
    
    while ($continueProcessing) {
        $jsonData = Get-JsonData -url $baseUrl
        
        if ($null -eq $jsonData -or $null -eq $jsonData.data -or $null -eq $jsonData.data.max) {
            Write-Host "No more data to process or invalid response." -ForegroundColor Yellow
            break
        }
        
        $currentMaxValue = $jsonData.data.max[1]
        $timestamp = $jsonData.data.max[0]

        if ($currentMaxValue -gt $maxValue) {
            Write-Host "Found value exceeding threshold: [$timestamp, $currentMaxValue]" -ForegroundColor Yellow
            $deleteUrl = "http://$serverAddress/data/$uuid.json?operation=delete&ts=$timestamp"
            
            if (Remove-DataEntry -url $deleteUrl) {
                Write-Host "Successfully deleted entry with timestamp $timestamp" -ForegroundColor Green
                $rowCount++
            } else {
                Write-Host "Failed to delete entry. Stopping process." -ForegroundColor Red
                $continueProcessing = $false
            }
            
            # Brief pause to avoid overwhelming the server
            Start-Sleep -Milliseconds 500
        } else {
            Write-Host "Max value ($currentMaxValue) is not higher than threshold ($maxValue)" -ForegroundColor Green
            $continueProcessing = $false
        }
    }
    
    Write-Host "Total entries deleted: $rowCount" -ForegroundColor Cyan
    return $rowCount
}

function Start-DataCleanup {
    Clear-Host
    Write-Host "=== Database Value Cleanup Tool ===" -ForegroundColor Cyan
    
    # Get server address
    $serverAddress = ""
    do {
        $serverAddress = Read-Host "Enter Server Address (IP or domain without http:// or https://)"
        $serverAddress = $serverAddress.TrimEnd('/')
        
        if (-not (Test-ValidIPorDomain $serverAddress)) {
            Write-Host "Invalid server address format. Please try again." -ForegroundColor Red
        }
    } while (-not (Test-ValidIPorDomain $serverAddress))

    # Get UUID
    $uuid = ""
    do {
        $uuid = Read-Host "Enter UUID (format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)"
        
        if (-not (Test-ValidUUID $uuid)) {
            Write-Host "Invalid UUID format. Please try again." -ForegroundColor Red
        }
    } while (-not (Test-ValidUUID $uuid))

    # Get start timestamp
    $startTimeInput = Read-Host "Enter Start Time (UNIX timestamp in ms or date in format dd.MM.yyyy HH:mm)"
    if ($startTimeInput -match '^\d+$') {
        $startTime = [long]$startTimeInput
    } else {
        $startTime = ConvertTo-UnixTimestamp $startTimeInput
        if ($null -eq $startTime) {
            return
        }
    }

    # Get end timestamp
    $endTimeInput = Read-Host "Enter End Time (UNIX timestamp in ms or date in format dd.MM.yyyy HH:mm)"
    if ($endTimeInput -match '^\d+$') {
        $endTime = [long]$endTimeInput
    } else {
        $endTime = ConvertTo-UnixTimestamp $endTimeInput
        if ($null -eq $endTime) {
            return
        }
    }

    # Get max value threshold
    $maxValueStr = ""
    do {
        $maxValueStr = Read-Host "Enter Max Value Threshold (format: xxx.xx)"
        
        if (-not (Test-ValidDecimal $maxValueStr)) {
            Write-Host "Invalid decimal format. Please use xxx.xx format." -ForegroundColor Red
        }
    } while (-not (Test-ValidDecimal $maxValueStr))
    $maxValue = [decimal]$maxValueStr

    # Process data deletion
    $deletedCount = Process-DataDeletion -serverAddress $serverAddress -uuid $uuid -startTime $startTime -endTime $endTime -maxValue $maxValue

    Write-Host "`nOperation completed. $deletedCount entries were deleted." -ForegroundColor Cyan
    Read-Host "Press Enter to exit..."
}

# Start the script
Start-DataCleanup

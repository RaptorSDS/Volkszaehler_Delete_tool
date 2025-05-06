function Get-JsonData {
    param ($url)
    try {
        $response = Invoke-RestMethod -Uri $url -Method Get
        return $response
    } catch {
        Write-Host "Failed to fetch JSON data: $_"
    }
}

function Delete-Data {
    param ($url)
    try {
        $response = Invoke-RestMethod -Uri $url -Method Get
        return $true
    } catch {
        return $false
    }
}

function IsValidIPorDomain {
    param ($value)
    $ipRegex = "\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"
    $domainRegex = "^(?:(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,6}$"
    if ($value -match $ipRegex -or $value -match $domainRegex) {
        return $true
    } else {
        return $false
    }
}

function IsValidUUID {
    param ($value)
    $uuidRegex = '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
    if ($value -match $uuidRegex) {
        return $true
    } else {
        return $false
    }
}

function ConvertToUnixTimestamp {
    param ($dateTime)
    try {
        $dateTimeObject = [DateTime]::ParseExact($dateTime, "dd.MM.yyyy HH:mm", $null)
        $unixTimestamp = $dateTimeObject.ToUniversalTime().Subtract((Get-Date "1970-01-01")).TotalMilliseconds
        return [math]::Round($unixTimestamp)
    } catch {
        Write-Host "Invalid date format. Please use dd.MM.yyyy HH:mm format."
        return $null
    }
}

function IsValidDecimal {
    param ($value)
    return $value -match '^\d+\.\d{2}$'
}


function Main {
    $V1 = ""
    do {
        $V1 = Read-Host "Enter Server Address (IP or URL/domain without http:// or https://)"
        if ($V1.EndsWith('/')) {
            Write-Host "Server Address should not end with '/'. Please try again."
        }
    } while (-not (IsValidIPorDomain $V1) -or $V1.EndsWith('/'))

    $V2 = ""
    do {
        $V2 = Read-Host "Enter UUID (e.g., xxxxxxxx-xxxx-xxxx-xxxxxxxxxxxx)"
    } while (-not (IsValidUUID $V2))

    $V3 = Read-Host "Enter TimeStamp Start (UNIX timestamp in ms or date in format dd.MM.yyyy HH:mm)"
    $V4 = Read-Host "Enter TimeStamp End (UNIX timestamp in ms or date in format dd.MM.yyyy HH:mm)"
    $V5 = ""
    do {
        $V5 = Read-Host "Enter Max Value (xxx.xx format)"
    } while (-not (IsValidDecimal $V5))

    # Convert date strings to UNIX timestamps
    if ($V3 -match '^\d+$') {
        # Check if it's already a UNIX timestamp (numeric)
        $V3 = [long]$V3
    } else {
        # Convert date to UNIX timestamp
        $V3 = ConvertToUnixTimestamp $V3
        if ($V3 -eq $null) {
            return
        }
    }

    if ($V4 -match '^\d+$') {
        # Check if it's already a UNIX timestamp (numeric)
        $V4 = [long]$V4
    } else {
        # Convert date to UNIX timestamp
        $V4 = ConvertToUnixTimestamp $V4
        if ($V4 -eq $null) {
            return
        }
    }

    $baseUrl = "http://$V1/data/$V2.json?from=$V3&to=$V4"
    $rowCount = 0

    while ($true) {
        $jsonData = Get-JsonData -url $baseUrl
        $maxValue = $jsonData.data.max[1]
        $timestamp = $jsonData.data.max[0]

        if ($maxValue -gt $V5) {
            Write-Host "Max value is higher than $V5 : [$timestamp, $maxValue]"
            $deleteUrl = "http://$V1/data/$V2.json?operation=delete&ts=$timestamp"
            if (Delete-Data -url $deleteUrl) {
                Write-Host "Data with timestamp $timestamp deleted."
                $rowCount++
            } else {
                Write-Host "Failed to delete data with timestamp $timestamp."
            }
        } else {
            Write-Host "Max value is not higher than $V5 : [$timestamp, $maxValue]"
            break
        }

        Start-Sleep -Seconds 1
    }
    Write-Host "Total rows deleted: $rowCount"
    Read-Host "Press Enter to continue..."
}

Main
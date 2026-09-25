Set-Location $PSScriptRoot
$proc = Start-Process -FilePath "$PSScriptRoot\sendenv\Scripts\pythonw.exe" `
    -ArgumentList "schedule_service.py" `
    -WorkingDirectory $PSScriptRoot `
    -WindowStyle Hidden `
    -PassThru
Write-Host "schedule_service.py started in the background (PID $($proc.Id)). Logs: schedule_service.log"
Write-Host "To stop it: Stop-Process -Id $($proc.Id)"

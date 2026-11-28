$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;

public static class RecipeAppWindow {
    private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindowsProc callback, IntPtr lParam);

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);

    public static bool IsOpen(uint targetProcessId, string expectedTitle) {
        bool found = false;
        EnumWindows((hWnd, lParam) => {
            uint processId;
            GetWindowThreadProcessId(hWnd, out processId);
            if (processId == targetProcessId && IsWindowVisible(hWnd)) {
                var title = new StringBuilder(512);
                GetWindowText(hWnd, title, title.Capacity);
                if (String.Equals(title.ToString(), expectedTitle, StringComparison.Ordinal)) {
                    found = true;
                    return false;
                }
            }
            return true;
        }, IntPtr.Zero);
        return found;
    }
}
'@

function Show-Error($message) {
    [System.Windows.Forms.MessageBox]::Show(
        $message,
        "宿舍食譜助手",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    ) | Out-Null
}

function Request-ApiKey {
    $form = New-Object System.Windows.Forms.Form
    $form.Text = "宿舍食譜助手"
    $form.Width = 430
    $form.Height = 150
    $form.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen
    $form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedDialog
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false

    $label = New-Object System.Windows.Forms.Label
    $label.Text = "請輸入 Gemini API 金鑰（不會保存到檔案）："
    $label.AutoSize = $true
    $label.Location = [System.Drawing.Point]::new(14, 14)

    $textBox = New-Object System.Windows.Forms.TextBox
    $textBox.Width = 385
    $textBox.UseSystemPasswordChar = $true
    $textBox.Location = [System.Drawing.Point]::new(14, 40)

    $okButton = New-Object System.Windows.Forms.Button
    $okButton.Text = "啟動"
    $okButton.DialogResult = [System.Windows.Forms.DialogResult]::OK
    $okButton.Location = [System.Drawing.Point]::new(238, 76)

    $cancelButton = New-Object System.Windows.Forms.Button
    $cancelButton.Text = "取消"
    $cancelButton.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
    $cancelButton.Location = [System.Drawing.Point]::new(324, 76)

    $form.Controls.AddRange(@($label, $textBox, $okButton, $cancelButton))
    $form.AcceptButton = $okButton
    $form.CancelButton = $cancelButton

    try {
        if ($form.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
            return $textBox.Text.Trim()
        }
        return $null
    } finally {
        $form.Dispose()
    }
}

$serverProcess = $null
$browserProcess = $null
$edgeProfile = $null
$stdoutLog = $null
$stderrLog = $null
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"
$url = "http://127.0.0.1:8501"
$runId = [Guid]::NewGuid().ToString("N")
$stdoutLog = Join-Path $env:TEMP "recipe-app-$runId.out.log"
$stderrLog = Join-Path $env:TEMP "recipe-app-$runId.err.log"

try {
    if (-not $env:GEMINI_API_KEY) {
        $env:GEMINI_API_KEY = Request-ApiKey
        if (-not $env:GEMINI_API_KEY) {
            exit 0
        }
    }

    if (-not (Test-Path -LiteralPath $python)) {
        $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($launcher) {
            & $launcher.Source -m venv (Join-Path $root ".venv")
        } else {
            $launcher = Get-Command python.exe -ErrorAction SilentlyContinue
            if (-not $launcher) {
                throw "找不到 Python，請先安裝 Python 3。"
            }
            & $launcher.Source -m venv (Join-Path $root ".venv")
        }
        if ($LASTEXITCODE -ne 0) {
            throw "建立 Python 虛擬環境失敗。"
        }
    }

    & $python -c "import streamlit, google.genai" 2>$null
    if ($LASTEXITCODE -ne 0) {
        $installOutput = & $python -m pip install -r (Join-Path $root "requirements.txt") 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) {
            throw "安裝套件失敗。`r`n$installOutput"
        }
    }

    $edgePaths = @(
        (Join-Path ${env:ProgramFiles(x86)} "Microsoft\Edge\Application\msedge.exe"),
        (Join-Path $env:ProgramFiles "Microsoft\Edge\Application\msedge.exe")
    )
    $edgePath = $edgePaths | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $edgePath) {
        $edgeCommand = Get-Command msedge.exe -ErrorAction SilentlyContinue
        if ($edgeCommand) {
            $edgePath = $edgeCommand.Source
        } else {
            throw "找不到 Microsoft Edge。"
        }
    }

    $portCheck = [System.Net.Sockets.TcpListener]::new(
        [System.Net.IPAddress]::Loopback,
        8501
    )
    try {
        $portCheck.Start()
    } finally {
        $portCheck.Stop()
    }

    $edgeProfile = Join-Path $env:TEMP "recipe-app-edge-$runId"
    $serverProcess = Start-Process `
        -FilePath $python `
        -ArgumentList @(
            "-m streamlit run app.py",
            "--server.headless=true",
            "--server.port=8501",
            "--browser.gatherUsageStats=false"
        ) `
        -WorkingDirectory $root `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -PassThru

    $ready = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        if ($serverProcess.HasExited) {
            throw "Streamlit 啟動失敗。"
        }
        try {
            $response = Invoke-WebRequest `
                -Uri "$url/_stcore/health" `
                -TimeoutSec 1 `
                -UseBasicParsing `
                -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    if (-not $ready) {
        throw "App 未能在限定時間內啟動。"
    }

    $browserArguments = "--app=$url --user-data-dir=`"$edgeProfile`" --no-first-run --no-default-browser-check --disable-background-mode"
    $browserProcess = Start-Process `
        -FilePath $edgePath `
        -ArgumentList $browserArguments `
        -PassThru

    $appTitle = "宿舍食譜助手"
    $appWindowReady = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        if ($browserProcess.HasExited) {
            throw "Edge App 視窗啟動失敗。"
        }
        if ([RecipeAppWindow]::IsOpen([uint32]$browserProcess.Id, $appTitle)) {
            $appWindowReady = $true
            break
        }
        Start-Sleep -Milliseconds 500
    }
    if (-not $appWindowReady) {
        throw "Edge App 視窗未能在限定時間內開啓。"
    }

    while ([RecipeAppWindow]::IsOpen([uint32]$browserProcess.Id, $appTitle)) {
        Start-Sleep -Milliseconds 500
    }
} catch {
    $message = $_.Exception.Message
    $logContents = @()
    if (Test-Path -LiteralPath $stdoutLog) {
        $logContents += Get-Content -LiteralPath $stdoutLog -Tail 30
    }
    if (Test-Path -LiteralPath $stderrLog) {
        $logContents += Get-Content -LiteralPath $stderrLog -Tail 30
    }
    if ($logContents.Count -gt 0) {
        $message += "`r`n`r`n" + ($logContents -join "`r`n")
    }
    Show-Error $message
} finally {
    if ($browserProcess -and -not $browserProcess.HasExited) {
        Stop-Process -Id $browserProcess.Id -Force -ErrorAction SilentlyContinue
    }
    if ($serverProcess -and -not $serverProcess.HasExited) {
        Stop-Process -Id $serverProcess.Id -Force
    }
    if ($edgeProfile -and (Test-Path -LiteralPath $edgeProfile)) {
        Remove-Item -LiteralPath $edgeProfile -Recurse -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $stdoutLog, $stderrLog -Force -ErrorAction SilentlyContinue
}

<#
.SYNOPSIS
    Authenticates SimplySign Desktop with TOTP to mount the cloud code signing certificate.
.DESCRIPTION
    Used in CI to automate Certum SimplySign authentication. Generates TOTP from
    otpauth:// URI, launches SimplySign Desktop, sends credentials via SendKeys, and verifies
    the certificate appears in the Current User store.
.PARAMETER OtpUri
    Full otpauth://totp/... URI (or set CERTUM_OTP_URI env var)
.PARAMETER Thumbprint
    SHA-1 thumbprint of the certificate (or set CERTUM_THUMBPRINT env var)
.PARAMETER Email
    SimplySign login email (or set CERTUM_EMAIL env var). Required if form has email field.
.PARAMETER ExePath
    Path to SimplySignDesktop.exe (default: auto-detect)
#>

param(
    [string]$OtpUri = $env:CERTUM_OTP_URI,
    [string]$Thumbprint = $env:CERTUM_THUMBPRINT,
    [string]$Email = $env:CERTUM_EMAIL,
    [string]$ExePath = ""
)

$ErrorActionPreference = "Stop"

if (-not $OtpUri) { throw "CERTUM_OTP_URI (or -OtpUri) is required." }
if (-not $Thumbprint) { throw "CERTUM_THUMBPRINT (or -Thumbprint) is required." }

# ── Resolve SimplySign exe ────────────────────────────────────────────────
$candidates = @(
    $ExePath,
    "C:\Program Files\Certum\SimplySign Desktop\SimplySignDesktop.exe",
    "C:\Program Files (x86)\Certum\SimplySign Desktop\SimplySignDesktop.exe"
)
$ExePath = ""
foreach ($p in $candidates) {
    if ($p -and (Test-Path $p)) { $ExePath = $p; break }
}
if (-not $ExePath) {
    $found = Get-ChildItem -Path "C:\Program Files\Certum","C:\Program Files (x86)\Certum" -Filter "SimplySignDesktop.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) { $ExePath = $found.FullName }
}
if (-not $ExePath) { throw "SimplySign Desktop not found. Install it on the runner machine." }
Write-Host "Using SimplySign at: $ExePath"

# ── Check if cert already mounted (skip auth if so) ───────────────────────────
$thumbprintUpper = $Thumbprint.ToUpperInvariant().Replace(' ', '')
$existingCert = Get-ChildItem Cert:\CurrentUser\My -ErrorAction SilentlyContinue |
    Where-Object { $_.Thumbprint -eq $thumbprintUpper }
if ($existingCert) {
    Write-Host "Certificate already mounted: $($existingCert.Subject)"
    exit 0
}

# ── Parse otpauth URI ───────────────────────────────────────────────────────
$uri = [Uri]$OtpUri
try {
    $q = [System.Web.HttpUtility]::ParseQueryString($uri.Query)
} catch {
    $q = @{}
    foreach ($part in $uri.Query.TrimStart('?') -split '&') {
        $kv = $part -split '=', 2
        if ($kv.Count -eq 2) { $q[$kv[0]] = [Uri]::UnescapeDataString($kv[1]) }
    }
}

$Base32 = $q['secret']
if ($q['digits']) { $Digits = [int]$q['digits'] } else { $Digits = 6 }
if ($q['period']) { $Period = [int]$q['period'] } else { $Period = 30 }
if ($q['algorithm']) { $Algorithm = $q['algorithm'].ToUpper() } else { $Algorithm = 'SHA1' }

if (-not $Base32) { throw "Could not parse 'secret' from otpauth URI." }
if ($Algorithm -notin 'SHA1','SHA256','SHA512') { throw "Unsupported algorithm: $Algorithm." }

# ── TOTP generator (RFC 6238) ───────────────────────────────────────────────
Add-Type -Language CSharp @"
using System;
using System.Security.Cryptography;

public static class Totp
{
    private const string B32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

    private static byte[] Base32Decode(string s)
    {
        s = s.TrimEnd('=').ToUpperInvariant();
        int byteCount = s.Length * 5 / 8;
        byte[] bytes = new byte[byteCount];
        int bitBuffer = 0, bitsLeft = 0, idx = 0;
        foreach (char c in s)
        {
            int val = B32.IndexOf(c);
            if (val < 0) throw new ArgumentException("Invalid Base32 char: " + c);
            bitBuffer = (bitBuffer << 5) | val;
            bitsLeft += 5;
            if (bitsLeft >= 8)
            {
                bytes[idx++] = (byte)(bitBuffer >> (bitsLeft - 8));
                bitsLeft -= 8;
            }
        }
        return bytes;
    }

    public static string Now(string secret, int digits, int period, string algorithm)
    {
        byte[] key = Base32Decode(secret);
        long counter = DateTimeOffset.UtcNow.ToUnixTimeSeconds() / period;
        byte[] cnt = BitConverter.GetBytes(counter);
        if (BitConverter.IsLittleEndian) Array.Reverse(cnt);
        byte[] hash;
        switch (algorithm.ToUpperInvariant())
        {
            case "SHA256": hash = new HMACSHA256(key).ComputeHash(cnt); break;
            case "SHA512": hash = new HMACSHA512(key).ComputeHash(cnt); break;
            default: hash = new HMACSHA1(key).ComputeHash(cnt); break;
        }
        int offset = hash[hash.Length - 1] & 0x0F;
        int binary =
            ((hash[offset] & 0x7F) << 24) |
            ((hash[offset + 1] & 0xFF) << 16) |
            ((hash[offset + 2] & 0xFF) << 8) |
            (hash[offset + 3] & 0xFF);
        int otp = binary % (int)Math.Pow(10, digits);
        return otp.ToString(new string('0', digits));
    }
}
"@

$otp = [Totp]::Now($Base32, $Digits, $Period, $Algorithm)
Write-Host "Generated TOTP."

# ── Ensure SimplySign shows login window ────────────────────────────────────
# Stop existing SimplySign so we get a fresh login dialog (avoids tray-only state)
$existing = Get-Process -Name "SimplySignDesktop" -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Stopping existing SimplySign to force fresh login..."
    $existing | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Start SimplySign
Start-Process -FilePath $ExePath
Write-Host "Waiting for SimplySign login window (up to 45 seconds)..."

# ── Find and activate the login window ───────────────────────────────────────
$wshell = New-Object -ComObject WScript.Shell
$focused = $false
$discoveredTitle = $null

# Strategy 1: Discover window title from SimplySignDesktop process
for ($i = 0; $i -lt 45; $i++) {
    Start-Sleep -Seconds 1
    $procs = Get-Process -Name "SimplySignDesktop" -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowTitle }
    foreach ($p in $procs) {
        $title = $p.MainWindowTitle.Trim()
        if ($title) {
            $discoveredTitle = $title
            if ($wshell.AppActivate($title)) {
                $focused = $true
                Write-Host "Activated window: $title"
                break
            }
        }
    }
    if ($focused) { break }

    # Strategy 2: Try known/partial titles (AppActivate does substring match)
    $knownTitles = @('SimplySign', 'Certum', 'Sign in', 'Login', 'Token', 'OTP')
    foreach ($t in $knownTitles) {
        if ($wshell.AppActivate($t)) {
            $focused = $true
            Write-Host "Activated window matching: $t"
            break
        }
    }
    if ($focused) { break }
}

if (-not $focused) {
    Write-Host "Visible windows (for debugging):"
    Get-Process | Where-Object { $_.MainWindowTitle } |
        ForEach-Object { Write-Host "  - [$($_.ProcessName)] $($_.MainWindowTitle)" }
    throw "Could not activate SimplySign. Ensure runner uses run.cmd (not service) and SimplySign shows a login window."
}

# ── Send credentials ─────────────────────────────────────────────────────────
Start-Sleep -Milliseconds 800

# Escape SendKeys special chars: + ^ % ~ ( ) [ ] { }
# See https://learn.microsoft.com/en-us/office/vba/language/reference/user-interface-help/sendkeys-statement
function Escape-SendKeys {
    param([string]$s)
    if (-not $s) { return $s }
    $s = $s -replace '\+', '{+}' -replace '\^', '{^}' -replace '%', '{%}' -replace '~', '{~}'
    $s = $s -replace '\)', '{)}' -replace '\(', '{(}' -replace '\]', '{]}' -replace '\[', '{[}'
    $s = $s -replace '\}', '}}' -replace '\{', '{{'  # braces last, } before {
    $s
}

if ($Email) {
    $emailEscaped = Escape-SendKeys $Email
    # Send email, TAB to token field, OTP, ENTER. Add small delays via separate SendKeys.
    $wshell.SendKeys($emailEscaped)
    Start-Sleep -Milliseconds 300
    $wshell.SendKeys("{TAB}")
    Start-Sleep -Milliseconds 300
    $wshell.SendKeys($otp)
    Start-Sleep -Milliseconds 200
    $wshell.SendKeys("{ENTER}")
} else {
    $wshell.SendKeys($otp)
    Start-Sleep -Milliseconds 200
    $wshell.SendKeys("{ENTER}")
}

Write-Host "Credentials sent. Waiting for certificate to mount..."

# ── Verify certificate appears (with retry) ───────────────────────────────────
for ($attempt = 1; $attempt -le 2; $attempt++) {
    for ($i = 0; $i -lt 40; $i++) {
        $cert = Get-ChildItem Cert:\CurrentUser\My -ErrorAction SilentlyContinue |
            Where-Object { $_.Thumbprint -eq $thumbprintUpper }
        if ($cert) {
            Write-Host "Certificate found: $($cert.Subject)"
            exit 0
        }
        Start-Sleep -Seconds 2
    }

    if ($attempt -eq 1) {
        Write-Host "Certificate not found yet. Retrying credential send..."
        $reactivated = $false
        if ($discoveredTitle) {
            $reactivated = $wshell.AppActivate($discoveredTitle)
        }
        if (-not $reactivated) {
            foreach ($t in @('SimplySign', 'Certum', 'Sign in', 'Login')) {
                if ($wshell.AppActivate($t)) { $reactivated = $true; break }
            }
        }
        if ($reactivated) {
            Start-Sleep -Milliseconds 500
            if ($Email) {
                $wshell.SendKeys((Escape-SendKeys $Email) + "{TAB}$otp{ENTER}")
            } else {
                $wshell.SendKeys("$otp{ENTER}")
            }
            Start-Sleep -Seconds 3
        }
    }
}

throw "Certificate with thumbprint $Thumbprint not found after 2 attempts. Check CERTUM_EMAIL matches your SimplySign login."

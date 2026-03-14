<#
.SYNOPSIS
    Authenticates SimplySign Desktop with TOTP to mount the cloud code signing certificate.
.DESCRIPTION
    Used in CI to automate Certum SimplySign authentication. Generates TOTP from
    otpauth:// URI, launches SimplySign Desktop, sends OTP via SendKeys, and verifies
    the certificate appears in the Current User store.
.PARAMETER OtpUri
    Full otpauth://totp/... URI (or set CERTUM_OTP_URI env var)
.PARAMETER Thumbprint
    SHA-1 thumbprint of the certificate (or set CERTUM_THUMBPRINT env var)
.PARAMETER ExePath
    Path to SimplySignDesktop.exe (default: standard install path)
#>

param(
    [string]$OtpUri = $env:CERTUM_OTP_URI,
    [string]$Thumbprint = $env:CERTUM_THUMBPRINT,
    [string]$ExePath = ""
)

$ErrorActionPreference = "Stop"

if (-not $OtpUri) { throw "CERTUM_OTP_URI (or -OtpUri) is required." }
if (-not $Thumbprint) { throw "CERTUM_THUMBPRINT (or -Thumbprint) is required." }

# Resolve exe path: try explicit path, then common locations, then search
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
if (-not $ExePath) { throw "SimplySign Desktop not found. Install step may have failed." }
Write-Host "Using SimplySign at: $ExePath"

# Parse otpauth:// URI
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
if ($Algorithm -notin 'SHA1','SHA256','SHA512') { throw "Unsupported algorithm: $Algorithm (use SHA1, SHA256, or SHA512)." }

# TOTP generator (RFC 6238)
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
Write-Host "Generated TOTP (current window)."

# Launch SimplySign Desktop
$proc = Start-Process -FilePath $ExePath -PassThru
Write-Host "Waiting for SimplySign Desktop window..."
Start-Sleep -Seconds 5

$wshell = New-Object -ComObject WScript.Shell
$focused = $wshell.AppActivate($proc.Id)
if (-not $focused) { $focused = $wshell.AppActivate('SimplySign Desktop') }

for ($i = 0; -not $focused -and $i -lt 10; $i++) {
    Start-Sleep -Milliseconds 500
    $focused = $wshell.AppActivate($proc.Id) -or $wshell.AppActivate('SimplySign Desktop')
}

if (-not $focused) {
    throw "Could not bring SimplySign Desktop to the foreground."
}

Start-Sleep -Milliseconds 400
$wshell.SendKeys("$otp{ENTER}")
Write-Host "OTP sent. Waiting for certificate to mount..."

# Verify certificate appears
$thumbprintUpper = $Thumbprint.ToUpperInvariant().Replace(' ', '')
for ($i = 0; $i -lt 30; $i++) {
    $cert = Get-ChildItem Cert:\CurrentUser\My -ErrorAction SilentlyContinue |
        Where-Object { $_.Thumbprint -eq $thumbprintUpper }
    if ($cert) {
        Write-Host "Certificate found: $($cert.Subject)"
        exit 0
    }
    Start-Sleep -Seconds 2
}

throw "Certificate with thumbprint $Thumbprint not found after 60 seconds."

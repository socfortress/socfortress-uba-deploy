<#
.SYNOPSIS
  Generate real UBA test activity on a lab Windows host (Wazuh agent + Sysmon installed).

.DESCRIPTION
  Everything happens on the real host, so events travel the production path
  (agent -> manager rules -> Fluent Bit -> Graylog -> indexer) with production field names.
  All test objects are prefixed "uba." / "uba-test-" and the script prints a UTC window to query.

  Phases (run in order, or pick with -Phase):
    setup      4720/4722/4738 create+enable local user; 4732 add to Administrators (rule 60154, L12);
               inventory: local_user_added, local_admin_added (syscollector interval 1m in Windows_lab)
    logons     4625 x N wrong password (60122), then 4624 type 2 + 4672 as the test user (67022, 67028)
    lockout    wrong passwords up to the lockout threshold -> 4740 (60115); skipped if no lockout policy
    processes  Sysmon 1 as the test user: discovery commands and an encoded PowerShell command
    service    7045 new auto-start service (61138); inventory: autostart_service_added (never started)
    cleanup    4733 remove from Administrators, delete service, 4726 delete user

  Not generated on purpose: 1102 (clearing the Security log destroys lab evidence), Kerberos 4768/4769/4771
  (needs a domain controller). 4648 and 4724 are generated but the stock Wazuh ruleset has no rule for
  them, so they stop at level 0 and never reach the SIEM unless
  src/socfortress_uba/integrations/wazuh/wazuh_rules/0950-uba_windows_account_rules.xml (4723/4724) is deployed.
  Results of the first run: docs/research/lab-activity-test.md.

  For a real RDP logon (4624 type 10 with a public source IP, used by geo rules), RDP in as the test
  user from your workstation after the setup phase; the password is printed once.

.EXAMPLE
  # elevated PowerShell on the lab host
  .\windows_activity.ps1                      # setup, logons, lockout, processes, service
  .\windows_activity.ps1 -Phase cleanup
#>
[CmdletBinding()]
param(
    [ValidateSet('all', 'setup', 'logons', 'lockout', 'processes', 'service', 'cleanup')]
    [string[]]$Phase = @('all'),
    [string]$User = 'uba.test1',
    [string]$ServiceName = 'uba-test-svc',
    [int]$FailedLogons = 3,
    # Wazuh rule 900003 drops a second logon by the same user within 5 s; keep steps further apart.
    [int]$GapSeconds = 8
)

$ErrorActionPreference = 'Stop'
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run from an elevated PowerShell session.'
}

$stateFile = Join-Path $env:ProgramData 'uba-test\state.json'
$started = (Get-Date).ToUniversalTime()
function Step([string]$msg) { Write-Host ("[{0:u}] {1}" -f (Get-Date).ToUniversalTime(), $msg) -ForegroundColor Cyan }
function Pause-Gap { Start-Sleep -Seconds $GapSeconds }
function Want([string]$p) { $Phase -contains 'all' -and $p -ne 'cleanup' -or $Phase -contains $p }

function New-TestPassword {
    $chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#%'.ToCharArray()
    'Uba!' + -join (1..16 | ForEach-Object { $chars | Get-Random })
}

function Get-TestCredential {
    if (-not (Test-Path $stateFile)) { throw "No state file; run -Phase setup first." }
    $pw = (Get-Content $stateFile | ConvertFrom-Json).Password
    New-Object PSCredential("$env:COMPUTERNAME\$User", (ConvertTo-SecureString $pw -AsPlainText -Force))
}

function Invoke-AsTestUser([string]$exe, [string]$arguments, [PSCredential]$cred) {
    # Secondary logon: 4648 (no Wazuh rule) + 4624 type 2 + 4672 (admin) + Sysmon 1 with user HOST\uba.test1
    Start-Process -FilePath $exe -ArgumentList $arguments -Credential $cred -WindowStyle Hidden `
        -WorkingDirectory $env:SystemRoot -Wait -LoadUserProfile:$false
}

function Invoke-FailedLogon([string]$password) {
    $bad = New-Object PSCredential("$env:COMPUTERNAME\$User", (ConvertTo-SecureString $password -AsPlainText -Force))
    try { Start-Process cmd.exe -ArgumentList '/c exit' -Credential $bad -WindowStyle Hidden -Wait } catch { }
}

if (Want 'setup') {
    $pw = New-TestPassword
    if (Get-LocalUser -Name $User -ErrorAction SilentlyContinue) {
        Step "user $User exists; resetting password (4724, no Wazuh rule) and re-enabling"
        Set-LocalUser -Name $User -Password (ConvertTo-SecureString $pw -AsPlainText -Force)
        Enable-LocalUser -Name $User
    } else {
        Step "create local user $User (4720, 4722, 4738 -> rules 60109/60110, L8)"
        New-LocalUser -Name $User -Password (ConvertTo-SecureString $pw -AsPlainText -Force) `
            -Description 'SOCFortress UBA lab test account' -PasswordNeverExpires | Out-Null
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $stateFile) | Out-Null
    @{ User = $User; Password = $pw } | ConvertTo-Json | Set-Content -Path $stateFile
    icacls (Split-Path $stateFile) /inheritance:r /grant:r 'Administrators:(OI)(CI)F' 'SYSTEM:(OI)(CI)F' | Out-Null
    Pause-Gap
    $admins = (Get-LocalGroup -SID 'S-1-5-32-544').Name
    if (-not (Get-LocalGroupMember -SID 'S-1-5-32-544' | Where-Object Name -like "*\$User")) {
        Step "add $User to $admins (4732 -> rule 60154, L12; inventory local_admin_added)"
        Add-LocalGroupMember -SID 'S-1-5-32-544' -Member $User
    }
    Write-Host "Test user password (for an optional RDP logon): $pw" -ForegroundColor Yellow
    Pause-Gap
}

if (Want 'logons') {
    $cred = Get-TestCredential
    Step "$FailedLogons failed logons for $User (4625 status 0xc000006d/0xc000006a -> rule 60122)"
    1..$FailedLogons | ForEach-Object { Invoke-FailedLogon ('Wrong' + (Get-Random)); Start-Sleep 2 }
    Pause-Gap
    Step "successful logon as $User after failures (4624 type 2 -> 67022; 4672 -> 67028)"
    Invoke-AsTestUser 'cmd.exe' '/c exit' $cred
    Pause-Gap
}

if (Want 'lockout') {
    $threshold = (net accounts | Select-String 'Lockout threshold').ToString().Split(':')[-1].Trim()
    if ($threshold -match '^\d+$' -and [int]$threshold -gt 0) {
        Step "lockout: $threshold wrong passwords (4625 x $threshold, then 4740 -> rule 60115, L9)"
        1..([int]$threshold) | ForEach-Object { Invoke-FailedLogon ('Wrong' + (Get-Random)); Start-Sleep 1 }
        Pause-Gap
        # The account stays locked until the lockout duration passes or an admin unlocks it.
        Step "unlock $User"
        $acct = [ADSI]"WinNT://$env:COMPUTERNAME/$User,user"
        $acct.IsAccountLocked = $false; $acct.SetInfo()
    } else {
        Step "lockout skipped: no account lockout threshold on this host ($threshold)"
    }
    Pause-Gap
}

if (Want 'processes') {
    $cred = Get-TestCredential
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes('Get-Date | Out-Null'))
    $commands = @(
        @('whoami.exe', '/all'),
        @('net.exe', 'localgroup administrators'),
        @('net.exe', "user $User"),
        @('ipconfig.exe', '/all'),
        @('systeminfo.exe', ''),
        @('nltest.exe', '/domain_trusts'),
        @('certutil.exe', "-encode $env:SystemRoot\win.ini $env:TEMP\uba-test.b64"),
        @('powershell.exe', "-NoProfile -EncodedCommand $encoded")
    )
    foreach ($c in $commands) {
        Step ("Sysmon 1 as {0}: {1} {2}" -f $User, $c[0], $c[1])
        Invoke-AsTestUser 'cmd.exe' ("/c {0} {1} > NUL 2>&1" -f $c[0], $c[1]) $cred
        Pause-Gap
    }
}

if (Want 'service') {
    if (-not (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue)) {
        Step "install auto-start service $ServiceName (7045 -> rule 61138; inventory autostart_service_added). Not started."
        New-Service -Name $ServiceName -DisplayName 'UBA test service' -StartupType Automatic `
            -BinaryPathName "$env:SystemRoot\System32\cmd.exe /c exit" | Out-Null
    }
    Pause-Gap
}

if ($Phase -contains 'cleanup') {
    Step "cleanup: remove $User from Administrators (4733), delete $ServiceName, delete $User (4726)"
    Remove-LocalGroupMember -SID 'S-1-5-32-544' -Member $User -ErrorAction SilentlyContinue
    if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) { sc.exe delete $ServiceName | Out-Null }
    Remove-LocalUser -Name $User -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force (Split-Path $stateFile) -ErrorAction SilentlyContinue
}

$ended = (Get-Date).ToUniversalTime()
Write-Host ("`nDone. Query window (UTC): {0:yyyy-MM-dd HH:mm:ss} .. {1:yyyy-MM-dd HH:mm:ss}; host {2}; user {3}" -f `
        $started, $ended.AddMinutes(10), $env:COMPUTERNAME, $User) -ForegroundColor Green

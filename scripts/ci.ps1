param(
  [ValidateSet('lint','typecheck','test','run','all')]
  [string]$Task = 'all'
)

$ErrorActionPreference = 'Stop'

function Invoke-Step {
  param(
    [Parameter(Mandatory=$true)][string]$Label,
    [Parameter(Mandatory=$true)][string[]]$Args
  )

  Write-Host "`n== $Label ==" -ForegroundColor Cyan
  Write-Host ("$($Args -join ' ')")
  & $Args[0] @($Args[1..($Args.Length-1)])
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
}

switch ($Task) {
  'lint' {
    Invoke-Step -Label 'ruff' -Args @('python','-m','ruff','check','.')
  }
  'typecheck' {
    Invoke-Step -Label 'mypy' -Args @('python','-m','mypy','src')
  }
  'test' {
    Invoke-Step -Label 'pytest' -Args @('python','-m','pytest')
  }
  'run' {
    Invoke-Step -Label 'run' -Args @('python','-m','cinetcg')
  }
  'all' {
    Invoke-Step -Label 'ruff' -Args @('python','-m','ruff','check','.')
    Invoke-Step -Label 'mypy' -Args @('python','-m','mypy','src')
    Invoke-Step -Label 'pytest' -Args @('python','-m','pytest')
  }
}

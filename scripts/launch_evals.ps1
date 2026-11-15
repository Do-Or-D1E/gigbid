# Launches the long eval runs as detached Windows processes (they survive the terminal or IDE
# session ending). Logs go to cache/*.log; results stream into evals/results/*_partial.jsonl.
param([string[]]$Only = @())
$root = Split-Path -Parent $PSScriptRoot
$uv = (Get-Command uv).Source
$db = (Get-Content (Join-Path $root "cache\db_uri.txt") -Raw).Trim()
$runs = [ordered]@{
  "decisions_main"      = @{ env = @{ GIGBID_PROFILE = "paid" }; args = "-m evals.runners.decision_eval --n 20 --tag main --submit --concurrency 6 --profile paid" }
  "decisions_inj_on"    = @{ env = @{ GIGBID_DEFENCES = "on" };  args = "-m evals.runners.decision_eval --only injection --n 7 --tag inj_on --profile paid --concurrency 5" }
  "decisions_inj_off"   = @{ env = @{ GIGBID_DEFENCES = "off" }; args = "-m evals.runners.decision_eval --only injection --n 7 --tag inj_off --profile paid --concurrency 5" }
  "multiagent"          = @{ env = @{}; args = "-m evals.runners.multiagent_compare --n 5 --profile paid --concurrency 5" }
  "decisions_open"      = @{ env = @{}; args = "-m evals.runners.decision_eval --n 4 --tag open --profile open --concurrency 3" }
  "decisions_open_qwen" = @{ env = @{}; args = "-m evals.runners.decision_eval --n 4 --tag open_qwen --profile open_qwen --concurrency 3" }
  "ablation_final"      = @{ env = @{}; args = "-m evals.runners.ablation_finalize --rerank-limit 20" }
}
foreach ($name in $runs.Keys) {
  if ($Only.Count -gt 0 -and $Only -notcontains $name) { continue }
  $r = $runs[$name]
  $envs = ($r.env.GetEnumerator() | ForEach-Object { "set $($_.Key)=$($_.Value)&&" }) -join ""
  $cmd = "cd /d `"$root`" && set DATABASE_URL=$db&& set GIGSIM_DATABASE_URL=$db&& $envs `"$uv`" run python $($r.args) > cache\$name.log 2>&1"
  Start-Process -FilePath cmd.exe -ArgumentList "/c", $cmd -WindowStyle Hidden
  "launched $name"
}

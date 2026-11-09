param([string]$HostUrl="http://localhost:8080",[int]$Users=10,[string]$Duration="60s")
python -m locust -f "$PSScriptRoot/locustfile.py" --headless --host $HostUrl -u $Users -r 2 -t $Duration --csv "$PSScriptRoot/../benchmark" --html "$PSScriptRoot/../benchmark.html"
exit $LASTEXITCODE

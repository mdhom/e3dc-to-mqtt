$initialLocation = Get-Location;
Set-Location ..
try
{
    docker build --rm -f docker/Dockerfile -t mdhom/e3dc-to-mqtt:latest .
}
finally
{
	Set-Location $initialLocation;
}
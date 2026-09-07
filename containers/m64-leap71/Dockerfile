# Managed compile preflight only. Does not claim a Linux native PicoGK runtime.
FROM mcr.microsoft.com/dotnet/sdk:9.0@sha256:f190d2dd9eef2899c91ac323caa0bd2b39334a5400ba93013e5199da39dad940
WORKDIR /src
COPY sources.lock bootstrap.sh Smoke.csproj Program.cs ./
RUN sh bootstrap.sh /upstream
RUN dotnet build Smoke.csproj -c Release -o /app -p:GeneratePackageOnBuild=false
ENTRYPOINT ["dotnet", "/app/Smoke.dll"]

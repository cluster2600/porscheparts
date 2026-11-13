# syntax=docker/dockerfile:1.7
# Managed compilation only; native execution is checked in m64-leap71-native.
FROM mcr.microsoft.com/dotnet/sdk:10.0@sha256:de4fe90a98845d75910b9769662465c84de1a934665c431279d1382b2bddc02b
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
WORKDIR /src
COPY containers/stack-20261105/sources.lock containers/stack-20261105/Smoke.csproj ./
COPY containers/m64-leap71/bootstrap.sh containers/m64-leap71/Program.cs ./
RUN sh bootstrap.sh /upstream \
    && dotnet build Smoke.csproj -c Release -o /app -p:GeneratePackageOnBuild=false
CMD ["/bin/sh", "-ec", "test -s /app/Smoke.dll; dotnet --version; echo managed_compile_only_no_native_runtime_claim"]

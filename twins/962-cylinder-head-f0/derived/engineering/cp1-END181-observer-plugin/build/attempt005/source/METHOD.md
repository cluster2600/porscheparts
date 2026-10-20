# Explicit CLT linker and LTO path correction

Preserved004 stopped on the versioned libLTO filename before SDK parsing was observed. The exact captured Clang19 linker vectors are reused, replacing only the -lto_library value with the existing CLT libLTO.dylib and rebinding fresh output paths. Direct ld avoids a second automatic, invalid driver argument. The native observer/shim objects from003 are unchanged. The guard source compiles separately with its byte-identical common held compilation prefix; its captured temporary linker-object association is replaced with that fresh object. No LTO enablement, production-source change or prebuilt rewrite occurs.

Official Clang19 Darwin.cpp240–257 supplies this library argument unconditionally from the installed directory. Its comments limit actual LTO use to cases needing it and expect compiler/library consistency. Installed downstream spelling differs from upstream, so source/binary equivalence is not claimed. Inputs here are native ARM64 Mach-O objects and the held recipe does not enable LTO. The paired CLT linker/library capability is tested by the bounded commands; neither compilation nor linking establishes app ABI or physical verification.

Primary source: https://github.com/llvm/llvm-project/blob/llvmorg-19.1.7/clang/lib/Driver/ToolChains/Darwin.cpp#L240-L257

Exactly3 fixed commands: plugin link, unchanged guard-main compile, guard link. Stop first failure; preserve every outcome. Reuse003 nonnegative sampled RSS/lifecycle semantics unchanged:120s percommand,2GiB aggregate owned RSS,64MiB owned build/log output,TERM8/KILL/wait, sequential commands plus OMP/BLAS/VECLIB1. No guard execution, host load, native case, resource increase, solver/tolerance change or ABI acceptance.

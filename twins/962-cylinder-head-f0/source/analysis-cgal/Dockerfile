# The toolchain layer is separately pinned by its observed image ID and package receipt.
ARG TOOLCHAIN_IMAGE=962-cgal-envelope-toolchain:20261016-001
FROM ${TOOLCHAIN_IMAGE}
COPY cgal-envelope /opt/cgal-envelope
ENTRYPOINT ["/opt/cgal-envelope"]

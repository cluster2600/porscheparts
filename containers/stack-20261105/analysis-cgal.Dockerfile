# syntax=docker/dockerfile:1.7
FROM porscheparts/analysis-cgal-toolchain:stack-20261105
COPY twins/962-cylinder-head-f0/source/analysis-cgal/envelope.cpp /opt/stack/envelope.cpp
RUN g++ -std=c++17 -O2 -I/opt/CGAL/include /opt/stack/envelope.cpp \
    -lgmp -lmpfr -o /opt/cgal-envelope
RUN --network=none /opt/cgal-envelope --self-test
ENTRYPOINT ["/opt/cgal-envelope"]
CMD ["--self-test"]

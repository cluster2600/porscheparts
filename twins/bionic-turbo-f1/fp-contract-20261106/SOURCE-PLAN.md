# Complete the input-reader source binding

The recovered dossier defines the output stream and scalar dispatch but does
not include the implementation of the input parser. Before relying on that
parser, download the official archive already pinned by the historical source
audit: `https://dl.openfoam.com/source/v2406/OpenFOAM-v2406.tgz`, SHA-256
`8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a`.

New acquisition limits: 256 MiB compressed, 180 seconds, 1 GiB total new private
storage. Keep the archive outside Git; verify its complete hash before reading
members. Read only regular source members needed for scalar input/output and
the published compiler rules. No archive extraction command or source program
will execute. Hash selected members and record paths/line spans in the report.
Published build defaults are not proof that a particular binary used them.

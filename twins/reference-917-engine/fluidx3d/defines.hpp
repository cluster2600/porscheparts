#pragma once

// F34: solveur LBM indépendant d'OpenFOAM pour le refroidissement externe.
#define D3Q19
#define TRT
// FP32 volontaire: le premier run FP16S a divergé au nombre de Reynolds F34.
// Ce choix sacrifie de la mémoire pour conserver la précision de stockage.
#define EQUILIBRIUM_BOUNDARIES
#define FORCE_FIELD
#define TEMPERATURE
#define SUBGRID

#define GRAPHICS_FRAME_WIDTH 1600
#define GRAPHICS_FRAME_HEIGHT 900
#define GRAPHICS_BACKGROUND_COLOR 0x0B1118
#define GRAPHICS_U_MAX 0.12f
#define GRAPHICS_RHO_DELTA 0.01f
#define GRAPHICS_T_DELTA 0.75f
#define GRAPHICS_F_MAX 0.001f
#define GRAPHICS_Q_CRITERION 0.0001f
#define GRAPHICS_STREAMLINE_SPARSE 8u
#define GRAPHICS_STREAMLINE_LENGTH 128u
#define GRAPHICS_RAYTRACING_TRANSMITTANCE 0.25f
#define GRAPHICS_RAYTRACING_COLOR 0x005F7F
#define GRAPHICS_LSF 4u
#define GRAPHICS_LSQ 8u
#define GRAPHICS_LSP 4u

#define TYPE_S 0b00000001
#define TYPE_E 0b00000010
#define TYPE_T 0b00000100
#define TYPE_F 0b00001000
#define TYPE_I 0b00010000
#define TYPE_G 0b00100000
#define TYPE_X 0b01000000
#define TYPE_Y 0b10000000

#define VIS_FLAG_LATTICE  0b00000001
#define VIS_FLAG_SURFACE  0b00000010
#define VIS_FIELD         0b00000100
#define VIS_STREAMLINES   0b00001000
#define VIS_Q_CRITERION   0b00010000
#define VIS_PHI_RASTERIZE 0b00100000
#define VIS_PHI_RAYTRACE  0b01000000
#define VIS_PARTICLES     0b10000000

#if defined(FP16S) || defined(FP16C)
#define fpxx ushort
#else
#define fpxx float
#endif

#ifdef TEMPERATURE
#define VOLUME_FORCE
#endif

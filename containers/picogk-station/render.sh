#!/bin/sh
set -eu
# OVRTX uses CUDA-visible indices in RendererConfig; Kit uses Vulkan indices.
export CUDA_VISIBLE_DEVICES=3 CUDA_DEVICE_ORDER=PCI_BUS_ID
export VK_LOADER_DISABLE_DYNAMIC_LIBRARY_UNLOADING=1
unset PYTHONPATH
exec /opt/ovrtx-runtime/bin/python /opt/station/render.py "$@"

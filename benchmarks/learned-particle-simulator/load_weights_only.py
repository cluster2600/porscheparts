import sys, torch
src, dst = sys.argv[1], sys.argv[2]
ckpt = torch.load(src, map_location="cpu", weights_only=True)
print("keys:", list(ckpt.keys()))
sd = ckpt["state_dict"]
n = sum(v.numel() for v in sd.values())
print("tensors:", len(sd), "parameters:", n, "dtypes:", sorted({str(v.dtype) for v in sd.values()}))
print("prefixes:", sorted({k.split('.')[0] for k in sd}))
torch.save({"state_dict": {k: v for k, v in sd.items()}}, dst)

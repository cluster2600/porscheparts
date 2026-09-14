# Dedicated role only; no listing, writes, or access to another workload.
path "secrets/data/huggingface-flashnext" {
  capabilities = ["read"]
}

path "auth/token/revoke-self" {
  capabilities = ["update"]
}

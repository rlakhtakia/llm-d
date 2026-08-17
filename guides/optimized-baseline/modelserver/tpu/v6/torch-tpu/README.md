# TorchTPU (`torch_tpu`) Optimized Baseline Guide (GKE TPU v6e)

This guide provides the deployment variant for running Qwen models on Google Cloud TPU v6e VMs using the new native `torch_tpu` PyTorch backend.

## Overview

Unlike legacy TPU implementations that relied on PyTorch/XLA lazy graph tracing (`torch_xla`), `torch_tpu` registers `"tpu"` natively via PyTorch's out-of-tree backend dispatch. It communicates directly with PJRT (`libtpu.so`), supporting eager execution and `torch.compile` out of the box.

In accordance with `llm-d` architecture, this variant inherits the common single-host Deployment structure from `recipes/modelserver/base/single-host/default` and applies TPU-specific host mapping sysctls and image components.

---

## Step 1: Deploy to GKE

Ensure your GKE cluster has TPU node pools provisioned (`tpu-v6e-slice`, topology `2x4`).

```bash
# Apply the Optimized Baseline model server variant
kubectl apply -k guides/optimized-baseline/modelserver/tpu/v6/torch-tpu/
```

Verify that the model server initializes successfully:

```bash
kubectl get pods -l llm-d.ai/guide=optimized-baseline,llm-d.ai/role=decode
kubectl logs -l llm-d.ai/guide=optimized-baseline,llm-d.ai/role=decode -c modelserver -f
```

Look for the following PJRT initialization signature in the logs:
```text
GetPjrtApi was found for TPU at /workspace/env/lib/python3.12/site-packages/libtpu/libtpu.so
Successfully renamed PrivateUse1 backend to 'tpu'. Device: device(type='tpu')
```

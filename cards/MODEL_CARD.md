---
license: cc-by-nc-4.0
base_model: CohereLabs/tiny-aya-global
tags:
- safety
- activation-steering
- refusal-direction
- safetune
- auditkit
- spanish
language:
- es
- en
---
<!-- MODEL_CARD.md: tarjeta del repo de modelo en Hugging Face (se sube como README.md): el vector
     de steering de rechazo para Tiny Aya Global, cómo aplicarlo y los resultados medidos.
     Se distingue de DATASET_CARD.md, que describe los prompts; {{REPORT}} se reemplaza al publicar. -->

# fraudiu — refusal steering vector for Tiny Aya Global

Not new weights: a **single refusal direction** (`refusal_direction.safetensors`, one vector of
the model's hidden size) extracted from English contrast prompts with
[SafeTune](https://github.com/Lexsi-Labs/SafeTune)'s `RefusalDirectionTrainer`, and added at
inference to every decoder layer of `CohereLabs/tiny-aya-global` with strength **{{STRENGTH}}**.
The base model is untouched; remove the hooks and it is the original model.

Evaluated with [AuditKIT](https://github.com/Lexsi-Labs/AuditKIT)'s multilingual refusal scorer,
extended with Spanish patterns, on the gated dataset
[{{DATASET}}](https://huggingface.co/datasets/{{DATASET}}).

## Use

```python
import torch
from safetensors.torch import load_file
from safetune.interventions.steer.refusal_direction import RefusalDirectionModel

direction = load_file("refusal_direction.safetensors")["refusal_direction"]
steered = RefusalDirectionModel(model, direction=direction, mode="steer", strength={{STRENGTH}})
with steered:
    out = model.generate(**inputs, max_new_tokens=64, do_sample=False)
```

{{REPORT}}

Code: {{GITHUB}} · License: CC BY-NC 4.0 (inherits Tiny Aya's licence).

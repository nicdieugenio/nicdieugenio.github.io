---
layout: post
title: A short note on something I keep forgetting
date: 2026-09-12 10:00:00
description: One or two lines that show up under the title on the blog grid.
categories: notes
tags: [physics]
giscus_comments: false
related_posts: false
---

This is the "notes" kind of post — the replacement for the old notes section.
Write down whatever you don't want to lose.

Math works inline, $$E = mc^2$$, and as a block:

$$
\frac{\partial \rho}{\partial t} + \nabla \cdot (\rho \mathbf{v}) = 0
$$

Code works too:

```python
import numpy as np
print(np.linalg.eigvalsh(np.eye(3)))
```

## To publish this

Move it into `_posts/` with a dated filename:

```bash
mv _drafts/example-note.md _posts/2026-09-12-example-note.md
```

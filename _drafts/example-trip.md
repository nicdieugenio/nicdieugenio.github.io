---
layout: post
title: Mainz, spring
date: 2026-09-12 12:00:00
description: Photos from the road.
categories: travel
thumbnail: assets/img/blog/mainz/cover.jpg
giscus_comments: false
related_posts: false
---

A line or two of context, then the pictures. Drop the files in
`assets/img/blog/mainz/` and list them below — `cols` sets how many per row,
and anything after a `|` becomes the caption.

{% include gallery.liquid cols=3 images="
  assets/img/blog/mainz/cover.jpg | the Rhine, early April
  assets/img/blog/mainz/two.jpg
  assets/img/blog/mainz/three.jpg | Institute courtyard
" %}

For a single wide photo, use `cols=1`:

{% include gallery.liquid cols=1 images="
  assets/img/blog/mainz/wide.jpg | looking back toward the bridge
" %}

Travel posts hide the "min read" estimate automatically — the pictures are the point.

## To publish this

```bash
mv _drafts/example-trip.md _posts/2026-09-12-mainz-spring.md
```

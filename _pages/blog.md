---
layout: default
permalink: /blog/
title: blog
nav: true
nav_order: 3
pagination:
  enabled: true
  collection: posts
  permalink: /page/:num/
  per_page: 12
  sort_field: date
  sort_reverse: true
  trail:
    before: 1 # The number of links before the current page
    after: 3 # The number of links after the current page
---

<div class="post">

{% assign blog_name_size = site.blog_name | size %}
{% assign blog_description_size = site.blog_description | size %}

{% if blog_name_size > 0 or blog_description_size > 0 %}

  <div class="header-bar">
    <h1>{{ site.blog_name }}</h1>
    <h2>{{ site.blog_description }}</h2>
  </div>
{% endif %}

{% comment %} Only show a filter chip for categories/tags that actually have posts. {% endcomment %}
{% assign live_categories = "" | split: "" %}
{% for category in site.display_categories %}
{% if site.categories[category].size > 0 %}
{% assign live_categories = live_categories | push: category %}
{% endif %}
{% endfor %}
{% assign live_tags = "" | split: "" %}
{% for tag in site.display_tags %}
{% if site.tags[tag].size > 0 %}
{% assign live_tags = live_tags | push: tag %}
{% endif %}
{% endfor %}

{% if live_categories.size > 0 or live_tags.size > 0 %}

  <div class="blog-filters">
    <span class="blog-filter active">all</span>
    {% for category in live_categories %}
      <a class="blog-filter" href="{{ category | slugify | prepend: '/blog/category/' | relative_url }}">{{ category }}</a>
    {% endfor %}
    {% for tag in live_tags %}
      <a class="blog-filter" href="{{ tag | slugify | prepend: '/blog/tag/' | relative_url }}"><i class="fa-solid fa-hashtag fa-xs"></i> {{ tag }}</a>
    {% endfor %}
  </div>
{% endif %}

{% assign featured_posts = site.posts | where: "featured", "true" %}
{% if featured_posts.size > 0 %}

  <div class="featured-posts">
    {% for post in featured_posts %}
      <a class="featured-post" href="{{ post.url | relative_url }}">
        {% if post.thumbnail %}
          <div class="featured-post-img" style="background-image: url('{{ post.thumbnail | relative_url }}');"></div>
        {% endif %}
        <div class="featured-post-body">
          <span class="pin"><i class="fa-solid fa-thumbtack fa-xs"></i></span>
          <h3>{{ post.title }}</h3>
          <p>{{ post.description }}</p>
          <p class="post-meta">{{ post.date | date: '%B %-d, %Y' }}</p>
        </div>
      </a>
    {% endfor %}
  </div>
  <hr />
{% endif %}

{% if page.pagination.enabled %}
{% assign postlist = paginator.posts %}
{% else %}
{% assign postlist = site.posts %}
{% endif %}

{% if postlist.size > 0 %}
{% include blog_grid.liquid posts=postlist %}
{% else %}

  <p class="post-meta">Nothing here yet.</p>
{% endif %}

{% if page.pagination.enabled %}
{% include pagination.liquid %}
{% endif %}

</div>

<template>
  <div class="md" v-html="html" />
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps({
  content: { type: String, default: '' },
})

marked.setOptions({ gfm: true, breaks: true })

const html = computed(() => {
  const raw = marked.parse(props.content || '')
  return DOMPurify.sanitize(raw, {
    ADD_ATTR: ['target', 'rel'],
  })
})
</script>

<style>
.md {
  font-size: 14px;
  line-height: 1.75;
  color: var(--ink-2);
  word-break: break-word;
}

.md > :first-child {
  margin-top: 0;
}

.md > :last-child {
  margin-bottom: 0;
}

.md h1,
.md h2,
.md h3,
.md h4 {
  margin: 20px 0 10px;
  color: var(--ink);
  line-height: 1.35;
}

.md h1 {
  font-size: 22px;
}

.md h2 {
  font-size: 18px;
}

.md h3 {
  font-size: 15.5px;
}

.md p {
  margin: 9px 0;
}

.md strong {
  color: var(--ink);
  font-weight: 700;
}

.md ul,
.md ol {
  margin: 8px 0;
  padding-left: 20px;
  list-style: revert;
}

.md li {
  margin: 4px 0;
}

.md li::marker {
  color: var(--violet);
}

.md blockquote {
  margin: 14px 0;
  padding: 10px 14px;
  border-left: 3px solid var(--violet);
  background: rgba(30, 78, 216, 0.06);
  border-radius: 0 10px 10px 0;
  color: var(--muted);
  font-size: 12.5px;
}

.md table {
  margin: 14px 0;
  font-size: 12.5px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--line);
}

.md th {
  text-align: left;
  padding: 9px 11px;
  background: rgba(21, 32, 43, 0.04);
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--muted);
  white-space: nowrap;
}

.md td {
  padding: 9px 11px;
  border-top: 1px solid var(--line);
}

.md code {
  font-family: var(--font-mono);
  font-size: 0.9em;
  padding: 1px 5px;
  border-radius: 5px;
  background: rgba(21, 32, 43, 0.06);
}

.md pre {
  padding: 14px;
  border-radius: 12px;
  background: #0f1730;
  color: #dce4ff;
  overflow-x: auto;
}

.md pre code {
  background: none;
  padding: 0;
  color: inherit;
}

.md a {
  color: var(--indigo);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.md hr {
  border: 0;
  height: 1px;
  background: var(--line);
  margin: 18px 0;
}
</style>

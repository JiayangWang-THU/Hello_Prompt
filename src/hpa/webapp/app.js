const stateStore = {
  snapshot: null,
  messages: [
    {
      role: "assistant",
      content:
        "欢迎来到 Hello Prompt Agent Web。先直接描述你的任务，我会尽量先给选择题，再一起改共享 prompt 文档。",
    },
  ],
  selectedSection: null,
  selectedExcerpt: "",
  pending: false,
};

const elements = {
  hero: document.querySelector("#hero"),
  messages: document.querySelector("#messages"),
  pendingChoice: document.querySelector("#pending-choice"),
  messageInput: document.querySelector("#message-input"),
  sendButton: document.querySelector("#send-button"),
  resetButton: document.querySelector("#reset-button"),
  factsList: document.querySelector("#facts-list"),
  modePill: document.querySelector("#mode-pill"),
  missingPill: document.querySelector("#missing-pill"),
  docPill: document.querySelector("#doc-pill"),
  documentEmpty: document.querySelector("#document-empty"),
  documentSections: document.querySelector("#document-sections"),
  reviseButton: document.querySelector("#revise-button"),
  clearSelectionButton: document.querySelector("#clear-selection-button"),
  selectionSummary: document.querySelector("#selection-summary"),
  sectionBadge: document.querySelector("#section-badge"),
  copyDocButton: document.querySelector("#copy-doc-button"),
  thinking: document.querySelector("#thinking-indicator"),
  messageTemplate: document.querySelector("#message-template"),
  optionTemplate: document.querySelector("#option-template"),
};

async function init() {
  bindEvents();
  await refreshState();
  render();
}

function bindEvents() {
  elements.sendButton.addEventListener("click", () => void handleSend());
  elements.messageInput.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      void handleSend();
    }
  });
  elements.resetButton.addEventListener("click", () => void handleReset());
  elements.copyDocButton.addEventListener("click", () => void copyDraft());
  elements.reviseButton.addEventListener("click", () => void reviseSelectedSection());
  elements.clearSelectionButton.addEventListener("click", () => clearDocumentSelection());
  document.addEventListener("selectionchange", handleSelectionChange);
  for (const chip of document.querySelectorAll("[data-command]")) {
    chip.addEventListener("click", () => {
      const command = chip.getAttribute("data-command");
      if (command) {
        void sendMessage(command);
      }
    });
  }
}

async function refreshState() {
  const response = await fetch("/api/state");
  const payload = await response.json();
  stateStore.snapshot = payload.state;
  if (payload.state?.history?.length) {
    stateStore.messages = [
      stateStore.messages[0],
      ...payload.state.history.map((item) => ({
        role: item.role,
        content: item.content,
      })),
    ];
  }
}

async function handleSend() {
  const message = elements.messageInput.value.trim();
  if (!message || stateStore.pending) {
    return;
  }
  elements.messageInput.value = "";
  await sendMessage(message);
}

async function sendMessage(message) {
  stateStore.pending = true;
  stateStore.messages.push({ role: "user", content: message });
  render();

  try {
    const response = await fetch("/api/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "request failed");
    }
    stateStore.snapshot = payload.state;
    stateStore.messages.push({ role: "assistant", content: payload.text });
  } catch (error) {
    stateStore.messages.push({
      role: "assistant",
      content: `请求失败：${error.message}`,
    });
  } finally {
    stateStore.pending = false;
    render();
  }
}

async function handleReset() {
  if (stateStore.pending) {
    return;
  }
  stateStore.pending = true;
  render();
  try {
    const response = await fetch("/api/reset", { method: "POST" });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "reset failed");
    }
    stateStore.snapshot = payload.state;
    stateStore.messages = [
      stateStore.messages[0],
      { role: "assistant", content: payload.text },
    ];
    stateStore.selectedSection = null;
    stateStore.selectedExcerpt = "";
  } catch (error) {
    stateStore.messages.push({
      role: "assistant",
      content: `重置失败：${error.message}`,
    });
  } finally {
    stateStore.pending = false;
    render();
  }
}

function render() {
  renderHero();
  renderMessages();
  renderPendingChoice();
  renderFacts();
  renderDocument();
  renderStatus();
  elements.thinking.classList.toggle("hidden", !stateStore.pending);
  elements.sendButton.disabled = stateStore.pending;
  elements.reviseButton.disabled = stateStore.pending;
  elements.resetButton.disabled = stateStore.pending;
}

function renderHero() {
  elements.hero.classList.toggle("hidden", !isPristineState());
}

function renderMessages() {
  elements.messages.innerHTML = "";
  const messages = isPristineState() ? [] : stateStore.messages;
  for (const message of messages) {
    const fragment = elements.messageTemplate.content.cloneNode(true);
    const root = fragment.querySelector(".message");
    root.dataset.role = message.role;
    fragment.querySelector(".message-role").textContent = message.role === "user" ? "You" : "Agent";
    fragment.querySelector(".message-body").textContent = message.content;
    elements.messages.appendChild(fragment);
  }
  elements.messages.scrollTop = elements.messages.scrollHeight;
}

function renderPendingChoice() {
  const pending = stateStore.snapshot?.pending_choice;
  if (!pending) {
    elements.pendingChoice.classList.add("hidden");
    elements.pendingChoice.innerHTML = "";
    return;
  }
  elements.pendingChoice.classList.remove("hidden");
  const container = document.createElement("div");
  const title = document.createElement("div");
  title.className = "choice-title";
  title.textContent = pending.title;
  const question = document.createElement("div");
  question.className = "choice-question";
  question.textContent = pending.question;
  const grid = document.createElement("div");
  grid.className = "option-grid";
  pending.options.forEach((option, index) => {
    const fragment = elements.optionTemplate.content.cloneNode(true);
    const button = fragment.querySelector(".option-card");
    fragment.querySelector(".option-index").textContent = String(index + 1);
    fragment.querySelector(".option-label").textContent = option.label;
    const rationale = fragment.querySelector(".option-rationale");
    if (option.rationale) {
      rationale.textContent = option.rationale;
    } else {
      rationale.remove();
    }
    button.addEventListener("click", () => void sendMessage(String(index + 1)));
    grid.appendChild(fragment);
  });
  const hint = document.createElement("div");
  hint.className = "manual-hint";
  hint.textContent = pending.allow_manual_text
    ? `也可以直接输入文本：${pending.manual_text_hint || "如果选项都不合适，可以自己写。"}`
    : "当前只接受选项输入。";

  container.append(title, question, grid, hint);
  elements.pendingChoice.replaceChildren(container);
}

function renderFacts() {
  const facts = stateStore.snapshot?.confirmed_slots || {};
  elements.factsList.innerHTML = "";
  const entries = Object.entries(facts);
  if (!entries.length) {
    const empty = document.createElement("div");
    empty.className = "fact-item";
    empty.textContent = "还没有已确认 facts。";
    elements.factsList.appendChild(empty);
    return;
  }
  for (const [key, value] of entries) {
    const item = document.createElement("div");
    item.className = "fact-item";
    item.innerHTML = `<span class="fact-key">${escapeHtml(key)}</span><div class="fact-value">${escapeHtml(
      value,
    )}</div>`;
    elements.factsList.appendChild(item);
  }
}

function renderDocument() {
  const documentState = stateStore.snapshot?.document;
  elements.documentSections.innerHTML = "";
  elements.documentEmpty.classList.toggle("hidden", Boolean(documentState));

  if (!documentState) {
    stateStore.selectedSection = null;
    stateStore.selectedExcerpt = "";
    elements.sectionBadge.textContent = "用鼠标选中文档内容";
    elements.selectionSummary.textContent =
      "在右侧文档里用鼠标选中一段文本；如果只想改整个 section，也可以直接点 section 卡片。";
    return;
  }

  if (
    stateStore.selectedSection &&
    !documentState.sections.some((section) => section.key === stateStore.selectedSection)
  ) {
    stateStore.selectedSection = null;
    stateStore.selectedExcerpt = "";
  }

  for (const section of documentState.sections) {
    const card = document.createElement("article");
    card.className = "section-card";
    if (stateStore.selectedSection === section.key) {
      card.classList.add("selected");
    }
    const header = document.createElement("div");
    header.className = "section-card-header";
    const titleWrap = document.createElement("div");
    titleWrap.innerHTML = `<div class="section-title">${escapeHtml(section.title)}</div><div class="section-key">${escapeHtml(
      section.key,
    )}</div>`;
    const button = document.createElement("button");
    button.className = "ghost-button";
    button.textContent = "Revise";
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      stateStore.selectedSection = section.key;
      render();
    });
    header.append(titleWrap, button);
    const content = document.createElement("div");
    content.className = "section-content";
    content.dataset.sectionKey = section.key;
    content.textContent = section.content;
    card.append(header, content);
    card.addEventListener("click", () => {
      stateStore.selectedSection = section.key;
      stateStore.selectedExcerpt = "";
      render();
    });
    elements.documentSections.appendChild(card);
  }

  if (stateStore.selectedExcerpt) {
    elements.sectionBadge.textContent = `selected text in ${stateStore.selectedSection}`;
    elements.selectionSummary.textContent = `当前选中文本：${truncate(stateStore.selectedExcerpt, 180)}`;
  } else if (stateStore.selectedSection) {
    elements.sectionBadge.textContent = `selected section: ${stateStore.selectedSection}`;
    elements.selectionSummary.textContent =
      "当前会对整个 section 生成改写候选项。也可以在该 section 内再拖选一段文本。";
  } else {
    elements.sectionBadge.textContent = "用鼠标选中文档内容";
    elements.selectionSummary.textContent =
      "在右侧文档里用鼠标选中一段文本；如果只想改整个 section，也可以直接点 section 卡片。";
  }
}

function renderStatus() {
  const snapshot = stateStore.snapshot;
  elements.modePill.textContent = snapshot?.mode_key || "未选择";
  elements.missingPill.textContent = String(snapshot?.missing_slots?.length || 0);
  elements.docPill.textContent = snapshot?.document ? `v${snapshot.document.version}` : "v0";
}

async function reviseSelectedSection() {
  if (!stateStore.selectedSection) {
    stateStore.messages.push({
      role: "assistant",
      content: "请先在右侧共享文档里点一个 section，或直接用鼠标选中一段文本。",
    });
    render();
    return;
  }
  const instruction = stateStore.selectedExcerpt
    ? buildSelectionInstruction(stateStore.selectedExcerpt)
    : "";
  const command = instruction
    ? `/revise ${stateStore.selectedSection} ${instruction}`
    : `/revise ${stateStore.selectedSection}`;
  await sendMessage(command);
}

function clearDocumentSelection() {
  stateStore.selectedExcerpt = "";
  const selection = window.getSelection();
  if (selection) {
    selection.removeAllRanges();
  }
  render();
}

async function copyDraft() {
  const draft = stateStore.snapshot?.document?.sections
    ?.map((section) => `## ${section.title}\n${section.content}`)
    .join("\n\n");
  if (!draft) {
    stateStore.messages.push({
      role: "assistant",
      content: "当前还没有可复制的共享文档。先通过对话补 facts，或点击 `/draft`。",
    });
    render();
    return;
  }
  try {
    await navigator.clipboard.writeText(draft);
    stateStore.messages.push({
      role: "assistant",
      content: "当前共享 prompt 文档已复制到剪贴板。",
    });
  } catch (error) {
    stateStore.messages.push({
      role: "assistant",
      content: `复制失败：${error.message}`,
    });
  }
  render();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function handleSelectionChange() {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0 || selection.isCollapsed) {
    return;
  }
  const anchorNode = selection.anchorNode;
  const focusNode = selection.focusNode;
  if (!anchorNode || !focusNode) {
    return;
  }
  const anchorElement = anchorNode.nodeType === Node.ELEMENT_NODE ? anchorNode : anchorNode.parentElement;
  const focusElement = focusNode.nodeType === Node.ELEMENT_NODE ? focusNode : focusNode.parentElement;
  if (!anchorElement || !focusElement) {
    return;
  }
  const startSection = anchorElement.closest(".section-content");
  const endSection = focusElement.closest(".section-content");
  if (!startSection || !endSection || startSection !== endSection) {
    return;
  }
  if (!elements.documentSections.contains(startSection)) {
    return;
  }
  const text = selection.toString().trim();
  if (!text) {
    return;
  }
  stateStore.selectedSection = startSection.dataset.sectionKey || null;
  stateStore.selectedExcerpt = text;
  render();
}

function buildSelectionInstruction(selectedText) {
  return `Revise this section with extra attention to the selected excerpt: "${selectedText}". Preserve all confirmed facts, keep surrounding structure consistent, and provide better alternatives for that part first.`;
}

function truncate(value, maxLength) {
  if (value.length <= maxLength) {
    return value;
  }
  return `${value.slice(0, maxLength - 1)}…`;
}

function isPristineState() {
  const snapshot = stateStore.snapshot;
  if (!snapshot) {
    return true;
  }
  const hasHistory = Array.isArray(snapshot.history) && snapshot.history.length > 0;
  const hasFacts = snapshot.confirmed_slots && Object.keys(snapshot.confirmed_slots).length > 0;
  const hasPendingChoice = Boolean(snapshot.pending_choice);
  const hasDocument = Boolean(snapshot.document);
  return !hasHistory && !hasFacts && !hasPendingChoice && !hasDocument;
}

void init();

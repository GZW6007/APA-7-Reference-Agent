const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const state = { file: null, report: null, filter: "all", progressTimer: null };
const elements = {
  form: $("#uploadForm"), input: $("#fileInput"), dropzone: $("#dropzone"), selected: $("#selectedFile"),
  fileName: $("#fileName"), fileSize: $("#fileSize"), fileType: $("#fileType"), remove: $("#removeFile"),
  button: $("#analyzeButton"), settingsToggle: $("#settingsToggle"), settings: $("#settingsPanel"),
  online: $("#onlineToggle"), autoFix: $("#autoFixToggle"), threshold: $("#thresholdRange"), thresholdValue: $("#thresholdValue"),
  processing: $("#processing"), processingText: $("#processingText"), progress: $("#progressBar"),
  results: $("#results"), list: $("#referenceList"), emptyFilter: $("#emptyFilter"), toast: $("#toast")
};

const formatBytes = (bytes) => bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
const statusLabel = { verified: "已查證", needs_review: "需人工確認", unverifiable: "無法驗證" };

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.add("show");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => elements.toast.classList.remove("show"), 2200);
}

function selectFile(file) {
  if (!file) return;
  const extension = `.${file.name.split(".").pop().toLowerCase()}`;
  if (![".pdf", ".docx", ".txt", ".md"].includes(extension)) return showToast("請選擇 PDF、DOCX、TXT 或 Markdown 檔案");
  if (file.size > 15 * 1024 * 1024) return showToast("檔案大小不可超過 15 MB");
  state.file = file;
  elements.fileName.textContent = file.name;
  elements.fileSize.textContent = `${formatBytes(file.size)} · 準備分析`;
  elements.fileType.textContent = extension.slice(1).toUpperCase();
  elements.selected.hidden = false;
  elements.dropzone.hidden = true;
  elements.button.disabled = false;
}

function clearFile() {
  state.file = null;
  elements.input.value = "";
  elements.selected.hidden = true;
  elements.dropzone.hidden = false;
  elements.button.disabled = true;
}

elements.dropzone.addEventListener("click", () => elements.input.click());
elements.dropzone.addEventListener("keydown", (event) => { if (["Enter", " "].includes(event.key)) { event.preventDefault(); elements.input.click(); } });
elements.input.addEventListener("change", () => selectFile(elements.input.files[0]));
elements.remove.addEventListener("click", clearFile);
["dragenter", "dragover"].forEach((name) => elements.dropzone.addEventListener(name, (event) => { event.preventDefault(); elements.dropzone.classList.add("dragging"); }));
["dragleave", "drop"].forEach((name) => elements.dropzone.addEventListener(name, (event) => { event.preventDefault(); elements.dropzone.classList.remove("dragging"); }));
elements.dropzone.addEventListener("drop", (event) => selectFile(event.dataTransfer.files[0]));
elements.settingsToggle.addEventListener("click", () => {
  const expanded = elements.settingsToggle.getAttribute("aria-expanded") === "true";
  elements.settingsToggle.setAttribute("aria-expanded", String(!expanded));
  elements.settings.hidden = expanded;
});
elements.threshold.addEventListener("input", () => { elements.thresholdValue.value = `${elements.threshold.value}%`; });

function startProgress() {
  const phases = [
    [18, "讀取文件與定位參考文獻…"], [37, "切分並解析書目欄位…"],
    [59, "查詢 DOI 與書目 metadata…"], [78, "檢查 APA 7 格式規則…"], [91, "整理修正建議與稽核報告…"]
  ];
  let index = 0;
  elements.progress.style.width = "8%";
  elements.processingText.textContent = phases[0][1];
  state.progressTimer = window.setInterval(() => {
    if (index >= phases.length) return;
    elements.progress.style.width = `${phases[index][0]}%`;
    elements.processingText.textContent = phases[index][1];
    index += 1;
  }, 900);
}

function stopProgress(success = true) {
  window.clearInterval(state.progressTimer);
  elements.progress.style.width = success ? "100%" : "8%";
}

elements.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.file) return;
  const form = new FormData();
  form.append("file", state.file);
  form.append("offline", String(!elements.online.checked));
  form.append("auto_fix", String(elements.autoFix.checked));
  form.append("title_threshold", String(Number(elements.threshold.value) / 100));
  elements.button.disabled = true;
  elements.processing.hidden = false;
  elements.results.hidden = true;
  startProgress();
  elements.processing.scrollIntoView({ behavior: "smooth", block: "center" });
  try {
    const response = await fetch("/api/analyze", { method: "POST", body: form });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "分析失敗，請稍後再試。");
    state.report = data;
    stopProgress(true);
    window.setTimeout(() => {
      elements.processing.hidden = true;
      renderReport(data);
      elements.results.hidden = false;
      elements.results.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 350);
  } catch (error) {
    stopProgress(false);
    elements.processing.hidden = true;
    elements.button.disabled = false;
    showToast(error.message);
  }
});

function addText(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.textContent = text;
  return node;
}

function renderReference(result) {
  const card = document.createElement("article");
  card.className = "reference-card";
  card.dataset.status = result.status;
  const top = document.createElement("button");
  top.type = "button";
  top.className = "reference-top";
  top.setAttribute("aria-expanded", "false");
  top.append(addText("span", "reference-number", String(result.index).padStart(2, "0")));
  const preview = document.createElement("span"); preview.className = "reference-preview";
  preview.append(addText("p", "", result.original), addText("small", "", result.verification_reason || "尚無查證說明"));
  top.append(preview, addText("span", `status-badge ${result.status}`, statusLabel[result.status]), addText("span", "chevron", "⌄"));
  const detail = document.createElement("div"); detail.className = "reference-detail";
  if (result.corrected) {
    const block = document.createElement("div"); block.className = "detail-block";
    block.append(addText("span", "detail-label", result.correction_applied ? "已套用修正" : "修正建議（未套用）"));
    const correction = addText("p", `correction${result.correction_applied ? "" : " suggested"}`, result.corrected); block.append(correction);
    const copy = addText("button", "copy-button", "複製這筆文獻"); copy.type = "button";
    copy.addEventListener("click", () => navigator.clipboard.writeText(result.corrected).then(() => showToast("已複製修正文獻")));
    block.append(copy); detail.append(block);
  }
  if (result.issues?.length) {
    const block = document.createElement("div"); block.className = "detail-block"; block.append(addText("span", "detail-label", "APA 7 檢查結果"));
    const list = document.createElement("ul"); list.className = "issue-list";
    result.issues.forEach((issue) => { const item = document.createElement("li"); item.append(addText("i", `issue-severity ${issue.severity}`, ""), addText("span", "", issue.message)); list.append(item); });
    block.append(list); detail.append(block);
  }
  if (result.metadata) {
    const metadata = result.metadata;
    const parts = [metadata.source, metadata.match_method, `信心值 ${Math.round(metadata.score * 100)}%`];
    const block = document.createElement("div"); block.className = "detail-block"; block.append(addText("span", "detail-label", "查證依據"), addText("p", "metadata-line", parts.filter(Boolean).join(" · ")));
    detail.append(block);
  }
  top.addEventListener("click", () => { const open = card.classList.toggle("open"); top.setAttribute("aria-expanded", String(open)); });
  card.append(top, detail);
  return card;
}

function renderReport(report) {
  $("#resultsSubtitle").textContent = `${report.upload.filename} · ${report.summary.total} 筆參考文獻`;
  $("#countTotal").textContent = report.summary.total;
  $("#countVerified").textContent = report.summary.verified;
  $("#countReview").textContent = report.summary.needs_review;
  $("#countUnknown").textContent = report.summary.unverifiable;
  elements.list.replaceChildren(...report.results.map(renderReference));
  state.filter = "all";
  $$(".filter-tabs button").forEach((button) => button.classList.toggle("active", button.dataset.filter === "all"));
  applyFilter();
}

function applyFilter() {
  let visible = 0;
  $$(".reference-card", elements.list).forEach((card) => {
    const show = state.filter === "all" || card.dataset.status === state.filter;
    card.hidden = !show;
    if (show) visible += 1;
  });
  elements.emptyFilter.hidden = visible !== 0;
}

$$('.filter-tabs button').forEach((button) => button.addEventListener("click", () => {
  state.filter = button.dataset.filter;
  $$('.filter-tabs button').forEach((item) => item.classList.toggle("active", item === button));
  applyFilter();
}));

$("#newAnalysis").addEventListener("click", () => {
  clearFile(); state.report = null; elements.results.hidden = true;
  $(".workspace-card").scrollIntoView({ behavior: "smooth", block: "center" });
});

$("#exportButton").addEventListener("click", () => {
  const options = $("#exportOptions"); const expanded = !options.hidden; options.hidden = expanded;
  $("#exportButton").setAttribute("aria-expanded", String(!expanded));
});

function download(content, filename, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = filename; anchor.click();
  URL.revokeObjectURL(url);
}

$$('[data-export]').forEach((button) => button.addEventListener("click", () => {
  if (!state.report) return;
  const base = state.report.upload.filename.replace(/\.[^.]+$/, "");
  if (button.dataset.export === "json") download(JSON.stringify(state.report, null, 2), `${base}-apa7-audit.json`, "application/json");
  if (button.dataset.export === "markdown") download(state.report.exports.markdown, `${base}-apa7-audit.md`, "text/markdown");
  if (button.dataset.export === "text") download(state.report.exports.corrected_references, `${base}-corrected-references.txt`, "text/plain");
  $("#exportOptions").hidden = true;
  showToast("匯出檔案已建立");
}));

document.addEventListener("click", (event) => {
  if (!event.target.closest(".export-menu")) { $("#exportOptions").hidden = true; $("#exportButton").setAttribute("aria-expanded", "false"); }
});


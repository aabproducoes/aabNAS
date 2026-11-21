(() => {
  const API = (window.NAS_CONFIG?.API_BASE || "").replace(/\/$/, "");
  const $ = (id) => document.getElementById(id);
  const content = $("content");
  let currentPath = "";
  let entries = [];
  let filter = "all";
  let viewerItems = [];
  let viewerIndex = 0;

  const esc = (s) => String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const encodePath = (p) => p.split("/").filter(Boolean).map(encodeURIComponent).join("/");
  const mediaUrl = (path) => `${API}/media/${encodePath(path)}`;
  const fmtSize = (n) => {
    if (n == null) return "";
    const units = ["B","KB","MB","GB","TB"]; let i=0, v=n;
    while(v>=1024 && i<units.length-1){v/=1024;i++;}
    return `${v.toFixed(i ? 1 : 0)} ${units[i]}`;
  };
  const setStatus = (online, message) => {
    $("statusDot").className = "dot " + (online ? "online" : "offline");
    $("statusText").textContent = message;
  };

  async function load(path = "") {
    if (!API || API.includes("SEU-ASUSTOR")) {
      setStatus(false, "Configure o endereço do NAS");
      content.innerHTML = '<div class="empty">Edite <b>config.js</b> e informe o endereço HTTPS do seu ASUSTOR.</div>';
      return;
    }
    content.innerHTML = '<div class="empty">Carregando arquivos…</div>';
    try {
      const response = await fetch(`${API}/api/list?path=${encodeURIComponent(path)}`);
      if (!response.ok) throw new Error(`Servidor respondeu ${response.status}`);
      const data = await response.json();
      currentPath = data.path || "";
      entries = data.items || [];
      setStatus(true, "NAS conectado");
      renderBreadcrumbs();
      render();
    } catch (err) {
      setStatus(false, "NAS indisponível");
      content.innerHTML = `<div class="empty">Não foi possível conectar ao NAS.<br><br>${esc(err.message)}<br><small>Verifique o endereço, o Tailscale e o servidor.</small></div>`;
    }
  }

  function renderBreadcrumbs() {
    const parts = currentPath.split("/").filter(Boolean);
    let html = '<button data-path="">Início</button>';
    let built = "";
    parts.forEach(part => {
      built = built ? `${built}/${part}` : part;
      html += `<span class="sep">/</span><button data-path="${esc(built)}">${esc(part)}</button>`;
    });
    $("breadcrumbs").innerHTML = html;
    $("breadcrumbs").querySelectorAll("button").forEach(btn => btn.addEventListener("click", () => load(btn.dataset.path)));
  }

  function render() {
    const query = $("searchInput").value.trim().toLocaleLowerCase();
    const visible = entries.filter(item => {
      const matchesText = item.name.toLocaleLowerCase().includes(query);
      const matchesFilter = filter === "all" || item.type === filter || item.type === "folder";
      return matchesText && matchesFilter;
    });
    $("itemCount").textContent = `${visible.length} itens`;
    if (!visible.length) {
      content.innerHTML = '<div class="empty">Nenhum arquivo encontrado nesta pasta.</div>';
      return;
    }
    content.innerHTML = visible.map(item => {
      const path = currentPath ? `${currentPath}/${item.name}` : item.name;
      if (item.type === "folder") return `
        <article class="media-card folder-card" data-folder="${esc(path)}">
          <div class="thumb">📁</div><div class="card-info">
            <div class="file-name">${esc(item.name)}</div><div class="file-meta">Pasta</div>
          </div>
        </article>`;
      const thumb = item.type === "image"
        ? `<div class="thumb"><img loading="lazy" src="${mediaUrl(path)}" alt=""></div>`
        : `<div class="thumb"><div class="video-thumb">▰<span class="play">▶</span></div></div>`;
      return `<article class="media-card" data-file="${esc(path)}" data-type="${item.type}">
        ${thumb}<div class="card-info"><div class="file-name" title="${esc(item.name)}">${esc(item.name)}</div>
        <div class="file-meta">${item.type === "video" ? "Vídeo" : "Imagem"} · ${fmtSize(item.size)}</div></div>
      </article>`;
    }).join("");

    content.querySelectorAll("[data-folder]").forEach(el => el.addEventListener("click", () => load(el.dataset.folder)));
    content.querySelectorAll("[data-file]").forEach(el => el.addEventListener("click", () => {
      viewerItems = visible.filter(x => x.type === "image" || x.type === "video")
        .map(x => ({...x, path: currentPath ? `${currentPath}/${x.name}` : x.name}));
      viewerIndex = viewerItems.findIndex(x => x.path === el.dataset.file);
      showViewer();
    }));
  }

  function showViewer() {
    const item = viewerItems[viewerIndex];
    if (!item) return;
    const url = mediaUrl(item.path);
    $("viewerContent").innerHTML = item.type === "image"
      ? `<img src="${url}" alt="${esc(item.name)}">`
      : `<video src="${url}" controls autoplay playsinline preload="metadata"></video>`;
    $("viewerCaption").textContent = item.name;
    $("viewer").classList.remove("hidden");
    $("prevBtn").style.display = viewerItems.length > 1 ? "" : "none";
    $("nextBtn").style.display = viewerItems.length > 1 ? "" : "none";
  }
  function closeViewer() {
    const video = $("viewerContent").querySelector("video");
    if (video) video.pause();
    $("viewer").classList.add("hidden");
    $("viewerContent").innerHTML = "";
  }
  function moveViewer(delta) {
    if (!viewerItems.length) return;
    viewerIndex = (viewerIndex + delta + viewerItems.length) % viewerItems.length;
    showViewer();
  }

  document.querySelectorAll(".filter").forEach(btn => btn.addEventListener("click", () => {
    document.querySelectorAll(".filter").forEach(b => b.classList.remove("active"));
    btn.classList.add("active"); filter = btn.dataset.filter; render();
  }));
  $("searchInput").addEventListener("input", render);
  $("refreshBtn").addEventListener("click", () => load(currentPath));
  $("closeViewer").addEventListener("click", closeViewer);
  $("prevBtn").addEventListener("click", () => moveViewer(-1));
  $("nextBtn").addEventListener("click", () => moveViewer(1));
  $("viewer").addEventListener("click", e => { if (e.target === $("viewer")) closeViewer(); });
  document.addEventListener("keydown", e => {
    if ($("viewer").classList.contains("hidden")) return;
    if (e.key === "Escape") closeViewer();
    if (e.key === "ArrowLeft") moveViewer(-1);
    if (e.key === "ArrowRight") moveViewer(1);
  });
  load();
})();

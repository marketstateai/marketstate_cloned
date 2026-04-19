#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


DEFAULT_CONFIG = {
    "allow_raw_html": True,
    "inject_test_table": False,
    "inject_extra_window": True,
    "inject_table_filters": True,
    "css": "",
    "test_table_html": "",
}

EXTRA_MARKER_START = "<!-- dbt-extra-window: start -->"
EXTRA_MARKER_END = "<!-- dbt-extra-window: end -->"
EXTRA_WINDOW_TITLE = "Colibri Data"
EXTRA_BUTTON_LABEL = "Colibri"
EXTRA_IFRAME_TITLE = "Colibri Data"

EXTRA_HTML_BLOCK = """<!-- dbt-extra-window: start -->
<div id="dbt-extra-window-root">
  <button id="dbt-extra-window-open" class="dbt-extra-window-button" type="button" aria-label="Open Colibri window">
    {button_label}
  </button>
  <div id="dbt-extra-window" class="dbt-extra-window-overlay" aria-hidden="true">
    <div class="dbt-extra-window-panel" role="dialog" aria-label="{window_title}">
      <div class="dbt-extra-window-toolbar">
        <div class="dbt-extra-window-title">{window_title}</div>
        <button id="dbt-extra-window-close" class="dbt-extra-window-close" type="button" aria-label="Close Colibri window">
          Close
        </button>
      </div>
      <iframe class="dbt-extra-window-frame" src="{iframe_src}" title="{iframe_title}"></iframe>
    </div>
  </div>
</div>
<style>
  .dbt-extra-window-button {{
    position: fixed;
    right: 24px;
    top: 24px;
    z-index: 9998;
    padding: 10px 14px;
    border-radius: 999px;
    border: none;
    background: #0b4b5a;
    color: #ffffff;
    font-size: 12px;
    font-weight: 600;
    box-shadow: 0 8px 18px rgba(0, 0, 0, 0.2);
    cursor: pointer;
  }}
  .dbt-extra-window-button:hover {{
    background: #0f5f73;
  }}
  .dbt-extra-window-overlay {{
    position: fixed;
    inset: 18px;
    z-index: 9999;
    background: rgba(12, 18, 23, 0.35);
    display: none;
    align-items: stretch;
    justify-content: center;
  }}
  .dbt-extra-window-overlay.is-open {{
    display: flex;
  }}
  .dbt-extra-window-panel {{
    display: flex;
    flex-direction: column;
    width: min(1400px, calc(100% - 32px));
    height: calc(100% - 32px);
    background: #ffffff;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 18px 40px rgba(0, 0, 0, 0.35);
  }}
  .dbt-extra-window-toolbar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    background: #0b4b5a;
    color: #ffffff;
    font-size: 13px;
    font-weight: 600;
  }}
  .dbt-extra-window-close {{
    background: #ffffff;
    color: #0b4b5a;
    border: none;
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
  }}
  .dbt-extra-window-close:hover {{
    background: #e6f2f5;
  }}
  .dbt-extra-window-frame {{
    width: 100%;
    height: 100%;
    border: 0;
    background: #ffffff;
  }}
</style>
<script>
  (function () {{
    var overlay = document.getElementById("dbt-extra-window");
    var openButton = document.getElementById("dbt-extra-window-open");
    var closeButton = document.getElementById("dbt-extra-window-close");
    if (!overlay || !openButton || !closeButton) {{
      return;
    }}
    function openWindow() {{
      overlay.classList.add("is-open");
      overlay.setAttribute("aria-hidden", "false");
    }}
    function closeWindow() {{
      overlay.classList.remove("is-open");
      overlay.setAttribute("aria-hidden", "true");
    }}
    openButton.addEventListener("click", function (event) {{
      event.preventDefault();
      openWindow();
    }});
    closeButton.addEventListener("click", function (event) {{
      event.preventDefault();
      closeWindow();
    }});
    overlay.addEventListener("click", function (event) {{
      if (event.target === overlay) {{
        closeWindow();
      }}
    }});
    document.addEventListener("keydown", function (event) {{
      if (event.key === "Escape") {{
        closeWindow();
      }}
    }});
  }})();
</script>
<!-- dbt-extra-window: end -->"""

FILTER_MARKER_START = "<!-- dbt-table-filters: start -->"
FILTER_MARKER_END = "<!-- dbt-table-filters: end -->"

FILTER_SCRIPT = """<!-- dbt-table-filters: start -->
<script>
  (function () {
    function normalize(text) {
      return (text || "").toString().trim();
    }

    function resolveColumnIndex(headerMap, name) {
      var key = normalize(name).toLowerCase();
      if (!key) {
        return -1;
      }
      if (Object.prototype.hasOwnProperty.call(headerMap, key)) {
        return headerMap[key];
      }
      for (var mapKey in headerMap) {
        if (Object.prototype.hasOwnProperty.call(headerMap, mapKey) && mapKey.indexOf(key) !== -1) {
          return headerMap[mapKey];
        }
      }
      return -1;
    }

    function buildFilterUI(table) {
      if (table.dataset.docsFilter === "true") {
        return;
      }
      table.dataset.docsFilter = "true";

      var headerRow = table.querySelector("thead tr") || table.querySelector("tr");
      if (!headerRow) {
        return;
      }

      var headerCells = headerRow.children;
      var headerMap = {};
      var headerNames = [];
      var labelColumnIndex = -1;
      var datalistId = "docs-table-columns-" + Math.random().toString(36).slice(2);
      var datalist = document.createElement("datalist");
      datalist.id = datalistId;

      for (var i = 0; i < headerCells.length; i += 1) {
        var name = normalize(headerCells[i].textContent);
        headerNames[i] = name;
        if (!name && i === 0) {
          labelColumnIndex = i;
          continue;
        }
        var key = name.toLowerCase();
        if (i === 0 && key === "column") {
          labelColumnIndex = i;
          continue;
        }
        if (!name) {
          continue;
        }
        if (!Object.prototype.hasOwnProperty.call(headerMap, key)) {
          headerMap[key] = i;
          var option = document.createElement("option");
          option.value = name;
          datalist.appendChild(option);
        }
      }

      var container = document.createElement("div");
      container.className = "docs-table-container";
      var toolbar = document.createElement("div");
      toolbar.className = "docs-table-toolbar";

      var columnInput = document.createElement("input");
      columnInput.type = "text";
      columnInput.placeholder = "Add column";
      columnInput.className = "docs-table-column";
      columnInput.setAttribute("list", datalistId);
      columnInput.setAttribute("aria-label", "Add column filter");

      var clearButton = document.createElement("button");
      clearButton.type = "button";
      clearButton.textContent = "Show all";
      clearButton.className = "docs-table-clear";

      var selectedWrap = document.createElement("div");
      selectedWrap.className = "docs-table-selected";

      toolbar.appendChild(columnInput);
      toolbar.appendChild(clearButton);
      toolbar.appendChild(selectedWrap);

      var scrollWrap = document.createElement("div");
      scrollWrap.className = "docs-table-scroll";

      var tableParent = table.parentNode;
      if (!tableParent) {
        return;
      }
      tableParent.insertBefore(container, table);
      container.appendChild(toolbar);
      container.appendChild(datalist);
      container.appendChild(scrollWrap);
      scrollWrap.appendChild(table);

      var selectedMap = {};

      function isLabelColumn(index) {
        return index === labelColumnIndex;
      }

      function renderSelected() {
        selectedWrap.innerHTML = "";
        var keys = Object.keys(selectedMap).map(function (item) {
          return parseInt(item, 10);
        });
        keys.sort(function (a, b) {
          return a - b;
        });
        if (!keys.length) {
          var empty = document.createElement("span");
          empty.className = "docs-table-selected-empty";
          empty.textContent = "All columns";
          selectedWrap.appendChild(empty);
          return;
        }
        for (var i = 0; i < keys.length; i += 1) {
          var index = keys[i];
          var label = headerNames[index] || "Column " + (index + 1);
          var chip = document.createElement("button");
          chip.type = "button";
          chip.className = "docs-table-chip";
          chip.textContent = label;
          chip.dataset.index = String(index);
          chip.addEventListener("click", function (event) {
            var target = event.currentTarget;
            var idx = parseInt(target.dataset.index || "-1", 10);
            if (idx >= 0 && Object.prototype.hasOwnProperty.call(selectedMap, idx)) {
              delete selectedMap[idx];
              renderSelected();
              applyColumnFilter();
            }
          });
          selectedWrap.appendChild(chip);
        }
      }

      function applyColumnFilter() {
        var selectedKeys = Object.keys(selectedMap);
        var showAll = selectedKeys.length === 0;
        var rows = table.rows;
        for (var r = 0; r < rows.length; r += 1) {
          var cells = rows[r].cells;
          for (var c = 0; c < cells.length; c += 1) {
            var shouldShow = showAll || selectedMap[c] || isLabelColumn(c);
            cells[c].style.display = shouldShow ? "" : "none";
          }
        }
      }

      function addColumnByName(name) {
        var index = resolveColumnIndex(headerMap, name);
        if (index < 0) {
          return false;
        }
        if (!Object.prototype.hasOwnProperty.call(selectedMap, index)) {
          selectedMap[index] = true;
          renderSelected();
          applyColumnFilter();
        }
        return true;
      }

      columnInput.addEventListener("change", function () {
        if (addColumnByName(columnInput.value)) {
          columnInput.value = "";
        }
      });
      columnInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
          event.preventDefault();
          if (addColumnByName(columnInput.value)) {
            columnInput.value = "";
          }
        }
      });
      clearButton.addEventListener("click", function () {
        selectedMap = {};
        renderSelected();
        applyColumnFilter();
      });

      renderSelected();
      applyColumnFilter();
    }

    function enhanceTables(root) {
      var tables = root.querySelectorAll("table");
      for (var i = 0; i < tables.length; i += 1) {
        buildFilterUI(tables[i]);
      }
    }

    function run() {
      var roots = document.querySelectorAll(".model-markdown");
      for (var i = 0; i < roots.length; i += 1) {
        enhanceTables(roots[i]);
      }
    }

    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", run);
    } else {
      run();
    }

    var observer = new MutationObserver(function () {
      run();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  })();
</script>
<!-- dbt-table-filters: end -->"""


def load_config(path: Path) -> dict:
    if not path.exists():
        return dict(DEFAULT_CONFIG)
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    config = dict(DEFAULT_CONFIG)
    config.update(data)
    return config


def copy_dist_assets(dist_dir: Path, target_dir: Path) -> bool:
    if not dist_dir.exists():
        raise FileNotFoundError(
            f"Missing dist dir: {dist_dir}. Run colibri generate before patching docs."
        )
    target_dir.mkdir(parents=True, exist_ok=True)
    changed = False
    for item in dist_dir.iterdir():
        dest = target_dir / item.name
        if item.is_dir():
            changed = copy_dist_assets(item, dest) or changed
            continue
        if not item.is_file():
            continue
        if dest.exists() and dest.read_bytes() == item.read_bytes():
            continue
        shutil.copy2(item, dest)
        changed = True
    return changed


def run_colibri_generate(project_root: Path) -> None:
    cmd = ["colibri", "generate"]
    result = subprocess.run(
        cmd,
        cwd=str(project_root),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "colibri generate failed\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def inject_extra_window(text: str, iframe_src: str) -> tuple[str, bool]:
    if EXTRA_MARKER_START in text and EXTRA_MARKER_END in text:
        return text, False
    if "</body>" not in text:
        raise ValueError("Missing </body> in dbt docs index.html")
    block = EXTRA_HTML_BLOCK.format(
        button_label=EXTRA_BUTTON_LABEL,
        window_title=EXTRA_WINDOW_TITLE,
        iframe_title=EXTRA_IFRAME_TITLE,
        iframe_src=iframe_src,
    )
    text = text.replace("</body>", f"{block}\n</body>", 1)
    return text, True


def inject_table_filters(text: str) -> tuple[str, bool]:
    if FILTER_MARKER_START in text and FILTER_MARKER_END in text:
        return text, False
    if "</body>" not in text:
        raise ValueError("Missing </body> in dbt docs index.html")
    text = text.replace("</body>", f"{FILTER_SCRIPT}\n</body>", 1)
    return text, True


def patch_index(path: Path, config: dict, iframe_src: str) -> bool:
    text = path.read_text(encoding="utf-8")
    updated = False

    if config.get("allow_raw_html") and "e.setOptions({ gfm: !0, sanitize: !0 })" in text:
        text = text.replace(
            "e.setOptions({ gfm: !0, sanitize: !0 })",
            "e.setOptions({ gfm: !0, sanitize: !1 })",
            1,
        )
        updated = True

    css = (config.get("css") or "").strip()
    if css:
        css_block = f"<style>\n{css}\n</style>"
        if css_block not in text:
            if "</head>" not in text:
                raise ValueError(f"Missing </head> in {path}")
            text = text.replace("</head>", f"{css_block}\n</head>", 1)
            updated = True

    if config.get("inject_test_table"):
        test_block = (config.get("test_table_html") or "").strip()
        if test_block and test_block not in text:
            if "</body>" not in text:
                raise ValueError(f"Missing </body> in {path}")
            text = text.replace("</body>", f"{test_block}\n</body>", 1)
            updated = True

    if config.get("inject_extra_window"):
        text, injected = inject_extra_window(text, iframe_src)
        updated = updated or injected

    if config.get("inject_table_filters"):
        text, injected = inject_table_filters(text)
        updated = updated or injected

    if updated:
        path.write_text(text, encoding="utf-8")

    return updated


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    target = project_root / "target" / "index.html"
    if not target.exists():
        raise FileNotFoundError(f"Missing file: {target}")
    config_path = Path(__file__).with_name("docs_preview_config.json")
    config = load_config(config_path)
    assets_changed = False
    iframe_src = "colibri/index.html"
    if config.get("inject_extra_window"):
        run_colibri_generate(project_root)
        dist_dir = project_root / "dist"
        target_dir = project_root / "target" / "colibri"
        assets_changed = copy_dist_assets(dist_dir, target_dir)

    changed = patch_index(target, config, iframe_src)
    if changed or assets_changed:
        print("Patched", target)
    else:
        print("No changes needed", target)


if __name__ == "__main__":
    main()

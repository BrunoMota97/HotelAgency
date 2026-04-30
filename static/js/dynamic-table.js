(() => {
  const parseValue = (value) => {
    const normalized = (value || "").replace(/\s+/g, " ").trim();
    const numericCandidate = normalized.replace(/\./g, "").replace(",", ".").replace(/[^\d.-]/g, "");
    if (numericCandidate && !Number.isNaN(Number(numericCandidate))) return Number(numericCandidate);
    return normalized.toLowerCase();
  };

  document.querySelectorAll("table[data-dynamic-table]").forEach((table) => {
    const tbody = table.querySelector("tbody");
    if (!tbody) return;

    const originalRows = Array.from(tbody.querySelectorAll("tr")).filter((row) => !row.hasAttribute("data-empty-row"));
    if (!originalRows.length) return;

    const pageSize = Number(table.dataset.pageSize || 6);
    let query = "";
    let sortIndex = null;
    let sortDirection = 1;
    let currentPage = 1;

    const wrapper = document.createElement("div");
    wrapper.className = "table-enhancer";

    const search = document.createElement("input");
    search.type = "search";
    search.placeholder = "Pesquisar na tabela...";
    search.className = "form-control table-enhancer__search";

    const meta = document.createElement("div");
    meta.className = "table-enhancer__meta";

    wrapper.appendChild(search);
    wrapper.appendChild(meta);
    table.parentElement.insertBefore(wrapper, table);

    const footer = document.createElement("div");
    footer.className = "table-enhancer__footer";

    const pageInfo = document.createElement("div");
    pageInfo.className = "table-enhancer__meta";

    const actions = document.createElement("div");
    actions.className = "d-flex gap-2";

    const prevBtn = document.createElement("button");
    prevBtn.type = "button";
    prevBtn.className = "btn btn-sm btn-outline-danger";
    prevBtn.textContent = "Anterior";

    const nextBtn = document.createElement("button");
    nextBtn.type = "button";
    nextBtn.className = "btn btn-sm btn-outline-danger";
    nextBtn.textContent = "Seguinte";

    actions.appendChild(prevBtn);
    actions.appendChild(nextBtn);
    footer.appendChild(pageInfo);
    footer.appendChild(actions);
    table.parentElement.insertAdjacentElement("afterend", footer);

    const headers = Array.from(table.querySelectorAll("thead th"));
    headers.forEach((header, index) => {
      if (header.dataset.sortable === "false") return;
      header.classList.add("table-sort");
      header.addEventListener("click", () => {
        if (sortIndex === index) sortDirection *= -1;
        else {
          sortIndex = index;
          sortDirection = 1;
        }
        render();
      });
    });

    const getFilteredRows = () => {
      let rows = [...originalRows];
      if (query) rows = rows.filter((row) => row.textContent.toLowerCase().includes(query));
      if (sortIndex !== null) {
        rows.sort((a, b) => {
          const aValue = parseValue(a.children[sortIndex]?.textContent || "");
          const bValue = parseValue(b.children[sortIndex]?.textContent || "");
          if (aValue < bValue) return -1 * sortDirection;
          if (aValue > bValue) return 1 * sortDirection;
          return 0;
        });
      }
      return rows;
    };

    const render = () => {
      const filteredRows = getFilteredRows();
      const totalPages = Math.max(1, Math.ceil(filteredRows.length / pageSize));
      currentPage = Math.min(currentPage, totalPages);
      const start = (currentPage - 1) * pageSize;
      const end = start + pageSize;
      const visibleRows = filteredRows.slice(start, end);

      tbody.innerHTML = "";
      if (!visibleRows.length) {
        const row = document.createElement("tr");
        row.setAttribute("data-empty-row", "true");
        const cell = document.createElement("td");
        cell.colSpan = headers.length;
        cell.className = "text-center text-muted py-4";
        cell.textContent = "Sem resultados para a pesquisa atual.";
        row.appendChild(cell);
        tbody.appendChild(row);
      } else {
        visibleRows.forEach((row) => tbody.appendChild(row));
      }

      meta.textContent = `${filteredRows.length} resultado(s)`;
      pageInfo.textContent = `Página ${currentPage} de ${totalPages}`;
      prevBtn.disabled = currentPage === 1;
      nextBtn.disabled = currentPage === totalPages;
    };

    search.addEventListener("input", (event) => {
      query = event.target.value.trim().toLowerCase();
      currentPage = 1;
      render();
    });

    prevBtn.addEventListener("click", () => {
      if (currentPage > 1) {
        currentPage -= 1;
        render();
      }
    });

    nextBtn.addEventListener("click", () => {
      const totalPages = Math.max(1, Math.ceil(getFilteredRows().length / pageSize));
      if (currentPage < totalPages) {
        currentPage += 1;
        render();
      }
    });

    render();
  });
})();

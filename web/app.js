const $ = (selector) => document.querySelector(selector);

function setFeedback(element, message, tone = "success", links = []) {
  element.replaceChildren();
  element.className = `feedback ${tone}`;
  element.hidden = false;
  element.append(document.createTextNode(message));
  for (const item of links) {
    const link = document.createElement("a");
    link.href = item.href;
    link.textContent = item.label;
    link.download = "";
    element.append(link);
  }
}

async function request(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "No se pudo completar la solicitud.");
  return data;
}

async function loadStatus() {
  const container = $("#checks");
  const badge = $("#connection");
  try {
    const status = await request("/api/status");
    const rows = [
      ["Registro Google Sheets", status.registro],
      ["Historial de postulaciones", status.historial],
      ["Credencial de Google", status.credencial],
      ["Generación de PDF", status.dependencias],
      ["CV maestro", status.cv_maestro],
    ];
    container.replaceChildren(...rows.map(([label, ready]) => {
      const li = document.createElement("li");
      const dot = document.createElement("span");
      dot.className = `check-dot ${ready ? "good" : "bad"}`;
      const name = document.createElement("span");
      name.textContent = label;
      const state = document.createElement("span");
      state.className = "check-state";
      state.textContent = ready ? "Conectado" : "Pendiente";
      li.append(dot, name, state);
      return li;
    }));
    const listo = status.registro && status.historial && status.credencial;
    badge.querySelector("span:last-child").textContent = listo ? "Agente conectado" : "Configuración incompleta";
    badge.querySelector(".pulse").className = `pulse ${listo ? "good" : "warn"}`;
    $("#setup-note").hidden = listo;
  } catch {
    badge.querySelector("span:last-child").textContent = "No se pudo conectar";
    badge.querySelector(".pulse").className = "pulse warn";
  }
}

async function loadOpportunities() {
  const container = $("#opportunities");
  container.innerHTML = '<div class="loading"><span class="spinner"></span> Cargando registro…</div>';
  try {
    const data = await request("/api/postulaciones");
    const items = data.postulaciones.slice(0, 6);
    if (!items.length) {
      container.innerHTML = '<div class="empty">Todavía no hay oportunidades en el registro.</div>';
      return;
    }
    container.replaceChildren(...items.map((item) => {
      const article = document.createElement("article");
      article.className = "opportunity";
      const head = document.createElement("div");
      head.className = "opp-head";
      const company = document.createElement("span");
      company.className = "opp-company";
      company.textContent = item.empresa || "Empresa sin nombre";
      const badge = document.createElement("span");
      badge.className = `badge ${item.estado === "postulada" ? "applied" : item.estado === "descartada" ? "rejected" : ""}`;
      badge.textContent = item.estado || "revisar";
      const role = document.createElement("div");
      role.className = "opp-role";
      role.textContent = item.rol || "Puesto sin nombre";
      const date = document.createElement("div");
      date.className = "opp-date";
      date.textContent = item.fecha || "";
      head.append(company, badge);
      article.append(head, role, date);
      return article;
    }));
  } catch (error) {
    container.innerHTML = "";
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = error.message;
    container.append(empty);
  }
}

function values(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function bindForm(formId, feedbackId, endpoint, onSuccess) {
  const form = $(formId);
  const feedback = $(feedbackId);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    const original = button.textContent;
    button.textContent = "Procesando…";
    feedback.hidden = true;
    try {
      const result = await request(endpoint, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(values(form)),
      });
      onSuccess(result, feedback);
      form.reset();
      await Promise.all([loadStatus(), loadOpportunities()]);
    } catch (error) {
      setFeedback(feedback, error.message, "error");
    } finally {
      button.disabled = false;
      button.textContent = original;
    }
  });
}

bindForm("#register-form", "#register-feedback", "/api/postulaciones", (result, feedback) => {
  const revisando = result.estado === "revisar";
  setFeedback(feedback, revisando
    ? `Oportunidad guardada para revisar. ${result.motivo || ""}`
    : result.estado === "omitir"
      ? `No se agregó: ${result.motivo || "el agente la marcó como duplicada"}.`
      : "Oportunidad registrada correctamente.", revisando ? "warning" : result.estado === "omitir" ? "warning" : "success");
});

bindForm("#docs-form", "#docs-feedback", "/api/documentos", (result, feedback) => {
  setFeedback(feedback, "Listo. Descargá tus borradores:", "success", result.archivos.map((href, index) => ({href, label: index === 0 ? "Descargar CV" : "Descargar carta"})));
});

$("#refresh").addEventListener("click", loadStatus);
$("#reload-list").addEventListener("click", loadOpportunities);
loadStatus();
loadOpportunities();

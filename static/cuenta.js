const _eyeOpen = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
const _eyeClosed = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;

function togglePass(id, btn) {
    const inp = document.getElementById(id);
    const show = inp.type === "password";
    inp.type = show ? "text" : "password";
    btn.innerHTML = show ? _eyeClosed : _eyeOpen;
}

// ── Sesión (localStorage) ─────────────────────────────────────────
function getSession() {
    const s = localStorage.getItem("session");
    return s ? JSON.parse(s) : null;
}

function saveSession(user) {
    localStorage.setItem("session", JSON.stringify(user));
}

function clearSession() {
    localStorage.removeItem("session");
}

// ── Tabs auth ─────────────────────────────────────────────────────
function switchTab(tab) {
    document.getElementById("form-login").style.display = tab === "login" ? "block" : "none";
    document.getElementById("form-registro").style.display = tab === "registro" ? "block" : "none";
    document.getElementById("tab-login").classList.toggle("active", tab === "login");
    document.getElementById("tab-registro").classList.toggle("active", tab === "registro");
}

// ── Tabs panel ────────────────────────────────────────────────────
function switchPanelTab(tab, el) {
    document.getElementById("panel-pedidos").style.display = tab === "pedidos" ? "block" : "none";
    document.getElementById("panel-datos").style.display = tab === "datos" ? "block" : "none";
    document.querySelectorAll(".panel-tab").forEach(t => t.classList.remove("active"));
    el.classList.add("active");
}

// ── Login ─────────────────────────────────────────────────────────
async function hacerLogin() {
    const email = document.getElementById("login-email").value.trim();
    const password = document.getElementById("login-password").value;
    const errEl = document.getElementById("login-error");

    if (!email || !password) {
        mostrarError(errEl, "Completá email y contraseña.");
        return;
    }

    try {
        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Session-ID": window.getSessionId ? window.getSessionId() : "",
            },
            body: JSON.stringify({ email, password }),
        });

        if (!res.ok) {
            const err = await res.json();
            mostrarError(errEl, err.detail || "Email o contraseña incorrectos.");
            return;
        }

        const user = await res.json();
        saveSession(user);

        if (user.rol === "admin" || user.rol === "owner") {
            localStorage.setItem("admin_token", user.token);
            localStorage.setItem("admin_user", JSON.stringify(user));
        }

        mostrarPanel(user);

    } catch (e) {
        mostrarError(errEl, "Error de conexión. Intentá de nuevo.");
    }
}

// ── Registro ──────────────────────────────────────────────────────
async function hacerRegistro() {
    const name = document.getElementById("reg-name").value.trim();
    const email = document.getElementById("reg-email").value.trim();
    const password = document.getElementById("reg-password").value;
    const password2 = document.getElementById("reg-password2").value;
    const errEl = document.getElementById("registro-error");

    if (!name || !email || !password) {
        mostrarError(errEl, "Completá todos los campos.");
        return;
    }
    if (password.length < 8) {
        mostrarError(errEl, "La contraseña debe tener al menos 8 caracteres.");
        return;
    }
    if (password !== password2) {
        mostrarError(errEl, "Las contraseñas no coinciden.");
        return;
    }

    try {
        const res = await fetch("/api/auth/registro", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ nombre: name, email, password }),
        });

        if (!res.ok) {
            const err = await res.json();
            mostrarError(errEl, err.detail || "No se pudo crear la cuenta.");
            return;
        }

        const user = await res.json();
        saveSession(user);
        mostrarPanel(user);

    } catch (e) {
        mostrarError(errEl, "Error de conexión. Intentá de nuevo.");
    }
}

// ── Logout ────────────────────────────────────────────────────────
function hacerLogout() {
    clearSession();
    localStorage.removeItem("admin_token");
    localStorage.removeItem("admin_user");
    document.getElementById("cuenta-auth").style.display = "flex";
    document.getElementById("cuenta-panel").style.display = "none";
    updateCartCount();
    updateNavAdmin();
}

// ── Panel usuario ─────────────────────────────────────────────────
function mostrarPanel(user) {
    document.getElementById("cuenta-auth").style.display = "none";
    document.getElementById("cuenta-panel").style.display = "block";
    document.getElementById("panel-nombre").textContent = user.nombre;
    document.getElementById("datos-name").value = user.nombre;
    document.getElementById("datos-email").value = user.email;
    cargarPedidos(user.id);
    updateNavAdmin();
}

// ── Pedidos ───────────────────────────────────────────────────────
async function cargarPedidos(userId) {
    const lista = document.getElementById("pedidos-lista");
    lista.innerHTML = "<p style='color:var(--text-muted)'>Cargando pedidos...</p>";

    try {
        const session = getSession();
        const res = await fetch(`/api/ordenes/usuario/${userId}`, {
            headers: { "X-User-Id": session?.id || "" },
        });
        const pedidos = await res.json();

        if (pedidos.length === 0) {
            lista.innerHTML = `
                <div style="padding:3rem 0; text-align:center">
                    <p style="color:var(--text-muted); margin-bottom:1.5rem">
                        Todavía no hiciste ningún pedido.
                    </p>
                    <a href="/catalogo" class="btn-outline">Ver colección</a>
                </div>
            `;
            return;
        }

        const statusLabel = {
            pending:   "⏳ Pendiente de pago",
            verifying: "🔍 Comprobante en revisión",
            paid:      "✅ Pagado",
            preparing: "🔨 En preparación",
            shipped:   "🚚 Enviado",
            delivered: "📦 Entregado",
            cancelled: "❌ Cancelado",
        };

        const shippingLabel = {
            domicilio: "Envío a domicilio",
            sucursal:  "Retiro en sucursal",
            personal:  "Entrega personal",
        };

        lista.innerHTML = pedidos.map(p => {
            const esTransfer = p.payment_method === "transfer";
            const puedeSubir = esTransfer && ["pending", "verifying"].includes(p.status);
            const labelComprobante = p.comprobante_url
                ? "Reemplazar comprobante"
                : "Subir comprobante";

            return `
            <div class="pedido-card">
                <div class="pedido-header">
                    <div>
                        <p class="pedido-num">Pedido #${p.id}</p>
                        <p class="pedido-fecha">${new Date(p.created_at).toLocaleDateString("es-AR", {
                            day: "numeric", month: "long", year: "numeric"
                        })}</p>
                    </div>
                    <span class="pedido-status">${statusLabel[p.status] || p.status}</span>
                </div>
                <div class="pedido-items">
                    ${p.items.map(i => `
                        <p class="pedido-item">
                            ${i.product_name} × ${i.quantity}
                            <span>$${(i.subtotal).toLocaleString("es-AR")}</span>
                        </p>
                    `).join("")}
                </div>
                <div class="pedido-total">
                    Total: $${p.total.toLocaleString("es-AR")}
                    ${p.shipping_cost > 0 ? `<span style="font-size:0.78rem;color:var(--text-muted);margin-left:0.5rem">(envío: $${p.shipping_cost.toLocaleString("es-AR")})</span>` : ""}
                </div>
                <div style="font-size:0.82rem;color:var(--text-muted);margin-top:0.4rem">
                    ${shippingLabel[p.shipping_method] || ""}
                    ${p.shipping_branch ? ` — ${p.shipping_branch}` : ""}
                    ${p.tracking_number ? `<br>Seguimiento CA: <strong>${p.tracking_number}</strong>` : ""}
                    ${p.factura_numero  ? `<br>Factura: <strong>${p.factura_numero}</strong>` : ""}
                </div>
                ${puedeSubir ? `
                <div style="margin-top:0.75rem;padding-top:0.75rem;border-top:1px solid var(--border-light,#eee)">
                    <input type="file" id="comp-input-${p.id}" accept="image/*,.pdf" style="display:none"
                           onchange="uploadComprobante(${p.id}, this)">
                    <button class="btn-outline" style="font-size:0.8rem;padding:0.4rem 1rem"
                            onclick="document.getElementById('comp-input-${p.id}').click()">
                        ${labelComprobante}
                    </button>
                    <span id="comp-msg-${p.id}" style="font-size:0.8rem;margin-left:0.75rem;color:var(--text-muted)"></span>
                </div>` : ""}
            </div>`;
        }).join("");

    } catch (e) {
        lista.innerHTML = "<p style='color:var(--text-muted)'>Error cargando pedidos.</p>";
    }
}

// ── Guardar datos ─────────────────────────────────────────────────
function guardarDatos() {
    document.getElementById("datos-success").style.display = "block";
    setTimeout(() => {
        document.getElementById("datos-success").style.display = "none";
    }, 3000);
}

// ── Upload comprobante desde cuenta ───────────────────────────────
async function uploadComprobante(ordenId, input) {
    const file = input.files[0];
    if (!file) return;

    const msg = document.getElementById(`comp-msg-${ordenId}`);
    msg.textContent = "Enviando...";

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch(`/api/ordenes/${ordenId}/comprobante`, {
            method: "POST",
            body:   formData,
        });
        if (res.ok) {
            msg.textContent = "✅ Comprobante enviado";
            msg.style.color = "var(--sage, green)";
            const session = getSession();
            setTimeout(() => cargarPedidos(session.id), 1500);
        } else {
            const data = await res.json().catch(() => ({}));
            msg.textContent = data.detail || "Error al enviar.";
            msg.style.color = "#c0392b";
        }
    } catch {
        msg.textContent = "Error de conexión.";
        msg.style.color = "#c0392b";
    }
}

// ── Helper ────────────────────────────────────────────────────────
function mostrarError(el, msg) {
    el.textContent = msg;
    el.style.display = "block";
}

// ── Init ──────────────────────────────────────────────────────────
const session = getSession();
if (session) {
    mostrarPanel(session);
}
updateCartCount();
updateNavAdmin();
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
            headers: { "Content-Type": "application/json" },
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
            pending: "⏳ Pendiente",
            paid: "✅ Pagado",
            preparing: "🔨 Preparando",
            shipped: "🚚 Enviado",
            delivered: "📦 Entregado",
            cancelled: "❌ Cancelado",
        };

        lista.innerHTML = pedidos.map(p => `
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
                </div>
            </div>
        `).join("");

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
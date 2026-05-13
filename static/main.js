// ── Carrito (localStorage) ─────────────────────────────────────────
function getCart() {
    return JSON.parse(localStorage.getItem("cart") || "{}");
}

function saveCart(cart) {
    localStorage.setItem("cart", JSON.stringify(cart));
    updateCartCount();
}

function addToCart(producto) {
    const cart = getCart();
    if (cart[producto.id]) {
        cart[producto.id].quantity += 1;
    } else {
        cart[producto.id] = { ...producto, quantity: 1 };
    }
    saveCart(cart);
    showToast(`${producto.nombre} agregado al carrito`);
}

function updateCartCount() {
    const cart    = getCart();
    const count   = Object.values(cart).reduce((sum, i) => sum + i.quantity, 0);
    const session = JSON.parse(localStorage.getItem("session") || "null");
    const el      = document.getElementById("cart-count");
    if (el) {
        el.textContent   = count;
        el.style.display = (session && count > 0) ? "flex" : "none";
    }
}

// ── Cart Drawer ───────────────────────────────────────────────────
let _drawerCosts = { domicilio: 5000, sucursal: 3500, free_threshold: 50000 };

async function _loadDrawerCosts() {
    try {
        const res = await fetch("/api/envio/costos");
        _drawerCosts = await res.json();
    } catch {}
}

function toggleCartDrawer(forceClose) {
    if (!forceClose && !JSON.parse(localStorage.getItem("session") || "null")) {
        window.location = "/cuenta";
        return;
    }
    const drawer  = document.getElementById("cart-drawer");
    const overlay = document.getElementById("cart-overlay");
    if (!drawer) { console.warn("cart-drawer not found"); return; }
    const opening = forceClose ? false : !drawer.classList.contains("open");
    drawer.classList.toggle("open", opening);
    drawer.style.transform = opening ? "translateX(0)" : "translateX(100%)";
    overlay.style.display  = opening ? "block" : "none";
    document.body.style.overflow = "";
    if (opening) {
        _loadDrawerCosts().then(_renderCartDrawer);
        sessionStorage.setItem("cart_open", "1");
    } else {
        sessionStorage.removeItem("cart_open");
    }
}

function _renderCartDrawer() {
    const cart  = getCart();
    const items = Object.values(cart);
    const body  = document.getElementById("cart-drawer-items");
    const foot  = document.getElementById("cart-drawer-footer");
    const fmt   = n => `$${n.toLocaleString("es-AR")}`;
    if (!body) return;

    if (items.length === 0) {
        body.innerHTML = `<div style="text-align:center;padding:3rem 0;color:#888;font-size:0.85rem">Tu carrito está vacío</div>`;
        if (foot) foot.style.display = "none";
        return;
    }

    body.innerHTML = items.map(i => `
        <div style="display:grid;grid-template-columns:56px 1fr auto;gap:0.75rem;
                    align-items:center;padding:0.85rem 0;
                    border-bottom:1px solid rgba(196,135,90,0.1)">
            <img src="${i.imagen || `https://picsum.photos/seed/${i.slug}/200/260`}"
                 alt="${i.nombre}"
                 style="width:56px;height:72px;object-fit:cover;filter:sepia(8%)">
            <div>
                <div style="font-size:0.82rem;color:#2c1f14;line-height:1.3">${i.nombre}</div>
                <div style="font-size:0.75rem;color:#888;margin-top:0.2rem">${fmt(i.precio)} × ${i.quantity}</div>
            </div>
            <div style="font-family:'Cormorant Garamond',serif;font-size:1rem;color:#2c1f14;white-space:nowrap">
                ${fmt(i.precio * i.quantity)}
            </div>
        </div>
    `).join("");

    const subtotal  = items.reduce((s, i) => s + i.precio * i.quantity, 0);
    const envioGratis = subtotal >= _drawerCosts.free_threshold;
    const envio     = envioGratis ? 0 : _drawerCosts.domicilio;
    const total     = subtotal + envio;
    const hint      = envioGratis
        ? `<span style="color:#7a8c6e;font-size:0.75rem">✦ Envío gratis aplicado</span>`
        : `<span style="font-size:0.75rem;color:#888">Agregá ${fmt(_drawerCosts.free_threshold - subtotal)} más para envío gratis</span>`;

    if (foot) {
        foot.style.display = "block";
        foot.innerHTML = `
            <div style="font-size:0.78rem;color:#888;margin-bottom:0.75rem;padding-bottom:0.75rem;
                        border-bottom:1px solid rgba(196,135,90,0.1)">
                <div style="display:flex;justify-content:space-between;margin-bottom:0.3rem">
                    <span>Subtotal</span><span style="color:#2c1f14">${fmt(subtotal)}</span>
                </div>
                <div style="display:flex;justify-content:space-between;margin-bottom:0.4rem">
                    <span>Envío (domicilio)</span>
                    <span style="color:#2c1f14">${envioGratis ? "Gratis" : fmt(envio)}</span>
                </div>
                ${hint}
            </div>
            <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:1rem">
                <span style="font-size:0.75rem;letter-spacing:0.15em;text-transform:uppercase;color:#888">Total</span>
                <span style="font-family:'Cormorant Garamond',serif;font-size:1.5rem;color:#2c1f14">${fmt(total)}</span>
            </div>
            <button onclick="_drawerPagar()"
                    style="width:100%;background:#2c1f14;color:#f5f0e8;border:none;
                           padding:0.9rem;font-family:'Jost',sans-serif;font-size:0.78rem;
                           letter-spacing:0.15em;text-transform:uppercase;cursor:pointer">
                Proceder al pago
            </button>
        `;
    }
}

function _drawerPagar() {
    if (window.location.pathname === "/carrito" && typeof abrirCheckout === "function") {
        toggleCartDrawer(true);
        abrirCheckout();
    } else {
        window.location = "/carrito";
    }
}

// ── Account icon ─────────────────────────────────────────────────
function updateNavAccount() {
    const session = JSON.parse(localStorage.getItem("session") || "null");
    const btn = document.getElementById("account-icon-btn");
    if (!btn) return;
    if (session) {
        btn.classList.add("logged-in");
        btn.title = session.nombre || session.name || "Mi cuenta";
    } else {
        btn.classList.remove("logged-in");
        btn.title = "Iniciar sesión";
    }
}

function toggleAccountMenu() {
    const session = JSON.parse(localStorage.getItem("session") || "null");
    if (!session) { window.location = "/cuenta"; return; }

    const menu = document.getElementById("account-menu");
    if (!menu) return;
    const isOpen = menu.style.display !== "none";
    if (isOpen) { menu.style.display = "none"; return; }

    const btn = document.getElementById("account-icon-btn");
    if (btn) {
        const r = btn.getBoundingClientRect();
        menu.style.top   = (r.bottom + 8) + "px";
        menu.style.right = (window.innerWidth - r.right) + "px";
    }
    menu.style.display = "block";

    setTimeout(() => {
        document.addEventListener("click", function _close(e) {
            if (!menu.contains(e.target) && e.target.id !== "account-icon-btn") {
                menu.style.display = "none";
                document.removeEventListener("click", _close);
            }
        });
    }, 10);
}

function hacerLogoutNav() {
    localStorage.removeItem("session");
    const menu = document.getElementById("account-menu");
    if (menu) menu.style.display = "none";
    updateNavAccount();
    updateNavAdmin();
    updateCartCount();
    window.location = "/";
}

function updateNavAdmin() {
    const session = JSON.parse(localStorage.getItem("session") || "null");
    const adminLink = document.getElementById("nav-admin-link");
    if (adminLink) {
        if (session && (session.rol === "admin" || session.rol === "owner")) {
            adminLink.style.display = "inline";
        } else {
            adminLink.style.display = "none";
        }
    }
}

// ── Toast ─────────────────────────────────────────────────────────
function showToast(msg) {
    const toast = document.createElement("div");
    toast.textContent = msg;
    toast.style.cssText = `
        position:fixed; bottom:2rem; right:2rem; z-index:999;
        background:var(--earth); color:var(--cream);
        padding:1rem 1.5rem; font-size:0.85rem;
        letter-spacing:0.1em; opacity:0;
        transition:opacity 0.3s;
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.style.opacity = "1", 10);
    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}

// ── Productos destacados ──────────────────────────────────────────
async function cargarDestacados() {
    const grid = document.getElementById("products-grid");
    if (!grid) return;
    try {
        const res = await fetch("/api/productos?destacados=true");
        const productos = await res.json();
        if (productos.length === 0) {
            grid.innerHTML = "<p style='color:var(--text-muted)'>Próximamente...</p>";
            return;
        }
        grid.innerHTML = productos.map(p => {
            const precio = `$${p.precio.toLocaleString("es-AR")}`;
            const imagen = p.imagen || `https://picsum.photos/seed/${p.slug}/400/530`;
            const tag = p.categoria || p.tecnica || "Cerámica";
            return `
                <div class="product-card" onclick="window.location='/producto/${p.slug}'">
                    <div class="product-img">
                        <img src="${imagen}" alt="${p.nombre}" loading="lazy">
                        <div class="product-tag">${tag}</div>
                    </div>
                    <div class="product-info">
                        <h3 class="product-name">${p.nombre}</h3>
                        <p class="product-desc">${p.descripcion || ""}</p>
                        <div class="product-footer">
                            <span class="product-price">${precio}</span>
                            <button class="btn-pedido" onclick="event.stopPropagation(); addToCart(${JSON.stringify(p).replace(/"/g, '&quot;')})">
                                ${p.stock === 0 ? "Consultar" : "Agregar"}
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join("");

        // Scroll al hash si existe
        if (window.location.hash) {
            setTimeout(() => {
                const el = document.getElementById(window.location.hash.slice(1));
                if (el) el.scrollIntoView({ behavior: "smooth" });
            }, 300);
        }

    } catch (e) {
        console.error("Error cargando productos:", e);
    }
}

// ── Contacto ──────────────────────────────────────────────────────
async function enviarConsulta() {
    const nombre = document.getElementById("c-name")?.value.trim();
    const email = document.getElementById("c-email")?.value.trim();
    const msg = document.getElementById("c-msg")?.value.trim();

    if (!nombre || !email || !msg) {
        alert("Por favor completá todos los campos.");
        return;
    }

    try {
        const res = await fetch("/api/contacto", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ nombre, email, mensaje: msg }),
        });

        if (!res.ok) {
            alert("Error enviando el mensaje. Intentá de nuevo.");
            return;
        }

        document.getElementById("contact-success").style.display = "block";
        document.getElementById("c-name").value = "";
        document.getElementById("c-email").value = "";
        document.getElementById("c-msg").value = "";

    } catch (e) {
        alert("Error de conexión. Intentá de nuevo.");
    }
}

function toggleMenu() {
    const menu = document.getElementById("nav-menu");
    if (menu) menu.classList.toggle("open");
}

function scrollToSection(id) {
    setTimeout(() => {
        const el = document.getElementById(id);
        if (el) el.scrollIntoView({ behavior: "smooth" });
    }, 100);
}

// Cerrar menú al hacer click en un link
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".nav-menu a").forEach(link => {
        link.addEventListener("click", () => {
            const menu = document.getElementById("nav-menu");
            if (menu) menu.classList.remove("open");
        });
    });
});

// ── Session tracking ──────────────────────────────────────────────
function getSessionId() {
    let sid = sessionStorage.getItem("session_id");
    if (!sid) {
        sid = crypto.randomUUID();
        sessionStorage.setItem("session_id", sid);
        // Nueva sesión: notificar al backend
        fetch("/api/session/start", {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: sid,
                entry_page: window.location.pathname,
                referrer:   document.referrer || "",
            }),
        }).catch(() => {});
    }
    return sid;
}

// Exponer para que otros scripts lo usen
window.getSessionId = getSessionId;

// ── Init ──────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    // Inyectar drawer HTML
    document.body.insertAdjacentHTML("beforeend", `
        <div id="cart-overlay"
             style="display:none;position:fixed;inset:0;background:rgba(44,31,20,0.15);z-index:300;pointer-events:none"></div>
        <div id="cart-drawer"
             style="position:fixed;top:0;right:0;bottom:0;width:380px;max-width:92vw;
                    background:#f5f0e8;z-index:301;transform:translateX(100%);
                    transition:transform 0.3s ease;display:flex;flex-direction:column;
                    box-shadow:-4px 0 32px rgba(44,31,20,0.14)">
            <div style="display:flex;justify-content:space-between;align-items:center;
                        padding:1.5rem 1.75rem;border-bottom:1px solid rgba(196,135,90,0.15);flex-shrink:0">
                <span style="font-family:'Cormorant Garamond',serif;font-size:1.3rem;
                             font-weight:400;letter-spacing:0.1em;color:#2c1f14">Carrito</span>
                <button onclick="toggleCartDrawer()"
                        style="background:none;border:none;cursor:pointer;font-size:1.5rem;
                               color:#888;line-height:1;padding:0.2rem">×</button>
            </div>
            <div id="cart-drawer-items" style="flex:1;overflow-y:auto;padding:1rem 1.75rem"></div>
            <div id="cart-drawer-footer" style="display:none;padding:1.25rem 1.75rem;
                 border-top:1px solid rgba(196,135,90,0.15);flex-shrink:0"></div>
        </div>
    `);

    // Inyectar menú de cuenta
    document.body.insertAdjacentHTML("beforeend", `
        <div id="account-menu"
             style="display:none;position:fixed;background:#faf8f4;
                    border:1px solid rgba(196,135,90,0.2);
                    box-shadow:0 4px 16px rgba(44,31,20,0.1);
                    min-width:160px;z-index:302;padding:0.4rem 0">
            <a href="/cuenta"
               style="display:block;padding:0.6rem 1.2rem;font-size:0.8rem;
                      letter-spacing:0.12em;text-transform:uppercase;
                      color:#2c1f14;text-decoration:none;font-family:'Jost',sans-serif">
                Mi cuenta
            </a>
            <button onclick="hacerLogoutNav()"
                    style="display:block;width:100%;text-align:left;padding:0.6rem 1.2rem;
                           font-size:0.8rem;letter-spacing:0.12em;text-transform:uppercase;
                           color:#c4875a;background:none;border:none;cursor:pointer;
                           font-family:'Jost',sans-serif">
                Salir
            </button>
        </div>
    `);

    if (sessionStorage.getItem("cart_open")) toggleCartDrawer();

    getSessionId();
    updateCartCount();
    updateNavAccount();
    cargarDestacados();
    updateNavAdmin();
});
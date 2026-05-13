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

// ── Shipping costs (shared by drawer + checkout) ──────────────────
let shippingCosts = { domicilio: 5000, sucursal: 3500, free_threshold: 50000 };

async function cargarCostosEnvio() {
    try {
        const res = await fetch("/api/envio/costos");
        shippingCosts = await res.json();
    } catch {}
}

function calcularEnvio(subtotal, method) {
    if (subtotal >= shippingCosts.free_threshold) return 0;
    return method === "sucursal" ? shippingCosts.sucursal : shippingCosts.domicilio;
}

// ── Cart Drawer ───────────────────────────────────────────────────

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
        cargarCostosEnvio().then(_renderCartDrawer);
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
    const envioGratis = subtotal >= shippingCosts.free_threshold;
    const envio     = envioGratis ? 0 : shippingCosts.domicilio;
    const total     = subtotal + envio;
    const hint      = envioGratis
        ? `<span style="color:#7a8c6e;font-size:0.75rem">✦ Envío gratis aplicado</span>`
        : `<span style="font-size:0.75rem;color:#888">Agregá ${fmt(shippingCosts.free_threshold - subtotal)} más para envío gratis</span>`;

    if (foot) {
        foot.style.display = "block";
        foot.innerHTML = `
            <div style="font-family:'Cormorant Garamond',serif;font-size:1.1rem;letter-spacing:0.08em;
                        color:#2c1f14;margin-bottom:0.75rem">Resumen</div>
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
    toggleCartDrawer(true);
    abrirCheckout();
}

// ── Checkout modal ────────────────────────────────────────────────
function abrirCheckout() {
    cargarCostosEnvio().then(() => actualizarResumen());
    document.getElementById("checkout-success").style.display = "none";
    document.getElementById("checkout-error").style.display  = "none";
    const modal = document.getElementById("modal-overlay");
    modal.style.display = "flex";
    document.body.style.overflow = "hidden";
}

function cerrarModal() {
    document.getElementById("modal-overlay").style.display = "none";
    document.body.style.overflow = "";
    const count  = Object.values(getCart()).reduce((s, i) => s + i.quantity, 0);
    const drawer = document.getElementById("cart-drawer");
    if (drawer) {
        if (count > 0 && !drawer.classList.contains("open")) toggleCartDrawer();
        if (count === 0 && drawer.classList.contains("open"))  toggleCartDrawer(true);
    }
    updateCartCount();
}

function selectShipping(method) {
    const active   = { border: "2px solid #c4875a", background: "#fdf6f0" };
    const inactive = { border: "2px solid #ddd",    background: "#fff"    };
    const domEl = document.getElementById("sm-domicilio-box");
    const sucEl = document.getElementById("sm-sucursal-box");
    const isDom = method === "domicilio";
    domEl.style.border      = isDom ? active.border      : inactive.border;
    domEl.style.background  = isDom ? active.background  : inactive.background;
    sucEl.style.border      = isDom ? inactive.border     : active.border;
    sucEl.style.background  = isDom ? inactive.background : active.background;
    document.getElementById(isDom ? "sm-domicilio" : "sm-sucursal").checked = true;
    document.getElementById("sh-fields-domicilio").style.display = isDom ? "block" : "none";
    document.getElementById("sh-fields-sucursal").style.display  = isDom ? "none"  : "block";
    actualizarResumen();
}

function actualizarResumen() {
    const cart     = getCart();
    const subtotal = Object.values(cart).reduce((s, i) => s + i.precio * i.quantity, 0);
    const method   = document.querySelector("input[name='shipping_method']:checked")?.value || "domicilio";
    const envio    = calcularEnvio(subtotal, method);
    const total    = subtotal + envio;
    const fmt      = n => `$${n.toLocaleString("es-AR")}`;
    const resumen  = document.getElementById("modal-resumen");
    if (resumen) resumen.innerHTML = `
        <div class="resumen-linea"><span>Subtotal</span><span>${fmt(subtotal)}</span></div>
        <div class="resumen-linea"><span>Envío</span><span>${envio === 0 ? "Gratis" : fmt(envio)}</span></div>
        <div class="resumen-linea resumen-total"><span>Total</span><span>${fmt(total)}</span></div>
    `;
    const costoEl = document.getElementById("sh-costo-envio");
    if (costoEl) costoEl.textContent = envio === 0 ? "✓ Envío gratis" : `Costo de envío: ${fmt(envio)}`;
}

function selectPayment(method) {
    const active   = { border: "2px solid #c4875a", background: "#fdf6f0" };
    const inactive = { border: "2px solid #ddd",    background: "#fff"    };
    const mp = document.getElementById("pm-mp-box");
    const tr = document.getElementById("pm-transfer-box");
    const s  = method === "mp" ? { mp: active, tr: inactive } : { mp: inactive, tr: active };
    mp.style.border = s.mp.border; mp.style.background = s.mp.background;
    tr.style.border = s.tr.border; tr.style.background = s.tr.background;
    document.getElementById(method === "mp" ? "pm-mp" : "pm-transfer").checked = true;
}

async function confirmarPedido() {
    const name   = document.getElementById("sh-name").value.trim();
    const email  = document.getElementById("sh-email").value.trim();
    const phone  = document.getElementById("sh-phone").value.trim();
    const notes  = document.getElementById("sh-notes").value.trim();
    const shippingMethod = document.querySelector("input[name='shipping_method']:checked").value;
    const isDom  = shippingMethod === "domicilio";
    const address  = isDom ? document.getElementById("sh-address").value.trim()    : "";
    const city     = isDom ? document.getElementById("sh-city").value.trim()       : "";
    const province = isDom ? document.getElementById("sh-province").value.trim()   : document.getElementById("sh-province-s").value.trim();
    const zip      = isDom ? document.getElementById("sh-zip").value.trim()        : "";
    const branch   = isDom ? "" : document.getElementById("sh-branch").value.trim();

    if (!name || !email) { _errCheckout("Por favor completá nombre y email."); return; }
    if (isDom && (!address || !city || !province || !zip)) { _errCheckout("Por favor completá todos los campos de dirección."); return; }
    if (!isDom && !branch) { _errCheckout("Por favor ingresá la sucursal de Correo Argentino."); return; }

    const items = Object.values(getCart()).map(i => ({
        producto_id: i.id, cantidad: i.quantity, precio: i.precio, nombre: i.nombre,
    }));
    try {
        const res = await fetch("/api/ordenes", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-Session-ID": window.getSessionId ? window.getSessionId() : "" },
            body: JSON.stringify({
                nombre: name, email, telefono: phone, direccion: address, ciudad: city,
                provincia: province, cp: zip, notas: notes,
                payment_method: document.querySelector("input[name='payment_method']:checked").value,
                shipping_method: shippingMethod, shipping_branch: branch, items,
            }),
        });
        if (!res.ok) { const e = await res.json(); _errCheckout(e.detail || "Error al procesar tu pedido."); return; }
        const orden = await res.json();
        document.getElementById("checkout-success").style.display = "block";
        document.getElementById("checkout-error").style.display   = "none";
        if (orden.mp_url) {
            setTimeout(() => window.location = orden.mp_url, 1500);
        } else if (orden.payment_method === "transfer") {
            setTimeout(() => window.location = `/pago/transferencia?orden_id=${orden.orden_id}&total=${orden.total}`, 1500);
        } else {
            setTimeout(() => window.location = "/pago/exitoso", 1500);
        }
    } catch { _errCheckout("Error de conexión. Intentá de nuevo."); }
}

function _errCheckout(msg) {
    const el = document.getElementById("checkout-error");
    el.textContent = msg; el.style.display = "block";
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

    // Inyectar modal checkout
    document.body.insertAdjacentHTML("beforeend", `
        <div id="modal-overlay" onclick="if(event.target===this)cerrarModal()"
             style="position:fixed;inset:0;background:rgba(44,31,20,0.75);z-index:9999;
                    display:none;align-items:center;justify-content:center;padding:2rem">
            <div style="background:#faf8f4;padding:2.5rem;width:100%;max-width:520px;
                        max-height:90vh;overflow-y:auto;position:relative;border-radius:2px">
                <button onclick="cerrarModal()"
                        style="position:absolute;top:1rem;right:1rem;background:none;border:none;
                               cursor:pointer;font-size:1.4rem;color:#888;line-height:1">×</button>
                <p class="section-eyebrow">Último paso</p>
                <h3 class="modal-title">Datos de envío</h3>
                <div class="form-group"><label>Nombre completo</label>
                    <input type="text" id="sh-name" placeholder="María García"/></div>
                <div class="form-group"><label>Email</label>
                    <input type="email" id="sh-email" placeholder="maria@email.com"/></div>
                <div class="form-group"><label>Teléfono</label>
                    <input type="tel" id="sh-phone" placeholder="+54 11 1234-5678"/></div>
                <div class="form-group" style="margin-bottom:1.25rem">
                    <label style="margin-bottom:0.75rem;display:block">Tipo de envío</label>
                    <input type="radio" name="shipping_method" value="domicilio" checked id="sm-domicilio" style="display:none">
                    <input type="radio" name="shipping_method" value="sucursal" id="sm-sucursal" style="display:none">
                    <div style="display:flex;gap:0.75rem">
                        <div id="sm-domicilio-box" onclick="selectShipping('domicilio')"
                             style="flex:1;cursor:pointer;border:2px solid #c4875a;background:#fdf6f0;
                                    padding:0.9rem;text-align:center;border-radius:2px;font-size:0.85rem">
                            Envío a domicilio</div>
                        <div id="sm-sucursal-box" onclick="selectShipping('sucursal')"
                             style="flex:1;cursor:pointer;border:2px solid #ddd;background:#fff;
                                    padding:0.9rem;text-align:center;border-radius:2px;font-size:0.85rem">
                            Retiro en sucursal</div>
                    </div>
                    <p id="sh-costo-envio" style="font-size:0.82rem;color:var(--text-muted);margin-top:0.5rem;text-align:right"></p>
                </div>
                <div id="sh-fields-domicilio">
                    <div class="form-group"><label>Dirección</label>
                        <input type="text" id="sh-address" placeholder="Av. Corrientes 1234, Piso 2"/></div>
                    <div class="form-row">
                        <div class="form-group"><label>Ciudad</label>
                            <input type="text" id="sh-city" placeholder="Buenos Aires"/></div>
                        <div class="form-group"><label>Provincia</label>
                            <input type="text" id="sh-province" placeholder="CABA"/></div>
                    </div>
                    <div class="form-group"><label>Código postal</label>
                        <input type="text" id="sh-zip" placeholder="1043"/></div>
                </div>
                <div id="sh-fields-sucursal" style="display:none">
                    <div class="form-group"><label>Sucursal de Correo Argentino</label>
                        <input type="text" id="sh-branch" placeholder="Ej: Sucursal Palermo, Buenos Aires"/>
                        <p style="font-size:0.78rem;color:var(--text-muted);margin-top:0.3rem">
                            Ingresá el nombre o dirección de la sucursal.</p></div>
                    <div class="form-group"><label>Provincia</label>
                        <input type="text" id="sh-province-s" placeholder="Buenos Aires"/></div>
                </div>
                <div class="form-group"><label>Notas (opcional)</label>
                    <textarea id="sh-notes" placeholder="Instrucciones especiales..."></textarea></div>
                <div class="modal-resumen" id="modal-resumen"></div>
                <div class="form-group" style="margin-bottom:1.5rem">
                    <label style="margin-bottom:0.75rem;display:block">Método de pago</label>
                    <input type="radio" name="payment_method" value="mp" checked id="pm-mp" style="display:none">
                    <input type="radio" name="payment_method" value="transfer" id="pm-transfer" style="display:none">
                    <div style="display:flex;gap:0.75rem">
                        <div id="pm-mp-box" onclick="selectPayment('mp')"
                             style="flex:1;cursor:pointer;border:2px solid #c4875a;background:#fdf6f0;
                                    padding:0.9rem;text-align:center;border-radius:2px;font-size:0.85rem">
                            Mercado Pago</div>
                        <div id="pm-transfer-box" onclick="selectPayment('transfer')"
                             style="flex:1;cursor:pointer;border:2px solid #ddd;background:#fff;
                                    padding:0.9rem;text-align:center;border-radius:2px;font-size:0.85rem">
                            Transferencia</div>
                    </div>
                </div>
                <button class="btn-primary" style="width:100%" onclick="confirmarPedido()">Confirmar y pagar</button>
                <div class="success-msg" id="checkout-success">¡Pedido recibido! Te enviamos un email de confirmación.</div>
                <div class="error-msg" id="checkout-error"></div>
            </div>
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
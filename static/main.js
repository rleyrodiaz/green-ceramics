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
    const cart = getCart();
    const count = Object.values(cart).reduce((sum, i) => sum + i.quantity, 0);
    const el = document.getElementById("cart-count");
    if (el) el.textContent = count;
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
            const stockClass = p.stock === 0 ? "no-stock" : p.stock <= 3 ? "low-stock" : "in-stock";
            const stockText = p.stock === 0 ? "Sin stock" : p.stock <= 3 ? `Últimas ${p.stock}` : "Disponible";
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

    } catch (e) {
        console.error("Error cargando productos:", e);
    }
}

// ── Contacto ──────────────────────────────────────────────────────
function enviarConsulta() {
    const name = document.getElementById("c-name")?.value.trim();
    const email = document.getElementById("c-email")?.value.trim();
    const msg = document.getElementById("c-msg")?.value.trim();
    if (!name || !email || !msg) {
        alert("Por favor completá todos los campos.");
        return;
    }
    // TODO: conectar con endpoint real
    document.getElementById("contact-success").style.display = "block";
    document.getElementById("c-name").value = "";
    document.getElementById("c-email").value = "";
    document.getElementById("c-msg").value = "";
}

function toggleMenu() {
    const menu = document.getElementById("nav-menu");
    if (menu) menu.classList.toggle("open");
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

// ── Init ──────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    updateCartCount();
    cargarDestacados();
    updateNavAdmin();
});
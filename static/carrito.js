// ── Render carrito ────────────────────────────────────────────────
function renderCarrito() {
    const layout = document.getElementById("carrito-layout");
    const cart = getCart();
    const items = Object.values(cart);

    if (items.length === 0) {
        layout.innerHTML = `
            <div class="carrito-vacio">
                <p class="section-eyebrow">Nada por aquí</p>
                <h2 class="section-title">Tu carrito está vacío</h2>
                <p style="color:var(--text-muted); margin-bottom:2rem">
                    Explorá la colección y agregá las piezas que te gusten.
                </p>
                <a href="/catalogo" class="btn-primary">Ver colección</a>
            </div>`;
        return;
    }

    const subtotal = items.reduce((sum, i) => sum + i.precio * i.quantity, 0);
    const envio = subtotal >= 50000 ? 0 : 3500;
    const total = subtotal + envio;
    const fmtPrecio = n => `$${n.toLocaleString("es-AR")}`;

    const itemsHTML = items.map(item => `
        <div style="display:grid;grid-template-columns:100px 1fr;gap:1.5rem;padding:1.5rem 0;border-bottom:1px solid rgba(196,135,90,0.12)">
            <div style="width:100px;height:130px;overflow:hidden;background:var(--sand)">
                <img src="${item.imagen || `https://picsum.photos/seed/${item.slug}/200/260`}"
                    alt="${item.nombre}"
                    style="width:100%;height:100%;object-fit:cover;filter:sepia(10%)" />
            </div>
            <div style="display:flex;flex-direction:column;justify-content:space-between">
                <div>
                    <p style="font-size:0.7rem;letter-spacing:0.2em;text-transform:uppercase;color:var(--clay);margin-bottom:0.3rem">${item.categoria || "Cerámica"}</p>
                    <h3 style="font-family:'Cormorant Garamond',serif;font-size:1.2rem;font-weight:400;color:var(--earth);margin-bottom:0.3rem">${item.nombre}</h3>
                    <p style="font-size:0.9rem;color:var(--text-muted)">${fmtPrecio(item.precio)} c/u</p>
                </div>
                <div style="display:flex;flex-direction:column;gap:0.75rem;margin-top:1rem">
                    <div style="display:flex;align-items:center;gap:1rem;border:1px solid rgba(44,31,20,0.2);padding:0.4rem 0.8rem;width:fit-content">
                        <button onclick="actualizarItem(${item.id}, ${item.quantity - 1})" style="background:none;border:none;cursor:pointer;font-size:1.1rem;color:var(--earth);line-height:1">−</button>
                        <span style="font-size:0.95rem;min-width:1.5rem;text-align:center">${item.quantity}</span>
                        <button onclick="actualizarItem(${item.id}, ${item.quantity + 1})" style="background:none;border:none;cursor:pointer;font-size:1.1rem;color:var(--earth);line-height:1">+</button>
                    </div>
                    <p style="font-family:'Cormorant Garamond',serif;font-size:1.3rem;color:var(--earth)">${fmtPrecio(item.precio * item.quantity)}</p>
                    <button onclick="eliminarItem(${item.id})" style="background:none;border:none;font-family:'Jost',sans-serif;font-size:0.75rem;letter-spacing:0.1em;text-transform:uppercase;color:var(--text-muted);cursor:pointer;padding:0;text-align:left">Eliminar</button>
                </div>
            </div>
        </div>
    `).join("");
    const resumenHTML = `
        <h3 class="carrito-resumen-titulo">Resumen</h3>
        <div class="resumen-linea">
            <span>Subtotal</span>
            <span>${fmtPrecio(subtotal)}</span>
        </div>
        <div class="resumen-linea">
            <span>Envío</span>
            <span>${envio === 0 ? "Gratis" : fmtPrecio(envio)}</span>
        </div>
        ${envio > 0 ? `
            <p class="resumen-envio-hint">
                Agregá ${fmtPrecio(50000 - subtotal)} más para envío gratis
            </p>
        ` : `
            <p class="resumen-envio-hint" style="color:var(--sage)">
                ✦ Envío gratis aplicado
            </p>
        `}
        <div class="resumen-linea resumen-total">
            <span>Total</span>
            <span>${fmtPrecio(total)}</span>
        </div>
        <button class="btn-primary" style="width:100%;margin-top:1.5rem"
                onclick="abrirCheckout()">
            Proceder al pago
        </button>
        <a href="/catalogo" class="btn-outline"
           style="width:100%;margin-top:1rem;text-align:center;display:block;box-sizing:border-box">
            Seguir comprando
        </a>
    `;

    layout.style.cssText = "display:grid;grid-template-columns:1fr 360px;gap:4rem;padding:4rem 5rem;align-items:start";
    layout.innerHTML = `
        <div class="carrito-items">${itemsHTML}</div>
        <div class="carrito-resumen">${resumenHTML}</div>
    `;

    updateCartCount();
}

// ── Acciones ──────────────────────────────────────────────────────
function actualizarItem(id, nuevaCantidad) {
    const cart = getCart();
    if (!cart[id]) return;
    if (nuevaCantidad <= 0) {
        eliminarItem(id);
        return;
    }
    cart[id].quantity = nuevaCantidad;
    saveCart(cart);
    renderCarrito();
}

function eliminarItem(id) {
    const cart = getCart();
    delete cart[id];
    saveCart(cart);
    renderCarrito();
}

// ── Checkout modal ────────────────────────────────────────────────
function abrirCheckout() {
    const cart = getCart();
    const items = Object.values(cart);
    const subtotal = items.reduce((sum, i) => sum + i.precio * i.quantity, 0);
    const envio = subtotal >= 50000 ? 0 : 3500;
    const total = subtotal + envio;
    const fmt = n => `$${n.toLocaleString("es-AR")}`;

    document.getElementById("modal-resumen").innerHTML = `
        <div class="resumen-linea"><span>Subtotal</span><span>${fmt(subtotal)}</span></div>
        <div class="resumen-linea"><span>Envío</span><span>${envio === 0 ? "Gratis" : fmt(envio)}</span></div>
        <div class="resumen-linea resumen-total"><span>Total</span><span>${fmt(total)}</span></div>
    `;

    document.getElementById("checkout-success").style.display = "none";
    document.getElementById("checkout-error").style.display = "none";

    const modal = document.getElementById("modal-overlay");
    modal.style.display = "flex";
    document.body.style.overflow = "hidden";
}

function cerrarModal() {
    const modal = document.getElementById("modal-overlay");
    modal.style.display = "none";
    document.body.style.overflow = "";
}

document.getElementById("modal-overlay").addEventListener("click", e => {
    if (e.target === document.getElementById("modal-overlay")) cerrarModal();
});

// ── Confirmar pedido ──────────────────────────────────────────────
async function confirmarPedido() {
    const name = document.getElementById("sh-name").value.trim();
    const email = document.getElementById("sh-email").value.trim();
    const phone = document.getElementById("sh-phone").value.trim();
    const address = document.getElementById("sh-address").value.trim();
    const city = document.getElementById("sh-city").value.trim();
    const province = document.getElementById("sh-province").value.trim();
    const zip = document.getElementById("sh-zip").value.trim();
    const notes = document.getElementById("sh-notes").value.trim();

    if (!name || !email || !address || !city || !province || !zip) {
        mostrarError("Por favor completá todos los campos obligatorios.");
        return;
    }

    const cart = getCart();
    const items = Object.values(cart).map(i => ({
        producto_id: i.id,
        cantidad: i.quantity,
        precio: i.precio,
        nombre: i.nombre,
    }));

    try {
        const res = await fetch("/api/ordenes", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                nombre: name,
                email,
                telefono: phone,
                direccion: address,
                ciudad: city,
                provincia: province,
                cp: zip,
                notas: notes,
                items,
            }),
        });

        if (!res.ok) {
            const err = await res.json();
            mostrarError(err.detail || "Hubo un error al procesar tu pedido.");
            return;
        }

        const orden = await res.json();

        // Limpiar carrito
        localStorage.removeItem("cart");
        updateCartCount();

        document.getElementById("checkout-success").style.display = "block";
        document.getElementById("checkout-error").style.display = "none";

        // Si hay URL de pago de MercadoPago, redirigir
        if (orden.mp_url) {
            setTimeout(() => window.location = orden.mp_url, 1500);
        }

    } catch (e) {
        mostrarError("Error de conexión. Intentá de nuevo.");
    }
}

function mostrarError(msg) {
    const el = document.getElementById("checkout-error");
    el.textContent = msg;
    el.style.display = "block";
}

// ── Init ──────────────────────────────────────────────────────────
renderCarrito();
updateCartCount();
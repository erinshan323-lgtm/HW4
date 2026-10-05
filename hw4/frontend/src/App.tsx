import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, NavLink, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import { ArrowRight, ChevronRight, Menu, MessageCircle, Search, Send, ShoppingBag, X } from "lucide-react";
import type { ChatProduct, Product } from "./types";

const API = import.meta.env.VITE_API_URL ?? "";
type PublicUser = { id: number; name: string; email: string; first_name?: string | null; last_name?: string | null };

function useProducts() {
  const [products, setProducts] = useState<Product[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    fetch(`${API}/api/products`)
      .then((response) => { if (!response.ok) throw new Error("Could not load products"); return response.json(); })
      .then(setProducts)
      .catch((reason) => setError(reason.message));
  }, []);
  return { products, error };
}

function Header({ user, onLogout }: { user: PublicUser | null; onLogout: () => void }) {
  const [open, setOpen] = useState(false);
  const links = [["/", "Home"], ["/products", "Products"], ["/about", "About Us"], ["/login", "Log in"], ["/create-account", "Create account"]];
  return <>
    <div className="announcement">Officially licensed Yale merchandise · New Haven, Connecticut</div>
    <header className="header">
      <Link className="brand" to="/" onClick={() => setOpen(false)}><span>Y</span><strong>Campus Customs</strong></Link>
      <nav className={open ? "nav open" : "nav"} aria-label="Main navigation">
        {links.filter(([to]) => !user || (to !== "/login" && to !== "/create-account")).map(([to, label]) => <NavLink key={to} to={to} onClick={() => setOpen(false)}>{label}</NavLink>)}
        {user && <button className="nav-user" onClick={() => { onLogout(); setOpen(false); }}>Log out {user.first_name || user.name}</button>}
      </nav>
      <div className="header-actions"><Link to="/products" aria-label="Shop products"><ShoppingBag /></Link><button className="menu-button" onClick={() => setOpen(!open)} aria-label="Toggle menu">{open ? <X /> : <Menu />}</button></div>
    </header>
  </>;
}

function Home() {
  const { products } = useProducts();
  const featured = products.slice(0, 4);
  const hero = products.find((p) => p.product_id.includes("big-yale")) ?? products[0];
  return <main>
    <section className="hero">
      {hero && <img src={`${API}${hero.image_url}`} alt={hero.name} />}
      <div className="hero-copy"><p className="eyebrow">New Haven made. Yale ready.</p><h1>Wear the tradition your way.</h1><p>Everyday layers, game-day favorites, and gifts built around Bulldog pride.</p><Link className="button light" to="/products">Shop the collection <ArrowRight size={18} /></Link></div>
    </section>
    <section className="section intro"><p className="eyebrow">Campus Customs since 1975</p><h2>Classic spirit, made for right now.</h2><p>Find comfortable Yale gear for walks across campus, weekends in the Bowl, and every reunion still to come.</p></section>
    <section className="section"><div className="section-heading"><div><p className="eyebrow">The Yale edit</p><h2>Bulldog favorites</h2></div><Link to="/products">View all <ChevronRight size={18} /></Link></div><div className="product-grid">{featured.map((p) => <ProductCard product={p} key={p.product_id} />)}</div></section>
    <section className="story-band"><div><p className="eyebrow">From Chapel Street to everywhere</p><h2>Rooted in New Haven.</h2></div><p>Campus Customs brings together collegiate tradition and an easygoing local point of view. Our Yale collection is selected for students, alumni, families, and fans who want their school spirit to feel like their own.</p></section>
  </main>;
}

function ProductCard({ product }: { product: Product }) {
  return <Link className="product-card" to={`/products/${product.product_id}`}><div className="product-image"><img src={`${API}${product.image_url}`} alt={product.name} loading="lazy" /></div><div className="product-meta"><p>{product.garment_type}</p><h3>{product.name}</h3><span>${product.price.toFixed(2)}</span></div></Link>;
}

function Products() {
  const { products, error } = useProducts();
  const [query, setQuery] = useState("");
  const [garment, setGarment] = useState("all");
  const [sort, setSort] = useState("featured");
  const [recent] = useState<Product[]>(() => { try { return JSON.parse(localStorage.getItem("campus_recent") || "[]"); } catch { return []; } });
  const garmentTypes = useMemo(() => [...new Set(products.map((p) => p.garment_type))].sort(), [products]);
  const filtered = useMemo(() => {
    const matches = products.filter((p) => (garment === "all" || p.garment_type === garment) && `${p.name} ${p.description} ${p.search_tags.join(" ")}`.toLowerCase().includes(query.toLowerCase()));
    if (sort === "price-low") return [...matches].sort((a, b) => a.price - b.price);
    if (sort === "price-high") return [...matches].sort((a, b) => b.price - a.price);
    if (sort === "name") return [...matches].sort((a, b) => a.name.localeCompare(b.name));
    return matches;
  }, [products, query, garment, sort]);
  const reset = () => { setQuery(""); setGarment("all"); setSort("featured"); };
  return <main className="page"><div className="page-title"><p className="eyebrow">The full collection</p><h1>Shop Yale</h1><p>Campus staples, thoughtful gifts, and fresh layers for every kind of Bulldog.</p></div>{recent.length > 0 && <section className="recent-section"><div className="section-heading compact"><div><p className="eyebrow">Pick up where you left off</p><h2>Recently viewed</h2></div></div><div className="product-grid recent-grid">{recent.map((p) => <ProductCard product={p} key={p.product_id} />)}</div></section>}<div className="shop-toolbar"><label className="search-control"><Search size={18} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search the collection" /></label><div className="select-controls"><label>Type<select value={garment} onChange={(e) => setGarment(e.target.value)}><option value="all">All products</option>{garmentTypes.map((type) => <option value={type} key={type}>{type}</option>)}</select></label><label>Sort<select value={sort} onChange={(e) => setSort(e.target.value)}><option value="featured">Featured</option><option value="price-low">Price: low to high</option><option value="price-high">Price: high to low</option><option value="name">Name</option></select></label></div><span>{filtered.length} products</span></div>{error && <p className="status">{error}. Start the FastAPI server and refresh.</p>} {!products.length && !error && <p className="status">Loading the collection...</p>}{products.length > 0 && filtered.length === 0 && <div className="empty-products"><h2>No matches yet</h2><p>Try another search or reset the filters to see the full collection.</p><button className="button primary" onClick={reset}>Reset filters</button></div>}<div className="product-grid large">{filtered.map((p) => <ProductCard product={p} key={p.product_id} />)}</div></main>;
}

function ProductDetail() {
  const { id } = useParams();
  const [product, setProduct] = useState<Product | null>(null);
  useEffect(() => { fetch(`${API}/api/products/${id}`).then((r) => r.json()).then(setProduct); }, [id]);
  useEffect(() => {
    if (!product) return;
    let previous: Product[] = [];
    try { previous = JSON.parse(localStorage.getItem("campus_recent") || "[]"); } catch { previous = []; }
    const compact = { ...product, inventory: undefined };
    localStorage.setItem("campus_recent", JSON.stringify([compact, ...previous.filter((item) => item.product_id !== product.product_id)].slice(0, 4)));
  }, [product]);
  if (!product) return <main className="page status">Loading product...</main>;
  return <main className="page"><Link className="back-link" to="/products">← Back to products</Link><section className="product-detail"><div className="detail-image"><img src={`${API}${product.image_url}`} alt={product.name} /></div><div className="detail-copy"><p className="eyebrow">{product.garment_type}</p><h1>{product.name}</h1><p className="price">${product.price.toFixed(2)}</p><p className="description">{product.description}</p><div className="color-list"><strong>Colors</strong><p>{product.colors.join(" · ")}</p></div><div className="sizes"><strong>Size & availability</strong><div>{product.inventory?.map((stock) => <span className={stock.quantity ? "" : "sold-out"} key={stock.size}>{stock.size}<small>{stock.quantity ? `${stock.quantity} left` : "Sold out"}</small></span>)}</div></div><button className="button primary">Add to bag <ShoppingBag size={18} /></button><p className="license-note">Officially licensed Yale University merchandise.</p></div></section></main>;
}

function About() {
  return <main><section className="about-hero"><div><p className="eyebrow">Our story</p><h1>A New Haven original.</h1></div></section><section className="about-copy"><h2>Close to campus. Connected to the community.</h2><div><p>Campus Customs has outfitted generations of Yale students, families, alumni, and fans. We believe school spirit is personal: it can be a favorite sweatshirt worn thin, a first campus visit, or the gift that brings New Haven a little closer.</p><p>Our collection balances familiar Yale icons with pieces made for daily life. The result is straightforward, comfortable merchandise that carries the energy of campus wherever you take it.</p></div></section><section className="values"><div><strong>01</strong><h3>Local perspective</h3><p>Inspired by the streets, traditions, and people of New Haven.</p></div><div><strong>02</strong><h3>Everyday quality</h3><p>Useful pieces chosen to be worn often, not saved for special occasions.</p></div><div><strong>03</strong><h3>Bulldog pride</h3><p>Official Yale designs for the whole community, from first-years to lifelong fans.</p></div></section></main>;
}

function AccountPage({ create = false, onLogin }: { create?: boolean; onLogin?: (user: PublicUser) => void }) {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (create) { setError("Account creation will be connected in the next account feature."); return; }
    const data = new FormData(e.currentTarget);
    setWorking(true); setError("");
    try {
      const response = await fetch(`${API}/api/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: data.get("email"), password: data.get("password") }) });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Unable to log in");
      localStorage.setItem("campus_session", payload.token);
      localStorage.setItem("campus_user", JSON.stringify(payload.user));
      onLogin?.(payload.user);
      navigate("/");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to log in"); }
    finally { setWorking(false); }
  };
  return <main className="account-page"><section><p className="eyebrow">{create ? "Join the community" : "Welcome back"}</p><h1>{create ? "Create your account" : "Log in"}</h1><p>{create ? "Save favorites and keep your Campus Customs conversations together." : "Access your account and continue shopping Yale favorites."}</p><form onSubmit={submit}>{create && <div className="form-row"><label>First name<input name="first_name" type="text" autoComplete="given-name" /></label><label>Last name<input name="last_name" type="text" autoComplete="family-name" /></label></div>}<label>Email<input name="email" type="email" autoComplete="email" required /></label><label>Password<input name="password" type="password" autoComplete={create ? "new-password" : "current-password"} required /></label>{error && <p className="form-error" role="alert">{error}</p>}<button className="button primary" type="submit" disabled={working}>{working ? "Please wait..." : create ? "Create account" : "Log in"} <ArrowRight size={18} /></button></form><p className="account-switch">{create ? "Already have an account?" : "New to Campus Customs?"} <Link to={create ? "/login" : "/create-account"}>{create ? "Log in" : "Create one"}</Link></p></section></main>;
}

function ChatSearchResults({ products, onClear }: { products: ChatProduct[]; onClear: () => void }) {
  if (!products.length) return null;
  return <section className="chat-results" aria-live="polite"><div className="chat-results-heading"><div><p className="eyebrow">Found by your chat</p><h2>Matches for you</h2><p>These items came directly from the Campus Customs catalogue.</p></div><button onClick={onClear} aria-label="Clear chat search results"><X size={18} /> Clear</button></div><div className="result-grid">{products.map((product) => <Link className="result-card" to={`/products/${product.product_id}`} key={product.product_id}><div><img src={`${API}${product.image_url}`} alt={product.name} /></div><section><h3>{product.name}</h3><p>{product.description}</p>{product.stock_summary && <small>{product.stock_summary}</small>}<strong>${product.price.toFixed(2)}</strong><span>View item <ArrowRight size={15} /></span></section></Link>)}</div></section>;
}

function ChatWidget({ onProductsFound, user }: { onProductsFound: (products: ChatProduct[]) => void; user: PublicUser | null }) {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant"; text: string; products?: ChatProduct[] }>>([]);
  const [sending, setSending] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  useEffect(() => {
    const token = localStorage.getItem("campus_session");
    if (!open || !user || !token || historyLoaded) return;
    fetch(`${API}/api/chat/history`, { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => response.ok ? response.json() : [])
      .then((history) => {
        setMessages(history.map((item: { role: "user" | "assistant"; content: string; products: ChatProduct[] }) => ({ role: item.role, text: item.content, products: item.products })));
        setHistoryLoaded(true);
      });
  }, [open, user, historyLoaded]);
  const send = async (e: FormEvent) => {
    e.preventDefault();
    const message = text.trim();
    if (!message || sending) return;
    setMessages((current) => [...current, { role: "user", text: message }]);
    setText("");
    setSending(true);
    try {
      const token = localStorage.getItem("campus_session");
      const productMatch = location.pathname.match(/^\/products\/([^/]+)$/);
      const response = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ message, page_context: { path: location.pathname, current_product_id: productMatch?.[1] ?? null } }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "The assistant is unavailable.");
      setMessages((current) => [...current, { role: "assistant", text: payload.answer, products: payload.products }]);
      onProductsFound(payload.products ?? []);
    } catch (reason) {
      setMessages((current) => [...current, { role: "assistant", text: reason instanceof Error ? reason.message : "The assistant is unavailable." }]);
    } finally {
      setSending(false);
    }
  };
  return <div className="chat-wrap">{open && <section className="chat-panel"><header><div><strong>Bulldog Blue Assistant</strong><span>{user ? `Chatting as ${user.first_name || user.name}` : "Guest product help"}</span></div><button onClick={() => setOpen(false)} aria-label="Close chat"><X /></button></header><div className="chat-body"><p className="assistant-message">Hi! Tell me what kind of Yale gear you are looking for, including a size or budget if you have one.{!user && " Log in to save this conversation."}</p>{messages.map((message, i) => <div className={`chat-message ${message.role}`} key={i}><p>{message.text}</p>{message.products?.map((product) => <Link className="chat-product" to={`/products/${product.product_id}`} onClick={() => setOpen(false)} key={product.product_id}><img src={`${API}${product.image_url}`} alt="" /><span><strong>{product.name}</strong><small>${product.price.toFixed(2)}</small></span></Link>)}</div>)}{sending && <p className="assistant-message typing">Checking the shop...</p>}</div><form onSubmit={send}><input value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask about Yale merch" aria-label="Chat message" /><button aria-label="Send message" disabled={sending}><Send size={18} /></button></form></section>}<button className="chat-button" onClick={() => setOpen(!open)} aria-label="Open product help chat"><MessageCircle /> <span>Chat with us</span></button></div>;
}

function Footer() { return <footer><div className="footer-brand"><span>Y</span><div><strong>Campus Customs</strong><p>Yale gear from the heart of New Haven.</p></div></div><div><Link to="/products">Shop</Link><Link to="/about">Our story</Link><Link to="/login">Account</Link></div><p>© 2026 Campus Customs. Course demonstration.</p></footer>; }

export default function App() {
  const [chatProducts, setChatProducts] = useState<ChatProduct[]>([]);
  const [user, setUser] = useState<PublicUser | null>(() => { try { return JSON.parse(localStorage.getItem("campus_user") || "null"); } catch { return null; } });
  const logout = () => { const token = localStorage.getItem("campus_session"); if (token) fetch(`${API}/api/auth/logout`, { method: "POST", headers: { Authorization: `Bearer ${token}` } }); localStorage.removeItem("campus_session"); localStorage.removeItem("campus_user"); setUser(null); };
  return <div className="app"><Header user={user} onLogout={logout} /><Routes><Route path="/" element={<Home />} /><Route path="/products" element={<Products />} /><Route path="/products/:id" element={<ProductDetail />} /><Route path="/about" element={<About />} /><Route path="/login" element={<AccountPage onLogin={setUser} />} /><Route path="/create-account" element={<AccountPage create />} /></Routes><ChatSearchResults products={chatProducts} onClear={() => setChatProducts([])} /><Footer /><ChatWidget onProductsFound={setChatProducts} user={user} /></div>;
}

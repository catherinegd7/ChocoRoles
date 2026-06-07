import React, { useState, useEffect, useRef } from 'react';
import {
  AlertTriangle, Sparkles, ShieldAlert, Package, Users, Zap,
  CheckCircle, X, Send, VolumeX, ChevronRight, Star,
  Volume2, TrendingDown, ShoppingCart, Plus, Minus, Search
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend
} from 'recharts';

const API = 'http://localhost:8080';

// ── CATÁLOGO MOCK (productos reales de Arca) ──────────────────────────────────
const catalogo = [
  { id: 1, nombre: 'Coca-Cola Original',      presentacion: '600ml',  precio: 16, emoji: '🥤', categoria: 'Refrescos',  riesgo: true,  sustituto: 'Coca-Cola Sin Azúcar 600ml' },
  { id: 2, nombre: 'Sprite Lima Limón',        presentacion: '600ml',  precio: 14, emoji: '🥤', categoria: 'Refrescos',  riesgo: true,  sustituto: 'Sprite Sin Azúcar 600ml' },
  { id: 3, nombre: 'Topo Chico Mineral',       presentacion: '355ml',  precio: 18, emoji: '💧', categoria: 'Agua',       riesgo: true,  sustituto: 'Topo Chico 600ml PET' },
  { id: 4, nombre: 'Fanta Fresa',              presentacion: '600ml',  precio: 14, emoji: '🥤', categoria: 'Refrescos',  riesgo: false },
  { id: 5, nombre: 'Del Valle Durazno',        presentacion: '500ml',  precio: 13, emoji: '🧃', categoria: 'Jugos',      riesgo: false },
  { id: 6, nombre: 'Powerade Mora Azul',       presentacion: '600ml',  precio: 18, emoji: '⚡', categoria: 'Deportivas', riesgo: false },
  { id: 7, nombre: 'Agua Ciel',                presentacion: '1L',     precio: 10, emoji: '💧', categoria: 'Agua',       riesgo: false },
  { id: 8, nombre: 'Coca-Cola Light',          presentacion: '600ml',  precio: 16, emoji: '🥤', categoria: 'Refrescos',  riesgo: false },
];

// ── HELPER BADGE ──────────────────────────────────────────────────────────────
function RiesgoBadge({ nivel, churn }) {
  const cfg = {
    Alto:  { bg: 'bg-red-100',   text: 'text-red-700',   bar: 'bg-red-500' },
    Medio: { bg: 'bg-amber-100', text: 'text-amber-700', bar: 'bg-amber-400' },
    Bajo:  { bg: 'bg-green-100', text: 'text-green-700', bar: 'bg-green-500' },
  }[nivel] || {};
  return (
    <div className="flex flex-col gap-1 min-w-[90px]">
      <span className={`px-2 py-0.5 text-[11px] font-bold rounded-full ${cfg.bg} ${cfg.text} w-fit`}>{nivel}</span>
      <div className="w-full bg-gray-100 rounded-full h-1.5">
        <div className={`${cfg.bar} h-1.5 rounded-full`} style={{ width: `${churn}%` }} />
      </div>
      <span className="text-[10px] text-gray-400">{churn}% riesgo</span>
    </div>
  );
}

// ── 1. MODAL PLAN B ───────────────────────────────────────────────────────────
function ClienteModal({ isOpen, onClose, productoEnRiesgo }) {
  const [paso, setPaso] = useState('elegir');
  if (!isOpen) return null;

  if (paso === 'confirmado') return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center animate-fade-in">
      <div className="absolute inset-0 bg-black/50" />
      <div className="relative bg-white w-full sm:max-w-sm sm:rounded-3xl rounded-t-3xl p-8 text-center shadow-2xl">
        <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-5">
          <CheckCircle className="h-10 w-10 text-green-500" />
        </div>
        <h2 className="text-2xl font-black text-gray-900 mb-2">¡Listo, Don Pepe!</h2>
        <p className="text-gray-500 text-base mb-5 leading-relaxed">
          Si no hay <strong>{productoEnRiesgo?.nombre}</strong>, le mandamos <strong>{productoEnRiesgo?.sustituto}</strong>.
        </p>
        <div className="bg-amber-50 border-2 border-amber-200 rounded-2xl p-4 mb-6 flex items-center gap-3">
          <div className="text-3xl">🎁</div>
          <div className="text-left">
            <p className="font-black text-amber-800 text-lg">+50 Puntos Arca</p>
            <p className="text-amber-600 text-sm">Ya están en su cuenta</p>
          </div>
        </div>
        <button onClick={() => { setPaso('elegir'); onClose(); }}
          className="w-full bg-[#E3000B] text-white font-black text-xl py-5 rounded-2xl transition">
          Cerrar
        </button>
      </div>
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center animate-fade-in">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white w-full sm:max-w-sm sm:rounded-3xl rounded-t-3xl shadow-2xl overflow-hidden">
        <div className="bg-[#E3000B] px-6 pt-6 pb-5 text-white">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-red-200 font-semibold uppercase tracking-wide mb-1">Aviso de su pedido</p>
              <h2 className="text-2xl font-black leading-tight">Puede que no haya<br />suficiente producto</h2>
            </div>
            <button onClick={onClose} className="bg-white/20 rounded-full p-2"><X className="h-5 w-5 text-white" /></button>
          </div>
        </div>
        <div className="px-6 pt-5 pb-6">
          <div className="flex items-center gap-4 bg-red-50 border border-red-100 rounded-2xl p-4 mb-5">
            <div className="text-5xl">{productoEnRiesgo?.emoji || '🥤'}</div>
            <div>
              <p className="text-xs text-gray-400 mb-0.5">Su pedido incluye:</p>
              <p className="font-black text-gray-900 text-base">{productoEnRiesgo?.nombre}</p>
              <p className="text-red-600 text-sm font-bold mt-1">⚠ Puede escasear hoy</p>
            </div>
          </div>
          <p className="text-gray-700 text-lg font-semibold mb-5 text-center">¿Qué prefiere si no alcanza?</p>

          <button onClick={() => setPaso('confirmado')}
            className="w-full bg-[#E3000B] text-white rounded-2xl p-5 mb-3 flex items-center gap-4 transition shadow-lg border-2 border-[#E3000B]">
            <div className="text-4xl">{productoEnRiesgo?.emoji || '🥤'}</div>
            <div className="text-left flex-1">
              <p className="font-black text-xl leading-tight">{productoEnRiesgo?.sustituto}</p>
              <p className="text-red-200 text-sm mt-0.5">Sustituto sugerido · mismo precio</p>
            </div>
            <div className="flex flex-col items-center shrink-0">
              <Star className="h-5 w-5 text-amber-300 fill-amber-300" />
              <span className="text-xs text-amber-200 font-bold">+50 pts</span>
            </div>
          </button>

          <button onClick={() => { setPaso('elegir'); onClose(); }}
            className="w-full bg-gray-100 text-gray-600 rounded-2xl p-5 flex items-center gap-4 transition border-2 border-gray-200">
            <div className="text-4xl">🚫</div>
            <div className="text-left">
              <p className="font-black text-xl text-gray-700 leading-tight">No, gracias</p>
              <p className="text-gray-400 text-sm mt-0.5">Si no hay, no manden nada</p>
            </div>
          </button>
          <p className="text-center text-gray-400 text-xs mt-4">🎁 Al elegir sustituto, gana puntos Arca</p>
        </div>
      </div>
    </div>
  );
}

// ── 2. PANTALLA CLIENTE (carrito tipo Tuali) ──────────────────────────────────
function PantallaCliente({ onVolver }) {
  const [carrito, setCarrito] = useState({});
  const [busqueda, setBusqueda] = useState('');
  const [categoriaActiva, setCategoriaActiva] = useState('Todos');
  const [modalAbierto, setModalAbierto] = useState(false);
  const [productoEnRiesgo, setProductoEnRiesgo] = useState(null);

  const categorias = ['Todos', ...new Set(catalogo.map(p => p.categoria))];
  const filtrados = catalogo.filter(p =>
    (categoriaActiva === 'Todos' || p.categoria === categoriaActiva) &&
    p.nombre.toLowerCase().includes(busqueda.toLowerCase())
  );

  const agregar = id => setCarrito(c => ({ ...c, [id]: (c[id] || 0) + 1 }));
  const quitar  = id => setCarrito(c => { const n = { ...c }; n[id] > 1 ? n[id]-- : delete n[id]; return n; });

  const totalItems  = Object.values(carrito).reduce((a, b) => a + b, 0);
  const totalPrecio = Object.entries(carrito).reduce((s, [id, q]) => s + (catalogo.find(p => p.id === +id)?.precio || 0) * q, 0);
  const enRiesgo    = Object.keys(carrito).map(id => catalogo.find(p => p.id === +id)).find(p => p?.riesgo);

  const confirmar = () => {
    if (enRiesgo) { setProductoEnRiesgo(enRiesgo); setModalAbierto(true); }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col max-w-lg mx-auto">
      <header className="bg-[#E3000B] sticky top-0 z-40 shadow-md">
        <div className="px-4 py-3 flex items-center gap-3">
          <button onClick={onVolver} className="text-white/70 text-xs">← Salir</button>
          <div className="flex items-center gap-2 flex-1 justify-center">
            <div className="w-7 h-7 bg-white rounded-lg flex items-center justify-center">
              <span className="text-[#E3000B] font-black text-xs">T</span>
            </div>
            <div>
              <p className="text-white font-black text-sm leading-none">Tuali</p>
              <p className="text-red-200 text-[10px]">Hola, Don Pepe 👋</p>
            </div>
          </div>
          <div className="relative">
            <ShoppingCart className="h-5 w-5 text-white" />
            {totalItems > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-amber-400 text-gray-900 text-[9px] font-black rounded-full flex items-center justify-center">{totalItems}</span>
            )}
          </div>
        </div>
        <div className="px-4 pb-3">
          <div className="bg-white/20 rounded-xl flex items-center gap-2 px-3 py-2">
            <Search className="h-4 w-4 text-white/70" />
            <input type="text" placeholder="Buscar productos..." value={busqueda}
              onChange={e => setBusqueda(e.target.value)}
              className="bg-transparent text-white placeholder-red-200 text-sm flex-1 outline-none" />
          </div>
        </div>
      </header>

      <div className="bg-white border-b px-4 py-2.5 flex gap-2 overflow-x-auto no-scrollbar">
        {categorias.map(cat => (
          <button key={cat} onClick={() => setCategoriaActiva(cat)}
            className={`shrink-0 px-4 py-1.5 rounded-full text-xs font-bold transition ${categoriaActiva === cat ? 'bg-[#E3000B] text-white' : 'bg-gray-100 text-gray-500'}`}>
            {cat}
          </button>
        ))}
      </div>

      {enRiesgo && totalItems > 0 && (
        <div className="mx-4 mt-3 bg-amber-50 border border-amber-200 rounded-2xl p-3 flex items-center gap-3 animate-fade-in">
          <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0" />
          <p className="text-amber-800 text-xs"><strong>Aviso:</strong> Uno o más productos pueden escasear hoy. Al confirmar le pediremos su preferencia.</p>
        </div>
      )}

      <main className="flex-1 px-4 py-4 grid grid-cols-2 gap-3 pb-28">
        {filtrados.map(p => {
          const qty = carrito[p.id] || 0;
          return (
            <div key={p.id} className={`bg-white rounded-2xl shadow-sm border overflow-hidden ${p.riesgo ? 'border-red-100' : 'border-gray-100'}`}>
              {p.riesgo && <div className="bg-red-500 text-white text-[9px] font-black text-center py-1 uppercase tracking-wide">⚠ Puede escasear</div>}
              <div className={`flex items-center justify-center py-5 text-5xl ${p.riesgo ? 'bg-red-50' : 'bg-gray-50'}`}>{p.emoji}</div>
              <div className="p-3">
                <p className="font-bold text-gray-800 text-sm leading-tight">{p.nombre}</p>
                <p className="text-gray-400 text-xs mb-2">{p.presentacion}</p>
                <div className="flex items-center justify-between">
                  <p className="font-black text-gray-900">${p.precio}</p>
                  {qty === 0 ? (
                    <button onClick={() => agregar(p.id)} className="bg-[#E3000B] text-white w-8 h-8 rounded-full flex items-center justify-center shadow hover:bg-red-700 transition">
                      <Plus className="h-4 w-4" />
                    </button>
                  ) : (
                    <div className="flex items-center gap-1.5">
                      <button onClick={() => quitar(p.id)} className="bg-gray-100 w-7 h-7 rounded-full flex items-center justify-center"><Minus className="h-3 w-3" /></button>
                      <span className="font-black text-sm w-4 text-center">{qty}</span>
                      <button onClick={() => agregar(p.id)} className="bg-[#E3000B] text-white w-7 h-7 rounded-full flex items-center justify-center"><Plus className="h-3 w-3" /></button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </main>

      {totalItems > 0 && (
        <div className="fixed bottom-6 left-0 right-0 flex justify-center px-6 z-40">
          <button onClick={confirmar}
            className="bg-[#E3000B] text-white font-black px-6 py-4 rounded-2xl shadow-2xl flex items-center gap-3 w-full max-w-sm justify-between">
            <span className="bg-white/20 rounded-xl px-2 py-1 text-sm">{totalItems}</span>
            <span>Confirmar pedido</span>
            <span>${totalPrecio}</span>
          </button>
        </div>
      )}

      <ClienteModal isOpen={modalAbierto} onClose={() => setModalAbierto(false)} productoEnRiesgo={productoEnRiesgo} />
    </div>
  );
}

// ── 3. DASHBOARD (datos reales del backend) ───────────────────────────────────
function Dashboard() {
  const [stats, setStats]       = useState(null);
  const [loading, setLoading]   = useState(true);
  const [chatInput, setChatInput] = useState('');
  const [mensajes, setMensajes] = useState([
    { rol: 'gemini', texto: 'Hola Supervisor. Estoy listo para analizar los datos del CEDIS. ¿Qué quieres saber?' }
  ]);
  const [sessionId]   = useState(() => Math.random().toString(36).slice(2));
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    fetch(`${API}/api/stats`)
      .then(r => r.json())
      .then(d => { setStats(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [mensajes]);

  const enviarMensaje = async () => {
    if (!chatInput.trim() || chatLoading) return;
    const texto = chatInput;
    setChatInput('');
    setMensajes(m => [...m, { rol: 'user', texto }]);
    setChatLoading(true);
    try {
      const res = await fetch(`${API}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: texto, session_id: sessionId }),
      });
      const data = await res.json();
      setMensajes(m => [...m, { rol: 'gemini', texto: data.response || 'Error al responder.' }]);
    } catch {
      setMensajes(m => [...m, { rol: 'gemini', texto: '⚠ No pude conectar con el servidor.' }]);
    }
    setChatLoading(false);
  };

  // Temporadas (datos reales del backend si existen, fallback mock)
  const temporadas = stats?.temporadas || [
    { mes:'Ene',s:120,p:980 },{ mes:'Feb',s:98,p:870 },{ mes:'Mar',s:145,p:1100 },
    { mes:'Abr',s:160,p:1250 },{ mes:'May',s:210,p:1400 },{ mes:'Jun',s:310,p:1800 },
    { mes:'Jul',s:420,p:2200 },{ mes:'Ago',s:380,p:2000 },{ mes:'Sep',s:290,p:1600 },
    { mes:'Oct',s:230,p:1450 },{ mes:'Nov',s:280,p:1700 },{ mes:'Dic',s:460,p:2500 },
  ].map(x => ({ mes: x.mes, sustituciones: x.s || x.sustituciones, pedidos: x.p || x.pedidos }));

  // Clientes críticos reales
  const clientesCriticos = stats?.clientes_riesgo?.slice(0, 4).map((c, i) => ({
    id: i,
    nombre: c.nombre || `Cliente ${c.customer_id}`,
    iniciales: (c.nombre || 'CL').substring(0, 2).toUpperCase(),
    riesgo: c.score_riesgo >= 70 ? 'Alto' : c.score_riesgo >= 40 ? 'Medio' : 'Bajo',
    churn: c.score_riesgo || 0,
    sustituciones: c.total_sustituciones || 0,
    cedis: c.cedis || '—',
  })) || [];

  // SKUs más sustituidos reales
  const skus = stats?.top_sustituciones?.slice(0, 3).map(s => ({
    nombre: s.nombre_sku_solicitado,
    riesgo: Math.min(95, Math.round((s.frecuencia / 400) * 100)),
    sustituto: s.nombre_sku_solicitado_cambio,
  })) || [];

  const kpis = stats ? [
    { label: 'Pedidos Totales',    value: stats.summary?.total_pedidos?.toLocaleString()      || '—', delta: 'Dataset real', color: 'blue',   icon: Package },
    { label: 'Sustituciones',      value: stats.summary?.total_sustituciones?.toLocaleString() || '—', delta: `${stats.summary?.tasa_sustitucion}% tasa`, color: 'red', icon: AlertTriangle },
    { label: 'Clientes Críticos',  value: stats.summary?.clientes_criticos?.toLocaleString()   || '—', delta: 'Score ≥ 70',  color: 'orange', icon: Users },
    { label: 'Satisfacción',       value: `${(100 - (stats.summary?.tasa_sustitucion || 28)).toFixed(0)}%`, delta: 'Estimado', color: 'yellow', icon: TrendingDown },
  ] : [];

  const grad = { red:'from-red-600 to-red-700', orange:'from-orange-500 to-orange-600', blue:'from-blue-600 to-blue-700', yellow:'from-amber-500 to-amber-600' };

  if (loading) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-red-200 border-t-[#E3000B] rounded-full animate-spin mx-auto mb-4" />
        <p className="text-gray-500 text-sm">Cargando datos reales del CEDIS...</p>
      </div>
    </div>
  );

  return (
    <div className="p-4 lg:p-6">
      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
        {kpis.map(k => {
          const Icon = k.icon;
          return (
            <div key={k.label} className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
              <div className={`bg-gradient-to-br ${grad[k.color]} px-4 py-2.5 flex items-center gap-2`}>
                <Icon className="h-4 w-4 text-white/80" />
                <span className="text-white/90 text-xs font-semibold truncate">{k.label}</span>
              </div>
              <div className="px-4 py-3">
                <p className="text-3xl font-black text-gray-900">{k.value}</p>
                <p className="text-xs text-gray-400 mt-0.5">{k.delta}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Gráfica + Chat */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-5">
        <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
          <h2 className="font-bold text-gray-800 mb-0.5">Sustituciones por Temporada</h2>
          <p className="text-xs text-gray-400 mb-4">Julio y Diciembre: picos críticos — planificar 4 semanas antes.</p>
          <ResponsiveContainer width="100%" height={210}>
            <BarChart data={temporadas} barGap={3}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
              <XAxis dataKey="mes" tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)', fontSize: 12 }} />
              <Legend formatter={v => v === 'sustituciones' ? 'Sustituciones' : 'Pedidos'} />
              <Bar dataKey="pedidos" fill="#e5e7eb" radius={[4,4,0,0]} />
              <Bar dataKey="sustituciones" fill="#E3000B" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Chat Gemini REAL */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 flex flex-col overflow-hidden">
          <div className="bg-gradient-to-r from-[#1A1A2E] to-[#16213E] p-4 flex items-center gap-3">
            <div className="w-8 h-8 bg-[#E3000B] rounded-full flex items-center justify-center text-white text-xs font-black">AI</div>
            <div>
              <p className="text-white text-sm font-bold">ArcaBot · Gemini</p>
              <p className="text-gray-400 text-xs">Datos reales · {stats?.summary?.total_pedidos?.toLocaleString()} pedidos</p>
            </div>
            <div className="ml-auto flex items-center gap-1.5">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              <span className="text-green-400 text-[10px]">En línea</span>
            </div>
          </div>
          <div className="flex-1 p-3 space-y-2.5 bg-gray-50 overflow-y-auto" style={{ minHeight: 180, maxHeight: 220 }}>
            {mensajes.map((m, i) => (
              <div key={i} className={`flex ${m.rol === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-xs leading-relaxed ${m.rol === 'gemini' ? 'bg-white border border-gray-200 text-gray-700 shadow-sm' : 'bg-[#E3000B] text-white'}`}
                  dangerouslySetInnerHTML={m.rol === 'gemini' ? { __html: m.texto } : undefined}>
                  {m.rol === 'user' ? m.texto : undefined}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="flex justify-start">
                <div className="bg-white border border-gray-200 rounded-2xl px-3 py-2 text-xs text-gray-400">Gemini está pensando...</div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
          <div className="p-3 border-t border-gray-100 flex gap-2">
            <input type="text" value={chatInput} onChange={e => setChatInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && enviarMensaje()}
              placeholder="Pregunta sobre stock o clientes..."
              className="flex-1 text-xs p-2.5 border border-gray-200 rounded-xl focus:outline-none focus:border-red-400 bg-gray-50" />
            <button onClick={enviarMensaje} disabled={chatLoading}
              className="bg-[#E3000B] hover:bg-red-700 disabled:opacity-50 text-white p-2.5 rounded-xl transition">
              <Send className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Tablas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
          <div className="flex items-center gap-2 mb-4">
            <ShieldAlert className="text-red-500 h-5 w-5" />
            <h2 className="font-bold text-gray-800">Clientes en Riesgo</h2>
            <span className="ml-auto text-[10px] text-gray-400 bg-gray-100 px-2 py-1 rounded-full">Datos reales</span>
          </div>
          {clientesCriticos.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-4">Cargando clientes...</p>
          ) : (
            <div className="space-y-3">
              {clientesCriticos.map(c => (
                <div key={c.id} className="flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 transition border border-gray-50">
                  <div className="w-9 h-9 bg-gradient-to-br from-red-500 to-red-700 rounded-full flex items-center justify-center text-white text-xs font-black shrink-0">{c.iniciales}</div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-gray-800 text-sm truncate">{c.nombre}</p>
                    <p className="text-xs text-gray-400">CEDIS {c.cedis} · {c.sustituciones} sust.</p>
                  </div>
                  <RiesgoBadge nivel={c.riesgo} churn={c.churn} />
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Package className="text-orange-500 h-5 w-5" />
            <h2 className="font-bold text-gray-800">SKUs más Sustituidos</h2>
          </div>
          {skus.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-4">Cargando SKUs...</p>
          ) : (
            <div className="space-y-3">
              {skus.map((s, i) => (
                <div key={i} className="p-3 rounded-xl border border-gray-100 hover:bg-gray-50 transition">
                  <div className="flex items-center justify-between mb-2">
                    <p className="font-semibold text-gray-800 text-sm truncate pr-2">{s.nombre}</p>
                    <span className="text-xs font-black text-red-600 bg-red-50 px-2 py-0.5 rounded-full shrink-0">{s.riesgo}%</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-1.5 mb-2">
                    <div className="bg-red-500 h-1.5 rounded-full" style={{ width: `${s.riesgo}%` }} />
                  </div>
                  <p className="text-xs text-gray-400 truncate"><span className="text-green-600 font-semibold">↳ </span>{s.sustituto}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── 4. APP CONDUCTOR ──────────────────────────────────────────────────────────
function ConductorRuta() {
  const [audioReproducido, setAudioReproducido] = useState(false);
  const [entregaConfirmada, setEntregaConfirmada] = useState(false);

  useEffect(() => { setTimeout(() => setAudioReproducido(true), 800); }, []);

  const reproducir = () => {
    alert('🔊 ElevenLabs:\n\n"Cambio en pedido. MiniSúper Don Pepe. Llevar Coca-Cola Sin Azúcar en lugar de Coca-Cola Original. Cliente molesto — saludar por nombre y entregar cupón."');
  };

  if (entregaConfirmada) return (
    <div className="flex items-center justify-center min-h-[calc(100vh-56px)] bg-[#F5F5F5] p-4">
      <div className="w-[300px] bg-gray-950 rounded-[44px] p-3 shadow-2xl border-[7px] border-gray-800">
        <div className="bg-[#0F0F1A] rounded-[32px] min-h-[540px] flex flex-col items-center justify-center p-8 text-center">
          <div className="w-20 h-20 bg-green-500 rounded-full flex items-center justify-center mb-5 shadow-lg shadow-green-900">
            <CheckCircle className="h-10 w-10 text-white" />
          </div>
          <p className="text-white font-black text-xl mb-2">¡Entrega confirmada!</p>
          <p className="text-gray-400 text-sm">MiniSúper Don Pepe</p>
          <button onClick={() => setEntregaConfirmada(false)} className="mt-8 bg-gray-800 text-gray-300 rounded-2xl px-6 py-3 text-sm">Ver siguiente</button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-56px)] bg-[#F5F5F5] p-4">
      <div className="w-[300px] bg-gray-950 rounded-[44px] p-3 shadow-2xl border-[7px] border-gray-800">
        <div className="flex justify-center pt-2 pb-1"><div className="w-20 h-4 bg-gray-900 rounded-full" /></div>
        <div className="bg-[#0F0F1A] rounded-[32px] overflow-hidden min-h-[560px] flex flex-col">
          <div className="flex justify-between px-5 pt-3 pb-1 text-[10px] text-gray-500"><span>Ruta Activa 🚚</span><span>14:22 · 87%</span></div>
          <div className="px-5 pt-2 pb-3">
            <p className="text-gray-400 text-xs">Order Rescue · Conductor</p>
            <h2 className="text-white font-bold text-lg">Parada 4 de 12</h2>
          </div>

          <div className="mx-2 bg-[#E3000B] rounded-2xl overflow-hidden shadow-lg animate-fade-in">
            <div className="flex items-center justify-between px-4 pt-3 pb-1">
              <div className="flex items-center gap-2">
                <div className={`w-7 h-7 bg-white/20 rounded-full flex items-center justify-center ${audioReproducido ? 'animate-pulse' : ''}`}>
                  <Volume2 className="h-3.5 w-3.5 text-white" />
                </div>
                <span className="text-white text-[10px] font-bold uppercase tracking-wider">
                  {audioReproducido ? 'Reproduciendo...' : 'Alerta de pedido'}
                </span>
              </div>
            </div>
            <div className="px-4 pb-4 pt-2">
              <p className="text-white font-black text-lg">MiniSúper Don Pepe</p>
              <span className="text-[10px] bg-white/20 text-white rounded-full px-2 py-0.5 font-bold">⚠ CLIENTE CRÍTICO</span>
              <div className="bg-black/20 rounded-xl p-3 flex items-center gap-2 mt-3">
                <div className="text-center"><div className="text-xl">🥤</div><p className="text-[9px] text-red-200">Coca-Cola<br/>Original</p></div>
                <ChevronRight className="h-5 w-5 text-white/50 shrink-0" />
                <div className="text-center"><div className="text-xl">🥤</div><p className="text-[9px] text-green-300">Sin<br/>Azúcar</p></div>
                <div className="flex-1 ml-1"><p className="text-white text-[10px] font-bold">Plan B activado</p><p className="text-red-200 text-[9px]">Cliente lo autorizó</p></div>
              </div>
              <div className="bg-amber-500/20 border border-amber-400/30 rounded-xl p-2.5 mt-2">
                <p className="text-amber-300 text-[10px] font-bold">💡 Protocolo empático</p>
                <p className="text-amber-200/80 text-[9px] mt-0.5">Saluda por nombre · Entrega cupón · Trato prioritario</p>
              </div>
              <button onClick={reproducir} className="w-full mt-3 bg-white/20 text-white rounded-xl py-2.5 text-xs font-bold flex items-center justify-center gap-2">
                <Volume2 className="h-3.5 w-3.5" /> Repetir mensaje de voz
              </button>
            </div>
          </div>

          <div className="px-4 pt-3">
            <p className="text-gray-500 text-[10px] uppercase tracking-wide">Parada 4 de 12</p>
            <p className="text-white font-bold text-sm mt-0.5">MiniSúper Don Pepe</p>
            <p className="text-gray-400 text-xs">Calle Independencia 45, Col. Centro</p>
          </div>

          <div className="mt-auto px-3 pb-5 pt-4 grid grid-cols-2 gap-2">
            <button className="bg-gray-800 text-gray-300 rounded-2xl py-4 text-xs font-bold">↩ Pausa ruta</button>
            <button onClick={() => setEntregaConfirmada(true)} className="bg-[#E3000B] text-white rounded-2xl py-4 text-xs font-bold">✓ Entregado</button>
          </div>
        </div>
        <div className="flex justify-center py-2"><div className="w-24 h-1 bg-gray-700 rounded-full" /></div>
      </div>
    </div>
  );
}

// ── 5. APP PRINCIPAL ──────────────────────────────────────────────────────────
export default function App() {
  const [pantalla, setPantalla] = useState('dashboard');

  if (pantalla === 'cliente') return <PantallaCliente onVolver={() => setPantalla('dashboard')} />;

  return (
    <div className="min-h-screen bg-[#F5F5F5] font-sans">
      <header className="bg-[#E3000B] sticky top-0 z-40 shadow-lg">
        <div className="max-w-screen-2xl mx-auto px-4 py-3 flex flex-row items-center gap-3 justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-white rounded-xl flex items-center justify-center shadow-sm">
              <span className="text-[#E3000B] font-black text-sm">AC</span>
            </div>
            <div>
              <p className="text-white font-black text-sm tracking-tight leading-none">Arca Continental</p>
              <p className="text-red-200 text-[10px] uppercase tracking-widest leading-none mt-0.5">Order Rescue · Sistema Empático</p>
            </div>
          </div>
          <nav className="flex gap-2 shrink-0">
            <button onClick={() => setPantalla('cliente')}
              className="flex items-center gap-1.5 bg-white text-[#E3000B] text-xs px-4 py-2 rounded-xl font-black shadow transition hover:bg-red-50">
              🛒 App Cliente
            </button>
            <button onClick={() => setPantalla('dashboard')}
              className={`text-xs px-4 py-2 rounded-xl font-bold transition ${pantalla === 'dashboard' ? 'bg-white text-[#E3000B] shadow' : 'bg-white/15 text-white hover:bg-white/25'}`}>
              📊 Dashboard
            </button>
            <button onClick={() => setPantalla('conductor')}
              className={`text-xs px-4 py-2 rounded-xl font-bold transition ${pantalla === 'conductor' ? 'bg-white text-[#E3000B] shadow' : 'bg-white/15 text-white hover:bg-white/25'}`}>
              🚚 Conductor
            </button>
          </nav>
        </div>
      </header>

      <main className="animate-fade-in max-w-screen-2xl mx-auto">
        {pantalla === 'dashboard' ? <Dashboard /> : <ConductorRuta />}
      </main>
    </div>
  );
}

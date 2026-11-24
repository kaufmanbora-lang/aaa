/* GTA 6 — интерактивная карта Леониды (неофициальный фан-проект) */
(function () {
  'use strict';

  var RAR = {
    5: { n: 'Уникальное', c: '#f6c544' },
    4: { n: 'Эпическое', c: '#b774ff' },
    3: { n: 'Редкое', c: '#4aa8ff' },
    2: { n: 'Необычное', c: '#62d37e' },
    1: { n: 'Обычное', c: '#e9eef3' }
  };
  var VER = {
    3: { t: 'Подтверждено несколькими источниками', k: 'ok2', m: '✔✔' },
    2: { t: 'Один надёжный источник', k: 'ok1', m: '✔' },
    1: { t: 'Не подтверждено', k: 'unk', m: '?' },
    0: { t: 'Слух / примерное место', k: 'unk', m: '≈' }
  };
  var BLANK = 'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==';
  var DPR = Math.min(window.devicePixelRatio || 1, 3);
  var HOME = [[-8600, -10300], [9500, 3800]];

  var LS = {
    get: function (k, d) { try { var v = localStorage.getItem('gta6map.' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem('gta6map.' + k, JSON.stringify(v)); } catch (e) { /* private mode */ } }
  };
  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function norm(s) { return String(s || '').toLowerCase().replace(/ё/g, 'е'); }

  var DATA, ICONS, TILEIDX, map, layer;
  var CAT = {}, BYID = {};
  var state = {
    cats: null,                       // Set of enabled category ids
    rar: new Set(LS.get('rar', [1, 2, 3, 4, 5])),
    onlyPhoto: false, onlyVerified: false,
    hideFound: LS.get('hideFound', false),
    labels: LS.get('labels', true),
    found: new Set(LS.get('found', [])),
    sel: null
  };
  var visible = [];

  Promise.all(['data/markers.json', 'data/icons.json', 'data/tiles.json'].map(function (u) {
    return fetch(u).then(function (r) { if (!r.ok) throw new Error(u + ': ' + r.status); return r.json(); });
  })).then(function (res) {
    DATA = res[0]; ICONS = res[1]; TILEIDX = res[2];
    init();
  }).catch(function (e) {
    var l = $('loading'); l.className = 'err';
    l.innerHTML = 'Не удалось загрузить данные карты.<br><small>' + esc(e.message) + '</small>';
  });

  // ------------------------------------------------------------------ init
  function init() {
    DATA.cats.forEach(function (c) { CAT[c.id] = c; });
    DATA.markers.forEach(prep);
    var saved = LS.get('cats2', null);
    state.cats = new Set(saved || DATA.cats.filter(function (c) { return c.on; }).map(function (c) { return c.id; }));
    fillIcons(document);
    buildMap();
    buildChips();
    buildFilters();
    buildAbout();
    bindUI();
    applyFilters();
    readHash();
    $('loading').hidden = true;
    liveSync();
  }

  function prep(m) {
    BYID[m.id] = m;
    m._s = norm(m.n + ' ' + (m.sub || '') + ' ' + (m.a || '') + ' ' + CAT[m.c].n + ' ' + (m.f || []).map(function (f) { return f[1]; }).join(' '));
  }
  function fillIcons(root) {
    root.querySelectorAll('svg[data-i]').forEach(function (s) {
      var d = ICONS[s.getAttribute('data-i')];
      if (d) s.innerHTML = '<path d="' + d + '"/>';
    });
  }
  function svg(name) { return '<svg viewBox="0 0 24 24"><path d="' + (ICONS[name] || '') + '"/></svg>'; }
  function mini(cat, r, ic) { return '<span class="mini" style="--c:' + RAR[r || 1].c + '">' + svg(ic || cat.i) + '</span>'; }

  // ------------------------------------------------------------------ map
  function buildMap() {
    var crs = L.extend({}, L.CRS.Simple, { transformation: new L.Transformation(1 / 32, 512, -1 / 32, 512), infinite: true });
    map = L.map('map', {
      crs: crs, minZoom: 0, maxZoom: 7.5, zoomSnap: 0.25, zoomDelta: 1, wheelPxPerZoomLevel: 100,
      zoomControl: false, attributionControl: false, maxBounds: [[-15500, -15500], [15500, 15500]],
      maxBoundsViscosity: 0.85, bounceAtZoomLimits: false, doubleClickZoom: true, tap: false
    });
    var Tiles = L.TileLayer.extend({
      getTileUrl: function (c) {
        var col = TILEIDX[c.z] && TILEIDX[c.z][c.x];
        if (col) for (var i = 0; i < col.length; i++) if (c.y >= col[i][0] && c.y <= col[i][1]) return 'tiles/' + c.z + '/' + c.x + '/' + c.y + '.jpg';
        return BLANK;
      }
    });
    new Tiles('', { minZoom: 0, maxNativeZoom: 6, maxZoom: 8, tileSize: 256, noWrap: true, keepBuffer: 3, updateWhenZooming: false }).addTo(map);
    map.fitBounds(HOME, { animate: false });
    layer = new MarkerLayer();
    layer.addTo(map);
    map.on('click', onMapClick);
    map.on('mousemove', onMapHover);
    map.on('movestart zoomstart', function () { $('tip').hidden = true; });
  }

  // Canvas layer: draws every visible marker as a round blip (rarity colour + category glyph).
  var MarkerLayer = L.Layer.extend({
    options: { padding: 0.2 },
    onAdd: function (m) {
      this._map = m;
      this._canvas = L.DomUtil.create('canvas', 'mk-canvas leaflet-zoom-animated');
      m.getPane('overlayPane').appendChild(this._canvas);
      this._ctx = this._canvas.getContext('2d');
      this._hits = [];
      this._raf = 0;
      m.on('moveend zoomend resize viewreset', this._reset, this);
      m.on('move', this._onMove, this);
      m.on('zoomanim', this._onAnimZoom, this);
      this._reset();
    },
    onRemove: function (m) {
      L.DomUtil.remove(this._canvas);
      m.off('moveend zoomend resize viewreset', this._reset, this);
      m.off('move', this._onMove, this);
      m.off('zoomanim', this._onAnimZoom, this);
    },
    _onMove: function () {
      if (this._raf || this._map._animatingZoom) return;
      var self = this;
      this._raf = requestAnimationFrame(function () { self._raf = 0; self._reset(); });
    },
    _onAnimZoom: function (e) {
      var m = this._map, scale = m.getZoomScale(e.zoom, this._zoom),
        viewHalf = m.getSize().multiplyBy(0.5 + this.options.padding),
        cur = m.project(this._center, e.zoom),
        off = viewHalf.multiplyBy(-scale).add(cur).subtract(m._getNewPixelOrigin(e.center, e.zoom));
      L.DomUtil.setTransform(this._canvas, off, scale);
    },
    _reset: function () {
      var m = this._map; if (!m) return;
      var p = this.options.padding, size = m.getSize(),
        min = m.containerPointToLayerPoint(size.multiplyBy(-p)).round(),
        w = Math.round(size.x * (1 + p * 2)), h = Math.round(size.y * (1 + p * 2));
      this._min = min; this._w = w; this._h = h;
      this._center = m.getCenter(); this._zoom = m.getZoom();
      var c = this._canvas;
      if (c.width !== Math.round(w * DPR) || c.height !== Math.round(h * DPR)) {
        c.width = Math.round(w * DPR); c.height = Math.round(h * DPR);
        c.style.width = w + 'px'; c.style.height = h + 'px';
      }
      L.DomUtil.setPosition(c, min);
      this.draw();
    },
    redraw: function () { if (this._map) this._reset(); },
    draw: function () {
      var m = this._map, g = this._ctx, z = this._zoom, scale = Math.pow(2, z), o = m.getPixelOrigin(),
        min = this._min, w = this._w, h = this._h, hits = [];
      g.setTransform(DPR, 0, 0, DPR, 0, 0);
      g.clearRect(0, 0, w, h);
      var ox = o.x + min.x, oy = o.y + min.y;
      var base = z < 1 ? 20 : z < 2 ? 23 : z < 3 ? 27 : z < 4 ? 31 : z < 5 ? 35 : 39;
      var sel = null;
      for (var i = 0; i < visible.length; i++) {
        var mk = visible[i];
        var px = (mk.x / 32 + 512) * scale - ox, py = (-mk.y / 32 + 512) * scale - oy;
        if (px < -24 || py < -24 || px > w + 24 || py > h + 24) continue;
        var r = mk.r, dot = (r === 1 && z < 2.5) || (r === 2 && z < 1.5) || (r === 3 && z < 0.75);
        if (mk === state.sel) { sel = [px, py]; dot = false; }
        if (dot) {
          var rad = z < 1.5 ? 2.6 : 3.4;
          g.beginPath(); g.arc(px, py, rad, 0, 6.2832);
          g.fillStyle = RAR[r].c; g.fill(); g.lineWidth = 1; g.strokeStyle = 'rgba(8,12,18,.85)'; g.stroke();
          hits.push(px, py, 9, i);
        } else {
          var s = base + (r >= 5 ? 6 : r === 4 ? 3 : (r === 3 && z < 1.5) ? -4 : 0);
          var sp = sprite(mk.ic || CAT[mk.c].i, r, s, state.found.has(mk.id));
          g.drawImage(sp, px - sp._half, py - sp._half, sp._css, sp._css);
          hits.push(px, py, s / 2 + 3, i);
        }
      }
      if (state.labels) this._labels(g, scale, ox, oy, w, h, z);
      if (sel) {
        g.beginPath(); g.arc(sel[0], sel[1], base / 2 + 7, 0, 6.2832);
        g.lineWidth = 3; g.strokeStyle = '#fff'; g.stroke();
        g.lineWidth = 1.2; g.strokeStyle = 'rgba(0,0,0,.7)'; g.beginPath(); g.arc(sel[0], sel[1], base / 2 + 9, 0, 6.2832); g.stroke();
      }
      this._hits = hits;
    },
    _labels: function (g, scale, ox, oy, w, h, z) {
      var L1 = z < 3.6, L2 = z >= 2.6 && z < 5.6, boxes = [];
      if (!L1 && !L2) return;
      g.textAlign = 'center'; g.textBaseline = 'middle'; g.lineJoin = 'round';
      for (var i = 0; i < DATA.labels.length; i++) {
        var lb = DATA.labels[i];
        if (lb.k === 1 ? !L1 : !L2) continue;
        if (lb.k === 1 && z < 1 && lb.w < 60) continue;
        var px = (lb.x / 32 + 512) * scale - ox, py = (-lb.y / 32 + 512) * scale - oy;
        if (px < -80 || py < -20 || px > w + 80 || py > h + 20) continue;
        var fs = lb.k === 1 ? (z < 2 ? 12 : 14) : 11.5, txt = lb.k === 1 ? lb.n.toUpperCase() : lb.n;
        g.font = (lb.k === 1 ? '800 ' : '700 ') + fs + 'px -apple-system,"Segoe UI",Roboto,Arial,sans-serif';
        var tw = g.measureText(txt).width + 8, bx = [px - tw / 2, py - fs / 2 - 2, px + tw / 2, py + fs / 2 + 2], hit = false;
        for (var j = 0; j < boxes.length; j++) { var b = boxes[j]; if (bx[0] < b[2] && bx[2] > b[0] && bx[1] < b[3] && bx[3] > b[1]) { hit = true; break; } }
        if (hit) continue;
        boxes.push(bx);
        g.lineWidth = 3.5; g.strokeStyle = 'rgba(6,10,16,.78)'; g.strokeText(txt, px, py);
        g.fillStyle = lb.k === 1 ? '#ffffff' : 'rgba(255,255,255,.92)'; g.fillText(txt, px, py);
      }
    },
    hit: function (cp, extra) {
      // cp: container point -> index into `visible` of the top-most marker under it, or -1
      var lp = this._map.containerPointToLayerPoint(cp), x = lp.x - this._min.x, y = lp.y - this._min.y, H = this._hits, best = -1, bd = 1e9;
      for (var i = H.length - 4; i >= 0; i -= 4) {
        var dx = H[i] - x, dy = H[i + 1] - y, d = dx * dx + dy * dy, rr = H[i + 2] + (extra || 0);
        if (d <= rr * rr && d < bd - 16) { bd = d; best = H[i + 3]; }
      }
      return best;
    }
  });

  var SPR = {}, SUB = {};
  function subpaths(icon) {
    // each closed sub-shape on its own, so holes (windows, wheels) can be painted dark instead of see-through
    if (!SUB[icon]) SUB[icon] = (ICONS[icon] || ICONS.star).split(/(?=M)/).filter(Boolean).map(function (d) { return new Path2D(d); });
    return SUB[icon];
  }
  function sprite(icon, r, px, found) {
    var key = icon + '|' + r + '|' + px + (found ? '|f' : '');
    var c = SPR[key]; if (c) return c;
    var pad = 5, css = px + pad * 2, sc = px / 24;
    c = document.createElement('canvas'); c.width = c.height = Math.ceil(css * DPR);
    c._css = css; c._half = css / 2;
    var g = c.getContext('2d'); g.scale(DPR, DPR);
    var full = new Path2D(ICONS[icon] || ICONS.star), parts = subpaths(icon);
    if (found) g.globalAlpha = 0.5;
    g.save(); g.translate(pad, pad); g.scale(sc, sc); g.lineJoin = 'round'; g.lineCap = 'round';
    g.save(); g.translate(0, 1.4 / sc); g.strokeStyle = 'rgba(0,0,0,.38)'; g.lineWidth = 4.4 / sc; g.stroke(full); g.restore();
    if (r >= 5) { g.strokeStyle = 'rgba(255,214,84,.62)'; g.lineWidth = 7 / sc; g.stroke(full); }
    g.strokeStyle = '#080c12'; g.lineWidth = 3.6 / sc; g.stroke(full);
    g.fillStyle = '#080c12'; parts.forEach(function (p) { g.fill(p); });
    var grd = g.createLinearGradient(0, 2, 0, 22);
    grd.addColorStop(0, lighten(RAR[r].c, 0.42)); grd.addColorStop(1, RAR[r].c);
    g.fillStyle = grd; g.fill(full);
    g.restore();
    if (found) {
      g.globalAlpha = 1; var q = Math.max(4, px * 0.17), fx = css - q - 2, fy = q + 2;
      g.beginPath(); g.arc(fx, fy, q + 1.5, 0, 6.2832); g.fillStyle = '#1f9d55'; g.fill();
      g.lineWidth = 1; g.strokeStyle = '#0a0e14'; g.stroke();
      g.beginPath(); g.moveTo(fx - q * 0.55, fy); g.lineTo(fx - q * 0.1, fy + q * 0.45); g.lineTo(fx + q * 0.6, fy - q * 0.4);
      g.lineWidth = 1.6; g.strokeStyle = '#fff'; g.stroke();
    }
    SPR[key] = c; return c;
  }
  function lighten(hex, a) {
    var n = parseInt(hex.slice(1), 16), r = n >> 16, gg = (n >> 8) & 255, b = n & 255;
    return 'rgb(' + Math.round(r + (255 - r) * a) + ',' + Math.round(gg + (255 - gg) * a) + ',' + Math.round(b + (255 - b) * a) + ')';
  }

  // ------------------------------------------------------------------ filters
  function applyFilters() {
    var out = [];
    for (var i = 0; i < DATA.markers.length; i++) {
      var m = DATA.markers[i];
      if (m.gone) continue;
      if (m !== state.sel) {
        if (!state.cats.has(m.c) || !state.rar.has(m.r)) continue;
        if (state.onlyPhoto && !(m.p || m.img)) continue;
        if (state.onlyVerified && m.v < 3) continue;
        if (state.hideFound && state.found.has(m.id)) continue;
      }
      out.push(m);
    }
    out.sort(function (a, b) { return a.r - b.r || b.y - a.y; });
    visible = out;
    layer.redraw();
    $('counter').textContent = 'На карте: ' + out.length + ' из ' + DATA.markers.length + (state.live ? ' · обновлено ' + state.live : '');
    var def = DATA.cats.filter(function (c) { return c.on; }).length;
    $('filter-badge').textContent = state.cats.size;
    $('filter-badge').title = 'Включено категорий (по умолчанию ' + def + ')';
    syncFilterUI();
  }
  function saveCats() { LS.set('cats2', Array.from(state.cats)); }

  function buildChips() {
    var h = '';
    [5, 4, 3, 2, 1].forEach(function (r) {
      h += '<button type="button" class="chip' + (state.rar.has(r) ? '' : ' off') + '" data-r="' + r + '" style="--c:' + RAR[r].c + '"><i></i>' + RAR[r].n + '</button>';
    });
    $('chips').innerHTML = h;
    $('chips').addEventListener('click', function (e) {
      var b = e.target.closest('.chip'); if (!b) return;
      var r = +b.dataset.r;
      if (state.rar.has(r)) state.rar.delete(r); else state.rar.add(r);
      if (!state.rar.size) [1, 2, 3, 4, 5].forEach(function (x) { state.rar.add(x); });
      LS.set('rar', Array.from(state.rar));
      document.querySelectorAll('#chips .chip').forEach(function (c) { c.classList.toggle('off', !state.rar.has(+c.dataset.r)); });
      applyFilters();
    });
  }

  var PRESETS = [
    ['По умолчанию', function () { return DATA.cats.filter(function (c) { return c.on; }).map(id); }],
    ['Только редкое', function () { return DATA.cats.filter(function (c) { return c.g === 'rare'; }).map(id); }],
    ['Коллекционки', function () { return DATA.cats.filter(function (c) { return c.g === 'collect'; }).map(id); }],
    ['Всё', function () { return DATA.cats.map(id); }],
    ['Ничего', function () { return []; }]
  ];
  function id(c) { return c.id; }

  function buildFilters() {
    $('presets').innerHTML = PRESETS.map(function (p, i) { return '<button type="button" class="pbtn" data-p="' + i + '">' + p[0] + '</button>'; }).join('');
    $('toggles').innerHTML =
      trow('t-photo', 'Только с фото', state.onlyPhoto) +
      trow('t-ver', 'Только подтверждённые 2+ источниками', state.onlyVerified) +
      trow('t-found', 'Скрыть найденные', state.hideFound) +
      trow('t-labels', 'Подписи районов', state.labels);
    var h = '';
    DATA.groups.forEach(function (g) {
      var cats = DATA.cats.filter(function (c) { return c.g === g.id; });
      var total = cats.reduce(function (s, c) { return s + c.count; }, 0);
      h += '<section class="grp" data-g="' + g.id + '"><div class="grp-head"><b>' + esc(g.n) + '</b><small>' + total + '</small>' +
        '<button type="button" class="grp-all" data-gall="' + g.id + '">все</button></div>';
      cats.forEach(function (c) {
        h += '<label class="cat" data-c="' + c.id + '">' + mini(c, catRarity(c.id)) +
          '<span class="cat-n">' + esc(c.n) + '<small></small></span>' +
          '<input type="checkbox" class="sw" data-cat="' + c.id + '"></label>';
      });
      h += '</section>';
    });
    $('catlist').innerHTML = h;
  }
  function trow(i, label, on) { return '<label class="trow">' + label + '<input type="checkbox" class="sw" id="' + i + '"' + (on ? ' checked' : '') + '></label>'; }
  var _catR = null;
  function catRarity(cid) {
    if (!_catR) {
      _catR = {};
      DATA.markers.forEach(function (m) { if (!_catR[m.c] || m.r > _catR[m.c]) _catR[m.c] = m.r; });
    }
    return _catR[cid] || 1;
  }
  function syncFilterUI() {
    var foundBy = {}, total = 0, tf = 0;
    state.found.forEach(function (fid) { var m = BYID[fid]; if (m) { foundBy[m.c] = (foundBy[m.c] || 0) + 1; } });
    document.querySelectorAll('#catlist .cat').forEach(function (row) {
      var c = CAT[row.dataset.c], on = state.cats.has(c.id);
      row.classList.toggle('off', !on);
      row.querySelector('input').checked = on;
      var f = foundBy[c.id] || 0;
      row.querySelector('small').textContent = f ? 'найдено ' + f + ' из ' + c.count : c.count + ' ' + plural(c.count);
    });
    DATA.cats.forEach(function (c) { if (c.g === 'rare' || c.g === 'collect') { total += c.count; tf += foundBy[c.id] || 0; } });
    $('progress').innerHTML = 'Прогресс (редкое и коллекционные): <b>' + tf + '</b> из ' + total +
      '<div class="bar"><i style="width:' + (total ? (100 * tf / total).toFixed(1) : 0) + '%"></i></div>';
    document.querySelectorAll('#catlist .grp').forEach(function (sec) {
      var cats = DATA.cats.filter(function (c) { return c.g === sec.dataset.g; });
      var all = cats.every(function (c) { return state.cats.has(c.id); });
      sec.querySelector('.grp-all').textContent = all ? 'скрыть' : 'все';
    });
  }
  function plural(n) {
    var a = n % 10, b = n % 100;
    return (a === 1 && b !== 11) ? 'метка' : (a >= 2 && a <= 4 && (b < 12 || b > 14)) ? 'метки' : 'меток';
  }

  // ------------------------------------------------------------------ UI events
  function bindUI() {
    $('btn-filters').onclick = function () { toggle('filters'); };
    $('btn-info').onclick = function () { toggle('about'); };
    $('z-in').onclick = function () { map.zoomIn(1); };
    $('z-out').onclick = function () { map.zoomOut(1); };
    $('z-home').onclick = function () { map.flyToBounds(HOME, { duration: 0.6 }); };
    document.addEventListener('click', function (e) {
      var c = e.target.closest('[data-close]');
      if (c) { closePanel(c.dataset.close); }
    });
    $('about').addEventListener('click', function (e) { if (e.target === $('about')) closePanel('about'); });
    $('lightbox').onclick = function () { $('lightbox').hidden = true; };
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') return;
      if (!$('lightbox').hidden) $('lightbox').hidden = true;
      else if (!$('about').hidden) closePanel('about');
      else if (!$('filters').hidden) closePanel('filters');
      else if (!$('results').hidden) hideResults();
      else closePanel('detail');
    });
    $('presets').addEventListener('click', function (e) {
      var b = e.target.closest('[data-p]'); if (!b) return;
      state.cats = new Set(PRESETS[+b.dataset.p][1]()); saveCats(); applyFilters();
    });
    $('catlist').addEventListener('change', function (e) {
      var c = e.target.dataset.cat; if (!c) return;
      if (e.target.checked) state.cats.add(c); else state.cats.delete(c);
      saveCats(); applyFilters();
    });
    $('catlist').addEventListener('click', function (e) {
      var b = e.target.closest('[data-gall]'); if (!b) return;
      e.preventDefault();
      var cats = DATA.cats.filter(function (c) { return c.g === b.dataset.gall; });
      var all = cats.every(function (c) { return state.cats.has(c.id); });
      cats.forEach(function (c) { if (all) state.cats.delete(c.id); else state.cats.add(c.id); });
      saveCats(); applyFilters();
    });
    $('t-photo').onchange = function () { state.onlyPhoto = this.checked; applyFilters(); };
    $('t-ver').onchange = function () { state.onlyVerified = this.checked; applyFilters(); };
    $('t-found').onchange = function () { state.hideFound = this.checked; LS.set('hideFound', this.checked); applyFilters(); };
    $('t-labels').onchange = function () { state.labels = this.checked; LS.set('labels', this.checked); layer.redraw(); };

    var q = $('q'), timer = 0;
    q.addEventListener('input', function () {
      $('q-clear').hidden = !q.value;
      clearTimeout(timer); timer = setTimeout(function () { search(q.value); }, 120);
    });
    q.addEventListener('focus', function () { if (q.value) search(q.value); });
    q.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { var f = $('results').querySelector('.res'); if (f) f.click(); q.blur(); }
    });
    $('q-clear').onclick = function () { q.value = ''; $('q-clear').hidden = true; hideResults(); q.focus(); };
    $('results').addEventListener('click', function (e) {
      var b = e.target.closest('.res'); if (!b) return;
      hideResults(); q.blur();
      select(BYID[b.dataset.id], true);
    });
    window.addEventListener('hashchange', readHash);
  }
  function toggle(name) { if ($(name).hidden) openPanel(name); else closePanel(name); }
  function openPanel(name) {
    hideResults();
    if (name === 'filters' && window.innerWidth < 900) closePanel('detail');
    $(name).hidden = false;
  }
  function closePanel(name) {
    $(name).hidden = true;
    if (name === 'detail') {
      document.body.classList.remove('has-detail');
      if (state.sel) { state.sel = null; pulse(null); applyFilters(); setHash(''); }
    }
  }

  // ------------------------------------------------------------------ search
  function search(text) {
    var words = norm(text).split(/\s+/).filter(Boolean), box = $('results');
    if (!words.length) { hideResults(); return; }
    var res = [];
    for (var i = 0; i < DATA.markers.length; i++) {
      var m = DATA.markers[i], ok = true;
      for (var j = 0; j < words.length; j++) if (m._s.indexOf(words[j]) < 0) { ok = false; break; }
      if (!ok) continue;
      var nm = norm(m.n), score = (nm.indexOf(words[0]) === 0 ? 100 : nm.indexOf(words[0]) >= 0 ? 50 : 0) + m.r * 8 + (m.v >= 3 ? 3 : 0);
      res.push([score, m]);
    }
    res.sort(function (a, b) { return b[0] - a[0]; });
    var h = res.slice(0, 40).map(function (x) {
      var m = x[1], c = CAT[m.c];
      return '<button type="button" class="res" data-id="' + esc(m.id) + '">' + mini(c, m.r, m.ic) + '<div><b>' + esc(m.n) + '</b><small>' +
        esc(c.n) + (m.a ? ' · ' + esc(m.a) : '') + '</small></div></button>';
    }).join('');
    box.innerHTML = h || '<div class="res-empty">Ничего не найдено. Попробуйте название на английском, как в игре.</div>';
    if (res.length > 40) box.innerHTML += '<div class="res-empty">…и ещё ' + (res.length - 40) + '. Уточните запрос.</div>';
    box.hidden = false;
  }
  function hideResults() { $('results').hidden = true; }

  // ------------------------------------------------------------------ selection / detail
  var pulseMarker = null;
  function pulse(m) {
    if (pulseMarker) { map.removeLayer(pulseMarker); pulseMarker = null; }
    if (m) pulseMarker = L.marker([m.y, m.x], { interactive: false, keyboard: false, icon: L.divIcon({ className: '', html: '<div class="pulse"></div>', iconSize: [0, 0] }) }).addTo(map);
  }
  function onMapClick(e) {
    hideResults();
    if (!$('filters').hidden && window.innerWidth < 900) { closePanel('filters'); return; }
    var i = layer.hit(e.containerPoint, ('ontouchstart' in window) ? 8 : 2);
    if (i >= 0) select(visible[i], false); else closePanel('detail');
  }
  function onMapHover(e) {
    if ('ontouchstart' in window) return;
    var i = layer.hit(e.containerPoint, 0), tip = $('tip');
    map.getContainer().style.cursor = i >= 0 ? 'pointer' : '';
    if (i < 0) { tip.hidden = true; return; }
    tip.textContent = visible[i].n; tip.hidden = false;
    tip.style.left = e.containerPoint.x + 'px'; tip.style.top = e.containerPoint.y + 'px';
  }
  function select(m, fly) {
    if (!m) return;
    state.sel = m;
    applyFilters();
    pulse(m);
    showDetail(m);
    setHash('m=' + encodeURIComponent(m.id));
    var z = Math.max(map.getZoom(), fly ? 5 : 0), mobile = window.innerWidth < 900;
    var size = map.getSize(), target = map.project([m.y, m.x], z);
    // keep the marker in the part of the map that the card does not cover
    var off = mobile ? L.point(0, size.y * 0.22) : L.point(200, 0);
    var center = map.unproject(target.add(off), z);
    if (fly) map.flyTo(center, z, { duration: 0.7 });
    else {
      var cp = map.latLngToContainerPoint([m.y, m.x]);
      var hidden = mobile ? cp.y > size.y * 0.42 : cp.x > size.x - 430;
      if (hidden) map.panTo(center, { duration: 0.35 });
    }
  }
  function showDetail(m) {
    var c = CAT[m.c], v = VER[m.v] || VER[1], h = '';
    var ph = m.p && m.p[0] ? { src: m.p[0], cap: 'Игровое фото · GTADB (CC BY 4.0)' } :
      m.img ? { src: m.img.u, cap: m.img.c || '', remote: true } : null;
    var near = !ph && m.np ? { src: m.np.p, cap: 'Ориентир рядом: ' + m.np.n + ' (≈' + m.np.d + ' м) · фото GTADB' } : null;
    if (ph) {
      h += '<figure class="d-photo" data-src="' + esc(ph.src) + '" data-cap="' + esc(ph.cap) + '"><img src="' + esc(ph.src) + '" alt="" loading="lazy"' +
        (ph.remote ? ' referrerpolicy="no-referrer"' : '') + ' onerror="this.parentNode.hidden=true"><figcaption>' + esc(ph.cap) + '</figcaption></figure>';
    }
    else h += '<div class="hero" style="--c:' + RAR[m.r].c + '">' + svg(m.ic || c.i) + '</div>';
    h += '<div class="d-head">' + mini(c, m.r, m.ic) + '<div class="d-title"><h3>' + esc(m.n) + '</h3><p>' + esc(c.n) + (m.sub ? ' · ' + esc(m.sub) : '') + '</p></div></div>';
    h += '<div class="tags"><span class="tag rar" style="--c:' + RAR[m.r].c + '">' + RAR[m.r].n + '</span>' +
      '<span class="tag ' + v.k + '">' + v.m + ' ' + v.t + '</span>' +
      (m.lk ? '<span class="tag leak">из слива 2022</span>' : '') +
      (m.ap ? '<span class="tag unk">≈ место примерное</span>' : '') +
      (m.nw ? '<span class="tag new">новое — добавлено после сборки</span>' : '') + '</div>';
    if (m.a) h += '<p class="d-area">' + svg('ui-pin') + '<span>' + esc(m.a) + '</span></p>';
    if (m.t) h += '<p class="d-text">' + esc(m.t) + '</p>' + (m.en ? '<p class="src">Подсказка пока на английском — перевод появится при следующем обновлении.</p>' : '');
    if (m.q && m.q.length) {
      h += '<div class="need"><h4>Что нужно</h4>' + (m.qs ? '<p class="need-sum">' + esc(m.qs) + '</p>' : '') +
        m.q.map(function (q) {
          return '<div class="nrow n-' + q[1] + '"><span class="nic">' + svg(q[0]) + '</span><div><b>' + esc(q[2]) + '</b>' +
            (q[3] ? '<small>' + esc(q[3]) + '</small>' : '') + '</div></div>';
        }).join('') + '</div>';
    }
    if (near) {
      h += '<figure class="d-photo near" data-src="' + esc(near.src) + '" data-cap="' + esc(near.cap) + '"><img src="' + esc(near.src) + '" alt="" loading="lazy" onerror="this.parentNode.hidden=true"><figcaption>' + esc(near.cap) + '</figcaption></figure>';
    }
    if (m.f && m.f.length) {
      h += '<table class="facts">' + m.f.map(function (f) { return '<tr><td>' + esc(f[0]) + '</td><td>' + esc(f[1]) + '</td></tr>'; }).join('') + '</table>';
    }
    var found = state.found.has(m.id);
    var qs = encodeURIComponent('GTA 6 ' + m.n + (c.g === 'place' || /^[А-Яа-я]/.test(m.n) ? ' ' + (m.a || '') : ''));
    h += '<div class="acts">' +
      '<button type="button" class="abtn ' + (found ? 'done' : 'primary') + '" id="a-found">' + svg('ui-check') + (found ? 'Найдено' : 'Отметить найденным') + '</button>' +
      '<button type="button" class="abtn" id="a-share">' + svg('ui-share') + 'Поделиться</button>' +
      '<a class="abtn" target="_blank" rel="noopener" href="https://www.google.com/search?tbm=isch&q=' + qs + '">' + svg('ui-image') + 'Фото в интернете</a>' +
      '<a class="abtn" target="_blank" rel="noopener" href="https://www.youtube.com/results?search_query=' + qs + '">' + svg('ui-search') + 'Видео</a>' +
      (m.rl ? '<a class="abtn wide" target="_blank" rel="noopener" href="https://www.google.com/maps?q=' + m.rl[0] + ',' + m.rl[1] + '">' + svg('ui-pin') + 'Прототип на Google Maps</a>' : '') +
      '</div>';
    if (m.u && m.u.length) {
      h += '<ul class="links">' + m.u.map(function (u) { return '<li>' + (u[1] ? '<a target="_blank" rel="noopener" href="' + esc(u[1]) + '">' + esc(u[0]) + '</a>' : esc(u[0])) + '</li>'; }).join('') + '</ul>';
    }
    h += '<p class="src">Источники: ' + (m.s || []).map(function (s) { var d = DATA.sources[s]; return d ? esc(d.n) : esc(s); }).join('; ') + '</p>';
    h += '<p class="coords">Координаты в игре: X ' + m.x + ', Y ' + m.y + '</p>';
    $('detail-body').innerHTML = h;
    $('detail').hidden = false; $('detail').scrollTop = 0;
    document.body.classList.add('has-detail');
    $('a-found').onclick = function () {
      if (state.found.has(m.id)) state.found.delete(m.id); else state.found.add(m.id);
      LS.set('found', Array.from(state.found));
      applyFilters(); showDetail(m);
    };
    $('a-share').onclick = function () {
      var url = location.href.split('#')[0] + '#m=' + encodeURIComponent(m.id);
      if (navigator.share) navigator.share({ title: m.n + ' — карта GTA 6', url: url }).catch(function () { });
      else if (navigator.clipboard) navigator.clipboard.writeText(url).then(function () { toast('Ссылка скопирована'); });
      else toast(url);
    };
    $('detail-body').querySelectorAll('.d-photo').forEach(function (fig) {
      fig.onclick = function () {
        var lb = $('lightbox'); lb.querySelector('img').src = fig.dataset.src; $('lightbox-cap').textContent = fig.dataset.cap; lb.hidden = false;
      };
    });
  }
  function liveSync() {
    var L = DATA.live; if (!L || !window.fetch) return;
    var ctl = window.AbortController ? new AbortController() : null;
    var timer = setTimeout(function () { if (ctl) ctl.abort(); }, 15000);
    fetch(L.url, { cache: 'no-cache', signal: ctl ? ctl.signal : undefined }).then(function (r) {
      if (!r.ok) throw new Error('live ' + r.status); return r.json();
    }).then(function (rows) {
      clearTimeout(timer);
      if (!Array.isArray(rows) || rows.length < L.ids.length * 0.6) return;   // looks broken: keep the built data
      var known = new Set(L.ids), liveIds = new Set(), added = 0, removed = 0;
      rows.forEach(function (l) {
        liveIds.add(l.id);
        if (known.has(l.id) || BYID['o-' + l.id] || typeof l.x !== 'number' || typeof l.y !== 'number') return;
        var cat = L.types[l.type] || (/ card$/.test(l.type || '') ? 'card' : 'lm_other');
        if (!CAT[cat]) return;
        var m = { id: 'o-' + l.id, c: cat, n: l.name || l.type, x: Math.round(32 * l.x - 16384), y: Math.round(16384 - 32 * l.y),
          r: CAT[cat].dr || 1, s: ['om'], v: 2, nw: 1 };
        if (l.description) { m.t = l.description; m.en = 1; }
        if (l.area) m.a = l.area;
        if (l.screenshot) m.img = { u: L.base + l.screenshot, c: 'Скриншот: Open GTA 6 Map' };
        prep(m); DATA.markers.push(m); CAT[cat].count++; added++;
      });
      DATA.markers.forEach(function (m) {
        if (!m.nw && !m.gone && m.id.indexOf('o-') === 0 && !liveIds.has(m.id.slice(2))) { m.gone = 1; CAT[m.c].count--; removed++; }
      });
      var d = new Date();
      state.live = ('0' + d.getDate()).slice(-2) + '.' + ('0' + (d.getMonth() + 1)).slice(-2) + ' ' + ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
      _catR = null;
      if (added || removed) { buildFilters(); toast('Карта обновлена: +' + added + (removed ? ', убрано ' + removed : '')); }
      applyFilters();
    }).catch(function () { clearTimeout(timer); });
  }
  function toast(t) {
    var d = document.createElement('div'); d.className = 'toast'; d.textContent = t; document.body.appendChild(d);
    setTimeout(function () { d.remove(); }, 1800);
  }
  var _hashLock = false;
  function setHash(h) {
    _hashLock = true;
    try { history.replaceState(null, '', h ? '#' + h : location.pathname + location.search); } catch (e) { /* file:// */ }
    setTimeout(function () { _hashLock = false; }, 0);
  }
  function readHash() {
    if (_hashLock) return;
    var mm = /[#&]m=([^&]+)/.exec(location.hash);
    if (mm) { var m = BYID[decodeURIComponent(mm[1])]; if (m && m !== state.sel) select(m, true); }
  }

  // ------------------------------------------------------------------ about
  function buildAbout() {
    var n = DATA.markers.length, v3 = 0, ph = 0;
    DATA.markers.forEach(function (m) { if (m.v >= 3) v3++; if (m.p || m.img) ph++; });
    var leg = [5, 4, 3, 2, 1].map(function (r) {
      return '<div><span class="mini" style="--c:' + RAR[r].c + '">' + svg('star') + '</span><span><b>' + RAR[r].n + '</b> — ' + RDESC[r] + '</span></div>';
    }).join('');
    $('about-body').innerHTML =
      '<p>Неофициальная фан-карта штата Леонида из Grand Theft Auto VI. Сборка от <b>' + esc(DATA.generated) + '</b>: ' +
      '<b>' + n + '</b> меток в ' + DATA.cats.length + ' категориях, ' + ph + ' с фото или скриншотами, ' + v3 + ' отмечены на двух и более независимых картах.</p>' +
      '<p>Новые точки с открытой карты Open GTA 6 Map подгружаются при каждом открытии сайта; полная пересборка с переводом подсказок выполняется по расписанию.</p>' +
      '<h4>Цвета меток</h4><div class="legend">' + leg + '</div>' +
      '<p>В самой игре золотым выделяются уникальные варианты оружия — здесь так же. Для транспорта, ограблений и карточек официальной шкалы редкости нет: цвет присвоен по цене продажи, размеру добычи или версии карточки.</p>' +
      '<h4>Трекеры и замки машин</h4><div class="legend">' +
      '<div class="nrow n-g"><span class="nic">' + svg('tracker') + '</span><div><b>Без трекера</b><small>можно продать Мозесу, в Pay \'n\' Spray или зарегистрировать</small></div></div>' +
      '<div class="nrow n-y"><span class="nic">' + svg('tracker') + '</span><div><b>Жёлтый трекер (стандартный)</b><small>снимается регистрацией в Pay \'n\' Spray</small></div></div>' +
      '<div class="nrow n-r"><span class="nic">' + svg('tracker') + '</span><div><b>Красный трекер (продвинутый)</b><small>нельзя ехать медленно; такие машины берёт Рэнди</small></div></div>' +
      '<div class="nrow n-y"><span class="nic">' + svg('lock') + '</span><div><b>Заперта</b><small>Slim Jim или разбить стекло</small></div></div>' +
      '<div class="nrow n-r"><span class="nic">' + svg('keyfob') + '</span><div><b>Клонер ключей</b><small>нужен Key Cloner (глава 3)</small></div></div></div>' +
      '<p>Данные о замках и трекерах есть не у всех машин; где их нет, в карточке так и написано. Механика описана по гайдам первой недели после релиза.</p>' +
      '<h4>Проверка данных</h4><ul>' +
      '<li><b>✔✔</b> — точка независимо отмечена минимум на двух картах или подтверждена гайдами.</li>' +
      '<li><b>✔</b> — один источник.</li>' +
      '<li><b>?</b> и <b>≈</b> — не подтверждено или положение примерное; такие метки помечены в карточке.</li></ul>' +
      '<h4>Источники</h4><ul>' +
      '<li><a href="https://github.com/fbritoferreira/gta6" target="_blank" rel="noopener">Open GTA 6 Map</a> (fbritoferreira и участники, CC BY 4.0) — точки сообщества и скриншоты мест.</li>' +
      '<li><a href="https://gtadb.org" target="_blank" rel="noopener">gtadb.org</a> и участники (CC BY 4.0) — тайлы карты, ориентиры и игровые фото.</li>' +
      '<li>Интерактивная карта <a href="https://www.ign.com/maps/gta-6/leonida" target="_blank" rel="noopener">IGN / MapGenie</a> — факты о предметах и транспорте (замок, трекер, цена); тексты написаны заново.</li>' +
      '<li>Миссии и банки — по скриншотам прохождений <a href="https://www.powerpyx.com/" target="_blank" rel="noopener">PowerPyx</a>.</li>' +
      '<li>Уникальное оружие, редкие машины, секреты и баги — гайды и находки игроков; ссылки есть в карточках.</li>' +
      '<li>Значки — Material Design Icons (Apache 2.0), движок карты — Leaflet (BSD-2).</li></ul>' +
      '<p>Баги и глитчи показаны только те, что ещё работают; после каждого патча список перепроверяется. Фотографии из слива 2022 года не публикуются.</p>' +
      (DATA.unplaced && DATA.unplaced.length ? '<h4>Известно, но не нанесено на карту</h4><p>' + DATA.unplaced.length +
        ' находок из гайдов без надёжного места (или слухи и опровергнутые фейки). На карту они не поставлены, чтобы не вводить в заблуждение.</p>' +
        '<button type="button" class="abtn wide" id="unplaced-btn">Показать список</button><div id="unplaced" hidden></div>' : '') +
      '<h4>Важно</h4><p>Сайт не связан с Rockstar Games и Take-Two Interactive. Grand Theft Auto, карта и изображения из игры принадлежат правообладателям. Отметки «найдено» хранятся только в этом браузере.</p>';
  }
  var UK = { weapon: 'Оружие', vehicle: 'Транспорт', secret: 'Секрет', glitch: 'Баг без точного места', rumor: 'Слух (не подтверждён)', fake: 'Фейк (опровергнут)' };
  document.addEventListener('click', function (e) {
    if (!e.target.closest || !e.target.closest('#unplaced-btn')) return;
    var box = $('unplaced');
    if (!box.innerHTML) {
      box.innerHTML = DATA.unplaced.map(function (u) {
        return '<div class="up"><b>' + esc(u.n) + '</b> <span class="tag ' + (u.k === 'fake' || u.k === 'rumor' ? 'unk' : '') + '">' + (UK[u.k] || '') + '</span>' +
          (u.t ? '<p>' + esc(u.t) + '</p>' : '') +
          (u.u && u.u.length ? '<p class="src">' + u.u.map(function (l) { return '<a target="_blank" rel="noopener" href="' + esc(l[1]) + '">' + esc(l[0]) + '</a>'; }).join(' · ') + '</p>' : '') + '</div>';
      }).join('');
    }
    box.hidden = !box.hidden;
  });
  var RDESC = {
    5: 'уникальные варианты оружия, самые дорогие машины, крупнейшая добыча',
    4: 'суперкары, ценные часы, объекты с высокой охраной',
    3: 'редкие машины, сейфы, коллекционные предметы',
    2: 'трюки, испытания и небольшие находки',
    1: 'обычные места: магазины, сервисы, ориентиры'
  };
})();

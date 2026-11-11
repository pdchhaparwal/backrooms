// The Backrooms: Level 0 demo. A tiny software raycaster, no libraries, no image assets.
(() => {
  'use strict';

  const canvas = document.getElementById('view');
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  const img = ctx.createImageData(W, H);
  const buf = new Uint32Array(img.data.buffer);
  const zbuf = new Float32Array(W);
  const DEMO_SECONDS = Number(canvas.dataset.seconds) || 5;

  const $ = (id) => document.getElementById(id);
  const ui = {
    timer: $('timer'), msg: $('msg'), start: $('overlay-start'), end: $('overlay-end'),
    summary: $('summary'), tested: $('tested'), again: $('again'),
  };

  // '#' = wall. Randomly segmented, mostly empty rooms.
  const MAP = [
    '########################',
    '#......#.......#.......#',
    '#......#.......#.......#',
    '#..##..#...##......##..#',
    '#..##..........##..##..#',
    '#..........#...........#',
    '####..######...#####...#',
    '#..............#.......#',
    '#...#....#.....#...#...#',
    '#...#....#.............#',
    '#...######...####..#####',
    '#..........#...........#',
    '#..##......#...##......#',
    '#..##..#...#...##..#...#',
    '#......#...........#...#',
    '#####..#####..######...#',
    '#......................#',
    '#...#.......#......#...#',
    '#...#...##..#..##..#...#',
    '#.......##.....##......#',
    '#..#####....#.......####',
    '#.......#...#..........#',
    '#.......#...#..........#',
    '########################',
  ];
  const MW = MAP[0].length, MH = MAP.length;
  const isWall = (x, y) => x < 0 || y < 0 || x >= MW || y >= MH || MAP[y | 0][x | 0] === '#';

  // ---- tunables ----
  const MOVE_SPEED = 2.6;   // tiles / s
  const TURN_SPEED = 2.5;   // rad / s
  const RADIUS = 0.22;      // player collision radius
  const FOV_PLANE = 0.66;
  const ENTITY_SPEED = 0.8;
  const ATTACK_TIME = 0.3;
  const ATTACK_RANGE = 1.7;

  const KEYMAP = {
    KeyW: 'fwd', ArrowUp: 'fwd', KeyS: 'back', ArrowDown: 'back',
    KeyA: 'left', ArrowLeft: 'left', KeyD: 'right', ArrowRight: 'right', Space: 'attack',
  };
  const KEY_LABELS = { KeyW: 'W', KeyA: 'A', KeyS: 'S', KeyD: 'D', ArrowUp: '↑', ArrowLeft: '←', ArrowDown: '↓', ArrowRight: '→', Space: 'SPACE' };

  // ---- state ----
  let state, timeLeft, player, ent, stats, held, attackT, touchT, msgT, walkPhase, flicker, flickerT;

  function reset() {
    state = 'ready';
    timeLeft = DEMO_SECONDS;
    player = { x: 1.5, y: 5.5, a: 0 };
    ent = { x: 8.5, y: 5.5, alive: true, hitT: 0, deadT: 0 };
    stats = { dist: 0, turned: 0, attacks: 0, hits: 0, touched: 0, tested: new Set() };
    held = new Set();
    attackT = 0; touchT = 0; msgT = 0; walkPhase = 0; flicker = 1; flickerT = 0;
    ui.start.hidden = false;
    ui.end.hidden = true;
    ui.msg.textContent = '';
    ui.timer.textContent = DEMO_SECONDS.toFixed(1) + 's';
  }

  function start() {
    state = 'running';
    ui.start.hidden = true;
    startHum();
  }

  function end() {
    state = 'over';
    held.clear();
    const all = Object.keys(KEY_LABELS);
    ui.summary.innerHTML =
      `Survived <b>${DEMO_SECONDS}s</b> · walked <b>${stats.dist.toFixed(1)}</b> tiles · ` +
      `${stats.attacks} attack${stats.attacks === 1 ? '' : 's'}, ${stats.hits} hit${stats.hits === 1 ? '' : 's'}` +
      (ent.alive ? ' · the entity is still out there' : ' · <b>entity banished</b>');
    ui.tested.textContent = 'Controls tested: ' + all.map((c) => KEY_LABELS[c] + (stats.tested.has(c) ? ' ✓' : ' ·')).join('  ');
    ui.end.hidden = false;
  }

  function flash(text) { ui.msg.textContent = text; msgT = 1.2; }

  // ---- input ----
  const down = (action) => {
    for (const code of held) if (KEYMAP[code] === action) return 1;
    return 0;
  };

  function lightKey(code, on) {
    const el = document.querySelector(`.keypanel [data-code="${code}"]`);
    if (el) el.classList.toggle('on', on);
  }

  window.addEventListener('keydown', (e) => {
    const action = KEYMAP[e.code];
    if (action || e.code === 'KeyR' || e.code === 'KeyM') e.preventDefault();
    lightKey(e.code, true);
    if (e.code === 'KeyR') { reset(); return; }
    if (e.code === 'KeyM') { toggleMute(); return; }
    if (!action || state === 'over') return;
    if (state === 'ready') start();
    stats.tested.add(e.code);
    if (action === 'attack') { if (!e.repeat) attack(); } else held.add(e.code);
  });
  window.addEventListener('keyup', (e) => { held.delete(e.code); lightKey(e.code, false); });
  window.addEventListener('blur', () => { held.clear(); document.querySelectorAll('.keypanel .on').forEach((el) => el.classList.remove('on')); });
  ui.again.addEventListener('click', reset);

  function attack() {
    if (attackT > 0) return;
    attackT = ATTACK_TIME;
    stats.attacks++;
    if (!ent.alive) return;
    const dx = ent.x - player.x, dy = ent.y - player.y;
    let ang = Math.atan2(dy, dx) - player.a;
    ang = Math.atan2(Math.sin(ang), Math.cos(ang));
    if (Math.hypot(dx, dy) < ATTACK_RANGE && Math.abs(ang) < 0.45) {
      stats.hits++;
      ent.alive = false;
      ent.hitT = 0.2;
      ent.deadT = 0.7;
      flash('ENTITY BANISHED');
    } else {
      flash('miss');
    }
  }

  // ---- simulation ----
  function tryMove(obj, dx, dy, r) {
    let moved = 0;
    if (!isWall(obj.x + dx + Math.sign(dx) * r, obj.y)) { obj.x += dx; moved += Math.abs(dx); }
    if (!isWall(obj.x, obj.y + dy + Math.sign(dy) * r)) { obj.y += dy; moved += Math.abs(dy); }
    return moved;
  }

  function update(dt) {
    attackT = Math.max(0, attackT - dt);
    touchT = Math.max(0, touchT - dt);
    ent.hitT = Math.max(0, ent.hitT - dt);
    if (!ent.alive) ent.deadT = Math.max(0, ent.deadT - dt);
    if (msgT > 0 && (msgT -= dt) <= 0) ui.msg.textContent = '';

    // fluorescent flicker
    flickerT -= dt;
    if (flickerT <= 0) {
      flicker = Math.random() < 0.12 ? 0.55 + Math.random() * 0.25 : 1;
      flickerT = flicker < 1 ? 0.05 + Math.random() * 0.08 : 0.3 + Math.random() * 1.2;
    }

    if (state !== 'running') return;

    timeLeft -= dt;
    if (timeLeft <= 0) { timeLeft = 0; ui.timer.textContent = '0.0s'; end(); return; }
    ui.timer.textContent = timeLeft.toFixed(1) + 's';

    const turn = down('right') - down('left');
    const move = down('fwd') - down('back');
    player.a += turn * TURN_SPEED * dt;
    stats.turned += Math.abs(turn * TURN_SPEED * dt);
    if (move) {
      const step = move * MOVE_SPEED * dt;
      stats.dist += tryMove(player, Math.cos(player.a) * step, Math.sin(player.a) * step, RADIUS);
      walkPhase += dt * 9;
    }

    if (ent.alive) {
      const dx = player.x - ent.x, dy = player.y - ent.y, d = Math.hypot(dx, dy);
      if (d > 0.6) {
        tryMove(ent, (dx / d) * ENTITY_SPEED * dt, (dy / d) * ENTITY_SPEED * dt, 0.2);
      } else if (touchT === 0) {
        touchT = 0.5;
        stats.touched++;
        flash('IT TOUCHED YOU');
      }
    }
  }

  // ---- rendering ----
  const FOG = [24, 20, 8];
  const pack = (r, g, b, s) =>
    (0xff000000 | (((FOG[2] + (b - FOG[2]) * s) | 0) << 16) | (((FOG[1] + (g - FOG[1]) * s) | 0) << 8) | ((FOG[0] + (r - FOG[0]) * s) | 0)) >>> 0;
  const shade = (dist) => Math.max(0, Math.min(1, flicker * (1.12 - dist * 0.1)));
  const hash = (x, y) => {
    let h = (Math.imul(x, 374761393) + Math.imul(y, 668265263)) | 0;
    h = Math.imul(h ^ (h >>> 13), 1274126177);
    return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
  };
  const mod = (n, m) => ((n % m) + m) % m;

  function entityPixel(u, v) {
    // eyes (glow, ignore fog)
    if ((u - 0.44) ** 2 + (v - 0.13) ** 2 < 0.0011 || (u - 0.56) ** 2 + (v - 0.13) ** 2 < 0.0011) return 2;
    const du = Math.abs(u - 0.5);
    if ((du / 0.13) ** 2 + ((v - 0.14) / 0.11) ** 2 < 1) return 1;                 // head
    if (v > 0.22 && v < 0.64 && du < 0.13) return 1;                                // torso
    if (v > 0.25 && v < 0.8 && du > 0.16 && du < 0.205) return 1;                   // long arms
    if (v >= 0.64 && (Math.abs(u - 0.43) < 0.045 || Math.abs(u - 0.57) < 0.045)) return 1; // legs
    return 0;
  }

  function render() {
    const { x: px, y: py, a } = player;
    const dirX = Math.cos(a), dirY = Math.sin(a);
    const planeX = -dirY * FOV_PLANE, planeY = dirX * FOV_PLANE;
    const bob = state === 'running' && (down('fwd') || down('back')) ? Math.sin(walkPhase) * 2 : 0;
    const hz = (H >> 1) + Math.round(bob);

    // floor (carpet) and ceiling (tiles + light panels)
    const rx0 = dirX - planeX, ry0 = dirY - planeY, rx1 = dirX + planeX, ry1 = dirY + planeY;
    for (let y = 0; y < H; y++) {
      const floor = y > hz;
      const p = floor ? y - hz : hz - y;
      const row = y * W;
      if (p === 0) { buf.fill(pack(0, 0, 0, 0), row, row + W); continue; }
      const dist = (0.5 * H) / p;
      const sx = (dist * (rx1 - rx0)) / W, sy = (dist * (ry1 - ry0)) / W;
      let fx = px + dist * rx0, fy = py + dist * ry0;
      const s = shade(dist);
      for (let x = 0; x < W; x++) {
        const cx = Math.floor(fx), cy = Math.floor(fy), tx = fx - cx, ty = fy - cy;
        if (floor) {
          const n = hash((fx * 12) | 0, (fy * 12) | 0);
          buf[row + x] = pack(120 + n * 26, 104 + n * 22, 48 + n * 12, s);
        } else if (mod(cx, 3) === 1 && mod(cy, 3) === 1 && tx > 0.18 && tx < 0.82 && ty > 0.3 && ty < 0.7) {
          buf[row + x] = pack(255, 252, 228, Math.min(1, s * 1.4 + 0.15));
        } else if (tx < 0.035 || ty < 0.035) {
          buf[row + x] = pack(140, 134, 108, s);
        } else {
          buf[row + x] = pack(206, 199, 168, s);
        }
        fx += sx; fy += sy;
      }
    }

    // walls (DDA)
    for (let x = 0; x < W; x++) {
      const cam = (2 * x) / W - 1;
      const rdx = dirX + planeX * cam, rdy = dirY + planeY * cam;
      let mx = Math.floor(px), my = Math.floor(py);
      const ddx = Math.abs(1 / rdx), ddy = Math.abs(1 / rdy);
      const stepX = rdx < 0 ? -1 : 1, stepY = rdy < 0 ? -1 : 1;
      let sdx = rdx < 0 ? (px - mx) * ddx : (mx + 1 - px) * ddx;
      let sdy = rdy < 0 ? (py - my) * ddy : (my + 1 - py) * ddy;
      let side = 0;
      for (let i = 0; i < 64; i++) {
        if (sdx < sdy) { sdx += ddx; mx += stepX; side = 0; } else { sdy += ddy; my += stepY; side = 1; }
        if (isWall(mx, my)) break;
      }
      const dist = Math.max(0.05, side === 0 ? sdx - ddx : sdy - ddy);
      zbuf[x] = dist;
      const lineH = H / dist;
      const y0 = Math.floor(hz - lineH / 2), y1 = Math.floor(hz + lineH / 2);
      let wx = side === 0 ? py + dist * rdy : px + dist * rdx;
      wx -= Math.floor(wx);
      const stripe = (wx * 10) % 1 < 0.16;
      const stain = hash(mx * 31 + my * 17, (wx * 4) | 0);
      const s = shade(dist) * (side ? 0.8 : 1);
      for (let y = Math.max(0, y0); y < Math.min(H, y1); y++) {
        const v = (y - y0) / (y1 - y0);
        let r, g, b;
        if (v > 0.93) { r = 92; g = 74; b = 36; }               // baseboard
        else if (stripe) { r = 186; g = 166; b = 88; }
        else { r = 214; g = 194; b = 106; }
        if (stain > 0.8 && v > 0.55 && v < 0.93) { r *= 0.86; g *= 0.84; b *= 0.8; } // water damage
        buf[y * W + x] = pack(r, g, b, s);
      }
    }

    // entity billboard
    if (ent.alive || ent.deadT > 0) {
      const sx = ent.x - px, sy = ent.y - py;
      const inv = 1 / (planeX * dirY - dirX * planeY);
      const tX = inv * (dirY * sx - dirX * sy);
      const tY = inv * (-planeY * sx + planeX * sy);
      if (tY > 0.15) {
        const screenX = Math.floor((W / 2) * (1 + tX / tY));
        const bottom = hz + H / (2 * tY);
        const h = (0.95 * H) / tY, w = h * 0.55;
        const top = bottom - h, left = screenX - w / 2;
        const s = shade(tY);
        const fade = ent.alive ? 1 : ent.deadT / 0.7;
        for (let x = Math.max(0, Math.floor(left)); x < Math.min(W, Math.ceil(left + w)); x++) {
          if (tY >= zbuf[x]) continue;
          const u = (x - left) / w;
          for (let y = Math.max(0, Math.floor(top)); y < Math.min(H, Math.ceil(bottom)); y++) {
            const v = (y - top) / h;
            const p = entityPixel(u, v);
            if (!p) continue;
            if (fade < 1 && hash(x * 7 + y, (fade * 30) | 0) > fade) continue;
            if (ent.hitT > 0) buf[y * W + x] = pack(220, 30, 30, 1);
            else buf[y * W + x] = p === 2 ? pack(255, 255, 240, 1) : pack(10, 9, 6, Math.max(s, 0.85));
          }
        }
      }
    }

    ctx.putImageData(img, 0, 0);

    // crosshair
    ctx.fillStyle = 'rgba(255,255,240,0.7)';
    ctx.fillRect(W / 2 - 1, hz - 1, 2, 2);

    // weapon: a length of pipe
    const swing = attackT > 0 ? Math.sin((1 - attackT / ATTACK_TIME) * Math.PI) : 0;
    ctx.save();
    ctx.translate(W * 0.8, H + 8 - bob * 2);
    ctx.rotate(-0.45 - swing * 1.0);
    ctx.fillStyle = '#585c60'; ctx.fillRect(-4, -105, 8, 105);
    ctx.fillStyle = '#7a7f84'; ctx.fillRect(-4, -105, 3, 105);
    ctx.fillStyle = '#3b3e41'; ctx.fillRect(-6, -110, 12, 9);
    ctx.fillStyle = '#b98c62'; ctx.fillRect(-9, -26, 18, 26);
    ctx.restore();

    if (touchT > 0) { ctx.fillStyle = `rgba(170,0,0,${touchT * 0.8})`; ctx.fillRect(0, 0, W, H); }
  }

  // ---- ambient hum (starts on first key press; M toggles) ----
  let audio = null, muted = false;
  function startHum() {
    if (audio) return;
    try {
      const ac = new (window.AudioContext || window.webkitAudioContext)();
      const gain = ac.createGain();
      gain.gain.value = muted ? 0 : 0.03;
      const lp = ac.createBiquadFilter();
      lp.type = 'lowpass'; lp.frequency.value = 500;
      [60, 120, 240].forEach((f, i) => {
        const o = ac.createOscillator();
        o.type = i === 0 ? 'sawtooth' : 'sine';
        o.frequency.value = f;
        o.connect(lp); o.start();
      });
      lp.connect(gain); gain.connect(ac.destination);
      audio = { ac, gain };
    } catch (_) { /* audio is optional */ }
  }
  function toggleMute() {
    muted = !muted;
    if (audio) audio.gain.gain.value = muted ? 0 : 0.03;
    flash(muted ? 'muted' : 'sound on');
  }

  // ---- loop ----
  reset();
  let last = performance.now();
  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    update(dt);
    render();
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  // test hook (used by automated browser checks)
  window.__backrooms = { get state() { return state; }, get stats() { return stats; }, get player() { return player; }, get ent() { return ent; } };
})();

/**
 * app.js – frut frontend application
 *
 * - Geocodes start / end addresses via Nominatim (OpenStreetMap)
 * - Calls the frut backend API (/api/routes)
 * - Displays routes on a Leaflet map, colour-coded by frut_score
 * - Shows a sortable route list with distance, duration and frutidx
 */

'use strict';

// ── Configuration ────────────────────────────────────────────────────────────

/**
 * Base URL of the frut backend API.
 * Override by setting window.FRUT_API_BASE before this script runs,
 * or by setting the environment variable at build / deploy time.
 */
const API_BASE = window.FRUT_API_BASE || '';

const NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search';

// Colours used to draw the top-3 routes (index 0 = best score).
const ROUTE_COLOURS = ['#e84118', '#0097e6', '#44bd32'];

// ── Map initialisation ───────────────────────────────────────────────────────

const map = L.map('map').setView([48.1, 11.6], 6);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  maxZoom: 19,
}).addTo(map);

// Layer group that holds all drawn route polylines.
const routeLayer = L.layerGroup().addTo(map);

// ── State ────────────────────────────────────────────────────────────────────

let drawnPolylines = [];   // Leaflet polyline objects, parallel to routeData
let routeData      = [];   // Route objects returned by the API
let activeIndex    = -1;   // Index of the currently highlighted route

// ── DOM references ───────────────────────────────────────────────────────────

const startInput   = document.getElementById('start-input');
const endInput     = document.getElementById('end-input');
const weightSlider = document.getElementById('weight-slider');
const weightValue  = document.getElementById('weight-value');
const searchBtn    = document.getElementById('search-btn');
const errorMsg     = document.getElementById('error-msg');
const noResults    = document.getElementById('no-results');
const routeList    = document.getElementById('route-list');

// ── Helpers ──────────────────────────────────────────────────────────────────

function showError(msg) {
  errorMsg.textContent = msg;
  errorMsg.classList.remove('hidden');
}

function clearError() {
  errorMsg.classList.add('hidden');
}

function setLoading(loading) {
  searchBtn.disabled = loading;
  searchBtn.innerHTML = loading
    ? '<span class="spinner"></span>Searching…'
    : 'Find fun route';
}

function fmtDistance(m) {
  return m >= 1000
    ? (m / 1000).toFixed(1) + ' km'
    : Math.round(m) + ' m';
}

function fmtDuration(s) {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return h > 0 ? `${h} h ${m} min` : `${m} min`;
}

/** Geocode an address string → {lat, lon} via Nominatim. */
async function geocode(address) {
  const url = `${NOMINATIM_URL}?q=${encodeURIComponent(address)}&format=json&limit=1`;
  const res  = await fetch(url, { headers: { 'Accept-Language': 'en' } });
  if (!res.ok) throw new Error(`Geocoding failed (${res.status})`);
  const data = await res.json();
  if (!data.length) throw new Error(`Address not found: "${address}"`);
  return { lat: parseFloat(data[0].lat), lon: parseFloat(data[0].lon) };
}

/** Call the frut backend to retrieve scored routes. */
async function fetchRoutes(startLat, startLon, endLat, endLon, weight) {
  const params = new URLSearchParams({
    start_lat: startLat,
    start_lon: startLon,
    end_lat:   endLat,
    end_lon:   endLon,
    weight,
  });
  const res = await fetch(`${API_BASE}/api/routes?${params}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `API error ${res.status}`);
  }
  return res.json();
}

// ── Map drawing ──────────────────────────────────────────────────────────────

function clearRoutes() {
  routeLayer.clearLayers();
  drawnPolylines = [];
  routeData      = [];
  activeIndex    = -1;
  routeList.innerHTML = '';
  noResults.classList.remove('hidden');
}

function drawRoutes(routes) {
  routeData = routes;
  routes.forEach((route, idx) => {
    const coords   = route.geometry.coordinates.map(([lon, lat]) => [lat, lon]);
    const colour   = ROUTE_COLOURS[idx] || '#888';
    const weight   = idx === 0 ? 5 : 3;
    const opacity  = idx === 0 ? 0.9 : 0.55;

    const poly = L.polyline(coords, {
      color:   colour,
      weight,
      opacity,
    }).addTo(routeLayer);

    poly.on('click', () => highlightRoute(idx));
    drawnPolylines.push(poly);
  });

  // Fit map to the best route.
  if (drawnPolylines.length) {
    map.fitBounds(drawnPolylines[0].getBounds(), { padding: [30, 30] });
  }
}

function highlightRoute(idx) {
  drawnPolylines.forEach((poly, i) => {
    poly.setStyle({
      weight:  i === idx ? 6 : 3,
      opacity: i === idx ? 1.0 : 0.45,
    });
    if (i === idx) poly.bringToFront();
  });

  document.querySelectorAll('.route-item').forEach((el, i) => {
    el.classList.toggle('active', i === idx);
  });

  activeIndex = idx;
}

// ── Route list rendering ─────────────────────────────────────────────────────

function renderRouteList(routes) {
  routeList.innerHTML = '';
  noResults.classList.add('hidden');

  routes.forEach((route, idx) => {
    const colour = ROUTE_COLOURS[idx] || '#888';
    const li     = document.createElement('li');
    li.className = 'route-item' + (idx === 0 ? ' active' : '');
    li.style.setProperty('--item-colour', colour);

    const label = idx === 0 ? 'Best' : idx === 1 ? '2nd' : `${idx + 1}th`;

    li.innerHTML = `
      <div class="route-title">
        <span class="badge" style="background:${colour}">${label}</span>
        Route ${idx + 1}
      </div>
      <div class="route-stats">
        <span>📍 <strong>${fmtDistance(route.distance_m)}</strong></span>
        <span>⏱ <strong>${fmtDuration(route.duration_s)}</strong></span>
        <span>🏎 <strong>${route.total_frut_idx.toFixed(1)}°</strong></span>
        <span>Score <strong>${route.frut_score.toFixed(1)}</strong></span>
      </div>
    `;

    li.addEventListener('click', () => highlightRoute(idx));
    routeList.appendChild(li);
  });
}

// ── Search handler ───────────────────────────────────────────────────────────

async function handleSearch() {
  clearError();
  clearRoutes();

  const startAddr = startInput.value.trim();
  const endAddr   = endInput.value.trim();
  const weight    = parseFloat(weightSlider.value);

  if (!startAddr) { showError('Please enter a start location.'); return; }
  if (!endAddr)   { showError('Please enter an end location.');   return; }

  setLoading(true);
  try {
    const [start, end] = await Promise.all([geocode(startAddr), geocode(endAddr)]);

    const routes = await fetchRoutes(start.lat, start.lon, end.lat, end.lon, weight);

    if (!routes.length) {
      showError('No routes found between these locations.');
      return;
    }

    drawRoutes(routes);
    renderRouteList(routes);
    highlightRoute(0);
  } catch (err) {
    showError(err.message || 'An unexpected error occurred.');
  } finally {
    setLoading(false);
  }
}

// ── Event listeners ──────────────────────────────────────────────────────────

searchBtn.addEventListener('click', handleSearch);

[startInput, endInput].forEach(input => {
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') handleSearch();
  });
});

weightSlider.addEventListener('input', () => {
  weightValue.textContent = parseFloat(weightSlider.value).toFixed(1);
});

#!/usr/bin/env python3
"""World Cup 2026 Pick'em Live Dashboard — reads from Apple Notes via AppleScript"""

import subprocess, json, re, random, os, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

PORT = int(os.environ.get('PORT', 8766))

COLORS = {
    'CARSON': {'primary': '#10b981', 'bg': 'rgba(16,185,129,0.15)'},
    'KEITH':  {'primary': '#3b82f6', 'bg': 'rgba(59,130,246,0.15)'},
    'LUKE':   {'primary': '#f59e0b', 'bg': 'rgba(245,158,11,0.15)'},
    'WILL':   {'primary': '#8b5cf6', 'bg': 'rgba(139,92,246,0.15)'},
}

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>World Cup 2026 Pick'em</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;700;900&display=swap" rel="stylesheet">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  background: #051208;
  color: #e8f3ea;
  min-height: 100vh;
}

/* Pitch stripes + stadium floodlight glow */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image:
    repeating-linear-gradient(115deg, rgba(255,255,255,0.018) 0px, rgba(255,255,255,0.018) 60px, transparent 60px, transparent 120px),
    radial-gradient(ellipse at 15% 0%, rgba(250,204,21,0.07) 0%, transparent 55%),
    radial-gradient(ellipse at 85% 10%, rgba(34,197,94,0.10) 0%, transparent 55%),
    radial-gradient(ellipse at 50% 100%, rgba(34,197,94,0.06) 0%, transparent 60%);
  pointer-events: none;
  z-index: 0;
}

.wrap { position: relative; z-index: 1; }

/* ── Header ── */
.header {
  background: linear-gradient(180deg, rgba(6,30,16,0.97) 0%, rgba(8,38,20,0.95) 100%);
  backdrop-filter: blur(12px);
  border-bottom: 2px solid rgba(250,204,21,0.25);
  padding: 20px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky; top: 0; z-index: 10;
}
.header h1 {
  font-family: 'Oswald', sans-serif;
  font-size: 28px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.5px;
  background: linear-gradient(135deg, #facc15 0%, #22c55e 60%, #16a34a 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.header-sub { color: #5b7a64; font-size: 13px; margin-top: 3px; letter-spacing: 0.3px; }
.live-badge {
  display: flex; align-items: center; gap: 7px;
  background: rgba(250,204,21,0.1); border: 1px solid rgba(250,204,21,0.35);
  padding: 6px 14px; border-radius: 100px;
  font-size: 12px; font-weight: 700; color: #facc15; letter-spacing: 1px;
}
.live-dot {
  width: 7px; height: 7px; background: #facc15; border-radius: 50%;
  animation: blink 1.5s ease-in-out infinite;
}
@keyframes blink { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.4;transform:scale(0.7)} }

/* ── Main layout: left content + right sidebar ── */
.page-body {
  max-width: 1280px;
  margin: 0 auto;
  padding: 32px 24px;
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 28px;
  align-items: start;
}

.main-col { min-width: 0; }

.section-label {
  font-family: 'Oswald', sans-serif;
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 2px; color: #3f6b4a; margin-bottom: 14px;
}

/* ── Leaderboard ── */
.leaderboard {
  background: #0a1f12; border: 1px solid rgba(250,204,21,0.12);
  border-radius: 20px; overflow: hidden; margin-bottom: 36px;
}
.lb-row {
  display: grid; grid-template-columns: 52px 1fr 72px 130px;
  align-items: center; padding: 16px 22px;
  border-bottom: 1px solid #07170d; gap: 12px; transition: background 0.15s;
}
.lb-row:last-child { border-bottom: none; }
.lb-row:hover { background: #14331c55; }
.lb-row.first { background: rgba(250,204,21,0.06); }
.lb-rank { font-size: 22px; text-align: center; }
.lb-player-name { font-size: 18px; font-weight: 800; }
.lb-player-sub { font-size: 12px; color: #5b7a64; margin-top: 2px; }
.lb-score { font-family: 'Oswald', sans-serif; font-size: 32px; font-weight: 900; text-align: right; line-height: 1; }
.lb-best-col { text-align: right; }
.lb-best-label { font-size: 10px; color: #3f6b4a; text-transform: uppercase; letter-spacing: 1px; }
.lb-best-val { font-size: 15px; font-weight: 700; color: #5b7a64; }
.best-rank-pill {
  display: inline-block; margin-top: 4px;
  padding: 2px 8px; border-radius: 100px; font-size: 11px; font-weight: 700;
}

/* ── Cards Grid ── */
.cards-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 18px; }

.player-card { background: #0a1f12; border: 1px solid rgba(250,204,21,0.12); border-radius: 20px; overflow: hidden; }
.card-header {
  padding: 16px 20px; display: flex; justify-content: space-between; align-items: flex-start;
  border-bottom-width: 1px; border-bottom-style: solid;
}
.card-name { font-family: 'Oswald', sans-serif; font-size: 16px; font-weight: 900; text-transform: uppercase; letter-spacing: 1.5px; }
.card-meta { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 6px; }
.meta-pill { font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 100px; }
.card-score { font-family: 'Oswald', sans-serif; font-size: 44px; font-weight: 900; line-height: 1; text-align: right; }
.card-best { font-size: 11px; font-weight: 600; text-align: right; opacity: 0.5; margin-top: 2px; }

.progress-wrap { padding: 10px 20px 0; }
.progress-bar { height: 3px; background: #143420; border-radius: 2px; overflow: hidden; margin-bottom: 14px; }
.progress-fill { height: 100%; border-radius: 2px; transition: width 0.8s ease; }

.team-list { padding: 0 20px 18px; display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
.team-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 5px 8px; border-radius: 7px; background: rgba(255,255,255,0.025);
}
.team-name { font-size: 12px; color: #a8c2ad; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 110px; display: flex; align-items: center; gap: 5px; }
.team-flag { font-size: 14px; flex-shrink: 0; line-height: 1; }
.team-right { display: flex; align-items: center; gap: 4px; flex-shrink: 0; min-width: 0; }
.team-pts { font-size: 12px; font-weight: 800; min-width: 14px; text-align: right; }
.pts-none  { color: #1e3a26; }
.pts-zero  { color: #3f5a47; }
.pts-low   { color: #facc15; }
.pts-high  { color: #22c55e; }

/* ── Pip tooltip (global, attached to body to avoid overflow:hidden clipping) ── */
#pip-tooltip {
  display: none; position: fixed; z-index: 9999;
  background: #0d2b17; border: 1px solid #2d5a3a;
  color: #c3d9c7; font-size: 11px; font-family: sans-serif;
  white-space: nowrap; padding: 6px 10px; border-radius: 7px;
  pointer-events: none;
  box-shadow: 0 4px 14px rgba(0,0,0,0.6);
}

/* ── Game pips (styled like ref cards: green win, yellow draw, red loss) ── */
.game-pips { display: flex; gap: 3px; align-items: center; }
.pip {
  width: 14px; height: 17px; border-radius: 3px;
  font-size: 8px; font-weight: 900;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; cursor: default;
}
.pip-win   { background: #22c55e; color: #07170d; }
.pip-draw  { background: #facc15; color: #07170d; }
.pip-loss  { background: #ef4444; color: #fff; }
.pip-live  { background: #22c55e; color: #07170d; animation: blink 1s infinite; }
.pip-empty { background: transparent; border: 1.5px dashed #1e3a26; border-radius: 3px; }
.team-bonus { font-size: 10px; font-weight: 800; color: #facc15; margin-left: 2px; }
.team-live { background: rgba(34,197,94,0.1) !important; border: 1px solid rgba(34,197,94,0.3) !important; }
.live-pip {
  display: inline-block; width: 6px; height: 6px;
  background: #22c55e; border-radius: 50%; flex-shrink: 0;
  animation: blink 1s ease-in-out infinite;
}

/* ── Schedule Sidebar ── */
.sidebar {
  position: sticky;
  top: 88px;
}

.schedule-panel {
  background: #0a1f12;
  border: 1px solid rgba(250,204,21,0.12);
  border-radius: 20px;
  overflow: hidden;
}

.schedule-header {
  padding: 16px 18px 12px;
  border-bottom: 1px solid rgba(250,204,21,0.12);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.schedule-title {
  font-family: 'Oswald', sans-serif;
  font-size: 12px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 1.5px; color: #5b7a64;
}
.schedule-badge {
  font-size: 10px; font-weight: 700; padding: 2px 7px;
  border-radius: 100px; background: rgba(250,204,21,0.15);
  color: #facc15; letter-spacing: 0.5px;
}

.game-item {
  padding: 14px 18px;
  border-bottom: 1px solid #061a0d;
  transition: background 0.15s;
}
.game-item:last-child { border-bottom: none; }
.game-item:hover { background: #14331c44; }

.game-time {
  font-size: 11px; font-weight: 600; color: #5b7a64;
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;
  display: flex; align-items: center; gap: 6px;
}
.game-status-dot {
  width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
}
.dot-live { background: #22c55e; animation: blink 1s infinite; }
.dot-soon { background: #facc15; }
.dot-scheduled { background: #2d4a36; }

.game-teams { display: flex; flex-direction: column; gap: 5px; }
.game-team {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 13px;
}
.game-team-name { font-weight: 600; color: #c3d9c7; }
.game-team-name.owned { color: #22c55e; font-weight: 800; }
.owner-tag { display:inline-block; font-size:9px; font-weight:700; padding:1px 4px; border-radius:4px; margin-left:4px; vertical-align:middle; letter-spacing:0.03em; }
.game-score {
  font-size: 14px; font-weight: 800; color: #e8f3ea;
  min-width: 20px; text-align: right;
}
.game-vs {
  text-align: center; font-size: 10px; color: #2d4a36;
  font-weight: 700; letter-spacing: 1px;
}

.game-venue {
  font-size: 10px; color: #4a7a56; margin-top: 4px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.schedule-loading { padding: 32px 18px; text-align: center; color: #2d4a36; font-size: 13px; }
.schedule-error { padding: 24px 18px; text-align: center; color: #5b7a64; font-size: 12px; }

/* ── Group Standings Section ── */
.standings-section {
  margin-top: 32px; padding: 0 0 32px;
}
.standings-title {
  font-family: 'Oswald', sans-serif; font-size: 13px; font-weight: 700;
  letter-spacing: 2px; text-transform: uppercase; color: #4a7a56;
  padding: 0 0 14px; border-bottom: 1px solid #1a3a22; margin-bottom: 18px;
}
.standings-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px;
}
#power-rankings { display: flex; flex-direction: column; gap: 5px; }
.pr-row { display: flex; align-items: center; gap: 8px; padding: 5px 10px; border-radius: 8px; background: #0a1f12; }
.pr-rank { width: 22px; text-align: right; font-size: 11px; color: #4a7a56; font-weight: 700; flex-shrink: 0; }
.pr-name { flex: 1; font-size: 12px; color: #d1fae5; }
.pr-bar-wrap { width: 160px; height: 6px; background: #0f2a18; border-radius: 3px; flex-shrink: 0; }
.pr-bar { height: 6px; border-radius: 3px; }
.pr-val { width: 36px; text-align: right; font-size: 11px; color: #4a7a56; font-family: monospace; flex-shrink: 0; }
.pr-delta { width: 38px; text-align: right; font-size: 10px; flex-shrink: 0; }
.pr-owner { display: inline-block; font-size: 8px; font-weight: 700; padding: 1px 4px; border-radius: 3px; margin-left: 4px; vertical-align: middle; }
.group-card {
  background: #0a1f12; border: 1px solid rgba(250,204,21,0.10);
  border-radius: 12px; overflow: hidden;
}
.group-header {
  background: #0f2a18; padding: 7px 12px;
  font-family: 'Oswald', sans-serif; font-size: 12px; font-weight: 700;
  letter-spacing: 1.5px; text-transform: uppercase; color: #facc15;
}
.group-table { width: 100%; border-collapse: collapse; font-size: 11px; }
.group-table th {
  padding: 4px 6px; color: #4a7a56; font-weight: 600;
  text-align: center; border-bottom: 1px solid #143420;
}
.group-table th:first-child { text-align: left; padding-left: 10px; }
.group-table td {
  padding: 5px 6px; text-align: center; color: #8aad92;
  border-bottom: 1px solid #0d2015;
}
.group-table td:first-child { text-align: left; padding-left: 10px; }
.group-table tr:last-child td { border-bottom: none; }
.group-table td.pts { font-weight: 800; color: #c3d9c7; }
.group-table tr.adv-yes td { color: #22c55e; }
.group-table tr.adv-yes td.pts { color: #22c55e; font-weight: 900; }
.group-table tr.adv-maybe td { color: #facc15; }
.group-table tr.adv-maybe td.pts { color: #facc15; font-weight: 900; }
.group-table tr.adv-no td { color: #3a5a42; }
.group-table tr.adv-no td.pts { color: #3a5a42; }
.group-table .team-name-cell { display: flex; align-items: center; gap: 5px; }
.group-table .owned-dot { color: #facc15; font-size: 8px; }
.grp-live-dot {
  display: inline-block; width: 6px; height: 6px; border-radius: 50%;
  background: #22c55e; flex-shrink: 0; animation: blink 1s infinite;
}
.grp-live-badge {
  font-size: 9px; font-weight: 800; letter-spacing: 1px;
  color: #22c55e; background: rgba(34,197,94,0.15);
  border: 1px solid rgba(34,197,94,0.3); padding: 1px 5px; border-radius: 4px;
  vertical-align: middle;
}
.group-card-live { border-color: rgba(34,197,94,0.3) !important; }
.group-table tr.grp-live-row td { font-style: italic; }
@media (max-width: 700px) {
  .standings-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 480px) {
  .standings-grid { grid-template-columns: 1fr; }
}

/* ── Monte Carlo Panel ── */
.mc-panel {
  background: #0a1f12; border: 1px solid rgba(250,204,21,0.12);
  border-radius: 20px; overflow: hidden; margin-top: 18px;
}
.mc-header { padding: 16px 18px 12px; border-bottom: 1px solid rgba(250,204,21,0.12); }
.mc-title { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; color: #5b7a64; }
.mc-sub { font-size: 10px; color: #2d4a36; margin-top: 3px; }
.mc-body { padding: 16px 18px; }
.mc-row { margin-bottom: 14px; }
.mc-row:last-child { margin-bottom: 0; }
.mc-label { display: flex; justify-content: space-between; align-items: baseline; font-size: 12px; font-weight: 700; margin-bottom: 6px; }
.mc-bar-bg { height: 8px; background: #143420; border-radius: 4px; overflow: hidden; }
.mc-bar-fill { height: 100%; border-radius: 4px; transition: width 1s ease; }
.mc-pct { font-size: 15px; font-weight: 900; }

/* Footer */
.footer { text-align: center; color: #2d4a36; font-size: 12px; padding: 24px 0 40px; }

/* Responsive */
@media (max-width: 900px) {
  .page-body { grid-template-columns: 1fr; }
  .sidebar { position: static; }
  .schedule-panel { margin-bottom: 24px; }
}
@media (max-width: 620px) {
  .cards-grid { grid-template-columns: 1fr; }
  .header { flex-direction: column; gap: 12px; align-items: flex-start; }
  .lb-row { grid-template-columns: 40px 1fr 56px; }
  .lb-best-col { display: none; }
}
@media (max-width: 480px) {
  body { overflow-x: hidden; }
  .wrap { padding: 0 10px; }
  .team-list { grid-template-columns: 1fr; padding: 0 12px 14px; gap: 3px; }
  .team-name { max-width: none; flex: 1; white-space: normal; }
  .team-item { padding: 5px 6px; }
  .card-score { font-size: 34px; }
  .card-header { padding: 12px 14px 10px; }
  .standings-grid { grid-template-columns: 1fr; }
  .group-table { font-size: 10px; }
  .group-table td, .group-table th { padding: 4px 3px; }
  .mc-body { padding: 12px; }
  #power-rankings .pr-bar-wrap { width: 80px; }
}
</style>
</head>
<body>
<div class="wrap">

<div class="header">
  <div>
    <h1>⚽ World Cup 2026 Pick'em 🏆</h1>
    <div class="header-sub">4 players · live scores from ESPN · rosters from Apple Notes</div>
  </div>
  <div class="live-badge"><div class="live-dot"></div>LIVE</div>
</div>

<div class="page-body">

  <!-- Left: main content -->
  <div class="main-col">
    <div class="cards-grid" id="cards"></div>
    <div class="footer" id="footer"></div>
  </div>

  <!-- Right: schedule sidebar -->
  <div class="sidebar">
    <div class="section-label">Next Games</div>
    <div class="schedule-panel">
      <div class="schedule-header">
        <span class="schedule-title">FIFA World Cup 2026</span>
        <span class="schedule-badge" id="schedule-badge">ESPN</span>
      </div>
      <div id="schedule-body">
        <div class="schedule-loading">Loading schedule…</div>
      </div>
    </div>

    <div class="mc-panel">
      <div class="mc-header">
        <div class="mc-title">🎲 Win Probability</div>
        <div class="mc-sub">Monte Carlo · 10,000 sims · weighted by team strength</div>
      </div>
      <div class="mc-body" id="mc-body">
        <div class="schedule-loading">Calculating…</div>
      </div>
    </div>
  </div>

</div><!-- end page-body -->

<div class="standings-section">
  <div class="standings-title">⚽ Group Standings</div>
  <div class="standings-grid" id="standings-grid">
    <div style="color:#4a7a56;font-size:12px;padding:12px;">Loading standings…</div>
  </div>
</div>

<div class="standings-section">
  <div class="standings-title">📊 Live Power Rankings <span id="power-meta" style="font-size:11px;font-weight:400;color:#4a7a56;margin-left:8px;"></span></div>
  <div id="power-rankings"></div>
</div>

</div><!-- end wrap -->

<script>
const C = {
  CARSON: {primary:'#10b981', bg:'rgba(16,185,129,0.15)', border:'rgba(16,185,129,0.2)'},
  KEITH:  {primary:'#3b82f6', bg:'rgba(59,130,246,0.15)',  border:'rgba(59,130,246,0.2)'},
  LUKE:   {primary:'#f59e0b', bg:'rgba(245,158,11,0.15)',  border:'rgba(245,158,11,0.2)'},
  WILL:   {primary:'#8b5cf6', bg:'rgba(139,92,246,0.15)',  border:'rgba(139,92,246,0.2)'},
};
const RANK_EMOJI = ['🥇','🥈','🥉','4️⃣'];

const FLAGS = {
  'argentina':'🇦🇷','australia':'🇦🇺','austria':'🇦🇹','algeria':'🇩🇿',
  'belgium':'🇧🇪','bosnia':'🇧🇦','brazil':'🇧🇷',
  'canada':'🇨🇦','cape verde':'🇨🇻','colombia':'🇨🇴','congo dr':'🇨🇩',
  'croatia':'🇭🇷','czech republic':'🇨🇿','curaçao':'🇨🇼',
  "cote d'ivoire":"🇨🇮","côte d'ivoire":"🇨🇮",
  'ecuador':'🇪🇨','egypt':'🇪🇬','england':'🏴󠁧󠁢󠁥󠁮󠁧󠁿',
  'france':'🇫🇷','germany':'🇩🇪','ghana':'🇬🇭',
  'haiti':'🇭🇹','iran':'🇮🇷','iraq':'🇮🇶',
  'japan':'🇯🇵','jordan':'🇯🇴',
  'mexico':'🇲🇽','morocco':'🇲🇦',
  'netherlands':'🇳🇱','new zealand':'🇳🇿','norway':'🇳🇴',
  'panama':'🇵🇦','paraguay':'🇵🇾','portugal':'🇵🇹',
  'qatar':'🇶🇦',
  'saudi arabia':'🇸🇦','scotland':'🏴󠁧󠁢󠁳󠁣󠁴󠁿','senegal':'🇸🇳',
  'south africa':'🇿🇦','south korea':'🇰🇷','spain':'🇪🇸','sweden':'🇸🇪',
  'switzerland':'🇨🇭',
  'tunisia':'🇹🇳','türkiye':'🇹🇷','turkiye':'🇹🇷',
  'united states':'🇺🇸','uruguay':'🇺🇾','uzbekistan':'🇺🇿',
};

function flag(name) {
  return FLAGS[name.toLowerCase()] || '🏳️';
}

// All teams owned by any player (for highlighting in schedule)
let ownedTeams = new Set();
let teamOwners = {}; // lowercase team name → player name (CARSON/KEITH/LUKE/WILL)

function ptsClass(pts) {
  if (pts === null || pts === undefined) return 'pts-none';
  if (pts === 0) return 'pts-zero';
  if (pts >= 3) return 'pts-high';
  return 'pts-low';
}

function gamesPlayedForPlayer(player) {
  return player.teams.reduce((sum, t) => sum + (t.gp || 0), 0);
}

function renderLeaderboard(players) {
  const totalPerPlayer = players[0]?.teams.length * 3 || 36; // 12 teams × 3 group games
  const html = players.map((p, i) => {
    const c = C[p.name] || {primary:'#fff'};
    const bestRank = players.filter(o => o.name !== p.name && o.total > p.best_possible).length + 1;
    const bestRankText = bestRank === 1 ? 'Can win 🏆' : `Best: #${bestRank}`;
    const played = gamesPlayedForPlayer(p);
    const remaining = totalPerPlayer - played;
    return `
    <div class="lb-row ${i===0?'first':''}">
      <div class="lb-rank">${RANK_EMOJI[i] || i+1}</div>
      <div class="lb-player">
        <div class="lb-player-name" style="color:${c.primary}">${p.name}</div>
        <div class="lb-player-sub">
          <span style="color:${c.primary};font-weight:700">${played}</span>/<span>${totalPerPlayer}</span> games played
          · <span style="color:#475569">${remaining} left</span>
        </div>
      </div>
      <div class="lb-score" style="color:${c.primary}">${p.total}</div>
      <div class="lb-best-col">
        <div class="lb-best-label">Best possible</div>
        <div class="lb-best-val">${p.best_possible}</div>
        <span class="best-rank-pill" style="background:${c.bg};color:${c.primary}">${bestRankText}</span>
      </div>
    </div>`;
  }).join('');
  document.getElementById('leaderboard').innerHTML = html;
}

/* ── Team game history (group stage pips) ── */
let teamGameData = {}; // normalized name -> [{result,pts,score,oppScore,oppName,completed,live}]

// Normalize team names to match between ESPN and the Apple Note
const NAME_OVERRIDES = {
  'usa': 'united states',
  'ivory coast': "cote d'ivoire",
  "cote d'ivoire": "cote d'ivoire",
  'bosnia and herzegovina': 'bosnia',
  'bosnia-herzegovina': 'bosnia',
  'korea republic': 'south korea',
  'dr congo': 'congo dr',
  'democratic republic of congo': 'congo dr',
  'republic of congo': 'congo dr',
  'turkey': 'turkiye',
  'cape verde islands': 'cape verde',
};

function normalizeName(name) {
  if (!name) return '';
  const s = name.toLowerCase()
    .replace(/[éèêë]/g, 'e').replace(/[àâä]/g, 'a')
    .replace(/[ùûü]/g, 'u').replace(/[ôö]/g, 'o')
    .replace(/[^a-z0-9\s']/g, '').trim();
  return NAME_OVERRIDES[s] || s;
}

async function fetchTeamGameHistory() {
  // Group stage runs June 11 – July 2, 2026; fetch from start to today
  const start = new Date('2026-06-11');
  const today = new Date();
  const dates = [];
  for (let d = new Date(start); d <= today; d.setDate(d.getDate() + 1)) {
    dates.push(d.toISOString().slice(0, 10).replace(/-/g, ''));
  }

  // Fetch all past days in parallel
  const allEvents = (await Promise.all(dates.map(async ds => {
    try {
      const r = await fetch(`https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=${ds}`);
      const data = await r.json();
      return data.events || [];
    } catch(e) { return []; }
  }))).flat();

  const map = {};
  for (const event of allEvents) {
    const comp = event.competitions?.[0];
    if (!comp) continue;
    const statusName = comp.status?.type?.name;
    const isCompleted = statusName === 'STATUS_FINAL' || statusName === 'STATUS_FULL_TIME' || statusName === 'STATUS_FT';
    const LIVE_S = ['STATUS_IN_PROGRESS','STATUS_HALFTIME','STATUS_FIRST_HALF','STATUS_SECOND_HALF','STATUS_EXTRA_TIME','STATUS_PENALTY']; const isLive = LIVE_S.includes(statusName);
    const competitors = comp.competitors || [];
    if (competitors.length < 2) continue;

    for (let i = 0; i < 2; i++) {
      const me = competitors[i];
      const opp = competitors[1 - i];
      const key = normalizeName(me.team?.displayName || '');
      if (!key) continue;
      if (!map[key]) map[key] = [];

      const myScore = parseInt(me.score);
      const oppScore = parseInt(opp.score);
      let result = null, pts = null;
      if (isCompleted && !isNaN(myScore) && !isNaN(oppScore)) {
        if (myScore > oppScore)      { result = 'W'; pts = 3; }
        else if (myScore === oppScore){ result = 'D'; pts = 1; }
        else                          { result = 'L'; pts = 0; }
      }

      map[key].push({ result, pts, score: myScore, oppScore, oppName: opp.team?.displayName, completed: isCompleted, live: isLive, date: event.date });
    }
  }
  teamGameData = map;
}

function buildPips(teamGames) {
  // teamGames is the array from the server: [{result,pts,score,opp_score,opp_name,live}]
  const games = teamGames || [];
  const TOTAL = 3;
  const pips = [];
  for (let i = 0; i < TOTAL; i++) {
    const g = games[i];
    if (!g) {
      pips.push(`<span class="pip pip-empty"></span>`);
    } else if (g.live) {
      pips.push(`<span class="pip pip-live" data-tip="🟢 LIVE vs ${g.opp_name}">●</span>`);
    } else {
      const cls = g.result === 'W' ? 'pip-win' : g.result === 'D' ? 'pip-draw' : 'pip-loss';
      const icon = g.result === 'W' ? '✅' : g.result === 'D' ? '🟡' : '❌';
      const tip = `${icon} ${g.result}  ${g.score}–${g.opp_score} vs ${g.opp_name}  +${g.pts}pt`;
      pips.push(`<span class="pip ${cls}" data-tip="${tip}">${g.pts}</span>`);
    }
  }
  return `<div class="game-pips">${pips.join('')}</div>`;
}

function renderCards(players) {
  const html = players.map(p => {
    const c = C[p.name] || {primary:'#fff', bg:'rgba(255,255,255,0.1)', border:'rgba(255,255,255,0.2)'};
    const pct = p.best_possible > 0 ? Math.round((p.total / p.best_possible) * 100) : 0;
    const rank = players.findIndex(x => x.name === p.name) + 1;
    const played = gamesPlayedForPlayer(p);
    const totalGames = p.teams.length * 3;
    const bestRank = players.filter(o => o.name !== p.name && o.total > p.best_possible).length + 1;
    const bestRankText = bestRank === 1 ? '🏆 Can win' : `Best: #${bestRank}`;

    const teamsHtml = p.teams.map(t => {
      const pts = t.match_pts ?? t.pts ?? null;
      const display = pts !== null ? pts : '—';
      const bonus = t.group_bonus > 0 ? `<span class="team-bonus" title="Group ${t.group_position === 1 ? 'winner' : t.group_position === 2 ? '2nd' : '3rd'} bonus">+${t.group_bonus}</span>` : '';
      const isLive = (t.games || []).some(g => g.live);
      const liveGame = isLive ? t.games.find(g => g.live) : null;
      const liveTip = liveGame ? `LIVE vs ${liveGame.opp_name}` : '';
      return `<div class="team-item ${isLive ? 'team-live' : ''}">
        <span class="team-name">
          <span class="team-flag">${flag(t.name)}</span>
          ${t.name}
          ${isLive ? `<span class="live-pip" title="${liveTip}"></span>` : ''}
        </span>
        <div class="team-right">
          ${buildPips(t.games)}
          <span class="team-pts ${ptsClass(pts)}">${display}</span>
          ${bonus}
        </div>
      </div>`;
    }).join('');
    return `
    <div class="player-card">
      <div class="card-header" style="background:${c.bg};border-bottom-color:${c.border}">
        <div>
          <div class="card-name" style="color:${c.primary}">${RANK_EMOJI[rank-1]} ${p.name}</div>
          <div class="card-meta">
            <span class="meta-pill" style="background:${c.bg};color:${c.primary}">${played}/${totalGames} games played</span>
            <span class="meta-pill" style="background:rgba(255,255,255,0.05);color:#64748b">${bestRankText}</span>
          </div>
        </div>
        <div>
          <div class="card-score" style="color:${c.primary}">${p.total}</div>
          <div class="card-best" style="color:${c.primary}">best: ${p.best_possible}</div>
        </div>
      </div>
      <div class="progress-wrap">
        <div class="progress-bar">
          <div class="progress-fill" style="width:${pct}%;background:${c.primary}"></div>
        </div>
      </div>
      <div class="team-list">${teamsHtml}</div>
    </div>`;
  }).join('');
  document.getElementById('cards').innerHTML = html;
}

/* ── Schedule ── */
function formatGameTime(isoDate) {
  const d = new Date(isoDate);
  return d.toLocaleString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric',
    hour: 'numeric', minute: '2-digit', timeZoneName: 'short'
  });
}

function statusDotClass(statusType) {
  if (['STATUS_IN_PROGRESS','STATUS_HALFTIME','STATUS_FIRST_HALF','STATUS_SECOND_HALF','STATUS_EXTRA_TIME','STATUS_PENALTY'].includes(statusType)) return 'dot-live';
  if (statusType === 'STATUS_SCHEDULED') {
    const soon = false; // could check if within 1hr
    return 'dot-scheduled';
  }
  return 'dot-scheduled';
}

async function fetchScheduleDates(dateStrings) {
  const all = [];
  for (const ds of dateStrings) {
    try {
      const r = await fetch(`https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=${ds}`);
      const data = await r.json();
      all.push(...(data.events || []));
    } catch(e) {}
  }
  return all;
}

function getNext4Games(events) {
  const now = Date.now();
  // Collect live + upcoming, sort by date
  const relevant = events
    .map(e => {
      const comp = e.competitions?.[0] || {};
      const statusType = comp.status?.type?.name || '';
      const date = new Date(e.date).getTime();
      return { e, comp, statusType, date };
    })
    .filter(x => !['STATUS_FINAL','STATUS_FULL_TIME','STATUS_FT'].includes(x.statusType) || x.date > now - 3*60*60*1000)
    .sort((a, b) => a.date - b.date);

  // Prefer live games first, then upcoming
  const live = relevant.filter(x => ['STATUS_IN_PROGRESS','STATUS_HALFTIME','STATUS_FIRST_HALF','STATUS_SECOND_HALF','STATUS_EXTRA_TIME','STATUS_PENALTY'].includes(x.statusType));
  const upcoming = relevant.filter(x => !['STATUS_IN_PROGRESS','STATUS_HALFTIME','STATUS_FIRST_HALF','STATUS_SECOND_HALF','STATUS_EXTRA_TIME','STATUS_PENALTY'].includes(x.statusType));
  return [...live, ...upcoming].slice(0, 4);
}

function renderSchedule(games) {
  if (!games.length) {
    document.getElementById('schedule-body').innerHTML = '<div class="schedule-error">No upcoming games found</div>';
    return;
  }
  const html = games.map(({e, comp, statusType, date}) => {
    const competitors = comp.competitors || [];
    const isLive = ['STATUS_IN_PROGRESS','STATUS_HALFTIME','STATUS_FIRST_HALF','STATUS_SECOND_HALF','STATUS_EXTRA_TIME','STATUS_PENALTY'].includes(statusType);
    const dotClass = isLive ? 'dot-live' : 'dot-scheduled';
    const timeLabel = isLive
      ? `LIVE · ${comp.status?.displayClock || ''} ${comp.status?.period ? `· ${comp.status.period}'` : ''}`
      : formatGameTime(e.date);

    const teamsHtml = competitors.map((c, idx) => {
      const name = c.team?.displayName || c.team?.name || '?';
      const score = c.score;
      const isOwned = ownedTeams.has(name.toLowerCase());
      const ownerKey = teamOwners[name.toLowerCase()];
      const ownerTag = ownerKey && C[ownerKey]
        ? `<span class="owner-tag" style="background:${C[ownerKey].bg};color:${C[ownerKey].primary};border:1px solid ${C[ownerKey].border}">${ownerKey[0]}</span>`
        : '';
      return `
        ${idx === 1 ? '<div class="game-vs">vs</div>' : ''}
        <div class="game-team">
          <span class="game-team-name ${isOwned ? 'owned' : ''}">${name}${ownerTag}</span>
          ${isLive || statusType === 'STATUS_FINAL' ? `<span class="game-score">${score ?? '—'}</span>` : ''}
        </div>`;
    }).join('');

    const venue = comp.venue || {};
    const stadiumName = venue.fullName || '';
    const city = venue.address?.city || '';
    const venueLabel = stadiumName ? `${stadiumName}${city ? ' · ' + city : ''}` : (city || '');

    return `
    <div class="game-item">
      <div class="game-time">
        <span class="game-status-dot ${dotClass}"></span>
        ${timeLabel}
      </div>
      <div class="game-teams">${teamsHtml}</div>
      ${venueLabel ? `<div class="game-venue">📍 ${venueLabel}</div>` : ''}
    </div>`;
  }).join('');

  document.getElementById('schedule-body').innerHTML = html;
}

async function updateSchedule() {
  try {
    // Fetch yesterday + today + next 3 days (local time, not UTC — avoids missing
    // late-night games that flip to "tomorrow" in UTC while still today locally)
    const now = new Date();
    const dates = [];
    for (let i = -1; i < 4; i++) {
      const d = new Date(now);
      d.setDate(d.getDate() + i);
      const yy = d.getFullYear();
      const mm = String(d.getMonth() + 1).padStart(2, '0');
      const dd = String(d.getDate()).padStart(2, '0');
      dates.push(`${yy}${mm}${dd}`);
    }
    const events = await fetchScheduleDates(dates);
    const next4 = getNext4Games(events);
    renderSchedule(next4);
  } catch(e) {
    document.getElementById('schedule-body').innerHTML = '<div class="schedule-error">Could not load schedule</div>';
  }
}

function renderMonteCarlo(simProbs, players) {
  const el = document.getElementById('mc-body');
  if (!simProbs || !players) { el.innerHTML = '<div class="schedule-error">Not available</div>'; return; }
  const sorted = [...players]
    .map(p => ({ name: p.name, prob: simProbs[p.name] ?? 0 }))
    .sort((a, b) => b.prob - a.prob);
  el.innerHTML = sorted.map(({ name, prob }) => {
    const c = C[name] || { primary: '#fff' };
    return `<div class="mc-row">
      <div class="mc-label">
        <span style="color:${c.primary};font-weight:800">${name}</span>
        <span class="mc-pct" style="color:${c.primary}">${prob.toFixed(1)}%</span>
      </div>
      <div class="mc-bar-bg">
        <div class="mc-bar-fill" style="width:${Math.min(prob,100)}%;background:${c.primary}"></div>
      </div>
    </div>`;
  }).join('');
}

async function updateAll() {
  try {
    const [, data] = await Promise.all([
      updateSchedule(),
      fetch('/api/data').then(r => r.json()),
    ]);
    ownedTeams = new Set();
    teamOwners = {};
    data.players.forEach(p => p.teams.forEach(t => {
      const key = t.name.toLowerCase();
      ownedTeams.add(key);
      teamOwners[key] = p.name.toUpperCase();
    }));
    renderCards(data.players);
    renderMonteCarlo(data.sim_probs, data.players);
    renderPowerRankings(data.live_strengths, data.games_used, data.odds_used);
    renderStandings(data.group_standings);
    const oddsNote = data.odds_used > 0 ? ` · DraftKings odds on ${data.odds_used} games` : '';
    document.getElementById('footer').textContent = `Scores from ESPN${oddsNote} · Updated: ${data.updated}`;
  } catch(e) {
    document.getElementById('footer').textContent = 'Error loading data — retrying…';
  }
}

function renderPowerRankings(strengths, gamesUsed, oddsUsed) {
  const el = document.getElementById('power-rankings');
  const meta = document.getElementById('power-meta');
  if (!strengths || !el) return;
  const parts = [];
  if (gamesUsed > 0) parts.push(`Elo-adjusted · ${gamesUsed} games played`);
  if (oddsUsed > 0) parts.push(`DraftKings odds on ${oddsUsed} upcoming games`);
  if (meta) meta.textContent = parts.length ? parts.join(' · ') : 'Pre-tournament baseline';

  // Sort teams by current live strength, show all teams in the roster
  const rosterTeams = new Set();
  Object.values(teamOwners).forEach(() => {});
  Object.keys(teamOwners).forEach(k => rosterTeams.add(k));
  // Build list of all teams with a strength rating
  const entries = Object.entries(strengths)
    .sort((a, b) => b[1] - a[1]);

  const maxStr = entries[0]?.[1] || 100;
  const rows = entries.map(([team, val], i) => {
    const base = TEAM_STRENGTH_JS[team] || 55;
    const delta = val - base;
    const deltaStr = delta > 0.05 ? `<span style="color:#22c55e">▲${delta.toFixed(1)}</span>`
                   : delta < -0.05 ? `<span style="color:#f87171">▼${Math.abs(delta).toFixed(1)}</span>`
                   : `<span style="color:#4a7a56">—</span>`;
    const ownerKey = teamOwners[team];
    const ownerBadge = ownerKey && C[ownerKey]
      ? `<span class="pr-owner" style="background:${C[ownerKey].bg};color:${C[ownerKey].primary}">${ownerKey[0]}</span>`
      : '';
    const barColor = delta > 0.5 ? '#22c55e' : delta < -0.5 ? '#f87171' : '#facc15';
    const barPct = Math.round(val / maxStr * 100);
    const displayName = team.split(' ').map(w => w[0].toUpperCase() + w.slice(1)).join(' ');
    return `<div class="pr-row">
      <div class="pr-rank">${i + 1}</div>
      <div class="pr-name">${flag(team)} ${displayName}${ownerBadge}</div>
      <div class="pr-bar-wrap"><div class="pr-bar" style="width:${barPct}%;background:${barColor}"></div></div>
      <div class="pr-val">${val.toFixed(1)}</div>
      <div class="pr-delta">${deltaStr}</div>
    </div>`;
  }).join('');
  el.innerHTML = rows;
}

// Baseline strengths for delta display
const TEAM_STRENGTH_JS = {
  'argentina':95,'france':94,'spain':92,'england':90,'brazil':90,'portugal':89,
  'netherlands':87,'germany':86,'belgium':84,'uruguay':81,'croatia':80,'morocco':79,
  'colombia':78,'switzerland':76,'senegal':76,"cote d'ivoire":74,'mexico':75,
  'japan':75,'united states':74,'turkiye':72,'austria':71,'ecuador':70,'norway':70,
  'south korea':70,'canada':68,'algeria':67,'sweden':67,'egypt':66,'ghana':65,
  'czech republic':65,'tunisia':64,'iran':64,'scotland':64,'australia':68,
  'paraguay':60,'bosnia':60,'panama':58,'saudi arabia':58,'qatar':56,
  'south africa':55,'uzbekistan':52,'congo dr':50,'jordan':50,'new zealand':50,
  'cape verde':48,'iraq':48,'curacao':45,'haiti':44,
};

function renderStandings(groups) {
  if (!groups || !groups.length) return;
  const el = document.getElementById('standings-grid');
  el.innerHTML = groups.map(g => {
    const rows = g.entries.map(e => {
      const adv = e.adv === 'yes' ? 'adv-yes' : e.adv === 'maybe' ? 'adv-maybe' : e.adv === 'no' ? 'adv-no' : '';
      const owned = ownedTeams.has(e.team.toLowerCase()) ? '<span class="owned-dot">●</span>' : '';
      const ownerKey = teamOwners[e.team.toLowerCase()];
      const ownerBadge = ownerKey && C[ownerKey]
        ? `<span class="owner-tag" style="background:${C[ownerKey].bg};color:${C[ownerKey].primary};border:1px solid ${C[ownerKey].border}">${ownerKey[0]}</span>`
        : '';
      const liveDot = e.is_live ? `<span class="grp-live-dot" title="${e.live_score}"></span>` : '';
      const liveTip = e.is_live ? ` title="LIVE: ${e.live_score}"` : '';
      return `<tr class="${adv}${e.is_live ? ' grp-live-row' : ''}">
        <td${liveTip}><div class="team-name-cell">${liveDot}${owned}<span>${e.team}</span>${ownerBadge}</div></td>
        <td>${e.gp}</td><td>${e.w}</td><td>${e.d}</td><td>${e.l}</td>
        <td>${e.gd}</td><td class="pts">${e.pts}</td>
      </tr>`;
    }).join('');
    const liveTag = g.has_live ? '<span class="grp-live-badge">LIVE</span>' : '';
    return `<div class="group-card${g.has_live ? ' group-card-live' : ''}">
      <div class="group-header">${g.name} ${liveTag}</div>
      <table class="group-table">
        <thead><tr>
          <th>Team</th><th>GP</th><th>W</th><th>D</th><th>L</th><th>GD</th><th>PTS</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
  }).join('');
}

updateAll();
setInterval(updateAll, 30000);

// ── Global pip tooltip (fixed position, never clipped by overflow:hidden) ──
const pipTip = document.getElementById('pip-tooltip');
document.addEventListener('mouseover', e => {
  const pip = e.target.closest('[data-tip]');
  if (!pip) return;
  pipTip.textContent = pip.dataset.tip;
  pipTip.style.display = 'block';
  const r = pip.getBoundingClientRect();
  const tw = pipTip.offsetWidth, th = pipTip.offsetHeight;
  const top = r.top - th - 8 > 0 ? r.top - th - 8 : r.bottom + 8;
  const left = Math.max(6, Math.min(r.left + r.width/2 - tw/2, window.innerWidth - tw - 6));
  pipTip.style.top = top + 'px';
  pipTip.style.left = left + 'px';
});
document.addEventListener('mouseout', e => {
  if (e.target.closest('[data-tip]')) pipTip.style.display = 'none';
});
</script>
<div id="pip-tooltip"></div>
</body>
</html>"""


import urllib.request, concurrent.futures
from datetime import timedelta

# ── Name normalization ────────────────────────────────────────────────────────

ESPN_NAME_MAP = {
    'czechia': 'czech republic',
    'bosnia-herzegovina': 'bosnia',       # with hyphen (stripped before lookup)
    'bosniaherzegovina': 'bosnia',         # ESPN live format (hyphen stripped by norm)
    'bosnia and herzegovina': 'bosnia',
    'ivory coast': "cote d'ivoire",
    'dr congo': 'congo dr',
    'democratic republic of congo': 'congo dr',
    'korea republic': 'south korea',
    'cape verde islands': 'cape verde',
    'turkey': 'turkiye',
    'usa': 'united states',
}

def norm(name):
    """Normalize a team name for comparison."""
    if not name: return ''
    s = name.lower()
    for a, b in [('é','e'),('è','e'),('ê','e'),('ë','e'),('à','a'),('â','a'),
                 ('ä','a'),('ù','u'),('û','u'),('ü','u'),('ô','o'),('ö','o'),('ç','c')]:
        s = s.replace(a, b)
    s = re.sub(r"[^\w\s']", '', s).strip()
    return ESPN_NAME_MAP.get(s, s)

# ── Roster (fixed — cloud deployment has no access to Apple Notes) ────────────
# Source of truth: Apple Note "World Cup" as of 2026-06-16.
# If rosters change, update this dict and redeploy.

FIXED_ROSTER = {
    'CARSON': ['Brazil', 'Portugal', 'United States', 'Switzerland', 'Sweden', 'Ecuador',
               'Scotland', 'Egypt', 'New Zealand', 'Panama', 'Congo DR', 'Cape Verde'],
    'KEITH': ['Spain', 'Netherlands', 'Belgium', 'Croatia', 'Morocco', 'South Korea',
              'Australia', 'Paraguay', 'Tunisia', 'Qatar', 'Jordan', 'South Africa'],
    'WILL': ['Germany', 'England', 'Japan', 'Uruguay', 'Mexico', 'Senegal',
             'Algeria', 'Bosnia', 'Iran', 'Ghana', 'Saudi Arabia', 'Curaçao'],
    'LUKE': ['France', 'Argentina', 'Norway', 'Colombia', 'Türkiye', "Côte d'Ivoire",
             'Austria', 'Canada', 'Czech Republic', 'Uzbekistan', 'Haiti', 'Iraq'],
}

def read_note():
    return ''  # not available in cloud deployment

def strip_html(html):
    text = re.sub(r'<br\s*/?>', '\n', html, flags=re.I)
    text = re.sub(r'</div>', '\n', text, flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)
    return text.replace('&gt;','>').replace('&lt;','<').replace('&amp;','&').replace('&nbsp;',' ')

RULES_KEYWORDS = [
    'you get a point', '=>', 'win group', 'bonus point', 'bronze winner',
    'runner up', 'winner =', 'credits ray', 'bernini', 'each win',
    'advancing to the next', 'group stage', '4 points', '2 points', '1 point',
    'and the points build',
]

def parse_note_roster(html):
    """Extract player → [team name, ...] from the Note. Ignores scores."""
    text = strip_html(html)
    players = {}
    current = None
    for raw in text.split('\n'):
        line = raw.strip()
        if not line: continue
        if '2022 results' in line.lower(): break
        m = re.match(r'^(CARSON|KEITH|LUKE|WILL)\b', line, re.I)
        if m:
            current = m.group(1).upper()
            players[current] = []
            continue
        if current:
            if any(kw in line.lower() for kw in RULES_KEYWORDS): continue
            clean = re.sub(r"[^\w\s'\-\.]", '', line, flags=re.UNICODE).strip()
            if not clean or len(clean) < 2: continue
            # Strip trailing score if present (e.g. "Brazil - 3")
            team_name = re.sub(r'\s*-\s*\d+\s*$', '', clean).strip(' -')
            if team_name and len(team_name) > 1:
                players[current].append(team_name)
    return players

# ── ESPN game data ─────────────────────────────────────────────────────────────

def fetch_espn_url(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.load(r)

def fetch_group_stage_games():
    """
    Fetch ALL group-stage games from ESPN for the full window (June 11 – July 2),
    including games that haven't been played yet (status == scheduled). This is
    required so that teams which haven't played any games so far are still known
    to the system (correct group membership + correct remaining fixture list),
    instead of being invisible to scoring/simulation until their first kickoff.
    Fetched concurrently across days to keep this fast.
    """
    dates = []
    d = datetime(2026, 6, 11)
    end = datetime(2026, 7, 3)
    while d < end:
        dates.append(d.strftime('%Y%m%d'))
        d += timedelta(days=1)

    def fetch_day(ds):
        day_games = []
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates={ds}"
            data = fetch_espn_url(url)
            for event in data.get('events', []):
                slug = event.get('season', {}).get('slug', '')
                if 'group' not in slug: continue  # skip knockout rounds
                comp = event['competitions'][0]
                status = comp['status']['type']['name']
                is_done = status in ('STATUS_FULL_TIME', 'STATUS_FINAL', 'STATUS_FT')
                is_live = status in ('STATUS_IN_PROGRESS', 'STATUS_HALFTIME',
                                     'STATUS_FIRST_HALF', 'STATUS_SECOND_HALF',
                                     'STATUS_EXTRA_TIME', 'STATUS_PENALTY')
                # Note: scheduled (not done, not live) games are kept too —
                # they're needed to know full group membership & remaining fixtures.
                cs = comp['competitors']
                if len(cs) < 2: continue
                t1, t2 = cs[0], cs[1]
                s1 = int(t1.get('score') or 0)
                s2 = int(t2.get('score') or 0)
                # Extract DraftKings moneyline odds (home=t1, away=t2)
                ml_home = ml_away = ml_draw = None
                try:
                    odds_obj = comp.get('odds', [{}])[0]
                    ml = odds_obj.get('moneyline', {})
                    ml_home = ml.get('home', {}).get('close', {}).get('odds')
                    ml_away = ml.get('away', {}).get('close', {}).get('odds')
                    ml_draw = ml.get('draw', {}).get('close', {}).get('odds')
                    if ml_home is not None: ml_home = float(ml_home)
                    if ml_away is not None: ml_away = float(ml_away)
                    if ml_draw is not None: ml_draw = float(ml_draw)
                except Exception:
                    pass
                day_games.append({
                    'team1': norm(t1['team']['displayName']),
                    'team2': norm(t2['team']['displayName']),
                    'team1_display': t1['team']['displayName'],
                    'team2_display': t2['team']['displayName'],
                    'score1': s1, 'score2': s2,
                    'done': is_done, 'live': is_live,
                    'date': event['date'],
                    'ml_home': ml_home, 'ml_away': ml_away, 'ml_draw': ml_draw,
                })
        except Exception:
            pass
        return day_games

    games = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        for day_games in ex.map(fetch_day, dates):
            games.extend(day_games)
    return games

def build_team_stats(games):
    """
    Returns:
      team_stats: {norm_name: {pts, gp, w, d, l, gf, ga, gd, group_id, group_pos, group_done, games[]}}
    Groups determined via union-find on opponents.
    """
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        if parent[x] != x: parent[x] = find(parent[x])
        return parent[x]
    def union(x, y):
        px, py = find(x), find(y)
        if px != py: parent[px] = py

    stats = {}
    def get(t):
        if t not in stats:
            stats[t] = {'pts':0,'gp':0,'w':0,'d':0,'l':0,'gf':0,'ga':0,'gd':0,'games':[]}
        return stats[t]

    for g in games:
        t1, t2 = g['team1'], g['team2']
        s1, s2 = g['score1'], g['score2']
        union(t1, t2)
        # Always register both teams, even for scheduled (not yet played) games,
        # so teams with 0 games played so far are still known to the system.
        get(t1); get(t2)
        if g['done']:
            for team, score, opp_score, opp_disp in [
                (t1, s1, s2, g['team2_display']),
                (t2, s2, s1, g['team1_display'])
            ]:
                st = get(team)
                st['gp'] += 1
                st['gf'] += score
                st['ga'] += opp_score
                st['gd'] = st['gf'] - st['ga']
                if score > opp_score:
                    result, pts = 'W', 3
                    st['pts'] += 3; st['w'] += 1
                elif score == opp_score:
                    result, pts = 'D', 1
                    st['pts'] += 1; st['d'] += 1
                else:
                    result, pts = 'L', 0
                    st['l'] += 1
                st['games'].append({
                    'result': result, 'pts': pts,
                    'score': score, 'opp_score': opp_score,
                    'opp_name': opp_disp, 'live': False,
                })
        elif g['live']:
            for team, opp_disp in [(t1, g['team2_display']), (t2, g['team1_display'])]:
                get(team)['games'].append({'live': True, 'opp_name': opp_disp, 'result': None, 'pts': None})

    # Assign group IDs via union-find roots
    group_roots = {}
    ctr = [0]
    for team in list(stats.keys()):
        root = find(team)
        if root not in group_roots:
            ctr[0] += 1
            group_roots[root] = ctr[0]
        stats[team]['group_id'] = group_roots[root]

    # Calculate group positions within each group
    groups = {}
    for team, s in stats.items():
        groups.setdefault(s['group_id'], []).append((team, s))

    for members in groups.values():
        sorted_m = sorted(members, key=lambda x: (-x[1]['pts'], -x[1]['gd'], -x[1]['gf']))
        group_done = all(x[1]['gp'] == 3 for x in members)
        for pos, (team, s) in enumerate(sorted_m, 1):
            s['group_pos'] = pos
            s['group_done'] = group_done

    # ── Wild-card 3rd-place advancement (best 8 third-placed teams) ─────────
    # The "+1 for 3rd place" bonus only applies if that team actually advances
    # to the Round of 32 as one of the 8 best third-place finishers. This can
    # only be determined for real once every group has finished (12 groups x
    # 3 games each); until then no team gets credit for it.
    all_groups_done = len(groups) > 0 and all(
        all(s['gp'] == 3 for _, s in members) for members in groups.values()
    )
    third_placers = []
    for members in groups.values():
        for team, s in members:
            if s.get('group_pos') == 3:
                third_placers.append((team, s))
                s['advances_wildcard'] = False
    if all_groups_done:
        third_placers.sort(key=lambda x: (-x[1]['pts'], -x[1]['gd'], -x[1]['gf']))
        for team, s in third_placers[:8]:
            s['advances_wildcard'] = True

    return stats

# ── Scoring rules ──────────────────────────────────────────────────────────────

def calculate_scores(roster, team_stats):
    """
    Scoring per the rules:
      Group stage:  3pts win / 1pt draw / 0pts loss
      Group finish: 1st +4, 2nd +2, 3rd (qualifying wildcard) +1
      Knockout:     +4 per round won
      Bronze match: +2 for winner (no +4 for the win)
      Runner-up:    +2 bonus
      Champion:     +4 bonus (on top of +4 for winning the final)
    """
    # Max knockout points by finishing position (1 team per slot):
    # Champion: 5 wins×4 + 4 bonus = 24
    # Runner-up: 4 wins×4 + 2 bonus = 18
    # Bronze: 3 wins×4 + 2 (bronze, not 4) = 14
    # SF loser: 3 wins×4 = 12
    # QF loser: 3 wins×4 = 12  (R32 + R16 + QF... wait: R32+R16+QF = 3 wins × 4 = 12)
    # R16 loser: 2 wins×4 = 8
    # R32 loser: 1 win×4 = 4
    KO_SLOTS = [24, 18, 14, 12, 12, 12, 12, 8, 8, 4, 4, 4]

    result = []
    for player, teams in roster.items():
        total = 0
        team_details = []
        for team_name in teams:
            key = norm(team_name)
            s = team_stats.get(key, {})
            match_pts = s.get('pts', 0)
            group_bonus = 0
            eliminated = False
            if s.get('group_done'):
                pos = s.get('group_pos', 99)
                if pos == 1: group_bonus = 4
                elif pos == 2: group_bonus = 2
                elif pos == 3 and s.get('advances_wildcard'): group_bonus = 1
                elif pos >= 4: eliminated = True
                elif pos == 3 and not s.get('advances_wildcard'): eliminated = True

            team_total = match_pts + group_bonus
            total += team_total

            # Group stage ceiling (no knockout yet — applied player-level below)
            gp = s.get('gp', 0)
            if s.get('group_done') or eliminated:
                group_remaining = 0
                potential_bonus = group_bonus
            else:
                group_remaining = max(0, 3 - gp) * 3
                potential_bonus = 4  # could still win group

            team_details.append({
                'name': team_name,
                'match_pts': match_pts,
                'group_bonus': group_bonus,
                'total': team_total,
                'gp': gp,
                'group_pos': s.get('group_pos'),
                'group_done': s.get('group_done', False),
                'games': s.get('games', []),
                'eliminated': eliminated,
                '_group_ceiling': team_total + group_remaining + max(0, potential_bonus - group_bonus),
            })

        # Group ceiling: sum of per-team group-stage ceilings
        group_ceiling_total = sum(t['_group_ceiling'] for t in team_details)

        # Knockout ceiling: declining slots — only 1 team can be champion, 1 runner-up, etc.
        # Sort eligible teams (not eliminated) by strength desc to assign best slots first
        eligible = sorted(
            [t for t in team_details if not t['eliminated']],
            key=lambda t: strength(norm(t['name'])),
            reverse=True
        )
        ko_ceiling = sum(KO_SLOTS[i] for i in range(min(len(eligible), len(KO_SLOTS))))

        best_possible = group_ceiling_total + ko_ceiling
        result.append({
            'name': player,
            'total': total,
            'best_possible': best_possible,
            'teams': [{k:v for k,v in t.items() if k not in ('_group_ceiling', 'eliminated')} for t in team_details],
        })

    result.sort(key=lambda x: x['total'], reverse=True)
    return result

# ── Monte Carlo simulation ────────────────────────────────────────────────────

# Approximate team strength ratings (0-100), based on general squad quality /
# FIFA-ranking tiers heading into the 2026 tournament. Used to weight simulated
# match outcomes instead of treating every game as a coin flip.
TEAM_STRENGTH = {
    'argentina': 95, 'france': 94, 'spain': 92, 'england': 90, 'brazil': 90,
    'portugal': 89, 'netherlands': 87, 'germany': 86, 'belgium': 84,
    'uruguay': 81, 'croatia': 80, 'morocco': 79, 'colombia': 78,
    'switzerland': 76, 'senegal': 76, "cote d'ivoire": 74, 'mexico': 75,
    'japan': 75, 'united states': 74, 'turkiye': 72, 'austria': 71,
    'ecuador': 70, 'norway': 70, 'south korea': 70, 'canada': 68,
    'algeria': 67, 'sweden': 67, 'egypt': 66, 'ghana': 65,
    'czech republic': 65, 'tunisia': 64, 'iran': 64, 'scotland': 64,
    'australia': 68, 'paraguay': 60, 'bosnia': 60, 'panama': 58, 'saudi arabia': 58,
    'qatar': 56, 'south africa': 55, 'uzbekistan': 52, 'congo dr': 50,
    'jordan': 50, 'new zealand': 50, 'cape verde': 48, 'iraq': 48,
    'curacao': 45, 'haiti': 44,
}

def strength(team):
    return TEAM_STRENGTH.get(team, 55)  # default: mid-table unknown

def compute_live_strengths(done_games, scheduled_games=None):
    """Apply Elo updates (K=50) from every completed tournament game to the baseline.
    Sportsbook odds are used only for match-level probabilities in the Monte Carlo,
    not to modify team ratings (odds against weak opponents produce artificially low
    implied ratings for strong teams, distorting the rankings)."""
    live = {team: float(v) for team, v in TEAM_STRENGTH.items()}
    for g in done_games:
        for t in (g['team1'], g['team2']):
            if t not in live:
                live[t] = 55.0
    K = 50
    for g in done_games:
        t1, t2 = g['team1'], g['team2']
        r1, r2 = live.get(t1, 55.0), live.get(t2, 55.0)
        expected1 = 1 / (1 + 10 ** (-(r1 - r2) * 20 / 400))
        s1, s2 = g['score1'], g['score2']
        actual1 = 1.0 if s1 > s2 else (0.5 if s1 == s2 else 0.0)
        delta = K * (actual1 - expected1) / 20
        live[t1] = max(20.0, min(100.0, r1 + delta))
        live[t2] = max(20.0, min(100.0, r2 - delta))
    return live

def _ml_to_implied(ml):
    """American moneyline → raw implied probability (before vig removal)."""
    if ml is None: return None
    return (abs(ml) / (abs(ml) + 100)) if ml < 0 else (100 / (ml + 100))

def odds_match_probs(game):
    """Extract vig-free (p1_win, p_draw, p2_win) from DraftKings moneyline on a game dict.
    Returns None if odds are missing or malformed."""
    try:
        p1r = _ml_to_implied(game['ml_home'])
        p2r = _ml_to_implied(game['ml_away'])
        pdr = _ml_to_implied(game['ml_draw'])
        if None in (p1r, p2r, pdr): return None
        total = p1r + p2r + pdr  # >1.0 due to vig; normalize to remove it
        return p1r / total, pdr / total, p2r / total
    except Exception:
        return None

def match_probs(t1, t2):
    """
    Return (p_t1_win, p_draw, p_t2_win) for a group-stage match,
    using an Elo-style logistic curve on the strength gap plus a flat draw rate.
    """
    diff = (strength(t1) - strength(t2)) * 20      # scale rating gap to elo-like units
    p1_decisive = 1 / (1 + 10 ** (-diff / 400))
    draw_rate = 0.24
    p1 = p1_decisive * (1 - draw_rate)
    p2 = (1 - p1_decisive) * (1 - draw_rate)
    return p1, draw_rate, p2

def knockout_win_prob(t1, t2):
    """P(t1 beats t2) in a knockout match (no draws — eventually decided)."""
    diff = (strength(t1) - strength(t2)) * 20
    return 1 / (1 + 10 ** (-diff / 400))


def get_remaining_games(done_games, team_stats):
    """Enumerate all group-stage games not yet played by round-robin within each group."""
    # Collect already-played pairs (normalized names)
    played = set()
    for g in done_games:
        played.add(frozenset([g['team1'], g['team2']]))

    # Group teams by group_id
    groups = {}
    for team, s in team_stats.items():
        gid = s.get('group_id')
        if gid is not None:
            groups.setdefault(gid, []).append(team)

    remaining = []
    for members in groups.values():
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                pair = frozenset([members[i], members[j]])
                if pair not in played:
                    remaining.append((members[i], members[j]))
    return remaining


def run_monte_carlo(roster, team_stats, done_games, n=10000, all_games=None):
    """
    Simulate n full tournaments (remaining group games + knockout rounds).
    Group games: outcome weighted by team strength (Elo-style) + flat draw rate.
    Knockout: weighted by team strength, no draws, +4 pts per round won.
    Top 2 per group + 8 best 3rd-place teams advance (32 teams total).
    Returns {player_name: win_probability_pct}.
    """
    remaining = get_remaining_games(done_games, team_stats)

    groups = {}
    for team, s in team_stats.items():
        gid = s.get('group_id')
        if gid is not None:
            groups.setdefault(gid, []).append(team)

    base_pts = {team: s['pts'] for team, s in team_stats.items()}
    player_teams = {player: [norm(t) for t in teams] for player, teams in roster.items()}
    win_counts = {p: 0.0 for p in roster}

    # Build live-adjusted strengths: Elo from results + odds-implied from upcoming games
    scheduled = [g for g in (all_games or []) if not g.get('done') and not g.get('live')]
    live_str = compute_live_strengths(done_games, scheduled_games=scheduled)
    def live_match_probs(t1, t2):
        diff = (live_str.get(t1, 55) - live_str.get(t2, 55)) * 20
        p1d = 1 / (1 + 10 ** (-diff / 400))
        dr = 0.24
        return p1d * (1 - dr), dr, (1 - p1d) * (1 - dr)
    def live_ko_prob(t1, t2):
        diff = (live_str.get(t1, 55) - live_str.get(t2, 55)) * 20
        return 1 / (1 + 10 ** (-diff / 400))

    # Build odds lookup from scheduled games: frozenset(t1,t2) → game dict
    odds_lookup = {}
    for g in (all_games or []):
        if not g.get('done') and not g.get('live'):
            key = frozenset([g['team1'], g['team2']])
            odds_lookup[key] = g

    odds_used = 0
    def best_match_probs(t1, t2):
        nonlocal odds_used
        g = odds_lookup.get(frozenset([t1, t2]))
        if g:
            result = odds_match_probs(g)
            if result:
                odds_used += 1
                return result
        return live_match_probs(t1, t2)

    # Precompute match probabilities once — sportsbook odds preferred, Elo fallback
    match_p = {(t1, t2): best_match_probs(t1, t2) for t1, t2 in remaining}

    for _ in range(n):
        pts = dict(base_pts)

        # ── Simulate remaining group games (quality-weighted) ────────────
        for t1, t2 in remaining:
            p1, pd, p2 = match_p[(t1, t2)]
            r = random.random()
            if r < p1:
                pts[t1] = pts.get(t1, 0) + 3
            elif r < p1 + pd:
                pts[t1] = pts.get(t1, 0) + 1
                pts[t2] = pts.get(t2, 0) + 1
            else:
                pts[t2] = pts.get(t2, 0) + 3

        # ── Group bonuses + determine who advances ──────────────────────
        group_bonus = {}
        advanced = []      # teams in knockout
        third_place = []   # (team, pts) for wild-card selection

        for members in groups.values():
            sorted_m = sorted(members, key=lambda t: -pts.get(t, 0))
            if len(sorted_m) > 0: group_bonus[sorted_m[0]] = 4
            if len(sorted_m) > 1: group_bonus[sorted_m[1]] = 2
            advanced.extend(sorted_m[:2])           # top 2 advance directly
            if len(sorted_m) >= 3:
                third_place.append((sorted_m[2], pts.get(sorted_m[2], 0)))

        # Best 8 third-place teams also advance (WC 2026 format); only those
        # 8 get the "+1 for 3rd place" bonus, per the rule "3rd, but you
        # advance to rd of 32, => 1 point".
        third_place.sort(key=lambda x: -x[1])
        wildcards = third_place[:8]
        for t, _ in wildcards:
            group_bonus[t] = 1
        advanced.extend(t for t, _ in wildcards)  # 24 + 8 = 32 teams

        # ── Simulate knockout rounds (quality-weighted) ──────────────────
        # Generic rule: +4 pts per win / round advanced.
        # Exceptions: 3rd-place (bronze) match winner gets +2 instead of +4;
        # Final loser (runner-up) gets +2 bonus; Final winner (champion) gets
        # an extra +4 bonus on top of their round-win points.
        knockout_bonus = {team: 0 for team in advanced}
        random.shuffle(advanced)
        current_round = list(advanced)
        semifinal_losers = []
        while len(current_round) > 1:
            next_round = []
            is_semifinal = len(current_round) == 4
            is_final = len(current_round) == 2
            for i in range(0, len(current_round) - 1, 2):
                a, b = current_round[i], current_round[i + 1]
                p_a = live_ko_prob(a, b)
                winner = a if random.random() < p_a else b
                loser = b if winner is a else a
                if is_semifinal:
                    semifinal_losers.append(loser)
                if is_final:
                    # Final winner: +4 round win + +4 champion bonus
                    knockout_bonus[winner] = knockout_bonus.get(winner, 0) + 4 + 4
                    # Runner-up: +2 bonus (no points for the round "win" since they lost)
                    knockout_bonus[loser] = knockout_bonus.get(loser, 0) + 2
                else:
                    knockout_bonus[winner] = knockout_bonus.get(winner, 0) + 4
                next_round.append(winner)
            if len(current_round) % 2 == 1:          # bye if odd (shouldn't happen at 32)
                next_round.append(current_round[-1])
            current_round = next_round

        # ── 3rd-place (bronze) match between the two semifinal losers ───
        if len(semifinal_losers) == 2:
            a, b = semifinal_losers
            p_a = live_ko_prob(a, b)
            bronze_winner = a if random.random() < p_a else b
            knockout_bonus[bronze_winner] = knockout_bonus.get(bronze_winner, 0) + 2

        # ── Player final scores ─────────────────────────────────────────
        scores = {
            player: sum(
                pts.get(t, 0) + group_bonus.get(t, 0) + knockout_bonus.get(t, 0)
                for t in teams
            )
            for player, teams in player_teams.items()
        }

        mx = max(scores.values()) if scores else 0
        winners = [p for p, s in scores.items() if s == mx]
        for w in winners:
            win_counts[w] += 1.0 / len(winners)

    return {
        'probs': {p: round(win_counts[p] / n * 100, 1) for p in win_counts},
        'live_strengths': {t: round(v, 1) for t, v in live_str.items()},
        'games_used': len(done_games),
        'odds_used': odds_used,
    }


# ── Group standings (from ESPN standings endpoint) ────────────────────────────

def fetch_group_standings(live_games=None):
    """
    Fetch live group standings for all 12 WC 2026 groups from ESPN.
    Overlays any in-progress game scores on top of the official standings
    so the table reflects the current live score, not just completed results.
    Returns a list of groups, each with name and sorted entries.
    """
    try:
        url = 'https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/standings'
        data = fetch_espn_url(url)

        # Build provisional live adjustments: {norm_team: {pts_delta, gd_delta, is_live, score, opp_score, opp_name}}
        live_adj = {}
        for g in (live_games or []):
            if not g.get('live'): continue
            s1, s2 = g['score1'], g['score2']
            t1, t2 = g['team1'], g['team2']
            # Points delta for each team based on current score
            if s1 > s2:   p1, p2 = 3, 0
            elif s1 == s2: p1, p2 = 1, 1
            else:          p1, p2 = 0, 3
            live_adj[t1] = {'pts': p1, 'gd': s1 - s2, 'is_live': True,
                            'score': s1, 'opp_score': s2, 'opp': g['team2_display']}
            live_adj[t2] = {'pts': p2, 'gd': s2 - s1, 'is_live': True,
                            'score': s2, 'opp_score': s1, 'opp': g['team1_display']}
        groups = []
        for child in data.get('children', []):
            name = child.get('name', '')          # e.g. "Group A"
            entries = []
            for e in child.get('standings', {}).get('entries', []):
                stats = {s['abbreviation']: s['displayValue'] for s in e.get('stats', [])}
                note = e.get('note', {}).get('description', '')
                if 'advance' in note.lower() and 'best' not in note.lower():
                    adv = 'yes'
                elif 'best' in note.lower():
                    adv = 'maybe'
                elif 'eliminat' in note.lower():
                    adv = 'no'
                else:
                    adv = ''
                team_disp = e['team']['displayName']
                team_key  = norm(team_disp)
                adj = live_adj.get(team_key, {})
                base_pts = int(stats.get('P',  '0'))
                base_gd  = int((stats.get('GD','0') or '0').replace('+',''))
                live_pts = base_pts + adj.get('pts', 0)
                live_gd  = base_gd  + adj.get('gd',  0)
                entries.append({
                    'team':    team_disp,
                    'gp':      stats.get('GP', '0'),
                    'w':       stats.get('W',  '0'),
                    'd':       stats.get('D',  '0'),
                    'l':       stats.get('L',  '0'),
                    'gf':      stats.get('F',  '0'),
                    'ga':      stats.get('A',  '0'),
                    'gd':      ('+' if live_gd > 0 else '') + str(live_gd),
                    'pts':     str(live_pts),
                    'rank':    stats.get('R',  '99'),
                    'adv':     adv,
                    'is_live': adj.get('is_live', False),
                    'live_score': f"{adj['score']}–{adj['opp_score']} vs {adj['opp']}" if adj.get('is_live') else '',
                })
            # Re-sort by live pts + gd (not ESPN's pre-game rank) so table reflects current score
            entries.sort(key=lambda x: (-int(x['pts']), -int((x['gd'] or '0').replace('+',''))))
            has_live = any(e['is_live'] for e in entries)
            groups.append({'name': name, 'entries': entries, 'has_live': has_live})

        # ── Correct the yellow "wildcard" highlighting ───────────────────────
        # ESPN marks ALL current 3rd-place teams as "Best 8 advance", but only
        # the top 8 of the 12 third-place teams actually advance. Collect all
        # 3rd-place teams, rank them by pts then GD, and only keep top 8 yellow.
        def gd_sort_key(gd_str):
            try: return int(gd_str.replace('+', ''))
            except: return 0

        third_place = []
        for g in groups:
            for e in g['entries']:
                if int(e.get('rank', 99)) == 3:
                    third_place.append(e)
                    e['adv'] = 'no'  # reset all to 'no' first

        third_place.sort(key=lambda e: (-int(e.get('pts', 0)), -gd_sort_key(e.get('gd', '0'))))
        for e in third_place[:8]:
            e['adv'] = 'maybe'

        return groups
    except Exception:
        return []

# ── Main data function (5-minute server-side cache) ────────────────────────────

_cache = {'data': None, 'ts': 0}
CACHE_TTL = 300  # seconds — shorter when a live game is in progress

def get_data():
    now = time.time()
    cached = _cache['data']
    # Use shorter TTL (30s) if a live game was detected last run
    ttl = 30 if (cached and any(
        g.get('live') for g in cached.get('_live_games', [])
    )) else CACHE_TTL
    if cached and (now - _cache['ts']) < ttl:
        return cached
    roster = FIXED_ROSTER
    games = fetch_group_stage_games()
    team_stats = build_team_stats(games)
    players = calculate_scores(roster, team_stats)
    done_games = [g for g in games if g['done']]
    mc = run_monte_carlo(roster, team_stats, done_games, n=10000, all_games=games)
    live_games = [g for g in games if g.get('live')]
    group_standings = fetch_group_standings(live_games=live_games)
    result = {
        'players': players,
        'sim_probs': mc['probs'],
        'live_strengths': mc['live_strengths'],
        'games_used': mc['games_used'],
        'odds_used': mc['odds_used'],
        'group_standings': group_standings,
        'updated': datetime.now().strftime('%b %d, %Y · %I:%M:%S %p'),
        '_live_games': live_games,  # used by cache TTL logic
    }
    _cache['data'] = result
    _cache['ts'] = time.time()
    return result


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def send_body(self, body: bytes, content_type: str, status: int = 200):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith('/api/data'):
            try:
                data = get_data()
                body = json.dumps(data).encode()
                self.send_body(body, 'application/json')
            except Exception as e:
                self.send_body(str(e).encode(), 'text/plain', 500)
        else:
            body = HTML.encode('utf-8')
            self.send_body(body, 'text/html; charset=utf-8')

    def log_message(self, fmt, *args):
        pass  # suppress server log noise


if __name__ == '__main__':
    print(f'⚽ World Cup 2026 Pick\'em Dashboard')
    print(f'   Running on port {PORT}')
    HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()

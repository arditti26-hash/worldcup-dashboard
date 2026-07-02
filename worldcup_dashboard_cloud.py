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
  display: flex; align-items: center; gap: 6px;
  padding: 5px 8px; border-radius: 7px; background: rgba(255,255,255,0.025);
}
.team-total { font-family: 'Oswald', sans-serif; font-size: 18px; font-weight: 900; min-width: 26px; text-align: right; flex-shrink: 0; line-height: 1; }
.team-total-divider { width: 1px; height: 24px; background: rgba(255,255,255,0.08); flex-shrink: 0; margin: 0 2px; }
.team-name { font-size: 12px; color: #a8c2ad; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100px; display: flex; align-items: center; gap: 5px; flex-shrink: 0; }
.team-flag { font-size: 14px; flex-shrink: 0; line-height: 1; }
.team-right { display: flex; align-items: center; gap: 3px; flex: 1; justify-content: flex-end; flex-wrap: wrap; min-width: 0; }
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
.ko-win-badge { font-size: 9px; font-weight: 800; padding: 1px 4px; border-radius: 4px; margin-left: 2px; white-space: nowrap; }
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
/* ── Group Points Overview tiles ── */
.gpo-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;
}
.gpo-card {
  background: #0a1f12; border: 1px solid rgba(250,204,21,0.10);
  border-radius: 10px; overflow: hidden;
}
.gpo-card-live { border-color: rgba(34,197,94,0.3) !important; }
.gpo-header {
  background: #0f2a18; padding: 5px 10px;
  font-family: 'Oswald', sans-serif; font-size: 11px; font-weight: 700;
  letter-spacing: 1.5px; text-transform: uppercase; color: #facc15;
  display: flex; align-items: center; gap: 6px;
}
.gpo-row {
  display: flex; align-items: center; gap: 5px;
  padding: 4px 8px; border-bottom: 1px solid #0d2015; font-size: 11px;
  color: #8aad92;
}
.gpo-row:last-child { border-bottom: none; }
.gpo-row.adv-yes { color: #22c55e; }
.gpo-row.adv-maybe { color: #facc15; }
.gpo-row.adv-no { color: #3a5a42; }
.gpo-row .gpo-flag { font-size: 13px; flex-shrink: 0; }
.gpo-row .gpo-name { flex: 1; font-size: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.gpo-row .gpo-owner { font-size: 8px; font-weight: 800; padding: 1px 3px; border-radius: 3px; flex-shrink: 0; }
.gpo-row .gpo-pts { font-size: 11px; font-weight: 800; flex-shrink: 0; min-width: 18px; text-align: right; }
.gpo-row .gpo-bonus { font-size: 8px; padding: 1px 3px; border-radius: 3px; background: rgba(250,204,21,0.15); color: #facc15; flex-shrink: 0; margin-left: 2px; }
.gpo-row .gpo-bonus.adv-wildcard { background: rgba(34,197,94,0.15); color: #22c55e; }
.gpo-row .gpo-bonus.eliminated { background: rgba(90,30,30,0.3); color: #6b3333; }
@media (max-width: 900px) { .gpo-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 600px) { .gpo-grid { grid-template-columns: repeat(2, 1fr); } }
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

/* ── Knockout Bracket ── */
.ko-rounds { display: flex; gap: 12px; overflow-x: auto; padding-bottom: 12px; }
.ko-round { min-width: 160px; flex-shrink: 0; }
.ko-round-title {
  font-family: 'Oswald', sans-serif; font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 1.5px; color: #facc15;
  text-align: center; margin-bottom: 8px; padding: 4px 0;
  border-bottom: 1px solid rgba(250,204,21,0.2);
}
.ko-game {
  background: #0a1f12; border: 1px solid rgba(250,204,21,0.1);
  border-radius: 8px; overflow: hidden; margin-bottom: 8px;
}
.ko-team {
  display: flex; align-items: center; gap: 4px;
  padding: 0 6px; height: 26px; font-size: 11px; font-weight: 600; color: #8aad92;
  border-bottom: 1px solid #071510; position: relative; overflow: hidden;
}
.ko-team:last-child { border-bottom: none; }
.ko-team.winner { color: #d1fae5; font-weight: 800; }
.ko-team.loser { opacity: 0.4; }
.ko-team.live-now { color: #22c55e; }
.ko-owner-bar { width: 3px; align-self: stretch; border-radius: 2px; flex-shrink: 0; }
.ko-score { font-size: 12px; font-weight: 900; flex-shrink: 0; margin-left: 4px; }
.ko-live-badge {
  font-size: 8px; font-weight: 800; color: #22c55e; background: rgba(34,197,94,0.15);
  padding: 1px 4px; border-radius: 3px; margin-left: 4px;
}
.ko-tbd { color: #2d4a36; font-style: italic; font-size: 10px; }
.ko-flag { font-size: 13px; flex-shrink: 0; margin-right: 3px; line-height: 1; }
.ko-owner-initial {
  font-size: 9px; font-weight: 900; border: 1px solid; border-radius: 3px;
  padding: 0 3px; margin-right: 4px; flex-shrink: 0; line-height: 16px;
}
.ko-pts-badge {
  font-size: 9px; font-weight: 900; border: 1px solid; border-radius: 4px;
  padding: 0 4px; margin-left: auto; flex-shrink: 0; line-height: 16px;
}

/* Knockout points tracker */
.ko-tracker { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 8px; }
@media (max-width: 540px) { .ko-tracker { grid-template-columns: repeat(2, 1fr); } }
.ko-tracker-card {
  background: #0a1f12;
  border-radius: 12px; padding: 12px 14px; text-align: center;
  border: 1px solid rgba(250,204,21,0.1);
}
.ko-tracker-name { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
.ko-tracker-pts { font-family: 'Oswald', sans-serif; font-size: 32px; font-weight: 900; line-height: 1; }
.ko-tracker-label { font-size: 9px; color: #3f6b4a; margin-top: 3px; }
.ko-tracker-best { font-size: 9px; color: #4a7a56; margin-top: 6px; }
.ko-tracker-best strong { font-weight: 800; }
.ko-tracker-alive { margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.06); }
.ko-alive-count { font-family: 'Oswald', sans-serif; font-size: 20px; font-weight: 900; }
.ko-alive-label { font-size: 9px; color: #4a7a56; }
.ko-tracker-prob { margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.06); }
.ko-prob-bar-bg { height: 5px; background: rgba(255,255,255,0.07); border-radius: 3px; overflow: hidden; margin-bottom: 5px; }
.ko-prob-bar-fill { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
.ko-prob-pct { font-size: 10px; font-weight: 800; }
.ko-tracker-breakdown { display: flex; align-items: center; justify-content: center; gap: 4px; margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.06); }
.ko-breakdown-item { font-size: 10px; color: #4a7a56; }
.ko-breakdown-item strong { font-weight: 800; }
.ko-breakdown-sep { font-size: 10px; color: #2d4a36; }

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
@media (max-width: 540px) {
  html, body { overflow-x: hidden; max-width: 100vw; }
  .page-body { padding: 16px 12px; grid-template-columns: 1fr; gap: 16px; }
  .wrap { padding: 0; }

  /* Leaderboard */
  .lb-row { grid-template-columns: 36px 1fr 56px; padding: 12px 14px; gap: 8px; }
  .lb-best-col { display: none; }
  .lb-score { font-size: 24px; }
  .lb-player-name { font-size: 15px; }

  /* Player cards */
  .cards-grid { grid-template-columns: 1fr; gap: 14px; }
  .card-header { padding: 12px 14px 10px; }
  .card-score { font-size: 34px; }
  .team-list { grid-template-columns: 1fr; padding: 0 12px 14px; gap: 3px; }
  .team-name { max-width: none; flex: 1; }
  .team-item { padding: 5px 6px; }

  /* Sidebar schedule */
  .schedule-panel { border-radius: 14px; }
  .game-venue { font-size: 9px; }

  /* Monte Carlo */
  .mc-body { padding: 12px; }

  /* Power rankings */
  #power-rankings .pr-bar-wrap { width: 70px; }
  .pr-name { font-size: 11px; }

  /* Group standings */
  .standings-grid { grid-template-columns: 1fr; }
  .group-table { font-size: 10px; }
  .group-table td, .group-table th { padding: 3px 2px; }
  .owner-tag { display: none; }
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

<div class="standings-section" id="knockout-section">
  <div class="standings-title">📈 Knockout Points Tracker</div>
  <div id="ko-pts-tracker"></div>

  <!-- Player cards: team-by-team points as they advance -->
  <div class="standings-title" style="margin-top:28px">🃏 Player Team Cards</div>
  <div class="cards-grid" id="cards"></div>

  <div class="ko-bracket-section">
    <div class="standings-title" style="margin-top:28px">🏆 Knockout Bracket</div>
    <div id="knockout-bracket"></div>
  </div>

  <!-- Group Stage Points: below bracket -->
  <div class="standings-title" style="margin-top:28px">⚽ Group Stage Points</div>
  <div class="gpo-grid" id="gpo-grid">
    <div style="color:#4a7a56;font-size:12px;padding:8px;">Loading…</div>
  </div>
</div>

<div class="standings-section">
  <div class="standings-title">📅 Next Games</div>
  <div class="schedule-panel" style="margin-top:8px">
    <div class="schedule-header">
      <span class="schedule-title">FIFA World Cup 2026</span>
      <span class="schedule-badge" id="schedule-badge">ESPN</span>
    </div>
    <div id="schedule-body">
      <div class="schedule-loading">Loading schedule…</div>
    </div>
  </div>
</div>

<div class="page-body">

  <!-- Left: footer -->
  <div class="main-col">
    <div class="footer" id="footer"></div>
  </div>

  <!-- Right: win probability -->
  <div class="sidebar">
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
  "cote d'ivoire":"🇨🇮","côte d'ivoire":"🇨🇮","ivory coast":"🇨🇮",
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
      const matchPts = t.match_pts ?? t.pts ?? 0;
      const groupBonus = t.group_bonus ?? 0;
      const koWins = (t.ko_wins || []).sort((a,b) => a.round_order - b.round_order);
      const koPtsSum = koWins.reduce((s, w) => s + w.pts, 0);
      const teamTotal = matchPts + groupBonus + koPtsSum;
      const totalCls = teamTotal === 0 ? 'pts-zero' : teamTotal < 5 ? 'pts-low' : 'pts-high';

      const isLive = (t.games || []).some(g => g.live);
      const liveGame = isLive ? t.games.find(g => g.live) : null;
      const liveTip = liveGame ? `LIVE vs ${liveGame.opp_name}` : '';

      // Group bonus badge: just "+N" with tooltip
      const bonusBadge = groupBonus > 0
        ? `<span class="team-bonus" title="Group ${t.group_position === 1 ? '1st' : t.group_position === 2 ? '2nd' : '3rd'} bonus">+${groupBonus}</span>`
        : '';

      // KO round badges: just "+N", no round label (tooltip shows round name)
      const koBadges = koWins.map(w => {
        const isChamp = w.round === 'Final';
        const isRU = w.round === 'Final (RU)';
        const bg = isChamp ? 'rgba(250,204,21,0.25)' : isRU ? 'rgba(139,92,246,0.2)' : 'rgba(34,197,94,0.15)';
        const col = isChamp ? '#facc15' : isRU ? '#a78bfa' : '#22c55e';
        return `<span class="ko-win-badge" style="background:${bg};color:${col}" title="${w.round} +${w.pts}pts">+${w.pts}</span>`;
      }).join('');

      return `<div class="team-item ${isLive ? 'team-live' : ''}">
        <span class="team-total ${totalCls}">${teamTotal}</span>
        <div class="team-total-divider"></div>
        <span class="team-name">
          <span class="team-flag">${flag(t.name)}</span>
          ${t.name}
          ${isLive ? `<span class="live-pip" title="${liveTip}"></span>` : ''}
        </span>
        <div class="team-right">
          ${buildPips(t.games)}
          ${bonusBadge}${koBadges}
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

function renderKnockout(koGames, players, simProbs) {
  const section = document.getElementById('knockout-section');
  const bracketEl = document.getElementById('knockout-bracket');
  const trackerEl = document.getElementById('ko-pts-tracker');
  if (section) section.style.display = '';

  // ── Points Tracker ──────────────────────────────────────────────
  // Build set of eliminated teams (lost a completed KO game)
  const eliminated = new Set();
  const inBracket = new Set();
  (koGames || []).forEach(g => {
    inBracket.add(normalizeName(g.team1));
    inBracket.add(normalizeName(g.team2));
    if (g.done && g.winner) {
      const loser = normalizeName(g.team1) === normalizeName(g.winner) ? normalizeName(g.team2) : normalizeName(g.team1);
      eliminated.add(loser);
    }
  });

  const playerOrder = [...(players || [])].sort((a, b) => (b.total || 0) - (a.total || 0));
  trackerEl.innerHTML = `<div class="ko-tracker">${playerOrder.map(p => {
    const name = p.name.toUpperCase();
    const koPts = p.ko_pts || 0;
    const total = p.total || 0;
    const groupPts = total - koPts;
    const col = C[name] || { primary: '#facc15', bg: 'rgba(250,204,21,0.1)', border: 'rgba(250,204,21,0.2)' };
    // Count teams still alive in knockout
    const alive = (p.teams || []).filter(t => {
      const tn = normalizeName(t.name);
      return inBracket.has(tn) && !eliminated.has(tn);
    });
    const teamsLeft = alive.length;
    const teamNames = alive.map(t => {
      const f = FLAGS[normalizeName(t.name)] || '';
      return `${f} ${t.name}`;
    }).join(', ');
    const winProb = simProbs ? (simProbs[p.name] ?? simProbs[name] ?? 0) : 0;
    const winProbPct = winProb.toFixed(1);
    return `<div class="ko-tracker-card" style="border-color:${col.border};background:${col.bg}">
      <div class="ko-tracker-name" style="color:${col.primary}">${name}</div>
      <div class="ko-tracker-pts" style="color:${col.primary}">${total}</div>
      <div class="ko-tracker-label">total pts</div>
      <div class="ko-tracker-breakdown">
        <span class="ko-breakdown-item">Group <strong style="color:${col.primary}">${groupPts}</strong></span>
        <span class="ko-breakdown-sep">+</span>
        <span class="ko-breakdown-item">KO <strong style="color:${col.primary}">${koPts}</strong></span>
      </div>
      <div class="ko-tracker-best">Best possible: <strong style="color:${col.primary}">${p.best_possible ?? '—'}</strong></div>
      <div class="ko-tracker-alive" title="${teamNames}">
        <span class="ko-alive-count" style="color:${col.primary}">${teamsLeft}</span>
        <span class="ko-alive-label"> team${teamsLeft !== 1 ? 's' : ''} left</span>
      </div>
      <div class="ko-tracker-prob">
        <div class="ko-prob-bar-bg">
          <div class="ko-prob-bar-fill" style="width:${Math.min(winProb,100)}%;background:${col.primary}"></div>
        </div>
        <span class="ko-prob-pct" style="color:${col.primary}">${winProbPct}% win chance</span>
      </div>
    </div>`;
  }).join('')}</div>`;

  if (!koGames || koGames.length === 0) return;

  // ── Bracket ─────────────────────────────────────────────────────
  const GAME_H = 52;   // px height of one game card
  const SLOT   = 72;   // px vertical slot per R32 game
  const COL_W  = 168;  // px column width
  const CONN   = 32;   // px connector width between columns
  const TOTAL_H = 16 * SLOT; // 1152px

  // Group games by round
  const rounds = {};
  koGames.forEach(g => {
    const k = g.round_order;
    if (!rounds[k]) rounds[k] = { name: g.round, order: g.round_order, games: [] };
    rounds[k].games.push(g);
  });
  const allRounds = Object.values(rounds).sort((a, b) => a.order - b.order);
  const bracketRounds = allRounds.filter(r => r.name !== '3rd Place');
  const thirdPlace    = allRounds.find(r => r.name === '3rd Place');

  // Points awarded per knockout round win
  const KO_PTS = { 'Round of 32':4, 'Round of 16':4, 'Quarterfinals':4, 'Semifinals':4, '3rd Place':2, 'Final':8 };

  // Render a single team row
  function teamRow(name, display, score, winner, loser, live, roundName) {
    const ok  = name ? (teamOwners[normalizeName(name)] || teamOwners[name.toLowerCase()]) : null;
    const col = ok && C[ok] ? C[ok] : null;
    const bar = col ? col.primary : '#1a3322';
    const cls = live ? 'ko-team live-now' : winner ? 'ko-team winner' : loser ? 'ko-team loser' : 'ko-team';
    const teamFlag = name ? `<span class="ko-flag">${flag(normalizeName(name))}</span>` : '';
    const lbl = display || (name ? name.replace(/\b\w/g, c => c.toUpperCase()) : '') || '<span class="ko-tbd">TBD</span>';
    const sc  = score !== null && score !== undefined ? `<span class="ko-score">${score}</span>` : '';
    const lv  = live ? '<span class="ko-live-badge">LIVE</span>' : '';
    const ownerBadge = col
      ? `<span class="ko-owner-initial" style="color:${col.primary};border-color:${col.border}">${ok[0]}</span>`
      : '';
    const pts = KO_PTS[roundName] || 4;
    const ptsBadge = winner && col
      ? `<span class="ko-pts-badge" style="background:${col.bg};color:${col.primary};border-color:${col.border}">+${pts}</span>`
      : '';
    return `<div class="${cls}"><div class="ko-owner-bar" style="background:${bar}"></div>${ownerBadge}${teamFlag}${lbl}${lv}${sc}${ptsBadge}</div>`;
  }

  function gameCard(g) {
    const done = g.done, live = g.live, rn = g.round;
    const t1w = done && g.score1 > g.score2, t2w = done && g.score2 > g.score1;
    return `<div class="ko-game">
      ${teamRow(g.team1, g.team1_display, done||live ? g.score1 : null, t1w, done&&!t1w, live, rn)}
      ${teamRow(g.team2, g.team2_display, done||live ? g.score2 : null, t2w, done&&!t2w, live, rn)}
    </div>`;
  }

  // ── Tree-based bracket layout ─────────────────────────────────
  // R32 games have bracket_idx (0-based, from backend sort).
  // R16 games have r32_src_0 / r32_src_1 telling which R32 game indices feed them.
  // Higher rounds chain off computed R16 centers.

  // Center y of R32 game at bracket_idx
  function r32Center(bIdx) { return (bIdx + 0.5) * SLOT; }

  // Compute center y for each game in each round, using actual parentage.
  // gameCenters[round_order] = [y0, y1, ...] parallel to round.games (sorted by computed y)
  const gameCenters = {};

  // R32: sort by bracket_idx, assign centers
  const r32Round = bracketRounds.find(r => r.order === 1);
  if (r32Round) {
    r32Round.games.sort((a, b) => (a.bracket_idx ?? 99) - (b.bracket_idx ?? 99));
    gameCenters[1] = r32Round.games.map(g => r32Center(g.bracket_idx ?? 0));
  }

  // R16: position at midpoint of the two R32 parents
  const r16Round = bracketRounds.find(r => r.order === 2);
  if (r16Round && r32Round) {
    r16Round.games.forEach(g => {
      const s0 = g.r32_src_0, s1 = g.r32_src_1;
      if (s0 != null && s1 != null) {
        g._centerY = (r32Center(s0) + r32Center(s1)) / 2;
      }
    });
    // Sort R16 by computed center so they appear top-to-bottom correctly
    r16Round.games.sort((a, b) => (a._centerY ?? 9999) - (b._centerY ?? 9999));
    gameCenters[2] = r16Round.games.map((g, i) =>
      g._centerY != null ? g._centerY : (i + 0.5) * SLOT * 2
    );
  }

  // QF and beyond: pair consecutive games from previous round
  function deriveCenters(round, prevCenters) {
    const centers = [];
    for (let i = 0; i < round.games.length; i++) {
      const p1 = prevCenters[i * 2];
      const p2 = prevCenters[i * 2 + 1];
      centers.push(p1 != null && p2 != null ? (p1 + p2) / 2 : (i + 0.5) * SLOT * Math.pow(2, bracketRounds.indexOf(round)));
    }
    return centers;
  }
  bracketRounds.forEach((round) => {
    if (round.order <= 2) return;
    const prevRound = bracketRounds.find(r => r.order === round.order - 1);
    const prevCenters = prevRound ? gameCenters[prevRound.order] : null;
    gameCenters[round.order] = prevCenters
      ? deriveCenters(round, prevCenters)
      : round.games.map((_, i) => (i + 0.5) * SLOT * Math.pow(2, round.order - 1));
  });

  // ── Render columns ─────────────────────────────────────────────
  const LINE = 'rgba(250,204,21,0.35)';
  const cols = bracketRounds.map((round) => {
    const centers = gameCenters[round.order] || [];
    let inner = '';

    // Game cards at computed positions
    round.games.forEach((g, gIdx) => {
      const cy = centers[gIdx] ?? (gIdx + 0.5) * SLOT;
      const t = Math.round(cy - GAME_H / 2);
      inner += `<div style="position:absolute;top:${t}px;left:0;right:0">${gameCard(g)}</div>`;
    });

    // Right-side connector: for each game pair their centers → next round
    const nextRound = bracketRounds.find(r => r.order === round.order + 1);
    if (nextRound) {
      const nextCenters = gameCenters[nextRound.order] || [];
      // Figure out which pairs of this round's games feed each next-round game
      if (round.order === 1 && r16Round) {
        // R32→R16: use r32_src to pair correctly
        r16Round.games.forEach((r16g, r16i) => {
          const s0 = r16g.r32_src_0, s1 = r16g.r32_src_1;
          if (s0 == null || s1 == null) return;
          const c1 = r32Center(s0), c2 = r32Center(s1);
          const mid = nextCenters[r16i] ?? (c1 + c2) / 2;
          const hx = CONN / 2 - 1;
          inner += `<div style="position:absolute;left:${COL_W}px;top:${Math.round(c1)}px;width:${hx}px;height:1px;background:${LINE}"></div>`;
          inner += `<div style="position:absolute;left:${COL_W}px;top:${Math.round(c2)}px;width:${hx}px;height:1px;background:${LINE}"></div>`;
          inner += `<div style="position:absolute;left:${COL_W+hx}px;top:${Math.round(Math.min(c1,c2))}px;width:1px;height:${Math.round(Math.abs(c2-c1))}px;background:${LINE}"></div>`;
          inner += `<div style="position:absolute;left:${COL_W+hx}px;top:${Math.round(mid)}px;width:${hx+1}px;height:1px;background:${LINE}"></div>`;
        });
      } else {
        // R16→QF, QF→SF, SF→Final: sequential pairing
        for (let i = 0; i < round.games.length; i += 2) {
          const c1  = centers[i];
          const c2  = centers[i + 1];
          if (c1 == null || c2 == null) continue;
          const mid = nextCenters[Math.floor(i / 2)] ?? (c1 + c2) / 2;
          const hx  = CONN / 2 - 1;
          inner += `<div style="position:absolute;left:${COL_W}px;top:${Math.round(c1)}px;width:${hx}px;height:1px;background:${LINE}"></div>`;
          inner += `<div style="position:absolute;left:${COL_W}px;top:${Math.round(c2)}px;width:${hx}px;height:1px;background:${LINE}"></div>`;
          inner += `<div style="position:absolute;left:${COL_W+hx}px;top:${Math.round(c1)}px;width:1px;height:${Math.round(c2-c1)}px;background:${LINE}"></div>`;
          inner += `<div style="position:absolute;left:${COL_W+hx}px;top:${Math.round(mid)}px;width:${hx+1}px;height:1px;background:${LINE}"></div>`;
        }
      }
    }

    return `<div style="position:relative;width:${COL_W}px;flex-shrink:0;margin-right:${CONN}px">
      <div class="ko-round-title" style="margin-bottom:10px">${round.name}</div>
      <div style="position:relative;height:${TOTAL_H}px">${inner}</div>
    </div>`;
  }).join('');

  // 3rd place game (separate, below bracket)
  const thirdHtml = thirdPlace ? `<div style="margin-top:20px">
    <div class="ko-round-title">3rd Place</div>
    <div style="max-width:${COL_W}px">${thirdPlace.games.map(gameCard).join('')}</div>
  </div>` : '';

  if (bracketEl) bracketEl.innerHTML = `
    <div style="display:flex;overflow-x:auto;padding:4px 4px 20px;align-items:flex-start;-webkit-overflow-scrolling:touch">${cols}</div>
    ${thirdHtml}`;
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
    renderGroupPoints(data.group_standings, data.players);
    renderKnockout(data.knockout_games, data.players, data.sim_probs);
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

function renderGroupPoints(groups, players) {
  const el = document.getElementById('gpo-grid');
  if (!el || !groups || !groups.length) return;

  // Build per-team earned pts: match pts (W=3, D=1) + group bonus (1st=+4, 2nd=+2, 3rd wildcard=+1)
  // We derive match pts from group standings: W*3 + D*1
  // Group bonus only once group is done (all 3 games played)

  // Build teamOwners map already exists globally — use it
  el.innerHTML = groups.map(g => {
    const isDone = g.entries.length > 0 && g.entries.every(e => parseInt(e.gp) >= 3);
    const rows = g.entries.map((e, idx) => {
      const rank = idx + 1; // 1-based after sort
      const matchPts = parseInt(e.w||0)*3 + parseInt(e.d||0);
      let bonus = 0, bonusLabel = '', bonusCls = '';
      if (isDone) {
        if (rank === 1)      { bonus = 4; bonusLabel = '+4 1st'; }
        else if (rank === 2) { bonus = 2; bonusLabel = '+2 2nd'; }
        else if (rank === 3 && e.adv !== 'no') { bonus = 1; bonusLabel = '+1 3rd'; bonusCls = ' adv-wildcard'; }
        else if (rank >= 4 || (rank === 3 && e.adv === 'no')) { bonusLabel = 'OUT'; bonusCls = ' eliminated'; }
      } else if (e.adv === 'yes') {
        // Group decided but not all done yet — group winner/runner-up locked
        if (rank === 1)      { bonus = 4; bonusLabel = '+4 1st'; }
        else if (rank === 2) { bonus = 2; bonusLabel = '+2 2nd'; }
      }
      const earned = matchPts + bonus;
      const advCls = e.adv === 'yes' ? 'adv-yes' : e.adv === 'maybe' ? 'adv-maybe' : e.adv === 'no' ? 'adv-no' : '';
      const ownerKey = teamOwners[normalizeName(e.team)] || teamOwners[e.team.toLowerCase()];
      const ownerStyle = ownerKey && C[ownerKey]
        ? `background:${C[ownerKey].bg};color:${C[ownerKey].primary};border:1px solid ${C[ownerKey].border}`
        : 'display:none';
      const ownerEl = `<span class="gpo-owner" style="${ownerStyle}">${ownerKey ? ownerKey[0] : ''}</span>`;
      const teamFl = `<span class="gpo-flag">${flag(normalizeName(e.team))}</span>`;
      const bonusBadge = bonusLabel ? `<span class="gpo-bonus${bonusCls}">${bonusLabel}</span>` : '';
      const liveDot = e.is_live ? `<span class="grp-live-dot"></span>` : '';
      return `<div class="gpo-row ${advCls}">
        ${liveDot}${teamFl}${ownerEl}
        <span class="gpo-name">${e.team}</span>
        <span class="gpo-pts">${earned}</span>
        ${bonusBadge}
      </div>`;
    }).join('');
    const liveTag = g.has_live ? '<span class="grp-live-badge" style="font-size:8px">LIVE</span>' : '';
    return `<div class="gpo-card${g.has_live ? ' gpo-card-live' : ''}">
      <div class="gpo-header">${g.name} ${liveTag}</div>
      ${rows}
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
    # Collect all third-place finishers from completed groups.
    # We award the +1 bonus progressively: a 3rd-place team from a finished group
    # gets credit as soon as it's mathematically locked into the top 8 (i.e. it
    # would still be in the top 8 even if all remaining unfinished groups produce
    # a better third-place team). Once all 12 groups finish we can be exact.
    all_groups_done = len(groups) > 0 and all(
        all(s['gp'] == 3 for _, s in members) for members in groups.values()
    )
    # Count how many groups are still unfinished (their 3rd-placer is unknown)
    groups_remaining = sum(
        1 for members in groups.values()
        if any(s['gp'] < 3 for _, s in members)
    )

    third_placers = []
    for members in groups.values():
        for team, s in members:
            if s.get('group_pos') == 3:
                third_placers.append((team, s))
                s['advances_wildcard'] = False

    # Sort by pts desc, gd desc, gf desc — same as FIFA tiebreakers
    third_placers.sort(key=lambda x: (-x[1]['pts'], -x[1]['gd'], -x[1]['gf']))

    if all_groups_done:
        # All groups done: exact top 8
        for team, s in third_placers[:8]:
            s['advances_wildcard'] = True
    else:
        # Partial: a finished-group 3rd placer is safe if even assuming all
        # remaining groups produce a perfect third-placer (9 pts, high GD)
        # they would still be in the top 8.
        BEST_POSSIBLE = {'pts': 9, 'gd': 99, 'gf': 99}
        hypothetical = third_placers + [
            (f'__tbd_{i}', BEST_POSSIBLE) for i in range(groups_remaining)
        ]
        hypothetical.sort(key=lambda x: (-x[1]['pts'], -x[1]['gd'], -x[1]['gf']))
        safe_teams = {t for t, _ in hypothetical[:8] if not t.startswith('__tbd')}
        for team, s in third_placers:
            if team in safe_teams:
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
    """Compute live team strengths in two passes:
    1. Elo updates from completed games (K=40 group, K=80 knockout).
    2. Odds-implied adjustment for upcoming knockout games — the market
       prices in current form far better than Elo alone. Only applied to
       KO games (not group stage, where weak-opponent deflation is a problem).
    """
    import math as _math
    live = {team: float(v) for team, v in TEAM_STRENGTH.items()}
    for g in done_games:
        for t in (g['team1'], g['team2']):
            if t not in live:
                live[t] = 55.0

    # Pass 1 — Elo from completed games
    for g in done_games:
        t1, t2 = g['team1'], g['team2']
        r1, r2 = live.get(t1, 55.0), live.get(t2, 55.0)
        expected1 = 1 / (1 + 10 ** (-(r1 - r2) * 20 / 400))
        s1, s2 = g['score1'], g['score2']
        actual1 = 1.0 if s1 > s2 else (0.5 if s1 == s2 else 0.0)
        K = 80 if g.get('round_order') else 40
        delta = K * (actual1 - expected1) / 20
        live[t1] = max(20.0, min(100.0, r1 + delta))
        live[t2] = max(20.0, min(100.0, r2 - delta))

    # Pass 2 — Blend in odds-implied strength for upcoming knockout games.
    # For each KO game with sportsbook odds, derive the implied strength
    # differential and move both teams toward what the market says.
    upcoming_ko = [g for g in (scheduled_games or [])
                   if g.get('round_order') and not g.get('done') and not g.get('live')]
    for g in upcoming_ko:
        result = odds_match_probs(g)
        if not result:
            continue
        p1, pd, p2 = result
        total = p1 + p2
        if total <= 0:
            continue
        p1_ko = p1 / total   # KO win prob for team1 (no draws)
        p2_ko = p2 / total
        if not (0.05 < p1_ko < 0.95):
            continue  # skip extreme lines (avoid log instability)
        t1, t2 = g['team1'], g['team2']
        r1, r2 = live.get(t1, 55.0), live.get(t2, 55.0)
        avg = (r1 + r2) / 2
        # Elo inversion: r1 - r2 implied by market
        implied_diff = 20 * _math.log10(p1_ko / p2_ko)
        current_diff = r1 - r2
        # 70% market, 30% Elo — market knows current form better
        blended_diff = 0.70 * implied_diff + 0.30 * current_diff
        live[t1] = max(20.0, min(100.0, avg + blended_diff / 2))
        live[t2] = max(20.0, min(100.0, avg - blended_diff / 2))

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


def run_monte_carlo(roster, team_stats, done_games, n=10000, all_games=None, knockout_games=None):
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

        # ── Simulate knockout rounds using actual bracket ────────────────
        # R32 slots are the actual ESPN matchups (sorted by date = bracket order).
        # Winners of slots 0&1 meet in R16, winners of 2&3, etc.
        # Completed games are locked; upcoming ones are simulated.
        knockout_bonus = {team: 0 for team in advanced}
        advanced_set = set(advanced)

        # Build the 32-slot bracket from actual R32 games
        r32 = sorted(
            [g for g in (knockout_games or []) if g.get('round_order') == 1],
            key=lambda g: g.get('date', '')
        )

        def resolve_slot(team_norm):
            """If team is a known real team that advanced, use it; else pick from pool."""
            if team_norm in advanced_set:
                return team_norm
            # Placeholder — draw a random remaining team (fallback only)
            return random.choice(list(advanced_set)) if advanced_set else team_norm

        # Simulate or lock each R32 game; result = list of 16 winners in bracket order
        remaining_advanced = set(advanced)
        r32_winners = []
        for g in r32:
            t1 = resolve_slot(g['team1'])
            t2 = resolve_slot(g['team2'])
            if g.get('done') and g.get('winner') and g['winner'] in advanced_set:
                winner = g['winner']
                loser = t2 if winner == t1 else t1
            else:
                p = live_ko_prob(t1, t2)
                winner = t1 if random.random() < p else t2
                loser = t2 if winner == t1 else t1
            knockout_bonus[winner] = knockout_bonus.get(winner, 0) + 4
            remaining_advanced.discard(t1)
            remaining_advanced.discard(t2)
            r32_winners.append(winner)

        # For any advanced teams not yet seeded into a R32 slot (TBD bracket slots),
        # randomly inject them in pairs so the bracket stays balanced.
        leftover = list(remaining_advanced)
        random.shuffle(leftover)
        while len(leftover) >= 2:
            a, b = leftover.pop(), leftover.pop()
            p = live_ko_prob(a, b)
            winner = a if random.random() < p else b
            knockout_bonus[winner] = knockout_bonus.get(winner, 0) + 4
            r32_winners.append(winner)

        # Simulate R16 → SF → Final following bracket pairing
        current_round = r32_winners
        semifinal_losers = []
        while len(current_round) > 1:
            next_round = []
            is_semifinal = len(current_round) == 4
            is_final     = len(current_round) == 2
            for i in range(0, len(current_round) - 1, 2):
                a, b = current_round[i], current_round[i + 1]
                p_a = live_ko_prob(a, b)
                winner = a if random.random() < p_a else b
                loser  = b if winner == a else a
                if is_semifinal:
                    semifinal_losers.append(loser)
                if is_final:
                    knockout_bonus[winner] = knockout_bonus.get(winner, 0) + 4 + 4
                    knockout_bonus[loser]  = knockout_bonus.get(loser,  0) + 2
                else:
                    knockout_bonus[winner] = knockout_bonus.get(winner, 0) + 4
                next_round.append(winner)
            if len(current_round) % 2 == 1:
                next_round.append(current_round[-1])
            current_round = next_round

        # ── 3rd-place (bronze) match ─────────────────────────────────────
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

# ── Knockout stage games ──────────────────────────────────────────────────────

# ESPN slug → human-readable round name + sort order
KNOCKOUT_ROUND_MAP = {
    'round-of-32':   ('Round of 32', 1),   # WC2026 new round: 48→32
    'round-of-16':   ('Round of 16', 2),   # 32→16
    'quarterfinals': ('Quarterfinals', 3),
    'semifinals':    ('Semifinals', 4),
    'third-place':   ('3rd Place',   5),
    'final':         ('Final',       6),
}

def fetch_knockout_games():
    """Fetch all knockout-stage games from ESPN (June 28 – July 20)."""
    dates = []
    d = datetime(2026, 6, 28)
    end = datetime(2026, 7, 21)
    while d < end:
        dates.append(d.strftime('%Y%m%d'))
        d += timedelta(days=1)

    def fetch_day(ds):
        day_games = []
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates={ds}"
            data = fetch_espn_url(url)
            for event in data.get('events', []):
                slug = event.get('season', {}).get('slug', '') or event.get('competitions', [{}])[0].get('type', {}).get('slug', '')
                slug = slug.lower()
                if slug not in KNOCKOUT_ROUND_MAP:
                    continue
                round_name, round_order = KNOCKOUT_ROUND_MAP[slug]
                comp = event['competitions'][0]
                status = comp['status']['type']['name']
                is_done = status in (
                    'STATUS_FULL_TIME', 'STATUS_FINAL', 'STATUS_FT',
                    'STATUS_FINAL_AET', 'STATUS_FINAL_PEN',
                    'STATUS_FULL_TIME_AET', 'STATUS_FULL_TIME_PEN',
                    'STATUS_AFTER_EXTRA_TIME', 'STATUS_AFTER_PENALTIES',
                )
                is_live = status in ('STATUS_IN_PROGRESS', 'STATUS_HALFTIME',
                                     'STATUS_FIRST_HALF', 'STATUS_SECOND_HALF',
                                     'STATUS_EXTRA_TIME', 'STATUS_PENALTY',
                                     'STATUS_EXTRA_TIME_HALF')
                cs = comp['competitors']
                if len(cs) < 2: continue
                t1, t2 = cs[0], cs[1]
                n1 = t1['team']['displayName']
                n2 = t2['team']['displayName']
                s1 = int(t1.get('score') or 0)
                s2 = int(t2.get('score') or 0)
                winner_norm = None
                if is_done:
                    # Prefer ESPN's own winner flag (handles penalties correctly)
                    if t1.get('winner') is True:
                        winner_norm = norm(n1)
                    elif t2.get('winner') is True:
                        winner_norm = norm(n2)
                    else:
                        winner_norm = norm(n1) if s1 > s2 else norm(n2)
                # Extract DraftKings moneyline odds if available
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
                    'round': round_name,
                    'round_order': round_order,
                    'slug': slug,
                    'team1': norm(n1), 'team2': norm(n2),
                    'team1_display': n1, 'team2_display': n2,
                    'score1': s1, 'score2': s2,
                    'done': is_done, 'live': is_live,
                    'winner': winner_norm,
                    'date': event['date'],
                    'event_id': event.get('id', ''),
                    'ml_home': ml_home, 'ml_away': ml_away, 'ml_draw': ml_draw,
                })
        except Exception:
            pass
        return day_games

    games = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for day_games in ex.map(fetch_day, dates):
            games.extend(day_games)
    games.sort(key=lambda g: (g['round_order'], g['date']))
    return games

def resolve_ko_placeholders(knockout_games, group_standings):
    """Replace ESPN placeholder names (e.g. 'Group A Winner') with real team names
    from our standings data, but only for groups that have finished all 3 games."""
    import re
    # Build lookup: 'Group A' → [1st_team, 2nd_team, 3rd_team]
    group_lookup = {}
    for grp in group_standings:
        name = grp.get('name', '')   # e.g. 'Group A'
        entries = grp.get('entries', [])
        # Only use if all teams have played 3 games
        if entries and all(int(e.get('gp', 0)) >= 3 for e in entries):
            group_lookup[name] = [e['team'] for e in entries]

    # Build R32 game number → winner mapping.
    # ESPN labels R16 slots as "Round of 32 N Winner" where N is the R32 game sequence number.
    # We assign sequence numbers by sorting all R32 games by date then by ESPN event order.
    r32_games_sorted = sorted(
        [g for g in knockout_games if g.get('round_order') == 1],
        key=lambda g: (g.get('date', ''), g.get('event_id', ''))
    )
    r32_num_to_winner = {}   # 1-indexed game number → winner display name
    r32_num_to_norm   = {}   # 1-indexed game number → winner norm
    for idx, g in enumerate(r32_games_sorted, start=1):
        if g.get('done') and g.get('winner'):
            w_norm = g['winner']
            # Determine winner's display name
            if norm(g.get('team1_display', '')) == w_norm:
                w_disp = g['team1_display']
            elif norm(g.get('team2_display', '')) == w_norm:
                w_disp = g['team2_display']
            else:
                w_disp = w_norm.title()
            r32_num_to_winner[idx] = w_disp
            r32_num_to_norm[idx]   = w_norm

    def resolve(display):
        if not display:
            return display
        # "Group A Winner" / "Group A 1st Place"
        m = re.match(r'(Group [A-L])\s+(?:Winner|1st)', display, re.I)
        if m:
            teams = group_lookup.get(m.group(1))
            if teams:
                return teams[0]
        # "Group A Runner-up" / "Group A 2nd Place"
        m = re.match(r'(Group [A-L])\s+(?:Runner.?up|2nd)', display, re.I)
        if m:
            teams = group_lookup.get(m.group(1))
            if teams and len(teams) >= 2:
                return teams[1]
        return display

    # Assign bracket_idx (0-based) to each R32 game so JS can position them
    for idx, g in enumerate(r32_games_sorted):
        g['bracket_idx'] = idx   # 0-based position in sorted R32 array

    # Build a reverse map: ESPN 1-based game num → 0-based bracket_idx
    r32_num_to_bracket_idx = {num: num - 1 for num in range(1, len(r32_games_sorted) + 1)}

    # First pass: resolve group placeholders
    for g in knockout_games:
        for key_d, key_n in [('team1_display', 'team1'), ('team2_display', 'team2')]:
            resolved = resolve(g.get(key_d, ''))
            if resolved != g.get(key_d):
                g[key_d] = resolved
                g[key_n] = norm(resolved)

    # Second pass: resolve "Round of 32 N Winner" in R16+ games.
    # Also capture r32_src so JS can draw correct bracket connectors.
    for g in knockout_games:
        if g.get('round_order', 0) <= 1:
            continue
        src_indices = []
        for key_d, key_n in [('team1_display', 'team1'), ('team2_display', 'team2')]:
            disp = g.get(key_d, '')
            m = re.search(r'Round\s+of\s+32\s+(\d+)\s+Winner', disp, re.I)
            if m:
                game_num = int(m.group(1))
                src_indices.append(r32_num_to_bracket_idx.get(game_num))
                if game_num in r32_num_to_winner:
                    g[key_d] = r32_num_to_winner[game_num]
                    g[key_n] = r32_num_to_norm[game_num]
            else:
                src_indices.append(None)
        # Store r32 source bracket indices on R16 games (may be None if already resolved team names)
        if g.get('round_order') == 2:
            if src_indices[0] is not None: g['r32_src_0'] = src_indices[0]
            if src_indices[1] is not None: g['r32_src_1'] = src_indices[1]

    return knockout_games

def compute_knockout_pts(knockout_games, roster):
    """Compute actual knockout points earned per player and per team from completed knockout games.
    Returns (player_total_pts, team_ko_wins) where team_ko_wins maps norm_team →
    list of {round, pts} dicts for each KO win."""
    player_teams = {p: set(norm(t) for t in teams) for p, teams in roster.items()}
    pts = {p: 0 for p in roster}
    # team_ko_wins: norm_team → list of {round, pts, round_order}
    team_ko_wins = {}

    by_round = {}
    for g in knockout_games:
        by_round.setdefault(g['round'], []).append(g)

    for g in knockout_games:
        if not g['done'] or not g['winner']:
            continue
        w = g['winner']
        rnd = g['round']
        round_order = g.get('round_order', 0)
        if rnd == '3rd Place':
            w_pts = 2
        elif rnd == 'Final':
            w_pts = 8   # 4 for win + 4 champion bonus (runner-up +2 handled below)
        else:
            w_pts = 4

        team_ko_wins.setdefault(w, []).append({'round': rnd, 'pts': w_pts, 'round_order': round_order})
        for player, teams in player_teams.items():
            if w in teams:
                pts[player] += w_pts

    # Runner-up bonus: +2 for final loser
    for g in by_round.get('Final', []):
        if not g['done']: continue
        loser = g['team2'] if g['winner'] == g['team1'] else g['team1']
        team_ko_wins.setdefault(loser, []).append({'round': 'Final (RU)', 'pts': 2, 'round_order': 6})
        for player, teams in player_teams.items():
            if loser in teams:
                pts[player] += 2

    return pts, team_ko_wins

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
    live_games = [g for g in games if g.get('live')]
    group_standings = fetch_group_standings(live_games=live_games)
    knockout_games = fetch_knockout_games()
    knockout_games = resolve_ko_placeholders(knockout_games, group_standings)
    # Include completed knockout games in Elo history so power rankings
    # reflect actual R32/R16/QF results, not just group stage.
    done_ko = [g for g in knockout_games if g.get('done')]
    all_done = done_games + done_ko
    # Combine group + knockout scheduled games for odds lookup in simulation.
    all_scheduled = games + [g for g in knockout_games if not g.get('done') and not g.get('live')]
    mc = run_monte_carlo(roster, team_stats, all_done, n=10000, all_games=all_scheduled, knockout_games=knockout_games)
    ko_pts, team_ko_wins = compute_knockout_pts(knockout_games, roster)
    # Add knockout pts to player totals and annotate each team with KO wins
    for p in players:
        p['ko_pts'] = ko_pts.get(p['name'], 0)
        p['total'] += p['ko_pts']
        for t in p['teams']:
            t['ko_wins'] = team_ko_wins.get(norm(t['name']), [])
    players.sort(key=lambda x: x['total'], reverse=True)
    result = {
        'players': players,
        'sim_probs': mc['probs'],
        'live_strengths': mc['live_strengths'],
        'games_used': mc['games_used'],
        'odds_used': mc['odds_used'],
        'group_standings': group_standings,
        'knockout_games': knockout_games,
        'updated': datetime.now().strftime('%b %d, %Y · %I:%M:%S %p'),
        '_live_games': live_games + [g for g in knockout_games if g.get('live')],
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
        elif self.path.startswith('/api/ko-debug'):
            try:
                # Return raw slug info from ESPN for knockout dates
                import urllib.request
                results = []
                for ds in ['20260628','20260629','20260630','20260701','20260702','20260703']:
                    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates={ds}"
                    with urllib.request.urlopen(url, timeout=10) as r:
                        d = json.loads(r.read())
                    for ev in d.get('events', []):
                        slug = ev.get('season', {}).get('slug', 'NONE')
                        comp = ev['competitions'][0]
                        t = [c['team']['displayName'] for c in comp['competitors']]
                        results.append({'date': ds, 'slug': slug, 'teams': t})
                self.send_body(json.dumps(results, indent=2).encode(), 'application/json')
            except Exception as e:
                self.send_body(str(e).encode(), 'text/plain', 500)
        elif self.path.startswith('/api/clear-cache'):
            _cache['data'] = None
            _cache['ts'] = 0
            self.send_body(b'Cache cleared', 'text/plain')
        else:
            body = HTML.encode('utf-8')
            self.send_body(body, 'text/html; charset=utf-8')

    def log_message(self, fmt, *args):
        pass  # suppress server log noise


if __name__ == '__main__':
    print(f'⚽ World Cup 2026 Pick\'em Dashboard')
    print(f'   Running on port {PORT}')
    HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()

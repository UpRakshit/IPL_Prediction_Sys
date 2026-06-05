const state = {
  matches: [],
  selectedMatchId: null,
  center: null,
};

const $ = (selector) => document.querySelector(selector);

function percent(value) {
  return `${Math.round(value * 100)}%`;
}

function scoreText(innings) {
  if (!innings) return "Yet to bat";
  return `${innings.runs}/${innings.wickets}`;
}

function setText(selector, value) {
  const element = $(selector);
  if (element) element.textContent = value ?? "-";
}

function teamInitials(team) {
  return team?.short_name || team?.name?.split(" ").map((part) => part[0]).join("").slice(0, 3) || "-";
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Request failed: ${url}`);
  return response.json();
}

async function loadMatches() {
  state.matches = await fetchJson("/matches/current");
  state.selectedMatchId = state.selectedMatchId || state.matches[0]?.id;
  renderMatches();
  if (state.selectedMatchId) await loadMatchCenter(state.selectedMatchId);
  else renderNoMatches();
}

async function loadMatchCenter(matchId) {
  state.selectedMatchId = matchId;
  state.center = await fetchJson(`/matches/${matchId}/center`);
  renderMatches();
  renderMatchCenter();
  setText("#last-updated", new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
}

function renderMatches() {
  setText("#match-count", state.matches.length);
  const list = $("#match-list");
  list.innerHTML = "";

  state.matches.forEach((match) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = `match-card ${match.id === state.selectedMatchId ? "active" : ""}`;
    card.innerHTML = `
      <span class="status-chip">${match.status}</span>
      <strong>${match.name}</strong>
      <small>${match.result_summary || match.venue || ""}</small>
    `;
    card.addEventListener("click", () => loadMatchCenter(match.id));
    list.appendChild(card);
  });

  if (!state.matches.length) {
    list.innerHTML = `<div class="empty-state">No matches available.</div>`;
  }
}

function renderNoMatches() {
  setText("#series-name", "CricketAI Match Centre");
  setText("#match-status", "standby");
  setText("#team-a-name", "No match");
  setText("#team-a-score", "-");
  setText("#team-a-overs", "-");
  setText("#team-b-name", "Check back shortly");
  setText("#team-b-score", "-");
  setText("#team-b-overs", "-");
  setText("#status-line", "No live, recent, or upcoming matches are available right now.");
  setText("#current-rr", "-");
  setText("#required-rr", "-");
  setText("#balls-left", "-");
  setText("#last-event", "No matches available");
  $("#commentary-feed").innerHTML = `<div class="empty-state">Match commentary will appear when cricket data is available.</div>`;
  $("#scorecard").innerHTML = `<div class="empty-state">Scorecards will appear when cricket data is available.</div>`;
  $("#squads").innerHTML = `<div class="empty-state">Squads will appear when cricket data is available.</div>`;
}

function renderMatchCenter() {
  const center = state.center;
  if (!center) return;

  const [firstInnings, chaseInnings] = center.innings;
  const battingInnings = chaseInnings || firstInnings;
  const bowlingInnings = firstInnings;
  const [teamA, teamB] = center.match.teams;

  setText("#series-name", `${center.match.series || "Cricket"} ${center.match.match_number || ""}`.trim());
  setText("#match-status", center.match.status);
  setTeamBadge("#team-a-badge", battingInnings?.team || teamA);
  setTeamBadge("#team-b-badge", bowlingInnings?.team || teamB);
  setText("#team-a-name", battingInnings?.team.name || teamA?.name);
  setText("#team-a-score", scoreText(battingInnings));
  setText("#team-a-overs", battingInnings ? `${battingInnings.overs} overs` : center.match.match_number);
  setText("#team-b-name", bowlingInnings?.team.name || teamB?.name);
  setText("#team-b-score", scoreText(bowlingInnings));
  setText("#team-b-overs", bowlingInnings ? `${bowlingInnings.overs} overs` : formatDate(center.match.start_time_utc));
  setText("#status-line", center.status_line);
  renderHeroMetrics(center);
  setText("#last-event", center.state.last_event);
  setText("#partnership", battingInnings?.current_partnership || "Partnership");
  setText("#match-number", center.match.match_number || "Match");
  setText("#venue", center.match.venue);
  setText("#toss", tossText(center.match));
  setText("#start-time", formatDate(center.match.start_time_utc));

  renderCommentary(center.commentary);
  renderScorecard(center.innings);
  renderSquads(center.squads);
  renderForecast(center.forecast, center.state);
  renderPitch(center.pitch);
  renderModel(center);
  renderOverProjections(center.over_projections || []);
}

function setTeamBadge(selector, team) {
  const element = $(selector);
  if (!element) return;
  element.textContent = teamInitials(team);
  element.className = `team-badge ${team?.id || ""}`;
}

function renderHeroMetrics(center) {
  if (center.innings.length) {
    setText("#current-rr", center.state.current_run_rate.toFixed(2));
    setText("#required-rr", center.state.required_run_rate?.toFixed(2) || "-");
    setText("#balls-left", center.state.balls_remaining ?? "-");
    setText("#metric-a-label", "CRR");
    setText("#metric-b-label", "RRR");
    setText("#metric-c-label", "balls");
    return;
  }

  setText("#current-rr", center.pitch?.par_score ?? center.state.projected_score);
  setText("#required-rr", percent(center.forecast.win_probability));
  setText("#balls-left", percent(center.forecast.confidence || 0));
  setText("#metric-a-label", "par score");
  setText("#metric-b-label", `${center.forecast.batting_team.short_name} win`);
  setText("#metric-c-label", "confidence");
}

function tossText(match) {
  const tossTeam = match.teams.find((team) => team.id === match.toss_winner_id);
  const battingTeam = match.teams.find((team) => team.id === match.batting_first_id);
  if (!tossTeam) return "-";
  return `${tossTeam.name}, ${battingTeam ? `${battingTeam.name} batting first` : "decision pending"}`;
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Kolkata",
    timeZoneName: "short",
  });
}

function renderCommentary(commentary) {
  const feed = $("#commentary-feed");
  feed.innerHTML = "";
  if (!commentary.length) {
    feed.innerHTML = `<div class="empty-state">No live ball-by-ball yet. This will fill automatically when the match starts.</div>`;
    return;
  }

  commentary.forEach((ball) => {
    const row = document.createElement("article");
    row.className = `ball-row ${ball.boundary ? "boundary" : ""} ${ball.wicket ? "wicket" : ""}`;
    row.innerHTML = `
      <div class="ball-number">${ball.over_ball}</div>
      <div class="ball-copy">
        <strong>${ball.runs} run${ball.runs === 1 ? "" : "s"} - ${ball.striker}</strong>
        <p>${ball.text}</p>
      </div>
      <div class="tag-list">
        ${ball.tags.map((tag) => `<span class="tag">${tag}</span>`).join("")}
      </div>
    `;
    feed.appendChild(row);
  });
}

function renderScorecard(inningsList) {
  const container = $("#scorecard");
  container.innerHTML = "";
  if (!inningsList.length) {
    container.innerHTML = `<div class="empty-state">Scorecard will appear when GT vs RR starts. Use the Model tab for pre-match prediction inputs.</div>`;
    return;
  }

  inningsList.forEach((innings) => {
    const block = document.createElement("section");
    block.className = "innings-block";
    block.innerHTML = `
      <div class="innings-title">
        <h3>${innings.team.name}</h3>
        <strong>${innings.runs}/${innings.wickets} (${innings.overs})</strong>
      </div>
      ${battingTable(innings.batting)}
      ${bowlingTable(innings.bowling)}
      <div class="fall-list">
        ${innings.fall_of_wickets.map((wicket) => `<span>${wicket}</span>`).join("")}
      </div>
    `;
    container.appendChild(block);
  });
}

function battingTable(rows) {
  return `
    <table class="data-table">
      <thead>
        <tr><th>Batter</th><th>R</th><th>B</th><th>4s</th><th>6s</th><th>SR</th></tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (row) => `
              <tr>
                <td><strong>${row.player.name}</strong><small>${row.dismissal || ""}</small></td>
                <td>${row.runs}</td>
                <td>${row.balls}</td>
                <td>${row.fours}</td>
                <td>${row.sixes}</td>
                <td>${row.strike_rate.toFixed(2)}</td>
              </tr>
            `
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function bowlingTable(rows) {
  return `
    <table class="data-table">
      <thead>
        <tr><th>Bowler</th><th>O</th><th>M</th><th>R</th><th>W</th><th>Econ</th></tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (row) => `
              <tr>
                <td><strong>${row.player.name}</strong></td>
                <td>${row.overs}</td>
                <td>${row.maidens}</td>
                <td>${row.runs}</td>
                <td>${row.wickets}</td>
                <td>${row.economy.toFixed(2)}</td>
              </tr>
            `
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function renderSquads(squads) {
  const container = $("#squads");
  container.innerHTML = "";
  if (!squads.length) {
    container.innerHTML = `<div class="empty-state">No squad available.</div>`;
    return;
  }

  squads.forEach((squad) => {
    const team = document.createElement("section");
    team.className = "squad-team";
    team.innerHTML = `
      <h3>${squad.team.name}</h3>
      <ul>
        ${
          squad.players.length
            ? squad.players
                .map((player) => `<li><span>${player.name}</span><small>${player.role || ""}</small></li>`)
                .join("")
            : `<li><span>Squad awaiting feed</span><small>-</small></li>`
        }
      </ul>
    `;
    container.appendChild(team);
  });
}

function renderForecast(forecast, matchState) {
  setText("#next-over", forecast.next_over);
  setText("#expected-runs", forecast.expected_runs.toFixed(1));
  setText("#run-range", `Range ${forecast.run_range}`);
  setText("#wicket-risk", percent(forecast.wicket_probability));
  setText("#boundary-chance", percent(forecast.boundary_probability));
  setText("#dot-chance", percent(forecast.dot_ball_probability));
  setText("#win-probability", percent(forecast.win_probability));
  setText("#strategy-text", forecast.suggested_strategy);
  setText("#momentum", forecast.momentum);
  setText("#striker", matchState.striker.name);
  setText("#non-striker", matchState.non_striker.name);
  setText("#bowler", matchState.bowler.name);

  $("#wicket-bar").style.width = percent(forecast.wicket_probability);
  $("#boundary-bar").style.width = percent(forecast.boundary_probability);
  $("#dot-bar").style.width = percent(forecast.dot_ball_probability);
  $("#win-bar").style.width = percent(forecast.win_probability);

  const factorList = $("#forecast-factors");
  factorList.innerHTML = forecast.factors.map((factor) => `<li>${factor}</li>`).join("");
}

function renderPitch(pitch) {
  const container = $("#pitch-report");
  if (!container) return;
  if (!pitch) {
    container.innerHTML = `<div class="empty-state">Pitch report unavailable.</div>`;
    return;
  }

  setText("#pitch-par", `Par ${pitch.par_score}`);
  container.innerHTML = `
    <article class="pitch-card wide">
      <span>Surface</span>
      <strong>${pitch.surface}</strong>
      <p>${pitch.boundary_size}</p>
    </article>
    <article class="pitch-card"><span>Par score</span><strong>${pitch.par_score}</strong></article>
    <article class="pitch-card"><span>Bat first avg</span><strong>${pitch.batting_first_avg}</strong></article>
    <article class="pitch-card"><span>Chase avg</span><strong>${pitch.chasing_avg}</strong></article>
    <article class="pitch-card"><span>Dew factor</span><strong>${percent(pitch.dew_factor)}</strong></article>
    <article class="pitch-card"><span>Pace assist</span><strong>${percent(pitch.pace_assist)}</strong></article>
    <article class="pitch-card"><span>Spin assist</span><strong>${percent(pitch.spin_assist)}</strong></article>
    <article class="pitch-card wide">
      <span>Notes</span>
      <ul class="pitch-notes">${pitch.notes.map((note) => `<li>${note}</li>`).join("")}</ul>
    </article>
  `;
}

function renderModel(center) {
  setText("#data-mode", center.data_mode);
  setText("#source-note", center.source_note);
  renderFeatureImportance(center.forecast.feature_importance || {});
  renderMatchups(center.matchups || []);
  renderPlayerForm(center.player_form || []);
}

function renderFeatureImportance(features) {
  const container = $("#feature-importance");
  if (!container) return;
  const entries = Object.entries(features);
  if (!entries.length) {
    container.innerHTML = `<div class="empty-state">No feature weights available.</div>`;
    return;
  }

  container.innerHTML = entries
    .map(([name, value]) => {
      const label = name
        .split("_")
        .map((word) => word[0].toUpperCase() + word.slice(1))
        .join(" ");
      return `
        <article class="feature-item">
          <span>${label}</span>
          <strong>${percent(value)}</strong>
          <div class="feature-meter"><i style="width:${percent(value)}"></i></div>
        </article>
      `;
    })
    .join("");
}

function renderMatchups(matchups) {
  const container = $("#matchups");
  if (!container) return;
  if (!matchups.length) {
    container.innerHTML = `<div class="empty-state">No matchup insights available.</div>`;
    return;
  }

  container.innerHTML = matchups
    .map(
      (matchup) => `
        <article class="matchup-item">
          <div>
            <span>${matchup.title}</span>
            <strong>${matchup.value}</strong>
          </div>
          <span class="edge-pill">${matchup.edge}</span>
          <p>${matchup.detail}</p>
        </article>
      `
    )
    .join("");
}

function renderPlayerForm(forms) {
  const container = $("#player-form");
  if (!container) return;
  if (!forms.length) {
    container.innerHTML = `<div class="empty-state">No player form inputs available.</div>`;
    return;
  }

  container.innerHTML = `
    <table class="data-table">
      <thead>
        <tr>
          <th>Player</th>
          <th>Team</th>
          <th>M</th>
          <th>Runs</th>
          <th>SR</th>
          <th>Wkts</th>
          <th>Econ</th>
          <th>Trend</th>
        </tr>
      </thead>
      <tbody>
        ${forms
          .map(
            (form) => `
              <tr>
                <td><strong>${form.player.name}</strong><small>${form.player.role || ""}</small></td>
                <td>${form.team.short_name}</td>
                <td>${form.matches}</td>
                <td>${form.runs || "-"}</td>
                <td>${form.strike_rate ? form.strike_rate.toFixed(1) : "-"}</td>
                <td>${form.wickets || "-"}</td>
                <td>${form.economy ? form.economy.toFixed(2) : "-"}</td>
                <td>${form.recent_trend}</td>
              </tr>
            `
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function renderOverProjections(projections) {
  const container = $("#over-projections");
  if (!container) return;
  if (!projections.length) {
    container.innerHTML = `<div class="empty-state">Over projections unavailable.</div>`;
    return;
  }

  container.innerHTML = projections
    .map(
      (projection) => `
        <article class="over-card">
          <span class="over-number">${projection.over}</span>
          <div>
            <strong>${projection.expected_runs.toFixed(1)} runs - ${projection.phase}</strong>
            <div class="over-metrics">
              <span>Wkt ${percent(projection.wicket_probability)}</span>
              <span>Boundary ${percent(projection.boundary_probability)}</span>
              <span>${projection.key_batter}</span>
              <span>${projection.key_bowler}</span>
            </div>
            <p>${projection.note}</p>
          </div>
        </article>
      `
    )
    .join("");
}

function bindTabs() {
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => showTab(button.dataset.tab));
  });

  document.querySelectorAll("[data-tab-target]").forEach((button) => {
    button.addEventListener("click", () => showTab(button.dataset.tabTarget));
  });
}

function showTab(tabName) {
  document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
  document.querySelectorAll(".content-panel").forEach((panel) => panel.classList.remove("active"));
  const tabButton = $(`.tab[data-tab="${tabName}"]`);
  const panel = $(`#tab-${tabName}`);
  if (tabButton) tabButton.classList.add("active");
  if (panel) panel.classList.add("active");
  if (panel) panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function bindRefresh() {
  const button = $("#refresh-button");
  if (!button) return;
  button.addEventListener("click", () => {
    if (state.selectedMatchId) loadMatchCenter(state.selectedMatchId).catch(console.error);
    else loadMatches().catch(console.error);
  });
}

function startPolling() {
  setInterval(() => {
    if (state.selectedMatchId) loadMatchCenter(state.selectedMatchId).catch(console.error);
  }, 30000);
}

bindTabs();
bindRefresh();
loadMatches().catch((error) => {
  console.error(error);
  $("#match-list").innerHTML = `<div class="empty-state">Unable to load matches.</div>`;
});
startPolling();

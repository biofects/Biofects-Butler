const COMPOSITIONS = {
  radial_command_overview: ["overview", "left_menu", "reactor", "right_menu", "media", "events"],
  security_camera_board: ["status", "camera_primary", "camera_grid", "controls", "events"],
  focused_control: ["left_instrument", "core", "right_instrument", "footer"],
};

const LAYOUTS = {
  radial_command_overview: { name: "Command Center", description: "Overview, menus, assistant, media and events" },
  security_camera_board: { name: "Camera & Security", description: "Status, cameras, controls and events" },
  focused_control: { name: "Room Controls", description: "Large central controls with supporting panels" },
};

const SLOT_LABELS = {
  overview: "Overview", left_menu: "Left Commands", reactor: "Assistant", right_menu: "Right Commands", media: "Media", events: "Upcoming Events",
  status: "Security Overview", camera_primary: "Featured Camera", camera_grid: "Camera Strip", controls: "Controls", events: "Recent Events",
  left_instrument: "Left Panel", core: "Main Control", right_instrument: "Right Panel", footer: "Lower Panel",
};

const SECTION_TYPES = [
  "status_overview", "orbital_menu", "entity_controls", "security", "climate",
  "cameras", "media", "events", "weather", "power", "quick_commands", "calendar_form",
];
const ACTION_TYPES = ["more_info", "toggle", "activate", "navigate", "call_service"];
const BINDING_ROLES = [
  "none", "calendar_source", "weather_source", "media_source", "event_title",
  "event_notification", "event_all_day", "event_all_day_date", "event_start",
  "event_end", "event_description", "event_repeat", "event_create", "event_reset",
];

const clone = (value) => JSON.parse(JSON.stringify(value));
const escapeHtml = (value) => String(value ?? "").replace(
  /[&<>'"]/g,
  (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character],
);
const label = (value) => String(value).replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const slug = (value) => String(value).toLowerCase().trim().replace(/[^a-z0-9_-]+/g, "_").replace(/^_+|_+$/g, "");

class BiofectsButlerPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._snapshot = null;
    this._draft = null;
    this._selectedId = null;
    this._message = "";
    this._loading = false;
    this._saving = false;
    this._activeScreenId = null;
    this._activeWorkspace = "screens";
    this._activeSectionSlot = null;
    this._editorDialog = null;
    this._iconBrowser = null;
    this._mdiIcons = [];
    this._setupOptions = null;
  }

  set hass(value) {
    const firstConnection = !this._hass;
    this._hass = value;
    if (firstConnection && this.isConnected) this._load();
    this._updateSelectors();
  }

  set panel(value) {
    this._panel = value;
  }

  connectedCallback() {
    this.shadowRoot.addEventListener("pointerdown", (event) => this._onPointerDown(event), true);
    this.shadowRoot.addEventListener("click", (event) => this._onClick(event));
    this.shadowRoot.addEventListener("change", (event) => this._onChange(event));
    this.shadowRoot.addEventListener("input", (event) => this._onInput(event));
    this.shadowRoot.addEventListener("dragstart", (event) => this._onDragStart(event));
    this.shadowRoot.addEventListener("dragover", (event) => this._onDragOver(event));
    this.shadowRoot.addEventListener("drop", (event) => this._onDrop(event));
    this._render();
    if (this._hass) this._load();
  }

  async _load(preferredId = this._selectedId) {
    if (this._loading) return;
    this._loading = true;
    this._message = "Loading profiles...";
    this._render();
    try {
      [this._snapshot, this._setupOptions] = await Promise.all([
        this._hass.callWS({ type: "biofects_butler/get_dashboard_profiles" }),
        this._hass.callWS({ type: "biofects_butler/get_setup_options" }),
      ]);
      const profiles = this._snapshot.profiles || [];
      const selected = profiles.find((profile) => profile.profile_id === preferredId) || profiles[0];
      this._selectedId = selected?.profile_id || null;
      this._draft = selected ? clone(selected) : null;
      this._draft?.screens.forEach((screen) => this._ensureScreenSections(screen));
      this._loadedProfile = selected ? clone(selected) : null;
      await this._loadMdiIcons();
      if (!this._draft?.screens.some((screen) => screen.screen_id === this._activeScreenId)) {
        this._activeScreenId = this._draft?.default_screen_id || this._draft?.screens[0]?.screen_id || null;
      }
      this._message = "";
    } catch (error) {
      this._message = error?.message || "Unable to load Butler profiles.";
    } finally {
      this._loading = false;
      this._render();
    }
  }

  _render() {
    if (!this.shadowRoot) return;
    const profiles = this._snapshot?.profiles || [];
    const displays = this._snapshot?.displays || [];
    const dashboards = Object.entries(this._hass?.panels || {})
      .filter(([, panel]) => panel.component_name === "lovelace")
      .map(([path, panel]) => ({ path, title: panel.title || panel.config?.title || label(path) }));
    const profileOptions = profiles.map((profile) =>
      `<option value="${escapeHtml(profile.profile_id)}" ${profile.profile_id === this._selectedId ? "selected" : ""}>${escapeHtml(profile.name)}</option>`,
    ).join("");
    const profileButtons = profiles.map((profile) =>
      `<button class="profile-choice ${profile.profile_id === this._selectedId ? "selected" : ""}" data-action="select-profile-button" data-profile-id="${escapeHtml(profile.profile_id)}"><ha-icon icon="${profile.profile_id === this._selectedId ? "mdi:radiobox-marked" : "mdi:radiobox-blank"}"></ha-icon><span>${escapeHtml(profile.name)}</span></button>`,
    ).join("");

    this.shadowRoot.innerHTML = `
      <style>${this._styles()}</style>
      <main>
        <header class="page-header">
          <div>
            <p class="eyebrow">BIOFECTS BUTLER / CONFIGURATION</p>
            <h1>Butler Configuration</h1>
          </div>
        </header>
        ${this._message ? `<div class="notice">${escapeHtml(this._message)}</div>` : ""}
        <nav class="task-tabs" aria-label="Configuration sections">
          ${[["profiles", "Profiles", "mdi:account-multiple-outline"], ["screens", "Screens", "mdi:view-dashboard-outline"], ["displays", "Displays", "mdi:monitor-cellphone"], ["integrations", "Integrations", "mdi:puzzle-outline"], ["advanced", "Advanced", "mdi:cog-outline"]].map(([id, title, icon]) => `<button class="task-tab ${this._activeWorkspace === id ? "selected" : ""}" data-action="select-workspace" data-workspace="${id}"><ha-icon icon="${icon}"></ha-icon>${title}</button>`).join("")}
        </nav>
        ${this._draft ? `<div class="profile-context"><label>EDITING PROFILE<select data-action="select-profile">${profileOptions}</select></label><span>${escapeHtml(this._draft.screens.length)} screens</span><button class="primary" data-action="save" ${this._saving ? "disabled" : ""}>${this._saving ? "Saving..." : "Save Profile"}</button></div>` : ""}
        <section class="task-workspace">
          ${this._workspaceEditor({ profiles, displays, dashboards, profileButtons })}
        </section>
        <input id="import-file" type="file" accept="application/json" hidden>
      </main>
      <datalist id="mdi-icon-options">${this._mdiIcons.map((icon) => `<option value="${escapeHtml(icon)}"></option>`).join("")}</datalist>`;
    this._wireImport();
    this._updateSelectors();
  }

  _workspaceEditor({ profiles, displays, dashboards, profileButtons }) {
    if (this._activeWorkspace === "profiles") return this._profilesWorkspace(profileButtons);
    if (this._activeWorkspace === "displays") return this._displayAssignments(displays, profiles);
    if (this._activeWorkspace === "integrations") return this._conversationBackends();
    if (this._activeWorkspace === "advanced") return this._advancedWorkspace(dashboards);
    return this._draft ? this._profileEditor() : "<div class='empty'>Create a profile before adding screens.</div>";
  }

  _profilesWorkspace(profileButtons) {
    const profile = this._draft;
    const weatherEntities = Object.values(this._hass?.states || {})
      .filter((state) => state.entity_id.startsWith("weather."))
      .sort((left, right) => (left.attributes.friendly_name || left.entity_id).localeCompare(right.attributes.friendly_name || right.entity_id));
    return `<section class="settings-page"><div class="settings-heading"><div><p class="eyebrow">PROFILES</p><h2>Dashboard profiles</h2><p>Choose who and what this dashboard is configured for.</p></div><div class="button-row"><button data-action="new">New profile</button><button data-action="duplicate" ${profile ? "" : "disabled"}>Duplicate</button></div></div><div class="profiles-layout"><div class="profile-list"><label>AVAILABLE PROFILES</label><div class="profile-choices">${profileButtons}</div></div>${profile ? `<div class="profile-settings"><div class="field"><label>PROFILE NAME</label><input data-profile-field="name" value="${escapeHtml(profile.name)}"></div><div class="field"><label>GREETING WEATHER</label><select data-greeting-weather><option value="">No weather summary</option>${weatherEntities.map((state) => `<option value="${escapeHtml(state.entity_id)}" ${state.entity_id === profile.greeting_weather_entity_id ? "selected" : ""}>${escapeHtml(state.attributes.friendly_name || state.entity_id)}</option>`).join("")}</select></div><div class="field"><label>START SCREEN</label><div class="fixed-value">Home</div></div><button class="danger profile-delete" data-action="delete-profile" ${profile.profile_id === "default" ? "disabled" : ""}><ha-icon icon="mdi:delete-outline"></ha-icon>Delete profile</button></div>` : "<div class='empty'>No profile selected.</div>"}</div></section>`;
  }

  _advancedWorkspace(dashboards) {
    return `<section class="settings-page"><div class="settings-heading"><div><p class="eyebrow">ADVANCED</p><h2>Import and maintenance</h2><p>Create from Home Assistant or move profile definitions between systems.</p></div></div><div class="advanced-grid"><article><h2>Start from HA dashboard</h2><p>Import a Lovelace dashboard as a new Butler draft.</p><select id="lovelace-dashboard">${dashboards.map((dashboard) => `<option value="${escapeHtml(dashboard.path)}">${escapeHtml(dashboard.title)}</option>`).join("")}</select><button data-action="import-lovelace" ${dashboards.length ? "" : "disabled"}>Create draft</button></article><article><h2>Profile file</h2><p>Import or export the selected profile as JSON.</p><div class="button-row"><button data-action="import">Import</button><button data-action="export" ${this._draft ? "" : "disabled"}>Export</button></div></article></div></section>`;
  }

  _profileEditor() {
    const profile = this._draft;
    const activeScreen = profile.screens.find((screen) => screen.screen_id === this._activeScreenId) || profile.screens[0];
    return `
      <div class="screen-workspace"><aside class="screen-list"><div class="screen-list-heading"><label>SCREENS</label><button class="add-screen-tab" title="Add dashboard" data-action="add-screen">+</button></div>
        ${profile.screens.map((screen) => `<button class="screen-tab ${screen.screen_id === activeScreen.screen_id ? "selected" : ""}" data-action="select-screen" data-screen-id="${escapeHtml(screen.screen_id)}">${escapeHtml(screen.title)}</button>`).join("")}
      </aside><div class="screens">${this._screenEditor(activeScreen, profile.screens.indexOf(activeScreen))}</div></div>
      ${this._renderEditorDialog()}`;
  }

  _conversationBackends() {
    const backends = this._setupOptions?.backends || [];
    return `<div class="dashboard-import backend-config"><h2>Conversation Backends</h2>${backends.map((backend) => {
      const configure = backend.state === "needs_configuration" && backend.configuration_url
        ? `<a class="backend-configure" href="${escapeHtml(backend.configuration_url)}">Configure</a>`
        : "";
      return `<div class="backend-row"><span><strong>${escapeHtml(backend.name)}</strong><small>${escapeHtml(label(backend.state || "unavailable"))}</small></span>${configure}</div>`;
    }).join("") || `<small>No conversation backends reported.</small>`}</div>`;
  }

  _screenEditor(screen, screenIndex) {
    if (screen.screen_id === "home") this._ensureHomeSidebarBlueprint(screen);
    const missingSlots = COMPOSITIONS[screen.composition].filter((slot) => !screen.sections.some((section) => section.slot === slot));
    const activeSection = screen.sections.find((section) => section.slot === this._activeSectionSlot) || screen.sections[0];
    const activeSectionIndex = activeSection ? screen.sections.indexOf(activeSection) : -1;
    this._activeSectionSlot = activeSection?.slot || null;
    return `
      <article class="screen-card">
        <div class="screen-head canvas-toolbar">
          <div class="field grow"><label>DASHBOARD NAME</label>${screen.screen_id === "home" ? `<div class="fixed-value">Home</div>` : `<input data-screen="${screenIndex}" data-field="title" value="${escapeHtml(screen.title)}">`}</div>
          ${screen.screen_id === "home" ? "" : `<button class="icon" title="Move screen up" data-action="move-screen" data-index="${screenIndex}" data-direction="-1">↑</button><button class="icon" title="Move screen down" data-action="move-screen" data-index="${screenIndex}" data-direction="1">↓</button>`}
          <button class="danger" title="Delete dashboard" data-action="remove-screen" data-index="${screenIndex}" ${screen.screen_id === "home" ? "disabled" : ""}><ha-icon icon="mdi:delete-outline"></ha-icon>Delete Dashboard</button>
        </div>
        <div class="home-mode-note"><ha-icon icon="${screen.screen_id === "home" ? "mdi:home-edit" : "mdi:tune-variant"}"></ha-icon><span><strong>${screen.screen_id === "home" ? "Concept Home panels" : "Native Butler controls"}</strong><small>${screen.screen_id === "home" ? "Add, remove, resize, and configure panels while retaining Butler's native Home design." : "Entity controls expand into a detailed Butler control panel when tapped."}</small></span></div>
        ${screen.screen_id === "home" ? "" : `<label class="layout-label">DASHBOARD TEMPLATE</label><div class="layout-choices">${Object.entries(LAYOUTS).map(([composition, layout]) => this._layoutChoice(composition, layout, screen.composition, screenIndex)).join("")}</div>`}
        <div class="panel-picker"><div class="panel-picker-heading"><strong>PANELS</strong><small>Select one to edit</small></div><div class="panel-picker-list">${screen.sections.map((section) => `<button class="panel-picker-item ${section === activeSection ? "selected" : ""}" data-action="select-panel" data-panel-slot="${escapeHtml(section.slot)}"><ha-icon icon="mdi:view-grid-outline"></ha-icon><span>${escapeHtml(section.title || this._slotLabel(section.slot, screen))}</span><small>${escapeHtml(label(section.type))}</small></button>`).join("")}</div></div>
        <details class="add-panel"><summary>Add panel</summary><div class="panel-toolbar">${missingSlots.map((slot) => `<button data-action="add-section" data-screen="${screenIndex}" data-slot="${slot}"><ha-icon icon="mdi:plus"></ha-icon>${escapeHtml(this._slotLabel(slot, screen))}</button>`).join("") || `<small>All panel positions are in use.</small>`}</div></details>
        <div class="focused-panel-editor">${activeSection ? this._sectionEditor(activeSection, screen, screenIndex, activeSectionIndex) : `<div class="empty-panels">Add a panel to build this dashboard.</div>`}</div>
      </article>`;
  }

  _layoutChoice(composition, layout, selected, screenIndex) {
    return `<button class="layout-choice ${composition === selected ? "selected" : ""}" data-action="select-layout" data-screen="${screenIndex}" data-composition="${composition}"><span class="mini-layout ${composition}">${COMPOSITIONS[composition].map((slot) => `<i class="slot-${slot}"></i>`).join("")}</span><strong>${layout.name}</strong><small>${layout.description}</small></button>`;
  }

  _slotLabel(slot, screen) {
    if (screen.screen_id === "home" && slot === "events") return "Upcoming Events";
    return SLOT_LABELS[slot] || label(slot);
  }

  _sectionEditor(section, screen, screenIndex, sectionIndex) {
    if (screen.screen_id === "home" && ["left_menu", "right_menu"].includes(section.slot) && section.type === "orbital_menu") {
      return this._homeSidebarEditor(section, screenIndex, sectionIndex);
    }
    if (section.type === "quick_commands") return this._quickCommandsEditor(section, screen, screenIndex, sectionIndex);
    if (section.type === "calendar_form") return this._calendarFormEditor(section, screen, screenIndex, sectionIndex);
    if (section.type === "weather") return this._weatherEditor(section, screen, screenIndex, sectionIndex);
    const entityDomain = screen.screen_id === "home" && section.slot === "media" ? "media_player"
      : screen.screen_id === "home" && section.slot === "events" ? "calendar" : null;
    const entityCards = (section.bindings || []).map((binding, bindingIndex) =>
      binding.kind === "entity" && (!entityDomain || binding.target_id.startsWith(`${entityDomain}.`)) ? this._bindingCard(binding, section, screenIndex, sectionIndex, bindingIndex) : "",
    ).join("");
    const profilePages = screen.screen_id === this._draft.default_screen_id
      ? this._draft.screens.filter((candidate) => candidate.screen_id !== this._draft.default_screen_id)
      : [];
    const menuPages = section.slot === "left_menu"
      ? profilePages.filter((_, index) => index % 2 === 0)
      : section.slot === "right_menu"
        ? profilePages.filter((_, index) => index % 2 === 1)
        : [];
    const pageCards = menuPages.map((page) => `<button class="page-link-card" data-action="select-screen" data-screen-id="${escapeHtml(page.screen_id)}"><ha-icon icon="mdi:view-dashboard-outline"></ha-icon><span><strong>${escapeHtml(page.title)}</strong><small>PROFILE PAGE</small></span><em>OPEN</em></button>`).join("");
    const cards = `${pageCards}${entityCards}`;
    const defaultHeading = this._slotLabel(section.slot, screen);
    const headingEditor = `<label><span>${escapeHtml(defaultHeading)}</span><input data-section-heading data-screen="${screenIndex}" data-section="${sectionIndex}" value="${escapeHtml(section.title || "")}" placeholder="${escapeHtml(defaultHeading)}" maxlength="80" aria-label="${escapeHtml(defaultHeading)} heading"></label><label><span>PANEL TYPE</span><select data-section-type data-screen="${screenIndex}" data-section="${sectionIndex}">${SECTION_TYPES.map((type) => `<option value="${type}" ${section.type === type ? "selected" : ""}>${label(type)}</option>`).join("")}</select></label>`;
    const calendarViewEditor = section.type === "events"
      ? `<label><span>INITIAL VIEW</span><select data-screen="${screenIndex}" data-section="${sectionIndex}" data-field="initial_view"><option value="dayGridMonth" ${(section.initial_view || "dayGridMonth") === "dayGridMonth" ? "selected" : ""}>Month + Day Agenda</option><option value="listWeek" ${section.initial_view === "listWeek" ? "selected" : ""}>Week List</option></select></label>`
      : "";
    return `
      <div class="section-block slot-${section.slot} ${section.panel_height === "full_height" ? "panel-full-height" : ""}" data-drop-screen="${screenIndex}" data-drop-section="${sectionIndex}">
        <div class="slot-heading">${headingEditor}${this._panelControls(screenIndex, sectionIndex, section, screen.sections.length)}<button class="region-add" title="Add card" data-action="open-entity-picker" data-screen="${screenIndex}" data-section="${sectionIndex}" ${entityDomain ? `data-entity-domain="${entityDomain}"` : ""}>+</button></div>
        ${calendarViewEditor}
        ${this._popupSettings(section, screenIndex, sectionIndex)}
        <div class="entity-canvas">${cards || `<button class="drop-empty" data-action="open-entity-picker" data-screen="${screenIndex}" data-section="${sectionIndex}" ${entityDomain ? `data-entity-domain="${entityDomain}"` : ""}><ha-icon icon="mdi:plus-circle-outline"></ha-icon><span>Add card</span></button>`}</div>
      </div>`;
  }

  _weatherEditor(section, screen, screenIndex, sectionIndex) {
    const location = `data-screen="${screenIndex}" data-section="${sectionIndex}"`;
    const weatherEntities = Object.values(this._hass?.states || {})
      .filter((state) => state.entity_id.startsWith("weather."))
      .sort((left, right) => (left.attributes.friendly_name || left.entity_id).localeCompare(right.attributes.friendly_name || right.entity_id));
    const selected = (section.bindings || []).find((binding) => binding.role === "weather_source")
      || (section.bindings || []).find((binding) => binding.target_id?.startsWith("weather."));
    const selectedId = selected?.target_id || "";
    const features = Number(this._hass?.states?.[selectedId]?.attributes?.supported_features || 0);
    const supported = [
      ["daily", "Daily", 1],
      ["hourly", "Hourly", 2],
      ["twice_daily", "Twice Daily", 4],
    ].filter(([, , flag]) => features === 0 || (features & flag));
    if (!supported.some(([value]) => value === (section.forecast_type || "daily"))) {
      section.forecast_type = supported[0]?.[0] || "daily";
    }
    return `<div class="section-block slot-${section.slot} ${section.panel_height === "full_height" ? "panel-full-height" : ""}">
      <div class="slot-heading"><label><span>${escapeHtml(this._slotLabel(section.slot, screen))}</span><input data-section-heading ${location} value="${escapeHtml(section.title || "")}" placeholder="Weather"></label><label><span>PANEL TYPE</span><select data-section-type ${location}>${SECTION_TYPES.map((type) => `<option value="${type}" ${section.type === type ? "selected" : ""}>${label(type)}</option>`).join("")}</select></label>${this._panelControls(screenIndex, sectionIndex, section, screen.sections.length)}</div>
      <div class="form-config-grid">
        <label><span>WEATHER PROVIDER</span><select data-weather-entity ${location}><option value="">Select a Home Assistant weather entity</option>${weatherEntities.map((state) => `<option value="${escapeHtml(state.entity_id)}" ${state.entity_id === selectedId ? "selected" : ""}>${escapeHtml(state.attributes.friendly_name || state.entity_id)}</option>`).join("")}</select></label>
        <label><span>FORECAST</span><select data-weather-forecast ${location} ${selectedId ? "" : "disabled"}>${supported.map(([value, name]) => `<option value="${value}" ${(section.forecast_type || "daily") === value ? "selected" : ""}>${name}</option>`).join("")}</select></label>
      </div>
      ${this._popupSettings(section, screenIndex, sectionIndex)}
      <div class="entity-canvas">${selected ? this._bindingCard(selected, section, screenIndex, sectionIndex, section.bindings.indexOf(selected)) : `<div class="drop-empty"><ha-icon icon="mdi:weather-partly-cloudy"></ha-icon><span>Select a weather provider above</span></div>`}</div>
    </div>`;
  }

  _quickCommandsEditor(section, screen, screenIndex, sectionIndex) {
    const commands = (section.actions || []).map((action, actionIndex) => {
      const location = `data-screen="${screenIndex}" data-section="${sectionIndex}" data-action-index="${actionIndex}"`;
      const behavior = action.type === "toggle" ? "toggle" : "call_service";
      const behaviorFields = behavior === "toggle"
        ? `<label class="command-entity"><span>ENTITY</span><div data-action-entity-selector="${screenIndex}-${sectionIndex}-${actionIndex}"></div></label>`
        : `<label><span>SERVICE OR SCRIPT</span><input ${location} data-action-service-call value="${escapeHtml([action.domain, action.service].filter(Boolean).join("."))}" placeholder="script.dinner_time"></label><label><span>OPTIONAL TARGET ENTITY</span><input ${location} data-action-field="target_id" value="${escapeHtml(action.target_id || "")}" placeholder="Leave empty for direct script calls"></label><label class="command-data"><span>OPTIONAL SERVICE DATA (JSON)</span><input ${location} data-action-json value="${escapeHtml(action.data ? JSON.stringify(action.data) : "")}" placeholder='{"brightness_pct":50}'></label>`;
      return `<div class="quick-command-row">
        <label><span>BEHAVIOR</span><select ${location} data-action-field="type"><option value="call_service" ${behavior === "call_service" ? "selected" : ""}>Call Service or Script</option><option value="toggle" ${behavior === "toggle" ? "selected" : ""}>Toggle Entity</option></select></label>
        <label><span>BUTTON NAME</span><input ${location} data-action-field="name" value="${escapeHtml(action.name || "")}" placeholder="Dinner Time"></label>
        <label><span>ICON</span><input ${location} data-action-field="icon" list="mdi-icon-options" autocomplete="off" value="${escapeHtml(action.icon || "mdi:gesture-tap-button")}" placeholder="mdi:food"></label>
        <label><span>ICON HEIGHT</span><input ${location} data-action-field="icon_height" type="number" min="24" max="120" value="${Number(action.icon_height || 48)}"></label>
        ${behaviorFields}
        <button class="icon danger" title="Remove command" data-action="remove-section-action" data-screen="${screenIndex}" data-section="${sectionIndex}" data-index="${actionIndex}">×</button>
      </div>`;
    }).join("");
    return `<div class="section-block slot-${section.slot} ${section.panel_height === "full_height" ? "panel-full-height" : ""}">
      <div class="slot-heading"><label><span>${escapeHtml(this._slotLabel(section.slot, screen))}</span><input data-section-heading data-screen="${screenIndex}" data-section="${sectionIndex}" value="${escapeHtml(section.title || "")}" placeholder="Quick Commands"></label><label><span>PANEL TYPE</span><select data-section-type data-screen="${screenIndex}" data-section="${sectionIndex}">${SECTION_TYPES.map((type) => `<option value="${type}" ${section.type === type ? "selected" : ""}>${label(type)}</option>`).join("")}</select></label>${this._panelControls(screenIndex, sectionIndex, section, screen.sections.length)}</div>
      <div class="quick-command-list">${commands || `<div class="drop-empty">No command buttons configured.</div>`}</div>
      <button class="quick-command-add" data-action="add-quick-command" data-screen="${screenIndex}" data-section="${sectionIndex}"><ha-icon icon="mdi:plus"></ha-icon>Add Command Button</button>
    </div>`;
  }

  _calendarFormEditor(section, screen, screenIndex, sectionIndex) {
    const location = `data-screen="${screenIndex}" data-section="${sectionIndex}"`;
    const bindings = (section.bindings || []).map((binding, bindingIndex) => this._bindingCard(binding, section, screenIndex, sectionIndex, bindingIndex)).join("");
    const actions = (section.actions || []).map((action, actionIndex) => this._actionEditor(action, screenIndex, sectionIndex, actionIndex)).join("");
    return `<div class="section-block slot-${section.slot} panel-full-height">
      <div class="slot-heading"><label><span>FORM TITLE</span><input data-section-heading ${location} value="${escapeHtml(section.title || "Calendar Form")}"></label><label><span>PANEL TYPE</span><select data-section-type ${location}>${SECTION_TYPES.map((type) => `<option value="${type}" ${section.type === type ? "selected" : ""}>${label(type)}</option>`).join("")}</select></label>${this._panelControls(screenIndex, sectionIndex, section, screen.sections.length)}<button class="region-add" title="Add form field" data-action="open-entity-picker" ${location}>+</button></div>
      ${this._popupSettings(section, screenIndex, sectionIndex, true)}
      <strong class="config-heading">FORM FIELDS</strong><div class="entity-canvas">${bindings || `<div class="drop-empty">Add entities, then assign their HUD roles to define the fields.</div>`}</div>
      <strong class="config-heading">FORM ACTIONS</strong><div class="action-list">${actions || `<div class="drop-empty">Add a submit or reset action.</div>`}</div>
      <button class="quick-command-add" data-action="add-form-action" ${location}><ha-icon icon="mdi:plus"></ha-icon>Add Form Action</button>
    </div>`;
  }

  _popupSettings(section, screenIndex, sectionIndex, expanded = false) {
    const location = `data-screen="${screenIndex}" data-section="${sectionIndex}"`;
    const fields = `<div class="form-config-grid"><label><span>POPUP STYLE</span><select ${location} data-field="popup_style"><option value="standard" ${(section.popup_style || "standard") === "standard" ? "selected" : ""}>Standard</option><option value="projector" ${section.popup_style === "projector" ? "selected" : ""}>Projector</option></select></label><label><span>WIDTH %</span><input type="number" min="30" max="100" ${location} data-field="popup_width" value="${Number(section.popup_width || 58)}"></label><label><span>MAX WIDTH</span><input type="number" min="320" max="1600" ${location} data-field="popup_max_width" value="${Number(section.popup_max_width || 720)}"></label><label><span>MAX HEIGHT</span><input type="number" min="240" max="1200" ${location} data-field="popup_max_height" value="${Number(section.popup_max_height || 580)}"></label><label><span>CONTENT SCALE %</span><input type="number" min="60" max="140" ${location} data-field="content_scale" value="${Number(section.content_scale || 100)}"></label><label><span>PROJECTION COLOR</span><input type="color" ${location} data-field="projection_color" value="${escapeHtml(section.projection_color || "#16d9ff")}"></label><label><span>LIGHT ORIGIN %</span><input type="number" min="0" max="100" ${location} data-field="projection_origin" value="${Number(section.projection_origin ?? 12)}"></label><label><span>LIGHT STRENGTH %</span><input type="number" min="0" max="100" ${location} data-field="projection_strength" value="${Number(section.projection_strength ?? 13)}"></label></div>`;
    return expanded ? fields : `<details class="popup-settings"><summary>Popup presentation</summary>${fields}</details>`;
  }

  _panelControls(screenIndex, sectionIndex, section, panelCount) {
    const fullHeight = section.panel_height === "full_height";
    return `<div class="panel-controls"><button class="icon" title="Move panel earlier" data-action="move-section" data-screen="${screenIndex}" data-index="${sectionIndex}" data-direction="-1" ${sectionIndex === 0 ? "disabled" : ""}><ha-icon icon="mdi:chevron-left"></ha-icon></button><button class="icon" title="Move panel later" data-action="move-section" data-screen="${screenIndex}" data-index="${sectionIndex}" data-direction="1" ${sectionIndex === panelCount - 1 ? "disabled" : ""}><ha-icon icon="mdi:chevron-right"></ha-icon></button><button class="panel-height ${fullHeight ? "selected" : ""}" title="${fullHeight ? "Use standard panel height" : "Make panel full height"}" data-action="toggle-panel-height" data-screen="${screenIndex}" data-section="${sectionIndex}"><ha-icon icon="${fullHeight ? "mdi:arrow-collapse-vertical" : "mdi:arrow-expand-vertical"}"></ha-icon>${fullHeight ? "Full Height" : "Standard"}</button><button class="icon danger" title="Remove panel and its cards" data-action="remove-section" data-screen="${screenIndex}" data-index="${sectionIndex}"><ha-icon icon="mdi:delete-outline"></ha-icon></button></div>`;
  }

  _homeSidebarEditor(section, screenIndex, sectionIndex) {
    const screen = this._draft.screens[screenIndex];
    const pages = this._draft.screens.filter((screen) => screen.screen_id !== "home");
    const entries = (section.actions || []).map((action, actionIndex) => ({ action, actionIndex }))
      .filter(({ action }) => action.type === "navigate")
      .slice(0, 5);
    const destinationSlot = section.slot === "left_menu" ? "right_menu" : "left_menu";
    const rows = entries.map(({ action, actionIndex }, position) => `
      <div class="sidebar-blueprint-row">
        <span class="sidebar-position">${position + 1}</span>
        <select data-screen="${screenIndex}" data-section="${sectionIndex}" data-action-index="${actionIndex}" data-action-field="target_id">
          ${pages.map((page) => `<option value="${escapeHtml(page.screen_id)}" ${page.screen_id === action.target_id ? "selected" : ""}>${escapeHtml(page.title)}</option>`).join("")}
        </select>
        <button class="icon" title="Move up" data-action="move-sidebar-item" data-screen="${screenIndex}" data-section="${sectionIndex}" data-index="${actionIndex}" data-direction="-1" ${position === 0 ? "disabled" : ""}>↑</button>
        <button class="icon" title="Move down" data-action="move-sidebar-item" data-screen="${screenIndex}" data-section="${sectionIndex}" data-index="${actionIndex}" data-direction="1" ${position === entries.length - 1 ? "disabled" : ""}>↓</button>
        <button class="icon" title="Move to ${label(destinationSlot)}" data-action="move-sidebar-across" data-screen="${screenIndex}" data-section="${sectionIndex}" data-index="${actionIndex}" data-destination="${destinationSlot}">${section.slot === "left_menu" ? "→" : "←"}</button>
        <button class="icon danger" title="Remove sidebar item" data-action="remove-sidebar-item" data-screen="${screenIndex}" data-section="${sectionIndex}" data-index="${actionIndex}">×</button>
      </div>`).join("");
    return `
      <div class="section-block slot-${section.slot} home-sidebar-blueprint ${section.panel_height === "full_height" ? "panel-full-height" : ""}">
        <div class="slot-heading"><label><span>${escapeHtml(SLOT_LABELS[section.slot])}</span><select data-section-type data-screen="${screenIndex}" data-section="${sectionIndex}">${SECTION_TYPES.map((type) => `<option value="${type}" ${section.type === type ? "selected" : ""}>${label(type)}</option>`).join("")}</select></label>${this._panelControls(screenIndex, sectionIndex, section, screen.sections.length)}<button class="region-add" title="Add page" data-action="add-sidebar-item" data-screen="${screenIndex}" data-section="${sectionIndex}" ${entries.length >= 5 || pages.length === 0 ? "disabled" : ""}>+</button></div>
        <div class="sidebar-blueprint-list">${rows || `<div class="sidebar-blueprint-empty">No pages assigned to this sidebar</div>`}</div>
      </div>`;
  }

  _bindingCard(binding, section, screenIndex, sectionIndex, bindingIndex) {
    const state = this._hass?.states?.[binding.target_id];
    const name = binding.name || state?.attributes?.friendly_name || binding.target_id;
    const stateText = state ? `${state.state}${state.attributes?.unit_of_measurement ? ` ${state.attributes.unit_of_measurement}` : ""}` : "Unavailable";
    const icon = binding.icon || state?.attributes?.icon || this._defaultIcon(binding.target_id, state?.attributes?.device_class);
    const tapAction = (section.actions || []).find((action) => action.gesture === "tap" && ["more_info", "toggle", "activate"].includes(action.type) && action.target_id === binding.target_id);
    const attributeSummary = (binding.display_attributes || []).map((key) => label(key)).join(" · ");
    return `<div class="entity-card" draggable="true" data-binding-card data-screen="${screenIndex}" data-section="${sectionIndex}" data-binding="${bindingIndex}">
      <div class="drag-handle" title="Drag to reorder or move">⠿</div>
      <ha-icon icon="${escapeHtml(icon)}"></ha-icon>
      <div class="entity-copy"><strong>${escapeHtml(name)}</strong><small>${escapeHtml(stateText)}</small>${(binding.entity_ids || []).length > 1 ? `<small class="attribute-summary">${binding.entity_ids.length} ENTITIES</small>` : attributeSummary ? `<small class="attribute-summary">${escapeHtml(attributeSummary)}</small>` : ""}</div>
      <span class="tap-mode">${tapAction ? label(tapAction.type) : "NO TAP"}</span>
      <button class="card-settings" title="Edit card" data-action="edit-binding" data-screen="${screenIndex}" data-section="${sectionIndex}" data-binding="${bindingIndex}"><ha-icon icon="mdi:cog-outline"></ha-icon></button>
    </div>`;
  }

  _renderEditorDialog() {
    const dialog = this._editorDialog;
    if (!dialog) return "";
    const section = this._draft.screens[dialog.screen].sections[dialog.section];
    if (dialog.type === "add") {
      const entities = Object.entries(this._hass?.states || {})
        .filter(([entityId]) => !dialog.domain || entityId.startsWith(`${dialog.domain}.`))
        .sort(([, left], [, right]) => {
        const leftName = left.attributes?.friendly_name || left.entity_id;
        const rightName = right.attributes?.friendly_name || right.entity_id;
        return leftName.localeCompare(rightName);
      });
      const options = entities.map(([entityId, state]) => {
        const name = state.attributes?.friendly_name || entityId;
        const domain = entityId.split(".", 1)[0];
        const icon = state.attributes?.icon || this._defaultIcon(entityId, state.attributes?.device_class);
        const search = `${name} ${entityId} ${domain}`.toLowerCase();
        const selected = (section.bindings || []).some((binding) => binding.kind === "entity" && binding.target_id === entityId);
        return `<button class="entity-picker-option ${selected ? "selected" : ""}" data-action="toggle-picker-entity" data-screen="${dialog.screen}" data-section="${dialog.section}" data-entity-id="${escapeHtml(entityId)}" data-entity-search-value="${escapeHtml(search)}"><ha-icon icon="${selected ? "mdi:checkbox-marked" : escapeHtml(icon)}"></ha-icon><span><strong>${escapeHtml(name)}</strong><small>${escapeHtml(entityId)}</small></span><em>${selected ? "SELECTED" : escapeHtml(state.state)}</em></button>`;
      }).join("");
      return `<div class="editor-modal" data-action="close-editor-dialog"><div class="editor-modal-card" data-dialog-card><header><div><p class="eyebrow">SELECT CARDS</p><h2>${escapeHtml(dialog.domain ? label(dialog.domain) : SLOT_LABELS[section.slot] || label(section.slot))}</h2></div><button data-action="close-editor-dialog" title="Close">×</button></header><p class="dialog-copy">Select one or more Home Assistant entities for this panel.</p><div class="entity-picker-search"><ha-icon icon="mdi:magnify"></ha-icon><input data-entity-search autocomplete="off" autofocus placeholder="Search entities"></div><div class="entity-picker-summary" data-entity-picker-count>${entities.length} entities</div><div class="entity-picker-list">${options}</div><p class="entity-picker-empty" data-entity-picker-empty hidden>No matching entities</p><button class="primary picker-done" data-action="close-editor-dialog">Done</button></div></div>`;
    }
    const binding = section.bindings[dialog.binding];
    const state = this._hass?.states?.[binding.target_id];
    const name = state?.attributes?.friendly_name || binding.target_id;
    const icon = binding.icon || state?.attributes?.icon || this._defaultIcon(binding.target_id, state?.attributes?.device_class);
    const tapMode = (section.actions || []).find((action) => action.gesture === "tap" && ["more_info", "toggle", "activate"].includes(action.type) && action.target_id === binding.target_id)?.type || "none";
    const graphType = binding.graph_type || "auto";
    const role = binding.role || "none";
    const hiddenAttributes = new Set(["attribution", "device_class", "friendly_name", "icon", "supported_features"]);
    const domain = binding.target_id.split(".", 1)[0];
    const syntheticAttributes = domain === "climate" ? ["climate_operation", "climate_current"] : [];
    const attributeKeys = [...syntheticAttributes, "state", "last_updated", ...Object.entries(state?.attributes || {}).filter(([key, value]) => !hiddenAttributes.has(key) && !key.endsWith("_unit") && ["string", "number", "boolean"].includes(typeof value)).map(([key]) => key)];
    const selectedAttributes = new Set(binding.display_attributes || []);
    const attributeOptions = attributeKeys.map((key) => `<label class="attribute-option"><input type="checkbox" data-binding-attribute="${escapeHtml(key)}" data-screen="${dialog.screen}" data-section="${dialog.section}" data-binding="${dialog.binding}" ${selectedAttributes.has(key) ? "checked" : ""}><span>${escapeHtml(label(key))}</span><small>${escapeHtml(key === "state" ? state?.state || "unknown" : key === "last_updated" ? "Relative update time" : key === "climate_operation" ? "Action, mode, preset and target" : key === "climate_current" ? "Current temperature and humidity" : String(state?.attributes?.[key] ?? ""))}</small></label>`).join("");
    return `<div class="editor-modal" data-action="close-editor-dialog"><div class="editor-modal-card" data-dialog-card><header><div class="dialog-title"><ha-icon icon="${escapeHtml(icon)}"></ha-icon><div><p class="eyebrow">EDIT CARD</p><h2>${escapeHtml(binding.name || name)}</h2></div></div><button data-action="close-editor-dialog" title="Close">×</button></header><div class="dialog-fields"><label>DISPLAY NAME<input data-binding-name data-screen="${dialog.screen}" data-section="${dialog.section}" data-binding="${dialog.binding}" value="${escapeHtml(binding.name || "")}" placeholder="${escapeHtml(name)}" maxlength="100"></label><label>ICON OVERRIDE<button class="icon-picker-button" data-action="open-icon-browser" data-screen="${dialog.screen}" data-section="${dialog.section}" data-binding="${dialog.binding}"><ha-icon icon="${escapeHtml(binding.icon || state?.attributes?.icon || icon)}"></ha-icon><span>${escapeHtml(binding.icon || "Choose an MDI icon")}</span><ha-icon icon="mdi:magnify"></ha-icon></button></label><label>HUD ROLE<select data-binding-role data-screen="${dialog.screen}" data-section="${dialog.section}" data-binding="${dialog.binding}">${BINDING_ROLES.map((value) => `<option value="${value}" ${role === value ? "selected" : ""}>${label(value)}</option>`).join("")}</select></label><label>WHEN TAPPED<select data-binding-tap-mode data-screen="${dialog.screen}" data-section="${dialog.section}" data-binding="${dialog.binding}"><option value="none" ${tapMode === "none" ? "selected" : ""}>No action</option><option value="more_info" ${tapMode === "more_info" ? "selected" : ""}>Open controls</option><option value="toggle" ${tapMode === "toggle" ? "selected" : ""}>Toggle / run</option><option value="activate" ${tapMode === "activate" ? "selected" : ""}>Activate</option></select></label><label>GRAPH STYLE<select data-binding-graph-type data-screen="${dialog.screen}" data-section="${dialog.section}" data-binding="${dialog.binding}"><option value="auto" ${graphType === "auto" ? "selected" : ""}>Automatic</option><option value="line" ${graphType === "line" ? "selected" : ""}>Line</option><option value="bars" ${graphType === "bars" ? "selected" : ""}>Bars</option><option value="gauge" ${graphType === "gauge" ? "selected" : ""}>Gauge</option><option value="none" ${graphType === "none" ? "selected" : ""}>None</option></select></label></div><section class="attribute-picker"><h3>DASHBOARD DETAILS</h3><p>Select up to 20 state attributes to show on the native card.</p><div class="attribute-options">${attributeOptions}</div></section><footer><button class="danger" data-action="remove-binding" data-screen="${dialog.screen}" data-section="${dialog.section}" data-binding="${dialog.binding}">Remove Card</button><button class="primary" data-action="close-editor-dialog">Done</button></footer></div></div>`;
  }

  _iconBrowserResults(query = "") {
    const normalized = query.trim().toLowerCase().replaceAll(" ", "-");
    const matches = normalized ? this._mdiIcons.filter((icon) => icon.includes(normalized)) : this._mdiIcons;
    return { matches, visible: matches.slice(0, 240) };
  }

  _iconBrowserOptions(query = "") {
    const { matches, visible } = this._iconBrowserResults(query);
    return {
      count: matches.length,
      html: visible.map((icon) => `<button class="mdi-icon-option" data-action="select-mdi-icon" data-icon="${escapeHtml(icon)}" title="${escapeHtml(icon)}"><ha-icon icon="${escapeHtml(icon)}"></ha-icon><span>${escapeHtml(icon.replace(/^mdi:/, ""))}</span></button>`).join(""),
    };
  }

  _renderIconBrowser() {
    if (!this._iconBrowser) return "";
    const options = this._iconBrowserOptions();
    return `<div class="editor-modal icon-browser-modal"><div class="editor-modal-card icon-browser-card"><header><div><p class="eyebrow">MATERIAL DESIGN ICONS</p><h2>Choose an icon</h2></div><button data-action="close-icon-browser" title="Close">×</button></header><div class="icon-browser-search"><ha-icon icon="mdi:magnify"></ha-icon><input data-icon-search autofocus autocomplete="off" placeholder="Search ${this._mdiIcons.length.toLocaleString()} icons"></div><div class="icon-browser-count" data-icon-browser-count>${options.count.toLocaleString()} icons</div><div class="mdi-icon-grid" data-icon-browser-results>${options.html}</div></div></div>`;
  }

  async _loadMdiIcons() {
    if (this._mdiIcons.length) return;
    const loader = document.createElement("ha-icon-picker");
    loader.hidden = true;
    this.shadowRoot.append(loader);
    await loader.updateComplete;
    for (let attempt = 0; attempt < 20 && !(loader._getIconPickerItems?.()?.length); attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
    this._mdiIcons = (loader._getIconPickerItems?.() || []).map((item) => item.id).filter((icon) => icon.startsWith("mdi:"));
    loader.remove();
  }

  _defaultIcon(entityId, deviceClass) {
    const domain = String(entityId).split(".", 1)[0];
    if (domain === "camera") return "mdi:cctv";
    if (domain === "climate") return "mdi:thermostat";
    if (domain === "cover") return "mdi:window-shutter";
    if (domain === "fan") return "mdi:fan";
    if (domain === "light") return "mdi:lightbulb";
    if (domain === "lock") return "mdi:lock";
    if (domain === "media_player") return "mdi:cast";
    if (domain === "switch") return "mdi:toggle-switch";
    if (domain === "vacuum") return "mdi:robot-vacuum";
    if (domain === "sensor" && deviceClass === "temperature") return "mdi:thermometer";
    if (domain === "sensor" && deviceClass === "humidity") return "mdi:water-percent";
    return "mdi:circle-outline";
  }

  _actionEditor(action, screenIndex, sectionIndex, actionIndex) {
    const location = `data-screen="${screenIndex}" data-section="${sectionIndex}" data-action-index="${actionIndex}"`;
    const target = action.type === "navigate"
      ? `<select ${location} data-action-field="target_id">${this._draft.screens.map((screen) => `<option value="${screen.screen_id}" ${screen.screen_id === action.target_id ? "selected" : ""}>${escapeHtml(screen.title)}</option>`).join("")}</select>`
      : action.type === "call_service"
        ? `<input ${location} data-action-field="target_id" value="${escapeHtml(action.target_id || "")}" placeholder="Optional entity ID"><input ${location} data-action-field="domain" value="${escapeHtml(action.domain || "")}" placeholder="Domain"><input ${location} data-action-field="service" value="${escapeHtml(action.service || "")}" placeholder="Service">`
        : `<div data-action-entity-selector="${screenIndex}-${sectionIndex}-${actionIndex}"></div>`;
    return `<div class="action-row"><select ${location} data-action-field="role"><option value="form_submit" ${action.role === "form_submit" ? "selected" : ""}>Submit Form</option><option value="form_reset" ${action.role === "form_reset" ? "selected" : ""}>Reset Form</option><option value="none" ${!action.role ? "selected" : ""}>No Role</option></select><select ${location} data-action-field="gesture"><option value="tap" ${action.gesture === "tap" ? "selected" : ""}>Tap</option><option value="hold" ${action.gesture === "hold" ? "selected" : ""}>Hold</option></select><select ${location} data-action-field="type">${ACTION_TYPES.map((type) => `<option value="${type}" ${type === action.type ? "selected" : ""}>${label(type)}</option>`).join("")}</select><input ${location} data-action-field="name" value="${escapeHtml(action.name || "")}" placeholder="Button name"><div class="action-target">${target}</div><button class="icon danger" title="Remove action" data-action="remove-section-action" data-screen="${screenIndex}" data-section="${sectionIndex}" data-index="${actionIndex}">×</button></div>`;
  }

  _displayAssignments(displays, profiles) {
    if (!displays.length) return `<div class="assignments"><h2>Displays</h2><p>No Butler displays registered yet.</p></div>`;
    return `<div class="assignments"><h2>Displays</h2>${displays.map((display) => {
      const assigned = this._snapshot.assignments?.[display.display_id] || "default";
      const theme = this._snapshot.display_themes?.[display.display_id] || "butler_neon";
      return `<div class="display"><span><strong>${escapeHtml(display.name)}</strong><small>${escapeHtml(display.model)} / ${escapeHtml(display.viewport_class)}</small><small>${escapeHtml(display.display_id)}</small></span><label>Dashboard<select data-display-profile="${escapeHtml(display.display_id)}">${profiles.map((profile) => `<option value="${escapeHtml(profile.profile_id)}" ${profile.profile_id === assigned ? "selected" : ""}>${escapeHtml(profile.name)}</option>`).join("")}</select></label><label>Theme<select data-display-theme="${escapeHtml(display.display_id)}"><option value="butler_neon" ${theme === "butler_neon" ? "selected" : ""}>Butler Neon</option><option value="holographic_interface" ${theme === "holographic_interface" ? "selected" : ""}>Holographic Interface</option></select></label><button class="icon danger" title="Delete display" data-action="delete-display" data-display-id="${escapeHtml(display.display_id)}" data-display-name="${escapeHtml(display.name)}"><ha-icon icon="mdi:delete-outline"></ha-icon></button></div>`;
    }).join("")}</div>`;
  }

  _preview() {
    const screen = this._draft.screens.find((item) => item.screen_id === this._draft.default_screen_id) || this._draft.screens[0];
    return `<section class="preview"><div><p class="eyebrow">LIVE STRUCTURE</p><h2>${escapeHtml(screen.title)}</h2></div><div class="preview-stage ${screen.composition}">${screen.sections.map((section) => `<div class="preview-slot slot-${section.slot}"><span>${label(section.slot)}</span><strong>${label(section.type)}</strong><small>${section.bindings?.length || 0} bindings</small></div>`).join("")}</div></section>`;
  }

  _updateSelectors() {
    if (!this._hass || !this._draft || !this.shadowRoot) return;
    if (this._editorDialog?.type === "edit" && !this.shadowRoot.querySelector("[data-binding-entities-selector]")) {
      const host = document.createElement("div");
      host.dataset.bindingEntitiesSelector = `${this._editorDialog.screen}-${this._editorDialog.section}-${this._editorDialog.binding}`;
      const field = document.createElement("label");
      field.append("ADDITIONAL ENTITIES", host);
      this.shadowRoot.querySelector(".dialog-fields")?.append(field);
    }
    this.shadowRoot.querySelectorAll(".icon-picker-button").forEach((button) => {
      const input = document.createElement("input");
      input.dataset.bindingIcon = "";
      input.dataset.screen = button.dataset.screen;
      input.dataset.section = button.dataset.section;
      input.dataset.binding = button.dataset.binding;
      input.setAttribute("list", "mdi-icon-options");
      input.setAttribute("autocomplete", "off");
      input.setAttribute("placeholder", "mdi:autofill");
      input.value = this._bindingAt(button).icon || "";
      button.replaceWith(input);
    });
    this.shadowRoot.querySelectorAll("[data-entity-selector]").forEach((host) => {
      if (host.firstElementChild) {
        host.firstElementChild.hass = this._hass;
        return;
      }
      const [screenIndex, sectionIndex] = host.dataset.entitySelector.split("-").map(Number);
      const section = this._draft.screens[screenIndex].sections[sectionIndex];
      const selector = document.createElement("ha-selector");
      selector.hass = this._hass;
      selector.selector = { entity: { multiple: true } };
      selector.value = (section.bindings || []).filter((binding) => binding.kind === "entity").map((binding) => binding.target_id);
      selector.addEventListener("value-changed", (event) => {
        const nonEntities = (section.bindings || []).filter((binding) => binding.kind !== "entity");
        const values = Array.isArray(event.detail.value) ? event.detail.value : [event.detail.value].filter(Boolean);
        const existing = new Map((section.bindings || []).filter((binding) => binding.kind === "entity").map((binding) => [binding.target_id, binding]));
        section.bindings = [...nonEntities, ...values.map((target_id) => existing.get(target_id) || ({ kind: "entity", target_id }))];
        this._syncDefaultPopupActions(section, values);
        this._render();
      });
      host.append(selector);
    });
    this.shadowRoot.querySelectorAll("[data-action-entity-selector]").forEach((host) => {
      if (host.firstElementChild) return;
      const [screenIndex, sectionIndex, actionIndex] = host.dataset.actionEntitySelector.split("-").map(Number);
      const action = this._draft.screens[screenIndex].sections[sectionIndex].actions[actionIndex];
      const selector = document.createElement("ha-selector");
      selector.hass = this._hass;
      selector.selector = { entity: {} };
      selector.value = action.target_id || "";
      selector.addEventListener("value-changed", (event) => { action.target_id = event.detail.value; });
      host.append(selector);
    });
    this.shadowRoot.querySelectorAll("[data-binding-entities-selector]").forEach((host) => {
      if (host.firstElementChild) return;
      const [screenIndex, sectionIndex, bindingIndex] = host.dataset.bindingEntitiesSelector.split("-").map(Number);
      const binding = this._draft.screens[screenIndex].sections[sectionIndex].bindings[bindingIndex];
      const selector = document.createElement("ha-selector");
      selector.hass = this._hass;
      selector.selector = { entity: { multiple: true } };
      selector.value = (binding.entity_ids || []).filter((entityId) => entityId !== binding.target_id);
      selector.addEventListener("value-changed", (event) => {
        const selected = Array.isArray(event.detail.value) ? event.detail.value : [event.detail.value].filter(Boolean);
        const related = selected.filter((entityId) => entityId !== binding.target_id);
        if (related.length) binding.entity_ids = [binding.target_id, ...new Set(related)]; else delete binding.entity_ids;
      });
      host.append(selector);
    });
  }

  async _onClick(event) {
    const button = event.composedPath().find((element) => element?.dataset?.action)
      || event.target.closest?.("[data-action]");
    if (!button || button.disabled) return;
    const action = button.dataset.action;
    if (action === "toggle-live") {
      await this._hass.callService("homeassistant", "toggle", { entity_id: button.dataset.entityId });
      return;
    }
    if (action === "import-lovelace") {
      await this._importLovelace();
      return;
    }
    if (action === "delete-display") {
      await this._deleteDisplay(button.dataset.displayId, button.dataset.displayName);
      return;
    }
    if (action === "import" || action === "export" || action === "new" || action === "duplicate" || action === "save" || action === "delete-profile") {
      await this[`_${action.replace("-profile", "Profile")}`]?.();
      return;
    }
    if (action === "select-profile-button") {
      this._selectProfile(button.dataset.profileId);
      return;
    }
    if (action === "select-workspace") {
      this._activeWorkspace = button.dataset.workspace;
      this._render();
      return;
    }
    if (!this._draft) return;
    const structuralHomeActions = new Set(["select-layout", "remove-screen", "move-screen"]);
    const targetScreen = this._draft.screens[Number(button.dataset.screen ?? button.dataset.index)];
    if (structuralHomeActions.has(action) && targetScreen?.screen_id === "home") return;
    if (action === "add-screen") this._addScreen();
    if (action === "add-sidebar-item") this._addSidebarItem(Number(button.dataset.screen), Number(button.dataset.section));
    if (action === "remove-sidebar-item") this._draft.screens[Number(button.dataset.screen)].sections[Number(button.dataset.section)].actions.splice(Number(button.dataset.index), 1);
    if (action === "move-sidebar-item") this._moveSidebarItem(Number(button.dataset.screen), Number(button.dataset.section), Number(button.dataset.index), Number(button.dataset.direction));
    if (action === "move-sidebar-across") this._moveSidebarAcross(Number(button.dataset.screen), Number(button.dataset.section), Number(button.dataset.index), button.dataset.destination);
    if (action === "select-screen") {
      this._activeScreenId = button.dataset.screenId;
      this._activeSectionSlot = null;
    }
    if (action === "select-panel") this._activeSectionSlot = button.dataset.panelSlot;
    if (action === "select-layout") this._applyComposition(Number(button.dataset.screen), button.dataset.composition);
    if (action === "remove-screen") this._removeScreen(Number(button.dataset.index));
    if (action === "move-screen") this._move(this._draft.screens, Number(button.dataset.index), Number(button.dataset.direction));
    if (action === "add-section") this._addSection(Number(button.dataset.screen), button.dataset.slot);
    if (action === "remove-section") this._draft.screens[Number(button.dataset.screen)].sections.splice(Number(button.dataset.index), 1);
    if (action === "toggle-panel-height") {
      const section = this._draft.screens[Number(button.dataset.screen)].sections[Number(button.dataset.section)];
      if (section.panel_height === "full_height") delete section.panel_height; else section.panel_height = "full_height";
    }
    if (action === "move-section") this._move(this._draft.screens[Number(button.dataset.screen)].sections, Number(button.dataset.index), Number(button.dataset.direction));
    if (action === "add-section-action") this._addSectionAction(Number(button.dataset.screen), Number(button.dataset.section));
    if (action === "add-quick-command") {
      const section = this._draft.screens[Number(button.dataset.screen)].sections[Number(button.dataset.section)];
      const scriptService = Object.keys(this._hass.states || {}).find((entityId) => entityId.startsWith("script."))?.substring(7) || "turn_on";
      section.type = "quick_commands";
      section.actions ||= [];
      section.actions.push({ gesture: "tap", type: "call_service", name: "New Command", icon: "mdi:gesture-tap-button", icon_height: 48, domain: "script", service: scriptService });
    }
    if (action === "add-form-action") {
      const section = this._draft.screens[Number(button.dataset.screen)].sections[Number(button.dataset.section)];
      section.actions ||= [];
      section.actions.push({ gesture: "tap", type: "call_service", role: section.actions.some((item) => item.role === "form_submit") ? "form_reset" : "form_submit", name: "Submit", domain: "calendar", service: "create_event" });
    }
    if (action === "remove-section-action") this._draft.screens[Number(button.dataset.screen)].sections[Number(button.dataset.section)].actions.splice(Number(button.dataset.index), 1);
    if (action === "open-entity-picker") this._editorDialog = { type: "add", screen: Number(button.dataset.screen), section: Number(button.dataset.section), domain: button.dataset.entityDomain || null };
    if (action === "toggle-picker-entity") this._togglePickerEntity(button);
    if (action === "edit-binding") this._editorDialog = { type: "edit", screen: Number(button.dataset.screen), section: Number(button.dataset.section), binding: Number(button.dataset.binding) };
    if (action === "close-editor-dialog") {
      if (button.classList.contains("editor-modal") && event.target.closest("[data-dialog-card]")) return;
      this._editorDialog = null;
    }
    if (action === "remove-binding") {
      this._removeBinding(Number(button.dataset.screen), Number(button.dataset.section), Number(button.dataset.binding));
      this._editorDialog = null;
    }
    this._render();
  }

  _onPointerDown(event) {
    if (event.button !== 0) return;
    const button = event.composedPath().find((element) => element?.dataset?.action === "toggle-picker-entity");
    if (!button || button.disabled) return;
    event.preventDefault();
    event.stopPropagation();
    this._togglePickerEntity(button);
    this._render();
  }

  _togglePickerEntity(button) {
    const section = this._draft.screens[Number(button.dataset.screen)].sections[Number(button.dataset.section)];
    const targetId = button.dataset.entityId;
    const existingIds = new Set((section.bindings || []).filter((binding) => binding.kind === "entity").map((binding) => binding.target_id));
    const wasEmpty = existingIds.size === 0;
    if (existingIds.has(targetId)) {
      section.bindings = section.bindings.filter((binding) => binding.kind !== "entity" || binding.target_id !== targetId);
    } else {
      section.bindings = [...(section.bindings || []), { kind: "entity", target_id: targetId }];
    }
    const entityIds = section.bindings.filter((binding) => binding.kind === "entity").map((binding) => binding.target_id);
    if (wasEmpty && section.type === "entity_controls" && entityIds.length) section.type = this._sectionTypeForEntities(entityIds);
    this._syncDefaultPopupActions(section, entityIds);
  }

  _onInput(event) {
    if (event.target.dataset.actionIndex !== undefined
      && (event.target.dataset.actionField !== undefined || event.target.dataset.actionServiceCall !== undefined)) {
      this._updateActionInput(event.target);
      return;
    }
    if (event.target.dataset.sectionSecondaryHeading !== undefined) {
      const section = this._draft.screens[Number(event.target.dataset.screen)].sections[Number(event.target.dataset.section)];
      const heading = event.target.value.trim();
      if (heading) section.secondary_title = heading; else delete section.secondary_title;
      return;
    }
    if (event.target.dataset.sectionHeading !== undefined) {
      const section = this._draft.screens[Number(event.target.dataset.screen)].sections[Number(event.target.dataset.section)];
      const heading = event.target.value.trim();
      if (heading) section.title = heading; else delete section.title;
      return;
    }
    if (event.target.dataset.entitySearch === undefined) return;
    const query = event.target.value.trim().toLowerCase();
    const options = [...this.shadowRoot.querySelectorAll("[data-entity-search-value]")];
    let visible = 0;
    options.forEach((option) => {
      option.hidden = Boolean(query) && !option.dataset.entitySearchValue.includes(query);
      if (!option.hidden) visible += 1;
    });
    this.shadowRoot.querySelector("[data-entity-picker-count]").textContent = `${visible} ${visible === 1 ? "entity" : "entities"}`;
    this.shadowRoot.querySelector("[data-entity-picker-empty]").hidden = visible !== 0;
  }

  _onChange(event) {
    const element = event.target;
    if (element.dataset.action === "select-profile") {
      this._selectProfile(element.value);
      return;
    }
    if (element.dataset.displayProfile) {
      const theme = this._snapshot.display_themes?.[element.dataset.displayProfile] || "butler_neon";
      this._assign(element.dataset.displayProfile, element.value, theme);
      return;
    }
    if (element.dataset.displayTheme) {
      const profileId = this._snapshot.assignments?.[element.dataset.displayTheme] || "default";
      this._assign(element.dataset.displayTheme, profileId, element.value);
      return;
    }
    if (!this._draft) return;
    if (element.dataset.greetingWeather !== undefined) {
      if (element.value) this._draft.greeting_weather_entity_id = element.value;
      else delete this._draft.greeting_weather_entity_id;
      return;
    }
    if (element.dataset.weatherEntity !== undefined) {
      const section = this._draft.screens[Number(element.dataset.screen)].sections[Number(element.dataset.section)];
      const retained = (section.bindings || []).filter((binding) => !binding.target_id?.startsWith("weather.") && binding.role !== "weather_source");
      section.bindings = element.value ? [...retained, { kind: "entity", target_id: element.value, role: "weather_source" }] : retained;
      this._render();
      return;
    }
    if (element.dataset.weatherForecast !== undefined) {
      const section = this._draft.screens[Number(element.dataset.screen)].sections[Number(element.dataset.section)];
      section.forecast_type = element.value;
      return;
    }
    if (element.dataset.bindingName !== undefined) {
      const binding = this._bindingAt(element);
      const name = element.value.trim();
      if (name) binding.name = name; else delete binding.name;
      this._render();
      return;
    }
    if (element.dataset.sectionHeading !== undefined) {
      const section = this._draft.screens[Number(element.dataset.screen)].sections[Number(element.dataset.section)];
      const heading = element.value.trim();
      if (heading) section.title = heading; else delete section.title;
      return;
    }
    if (element.dataset.bindingAttribute !== undefined) {
      const binding = this._bindingAt(element);
      const selected = new Set(binding.display_attributes || []);
      if (element.checked) selected.add(element.dataset.bindingAttribute); else selected.delete(element.dataset.bindingAttribute);
      binding.display_attributes = [...selected].slice(0, 20);
      this._render();
      return;
    }
    if (element.dataset.bindingGraphType !== undefined) {
      const binding = this._bindingAt(element);
      binding.graph_type = element.value;
      return;
    }
    if (element.dataset.bindingRole !== undefined) {
      const binding = this._bindingAt(element);
      if (element.value === "none") delete binding.role; else binding.role = element.value;
      return;
    }
    if (element.dataset.bindingIcon !== undefined) {
      const binding = this._bindingAt(element);
      const icon = element.value.trim();
      if (icon && !icon.startsWith("mdi:")) {
        this._message = "Icons must use the mdi:name format.";
      } else {
        if (icon) binding.icon = icon; else delete binding.icon;
        this._message = "";
      }
      this._render();
      return;
    }
    if (element.dataset.bindingToggle !== undefined) {
      const section = this._draft.screens[Number(element.dataset.screen)].sections[Number(element.dataset.section)];
      const binding = section.bindings[Number(element.dataset.binding)];
      this._setBindingTapAction(section, binding.target_id, element.checked ? "toggle" : "more_info");
      this._render();
      return;
    }
    if (element.dataset.bindingTapMode !== undefined) {
      const section = this._draft.screens[Number(element.dataset.screen)].sections[Number(element.dataset.section)];
      const binding = section.bindings[Number(element.dataset.binding)];
      this._setBindingTapAction(section, binding.target_id, element.value);
      this._render();
      return;
    }
    if (element.dataset.profileField) this._draft[element.dataset.profileField] = element.value;
    if (element.dataset.screen !== undefined && element.dataset.section === undefined) {
      const screen = this._draft.screens[Number(element.dataset.screen)];
      screen[element.dataset.field] = element.value;
      if (element.dataset.field === "composition") {
        const slots = COMPOSITIONS[element.value];
        screen.sections = screen.sections.slice(0, slots.length).map((section, index) => ({ ...section, slot: slots[index] }));
      }
    }
    if (element.dataset.section !== undefined) {
      const section = this._draft.screens[Number(element.dataset.screen)].sections[Number(element.dataset.section)];
      if (element.dataset.sectionType !== undefined) {
        section.type = element.value;
        this._render();
        return;
      }
      if (element.dataset.actionIndex !== undefined) {
        if (element.dataset.actionJson !== undefined) {
          const action = section.actions[Number(element.dataset.actionIndex)];
          try {
            if (element.value.trim()) action.data = JSON.parse(element.value); else delete action.data;
            this._message = "";
          } catch (_) {
            this._message = "Service data must be valid JSON.";
          }
        } else {
          this._updateActionInput(element);
        }
        const action = section.actions[Number(element.dataset.actionIndex)];
        if (element.dataset.actionField === "type") this._resetAction(action, element.value);
      } else {
        section[element.dataset.field] = element.type === "number" ? Number(element.value) : element.value;
      }
    }
    this._render();
  }

  _updateActionInput(element) {
    const section = this._draft.screens[Number(element.dataset.screen)].sections[Number(element.dataset.section)];
    const action = section.actions[Number(element.dataset.actionIndex)];
    if (element.dataset.actionServiceCall !== undefined) {
      const [domain, ...serviceParts] = element.value.trim().split(".");
      action.domain = domain || "";
      action.service = serviceParts.join(".");
    } else if (element.dataset.actionField === "icon_height") {
      action.icon_height = Math.max(24, Math.min(120, Number(element.value) || 48));
    } else if (element.dataset.actionField === "target_id" && !element.value.trim()) {
      delete action.target_id;
    } else if (element.dataset.actionField === "role" && element.value === "none") {
      delete action.role;
    } else {
      action[element.dataset.actionField] = element.value;
    }
  }

  _new() {
    const base = `profile_${Date.now()}`;
    this._draft = { schema_version: 1, profile_id: base, name: "New Profile", default_screen_id: "home", screens: [{ screen_id: "home", title: "Home", composition: "radial_command_overview", sections: [{ section_id: "overview", type: "status_overview", slot: "overview" }] }] };
    this._draft.screens.forEach((screen) => this._ensureScreenSections(screen));
    this._selectedId = null;
    this._message = "New profile is not saved yet.";
    this._render();
  }

  _selectProfile(profileId) {
    const profile = this._snapshot?.profiles?.find((candidate) => candidate.profile_id === profileId);
    if (!profile) return;
    this._selectedId = profileId;
    this._draft = clone(profile);
    this._draft.screens.forEach((screen) => this._ensureScreenSections(screen));
    this._activeScreenId = this._draft.default_screen_id;
    this._editorDialog = null;
    this._message = "";
    this._render();
  }

  _duplicate() {
    const copy = clone(this._draft);
    copy.profile_id = `${copy.profile_id}_copy_${Date.now()}`;
    copy.name = `${copy.name} Copy`;
    this._draft = copy;
    this._selectedId = null;
    this._message = "Duplicated profile is not saved yet.";
    this._render();
  }

  async _save() {
    if (this._saving) return;
    this._draft.name = this._draft.name.trim();
    this._saving = true;
    this._message = "Saving profile...";
    this._render();
    try {
      if (this._selectedId && this._loadedProfile) {
        const latestSnapshot = await this._hass.callWS({ type: "biofects_butler/get_dashboard_profiles" });
        const latest = (latestSnapshot.profiles || []).find((profile) => profile.profile_id === this._selectedId);
        if (latest && JSON.stringify(latest) !== JSON.stringify(this._loadedProfile)) {
          this._snapshot = latestSnapshot;
          this._message = "This profile changed in another Butler tab or display. Reload this page before saving so newer panel settings are not lost.";
          return;
        }
      }
      const result = await this._hass.callWS({ type: "biofects_butler/save_dashboard_profile", profile: this._draft });
      await this._load(result.profile.profile_id);
      this._message = "Profile saved.";
    } catch (error) {
      this._message = error?.message || "Profile validation failed.";
    } finally {
      this._saving = false;
      this._render();
    }
  }

  async _deleteProfile() {
    if (!confirm(`Delete ${this._draft.name}? Displays assigned to it will use the default HUD.`)) return;
    try {
      await this._hass.callWS({ type: "biofects_butler/delete_dashboard_profile", profile_id: this._draft.profile_id });
      this._selectedId = null;
      await this._load();
    } catch (error) {
      this._message = error?.message || "Profile could not be deleted.";
      this._render();
    }
  }

  async _assign(displayId, profileId, theme) {
    try {
      await this._hass.callWS({ type: "biofects_butler/assign_dashboard_profile", display_id: displayId, profile_id: profileId, theme });
      this._snapshot.assignments[displayId] = profileId;
      this._snapshot.display_themes ||= {};
      this._snapshot.display_themes[displayId] = theme;
      this._message = "Display settings saved.";
    } catch (error) {
      this._message = error?.message || "Display assignment failed.";
    }
    this._render();
  }

  async _deleteDisplay(displayId, displayName) {
    if (!confirm(`Delete ${displayName} (${displayId})? It will register again if that device reconnects.`)) return;
    try {
      await this._hass.callWS({ type: "biofects_butler/delete_display", display_id: displayId });
      await this._load(this._selectedId);
      this._message = "Display removed.";
    } catch (error) {
      this._message = error?.message || "Display could not be deleted.";
      this._render();
    }
  }

  _addScreen() {
    const id = `screen_${Date.now()}`;
    const screen = { screen_id: id, title: "New Screen", composition: "focused_control", sections: [] };
    this._draft.screens.push(screen);
    this._seedScreenSections(screen);
    this._activeScreenId = id;
  }

  _removeScreen(index) {
    const screen = this._draft.screens[index];
    if (!screen || screen.screen_id === "home") return;
    if (!confirm(`Delete dashboard ${screen.title}? Save the profile to make this permanent.`)) return;
    const [removed] = this._draft.screens.splice(index, 1);
    if (removed.screen_id === this._draft.default_screen_id) this._draft.default_screen_id = this._draft.screens[0].screen_id;
    if (removed.screen_id === this._activeScreenId) this._activeScreenId = this._draft.screens[0].screen_id;
    this._message = `Dashboard ${removed.title} removed from the draft. Save the profile to apply.`;
  }

  _addSection(screenIndex, requestedSlot) {
    const screen = this._draft.screens[screenIndex];
    const used = new Set(screen.sections.map((section) => section.slot));
    const slotName = COMPOSITIONS[screen.composition].find((candidate) => candidate === requestedSlot && !used.has(candidate));
    if (slotName) screen.sections.push({ section_id: `${slug(slotName)}_${Date.now()}`, type: slotName === "media" ? "media" : slotName === "events" ? "events" : "entity_controls", slot: slotName, bindings: [], actions: [] });
  }

  _addSectionAction(screenIndex, sectionIndex) {
    const section = this._draft.screens[screenIndex].sections[sectionIndex];
    section.actions ||= [];
    const entityId = section.bindings?.find((binding) => binding.kind === "entity")?.target_id
      || Object.keys(this._hass.states || {})[0];
    section.actions.push(entityId
      ? { gesture: "tap", type: "more_info", target_id: entityId }
      : { gesture: "tap", type: "navigate", target_id: this._draft.default_screen_id });
  }

  _ensureHomeSidebarBlueprint(screen) {
    const sidebarSections = ["left_menu", "right_menu"].map((slot) => screen.sections.find((section) => section.slot === slot));
    if (sidebarSections.some((section) => section?.actions?.some((action) => action.type === "navigate"))) return;
    const pages = this._draft.screens.filter((candidate) => candidate.screen_id !== "home");
    pages.slice(0, 10).forEach((page, index) => {
      const section = sidebarSections[index % 2];
      if (!section) return;
      section.actions ||= [];
      section.actions.push({ gesture: "tap", type: "navigate", target_id: page.screen_id });
    });
  }

  _addSidebarItem(screenIndex, sectionIndex) {
    const screen = this._draft.screens[screenIndex];
    const section = screen.sections[sectionIndex];
    const assigned = new Set(screen.sections.filter((candidate) => ["left_menu", "right_menu"].includes(candidate.slot)).flatMap((candidate) => (candidate.actions || []).filter((action) => action.type === "navigate").map((action) => action.target_id)));
    const page = this._draft.screens.find((candidate) => candidate.screen_id !== "home" && !assigned.has(candidate.screen_id));
    if (!page || (section.actions || []).filter((action) => action.type === "navigate").length >= 5) return;
    section.actions ||= [];
    section.actions.push({ gesture: "tap", type: "navigate", target_id: page.screen_id });
  }

  _moveSidebarItem(screenIndex, sectionIndex, actionIndex, direction) {
    const actions = this._draft.screens[screenIndex].sections[sectionIndex].actions;
    const positions = actions.map((action, index) => action.type === "navigate" ? index : -1).filter((index) => index >= 0).slice(0, 5);
    const position = positions.indexOf(actionIndex);
    const destination = positions[position + direction];
    if (position < 0 || destination === undefined) return;
    [actions[actionIndex], actions[destination]] = [actions[destination], actions[actionIndex]];
  }

  _moveSidebarAcross(screenIndex, sectionIndex, actionIndex, destinationSlot) {
    const screen = this._draft.screens[screenIndex];
    const source = screen.sections[sectionIndex];
    const destination = screen.sections.find((section) => section.slot === destinationSlot);
    if (!destination || (destination.actions || []).filter((action) => action.type === "navigate").length >= 5) return;
    const [action] = source.actions.splice(actionIndex, 1);
    if (!action || action.type !== "navigate") return;
    destination.actions ||= [];
    destination.actions.push(action);
  }

  _ensureScreenSections(screen) {
    const slots = COMPOSITIONS[screen.composition] || COMPOSITIONS.focused_control;
    const scriptService = Object.keys(this._hass?.states || {}).find((entityId) => entityId.startsWith("script."))?.substring(7) || "turn_on";
    screen.sections = (screen.sections || [])
      .filter((section) => slots.includes(section.slot))
      .map((section) => {
        const actions = (section.actions || []).map((action) => section.type !== "quick_commands" || ["call_service", "toggle"].includes(action.type)
          ? action
          : {
              gesture: "tap",
              type: "call_service",
              name: action.name,
              icon: action.icon,
              icon_height: action.icon_height,
              domain: "script",
              service: scriptService,
            });
        return { ...section, bindings: section.bindings || [], actions };
      });
  }

  _seedScreenSections(screen) {
    const slots = COMPOSITIONS[screen.composition] || COMPOSITIONS.focused_control;
    screen.sections = slots.map((slot, index) => ({ section_id: `${slug(slot)}_${Date.now()}_${index}`, type: slot === "media" ? "media" : slot === "events" ? "events" : "entity_controls", slot, bindings: [], actions: [] }));
  }

  _applyComposition(screenIndex, composition) {
    const screen = this._draft.screens[screenIndex];
    if (!screen || !COMPOSITIONS[composition] || screen.composition === composition) return;
    const slots = COMPOSITIONS[composition];
    screen.composition = composition;
    screen.sections = screen.sections.slice(0, slots.length).map((section, index) => ({ ...section, slot: slots[index] }));
  }

  _syncDefaultPopupActions(section, entityIds) {
    const validTargets = new Set(entityIds);
    section.actions = (section.actions || []).filter((action) =>
      !["more_info", "toggle", "activate"].includes(action.type) || validTargets.has(action.target_id),
    );
  }

  _bindingAt(element) {
    return this._draft.screens[Number(element.dataset.screen)].sections[Number(element.dataset.section)].bindings[Number(element.dataset.binding)];
  }

  _setBindingTapAction(section, entityId, type) {
    const otherActions = (section.actions || []).filter((action) => action.target_id !== entityId || action.gesture !== "tap" || !["more_info", "toggle", "activate"].includes(action.type));
    section.actions = (type === "none" ? otherActions : [{ gesture: "tap", type, target_id: entityId }, ...otherActions]).slice(0, 20);
  }

  _removeBinding(screenIndex, sectionIndex, bindingIndex) {
    const section = this._draft.screens[screenIndex].sections[sectionIndex];
    const [binding] = section.bindings.splice(bindingIndex, 1);
    if (binding?.kind === "entity") section.actions = (section.actions || []).filter((action) => action.target_id !== binding.target_id);
  }

  _onDragStart(event) {
    const card = event.target.closest("[data-binding-card]");
    if (!card) return;
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("application/x-butler-binding", JSON.stringify({ screen: Number(card.dataset.screen), section: Number(card.dataset.section), binding: Number(card.dataset.binding) }));
    card.classList.add("dragging");
  }

  _onDragOver(event) {
    if (event.target.closest("[data-drop-section]")) {
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
    }
  }

  _onDrop(event) {
    const destination = event.target.closest("[data-drop-section]");
    const encoded = event.dataTransfer.getData("application/x-butler-binding");
    if (!destination || !encoded) return;
    event.preventDefault();
    const source = JSON.parse(encoded);
    const sourceSection = this._draft.screens[source.screen].sections[source.section];
    const sourceBindings = sourceSection.bindings;
    const [binding] = sourceBindings.splice(source.binding, 1);
    const destinationSection = this._draft.screens[Number(destination.dataset.dropScreen)].sections[Number(destination.dataset.dropSection)];
    const targetCard = event.target.closest("[data-binding-card]");
    let destinationIndex = targetCard ? Number(targetCard.dataset.binding) : destinationSection.bindings.length;
    if (destinationSection === this._draft.screens[source.screen].sections[source.section] && source.binding < destinationIndex) destinationIndex -= 1;
    destinationSection.bindings.splice(destinationIndex, 0, binding);
    if (sourceSection !== destinationSection) {
      const tapAction = (sourceSection.actions || []).find((action) => action.target_id === binding.target_id && action.gesture === "tap" && ["more_info", "toggle", "activate"].includes(action.type));
      sourceSection.actions = (sourceSection.actions || []).filter((action) => action !== tapAction);
      this._setBindingTapAction(destinationSection, binding.target_id, tapAction?.type || "none");
    }
    this._render();
  }

  _resetAction(action, type) {
    const gesture = action.gesture || "tap";
    const presentation = Object.fromEntries(["name", "icon", "icon_height", "role"].filter((key) => action[key] !== undefined).map((key) => [key, action[key]]));
    Object.keys(action).forEach((key) => delete action[key]);
    Object.assign(action, presentation);
    action.gesture = gesture;
    action.type = type;
    if (type === "navigate") {
      action.target_id = this._draft.default_screen_id;
    } else if (type === "call_service") {
      action.domain = "homeassistant";
      action.service = "toggle";
    } else if (type === "activate") {
      action.target_id = Object.keys(this._hass.states || {}).find((entityId) => /^(scene|script|automation)\./.test(entityId)) || "scene.none";
    } else {
      action.target_id = Object.keys(this._hass.states || {})[0] || "sensor.none";
    }
  }

  async _importLovelace() {
    const path = this.shadowRoot.querySelector("#lovelace-dashboard")?.value;
    if (!path) return;
    this._message = "Reading Home Assistant dashboard...";
    this._render();
    try {
      const request = { type: "lovelace/config" };
      if (path !== "lovelace") request.url_path = path;
      const config = await this._hass.callWS(request);
      const panel = this._hass.panels?.[path];
      const usedScreenIds = new Set();
      const screens = (config.views || []).slice(0, 20).map((view, index) => {
        let screenId = slug(view.path || view.title || `screen_${index + 1}`) || `screen_${index + 1}`;
        while (usedScreenIds.has(screenId)) screenId = `${screenId}_${index + 1}`;
        usedScreenIds.add(screenId);
        const entityIds = [...this._entitiesFromLovelace(view)].filter((entityId) => this._hass.states?.[entityId]).slice(0, 100);
        const sectionType = this._sectionTypeForEntities(entityIds);
        const section = {
          section_id: `${screenId}_content`,
          type: sectionType,
          slot: index === 0 ? "overview" : "core",
          bindings: entityIds.map((target_id) => ({ kind: "entity", target_id })),
        };
        return {
          screen_id: screenId,
          title: String(view.title || label(screenId)).slice(0, 80),
          composition: index === 0 ? "radial_command_overview" : "focused_control",
          sections: [section],
        };
      });
      if (!screens.length) throw new Error("This dashboard has no views to import.");
      const dashboardName = panel?.title || config.title || label(path);
      this._draft = {
        schema_version: 1,
        profile_id: `ha_${slug(path)}_${Date.now()}`,
        name: `${dashboardName} Butler`.slice(0, 100),
        default_screen_id: screens[0].screen_id,
        screens,
      };
      this._draft.screens.forEach((screen) => {
        this._ensureScreenSections(screen);
        screen.sections.forEach((section) => {
          const entityIds = section.bindings.filter((binding) => binding.kind === "entity").map((binding) => binding.target_id);
          this._syncDefaultPopupActions(section, entityIds);
        });
      });
      this._selectedId = null;
      const mappedEntities = screens.reduce((total, screen) => total + screen.sections[0].bindings.length, 0);
      const emptyViews = screens.filter((screen) => screen.sections[0].bindings.length === 0).length;
      this._message = `Created an unsaved draft from ${dashboardName}: ${mappedEntities} entities mapped${emptyViews ? `, ${emptyViews} view${emptyViews === 1 ? "" : "s"} need manual bindings` : ""}. Review actions, then save.`;
    } catch (error) {
      this._message = error?.message || "Home Assistant dashboard could not be imported.";
    }
    this._render();
  }

  _entitiesFromLovelace(value, found = new Set()) {
    if (Array.isArray(value)) {
      value.forEach((item) => this._entitiesFromLovelace(item, found));
    } else if (value && typeof value === "object") {
      Object.entries(value).forEach(([key, item]) => {
        if ((key === "entity" || key === "entity_id") && typeof item === "string" && /^[a-z0-9_]+\.[a-z0-9_]+$/.test(item)) found.add(item);
        if (key === "entities" && Array.isArray(item)) item.forEach((entity) => {
          const entityId = typeof entity === "string" ? entity : entity?.entity;
          if (typeof entityId === "string" && /^[a-z0-9_]+\.[a-z0-9_]+$/.test(entityId)) found.add(entityId);
        });
        this._entitiesFromLovelace(item, found);
      });
    }
    return found;
  }

  _sectionTypeForEntities(entityIds) {
    const domains = new Set(entityIds.map((entityId) => entityId.split(".", 1)[0]));
    if (domains.has("camera")) return "cameras";
    if (domains.has("calendar")) return "events";
    if (domains.has("climate")) return "climate";
    if (domains.has("alarm_control_panel") || domains.has("lock")) return "security";
    if (domains.has("media_player")) return "media";
    if (domains.has("weather")) return "weather";
    return "entity_controls";
  }

  _move(items, index, direction) {
    const destination = index + direction;
    if (destination < 0 || destination >= items.length) return;
    [items[index], items[destination]] = [items[destination], items[index]];
  }

  _export() {
    const blob = new Blob([JSON.stringify(this._draft, null, 2)], { type: "application/json" });
    const anchor = document.createElement("a");
    anchor.href = URL.createObjectURL(blob);
    anchor.download = `${this._draft.profile_id}.json`;
    anchor.click();
    URL.revokeObjectURL(anchor.href);
  }

  _import() {
    this.shadowRoot.querySelector("#import-file").click();
  }

  _wireImport() {
    this.shadowRoot.querySelector("#import-file")?.addEventListener("change", async (event) => {
      const file = event.target.files?.[0];
      if (!file) return;
      try {
        this._draft = JSON.parse(await file.text());
        this._selectedId = null;
        this._message = "Imported profile is not saved yet.";
      } catch {
        this._message = "Import is not valid JSON.";
      }
      this._render();
    });
  }

  _styles() {
    return `
      .backend-row{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:8px 0;border-bottom:1px solid #143c42}.backend-row span strong,.backend-row span small{display:block}.backend-row span strong{font-size:9px}.backend-row span small{margin-top:2px;color:var(--muted);font-size:7px}.backend-configure{padding:6px 8px;border:1px solid var(--cyan);color:var(--cyan);font-size:8px;text-decoration:none}.entity-picker-option.selected{border-color:var(--cyan);background:#0b2a2f;color:var(--cyan)}.picker-done{display:block;width:calc(100% - 32px);margin:12px 16px 16px}
      .form-config-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:7px;margin:8px 0 12px;padding:9px;border:1px solid #17434a;background:#061014}.form-config-grid label{min-width:0;margin:0}.form-config-grid label span{display:block;margin-bottom:4px;color:var(--muted);font-size:7px}.form-config-grid input,.form-config-grid select{min-height:30px;padding:5px;font-size:8px}.form-config-grid input[type=color]{padding:2px}.config-heading{display:block;margin:9px 0 6px;color:var(--cyan);font-size:8px}.popup-settings{margin:0 0 8px}.popup-settings summary{cursor:pointer;color:var(--muted);font-size:8px}.action-list{display:grid;gap:7px}.calendar-form .action-row{grid-template-columns:110px 80px 110px minmax(100px,1fr) minmax(220px,2fr) 38px}
      .quick-command-list{display:grid;gap:10px;overflow:auto}.quick-command-row{position:relative;display:grid;grid-template-columns:1fr;gap:8px;padding:10px 42px 10px 10px;border:1px solid #245c63;background:#0a1d22}.quick-command-row label{min-width:0;margin:0}.quick-command-row label span{display:block;margin-bottom:4px;color:var(--muted);font-size:7px}.quick-command-row input{min-width:0;min-height:32px;padding:6px;font-size:9px}.quick-command-row>.danger{position:absolute;top:10px;right:8px;width:28px;min-height:28px;padding:0}.quick-command-add{display:flex;align-items:center;justify-content:center;gap:6px;width:100%;margin-top:9px;min-height:34px;color:var(--cyan)}.quick-command-add ha-icon{--mdc-icon-size:16px}
      .icon-picker-button{display:grid;grid-template-columns:26px minmax(0,1fr) 22px;align-items:center;gap:8px;width:100%;text-align:left}.icon-picker-button ha-icon{color:var(--cyan)}.icon-picker-button span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.icon-browser-modal{z-index:1100}.icon-browser-card{width:min(780px,100%)}.icon-browser-search{display:grid;grid-template-columns:24px minmax(0,1fr);align-items:center;gap:8px;margin:14px 16px 6px;padding:0 10px;border:1px solid var(--line);background:#061014}.icon-browser-search ha-icon{color:var(--cyan)}.icon-browser-search input{border:0;background:transparent}.icon-browser-count{padding:4px 16px 10px;color:var(--muted);font-size:9px}.mdi-icon-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(105px,1fr));gap:6px;max-height:55vh;overflow:auto;padding:0 16px 16px}.mdi-icon-option{display:grid;place-items:center;align-content:center;gap:6px;min-height:78px;padding:7px}.mdi-icon-option ha-icon{color:var(--cyan);--mdc-icon-size:28px}.mdi-icon-option span{width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--muted);font-size:8px;text-align:center}
      .home-sidebar-blueprint .slot-heading>span strong,.home-sidebar-blueprint .slot-heading>span small{display:block}.home-sidebar-blueprint .slot-heading>span small{margin-top:2px;color:var(--muted);font-size:7px}.sidebar-blueprint-list{display:grid;gap:7px}.sidebar-blueprint-row{display:grid;grid-template-columns:24px minmax(100px,1fr) repeat(4,30px);gap:5px;align-items:center;padding:6px;border:1px solid #245c63;background:#0a1d22}.sidebar-position{display:grid;place-items:center;min-height:30px;border:1px solid #267680;color:var(--cyan);font-size:9px}.sidebar-blueprint-row select{min-height:30px;padding:4px;font-size:9px}.sidebar-blueprint-row button{width:30px;min-height:30px;padding:0}.sidebar-blueprint-empty{display:grid;place-items:center;min-height:82px;border:1px dashed #28626a;color:var(--muted);font-size:9px;text-align:center}
      :host{display:block;min-height:100vh;container-type:inline-size;background:#050b0e;color:#d8f7f7;font-family:"Share Tech Mono","IBM Plex Mono",monospace;--cyan:#45e8e8;--line:#1d6870;--panel:#0a1519;--muted:#77999d}*{box-sizing:border-box}main{min-height:100vh;background-image:linear-gradient(rgba(69,232,232,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(69,232,232,.035) 1px,transparent 1px);background-size:42px 42px;padding:28px}header{display:flex;align-items:end;justify-content:space-between;border-bottom:1px solid var(--line);padding-bottom:16px;margin-bottom:18px}h1,h2,p{margin:0}h1{font-size:28px;font-weight:400;color:var(--cyan)}h2{font-size:13px;color:var(--cyan);margin:22px 0 10px}.eyebrow,label{display:block;color:var(--muted);font-size:10px;margin-bottom:6px}.workspace{display:grid;grid-template-columns:260px minmax(0,1fr);gap:18px}aside,.screen-card,.preview{background:rgba(10,21,25,.94);border:1px solid var(--line);padding:16px}select,input,button{font:inherit;color:#d8f7f7;background:#081115;border:1px solid var(--line);min-height:38px;padding:8px}select,input{width:100%}button{cursor:pointer}button:hover:not(:disabled){border-color:var(--cyan);color:var(--cyan)}button:disabled{opacity:.35;cursor:not-allowed}.primary{background:var(--cyan);color:#021012;border-color:var(--cyan)}.danger{color:#ff8181}.header-actions,.button-row,.profile-bar,.screen-head,.section-row{display:flex;gap:8px;align-items:end}.button-row{margin-top:8px}.button-row>*{flex:1}.notice{padding:10px 14px;border-left:3px solid var(--cyan);background:#0b1d21;margin-bottom:16px}.profile-bar{padding:14px;background:#071014;border:1px solid var(--line);margin-bottom:14px}.field{min-width:150px}.grow,.bindings{flex:1}.screen-card{margin-bottom:12px}.screen-head{padding-bottom:12px;border-bottom:1px solid #143c42}.index{font-size:22px;color:var(--cyan);align-self:center}.section-list{display:grid;gap:8px;margin:12px 0}.section-row{background:#071115;border-left:2px solid var(--cyan);padding:10px}.trace{width:14px;height:1px;background:var(--cyan);box-shadow:0 0 8px var(--cyan)}.icon{min-width:38px}.add{width:100%;border-style:dashed}.add.compact{width:auto}.action-count,small{font-size:10px;color:var(--muted)}.assignments p{color:var(--muted);font-size:11px}.display{display:grid;gap:8px;margin-bottom:12px}.display span{display:flex;flex-direction:column}.preview{margin-top:18px}.preview-stage{height:360px;margin-top:14px;padding:10px;display:grid;gap:8px;border:1px solid var(--line);background:#03090b}.preview-stage.radial_command_overview{grid-template-columns:1fr 1fr 1.6fr 1fr 1fr;grid-template-rows:1fr;grid-template-areas:"overview left_menu reactor right_menu media_events"}.preview-stage.security_camera_board{grid-template-columns:1fr 1.8fr 1fr;grid-template-rows:1fr 1fr;grid-template-areas:"status camera_primary controls" "events camera_grid controls"}.preview-stage.focused_control{grid-template-columns:1fr 1.7fr 1fr;grid-template-rows:1fr auto;grid-template-areas:"left_instrument core right_instrument" "footer footer footer"}.preview-slot{border:1px solid #267680;background:rgba(24,72,78,.35);display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;min-width:0}.preview-slot span,.preview-slot small{font-size:9px;color:var(--muted)}.preview-slot strong{color:var(--cyan);font-size:11px;margin:5px}.slot-overview{grid-area:overview}.slot-left_menu{grid-area:left_menu}.slot-reactor{grid-area:reactor}.slot-right_menu{grid-area:right_menu}.slot-media_events{grid-area:media_events}.slot-status{grid-area:status}.slot-camera_primary{grid-area:camera_primary}.slot-camera_grid{grid-area:camera_grid}.slot-controls{grid-area:controls}.slot-events{grid-area:events}.slot-left_instrument{grid-area:left_instrument}.slot-core{grid-area:core}.slot-right_instrument{grid-area:right_instrument}.slot-footer{grid-area:footer}ha-selector{display:block;min-width:260px}@container(max-width:1100px){.section-row{flex-wrap:wrap}.section-row .field{min-width:calc(50% - 8px)}.section-row .bindings{min-width:100%}}@container(max-width:760px){main{padding:12px}.workspace{grid-template-columns:1fr}.profile-bar,.screen-head,.section-row{flex-wrap:wrap}.field,.bindings{min-width:100%}.preview-stage{height:280px;overflow:auto}.header-actions{align-self:start}}
      main{container-type:inline-size}.editor{min-width:0}ha-selector{width:100%;min-width:0}
      .profile-choices{display:grid;gap:6px}.profile-choice{display:grid;grid-template-columns:20px minmax(0,1fr);align-items:center;gap:7px;width:100%;min-height:36px;padding:7px 9px;text-align:left}.profile-choice ha-icon{color:var(--muted);--mdc-icon-size:17px}.profile-choice span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.profile-choice.selected{border-color:var(--cyan);background:#0b2024;color:var(--cyan)}.profile-choice.selected ha-icon{color:var(--cyan)}.profile-select-fallback{margin-top:8px}.profile-select-fallback summary{cursor:pointer;color:var(--muted);font-size:8px}.profile-select-fallback select{margin-top:6px}.dashboard-import{margin-top:22px;padding-top:2px;border-top:1px solid #143c42}.dashboard-import select{margin-bottom:8px}.dashboard-import button{width:100%}.section-block{background:#071115;border-left:2px solid var(--cyan);padding:10px}.section-block .section-row{background:transparent;border:0;padding:0}.selected-entities{display:flex;flex-wrap:wrap;gap:5px;margin-top:7px}.selected-entities span{max-width:210px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding:4px 7px;border:1px solid #267680;background:#0b2024;color:#bdeff0;font-size:10px}.selected-entities em,.actions p{color:var(--muted);font-size:10px;font-style:normal}.actions{margin-top:10px;padding-top:10px;border-top:1px solid #143c42}.actions-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:7px}.actions-head label{margin:0}.actions-head button{min-height:30px;padding:4px 8px}.action-row{display:grid;grid-template-columns:90px 140px minmax(220px,1fr) 38px;gap:8px;align-items:center;margin-top:7px}.action-row select,.action-row input{min-height:36px}.action-target{display:flex;gap:6px;min-width:0}.action-target>*{flex:1;min-width:0}@container(max-width:760px){.action-row{grid-template-columns:1fr 1fr 38px}.action-target{grid-column:1/3}.section-block .section-row .field{min-width:100%}}
      .layout-label{margin-top:16px}.layout-choices{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:7px 0 14px}.layout-choice{display:grid;grid-template-columns:82px 1fr;grid-template-rows:auto auto;text-align:left;gap:2px 10px;min-height:92px;align-items:center}.layout-choice.selected{border-color:var(--cyan);background:#0b2024;box-shadow:inset 0 0 0 1px var(--cyan)}.layout-choice strong{color:var(--cyan);font-size:12px}.layout-choice small{color:var(--muted);font-size:9px;line-height:1.35}.mini-layout{grid-row:1/3;display:grid;width:82px;height:62px;gap:3px}.mini-layout i{display:block;border:1px solid #267680;background:#10282d}.mini-layout.radial_command_overview,.mini-layout.security_camera_board{grid-template-columns:repeat(5,1fr)}.mini-layout.focused_control{grid-template-columns:1fr 1.4fr 1fr;grid-template-rows:1fr 12px}.mini-layout.focused_control .slot-footer{grid-column:1/4}.slot-editor,.slot-editor.radial_command_overview,.slot-editor.security_camera_board,.slot-editor.focused_control{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:10px;margin-top:10px}.slot-editor>.section-block,.slot-editor.focused_control>.slot-footer{grid-area:auto;grid-column:auto;grid-row:auto;min-width:0;border:1px solid var(--line);border-top:3px solid var(--cyan);padding:12px}.slot-heading{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-bottom:10px}.slot-heading strong{color:var(--cyan);font-size:11px}.slot-heading span{color:var(--muted);font-size:8px;text-align:right}.slot-editor .section-row{display:block}.slot-editor .section-kind{min-width:0;margin-bottom:9px}.slot-editor .bindings{min-width:0}.slot-editor .selected-entities{max-height:86px;overflow:auto}.slot-editor .selected-entities span{max-width:100%}.actions summary{cursor:pointer;color:var(--muted);font-size:9px}.actions-head{gap:10px;margin-top:8px}.actions-head span{color:var(--muted);font-size:9px}.actions-head button{flex:none}@container(max-width:900px){.layout-choices{grid-template-columns:1fr}.layout-choice{grid-template-columns:92px 1fr}}
      .slot-editor,.slot-editor.radial_command_overview,.slot-editor.security_camera_board,.slot-editor.focused_control{display:grid;gap:10px;min-height:520px;padding:12px;background:rgba(2,10,13,.82);border:1px solid #143c42;background-image:linear-gradient(rgba(69,232,232,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(69,232,232,.025) 1px,transparent 1px);background-size:30px 30px}
      .slot-editor.radial_command_overview{grid-template-columns:1fr 1fr 1.35fr 1fr;grid-template-rows:1fr 1fr;grid-template-areas:"overview overview reactor media" "left_menu right_menu reactor events"}
      .slot-editor.security_camera_board{grid-template-columns:.8fr 1.65fr 1fr;grid-template-rows:1.15fr .85fr;grid-template-areas:"status camera_primary controls" "events camera_grid controls"}
      .slot-editor.focused_control{grid-template-columns:1fr 1.5fr 1fr;grid-template-rows:1fr .58fr;grid-template-areas:"left_instrument core right_instrument" "left_instrument core footer"}
      .slot-editor>.section-block,.slot-editor.focused_control>.slot-footer{grid-column:auto;grid-row:auto;min-width:0;min-height:150px;padding:10px;border:1px solid var(--line);border-top:3px solid var(--cyan);background:rgba(7,17,21,.92);overflow:hidden}
      .slot-editor .slot-overview{grid-area:overview}.slot-editor .slot-left_menu{grid-area:left_menu}.slot-editor .slot-reactor{grid-area:reactor}.slot-editor .slot-right_menu{grid-area:right_menu}.slot-editor .slot-media{grid-area:media}.slot-editor .slot-status{grid-area:status}.slot-editor .slot-camera_primary{grid-area:camera_primary}.slot-editor .slot-camera_grid{grid-area:camera_grid}.slot-editor .slot-controls{grid-area:controls}.slot-editor .slot-events{grid-area:events}.slot-editor .slot-left_instrument{grid-area:left_instrument}.slot-editor .slot-core{grid-area:core}.slot-editor .slot-right_instrument{grid-area:right_instrument}.slot-editor .slot-footer{grid-area:footer}.slot-editor>.panel-full-height{grid-row:1/-1!important}
      .entity-canvas{display:grid;gap:7px;align-content:start;min-height:66px}.drop-empty{display:grid;place-items:center;min-height:72px;border:1px dashed #28626a;color:var(--muted);font-size:10px}.entity-card{position:relative;display:grid;grid-template-columns:18px 30px minmax(0,1fr) 26px;align-items:center;gap:7px;padding:8px;background:#0b2024;border:1px solid #245c63;cursor:grab}.entity-card:active{cursor:grabbing}.entity-card.dragging{opacity:.45}.entity-card ha-icon{color:var(--cyan);--mdc-icon-size:24px}.drag-handle{color:#5da2a8;font-size:18px}.entity-copy{min-width:0}.entity-copy strong,.entity-copy small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.entity-copy strong{font-size:10px;color:#d8f7f7}.entity-copy small{font-size:9px;color:#7fbfc3;margin-top:2px}.remove-card{min-height:26px;width:26px;padding:0;color:#ff8181}.card-options{grid-column:2/5;display:grid;grid-template-columns:minmax(120px,1fr) auto;gap:8px;align-items:end;padding-top:6px;border-top:1px solid #173f44}.card-options label{margin:0;font-size:8px}.card-options input{min-height:30px;padding:5px;margin-top:3px}.toggle-option{display:flex!important;align-items:center;gap:6px;padding:7px 5px;color:#bdeff0}.toggle-option input{width:18px;min-height:18px;margin:0}.add-entity{margin-top:9px;padding-top:9px;border-top:1px dashed #245c63}.slot-settings,.actions{margin-top:8px}.slot-settings summary,.actions summary{cursor:pointer;color:var(--muted);font-size:9px}.slot-settings .field{margin-top:8px;min-width:0}
      @container(max-width:1050px){.layout-choices{grid-template-columns:1fr}.slot-editor,.slot-editor.radial_command_overview,.slot-editor.security_camera_board,.slot-editor.focused_control{grid-template-columns:1fr;grid-template-rows:auto;grid-template-areas:none;min-height:0}.slot-editor>.section-block,.slot-editor.focused_control>.slot-footer{grid-area:auto}.entity-card{grid-template-columns:18px 30px minmax(0,1fr) 26px}.workspace{grid-template-columns:220px minmax(0,1fr)}}
      @container(max-width:700px){main{padding:12px}.workspace{grid-template-columns:1fr}.profile-bar,.screen-head{flex-wrap:wrap}.card-options{grid-template-columns:1fr}.toggle-option{justify-content:flex-start}}
      .attribute-summary{color:var(--cyan)!important}.attribute-picker{margin-top:14px;padding-top:12px;border-top:1px solid #17434a}.attribute-picker h3{margin:0;color:var(--cyan);font-size:11px}.attribute-picker>p{margin:4px 0 9px;color:var(--muted);font-size:9px}.attribute-options{display:grid;grid-template-columns:1fr 1fr;gap:6px;max-height:250px;overflow:auto}.attribute-option{display:grid!important;grid-template-columns:20px minmax(0,1fr);grid-template-rows:auto auto;gap:1px 7px;margin:0!important;padding:7px;border:1px solid #245c63;background:#071115}.attribute-option input{grid-row:1/3;width:16px;min-height:16px;margin:0;align-self:center}.attribute-option span{color:#d8f7f7;font-size:9px}.attribute-option small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--muted);font-size:8px}
      .screen-tabs{display:flex;gap:6px;align-items:center;overflow-x:auto;padding:8px 0 12px}.screen-tab,.add-screen-tab{min-height:36px;white-space:nowrap}.screen-tab.selected{background:var(--cyan);border-color:var(--cyan);color:#021012}.add-screen-tab{width:38px;padding:0;font-size:20px;color:var(--cyan)}
      .screen-card{padding:14px}.canvas-toolbar{background:#071014;padding:10px;border:1px solid #143c42}.canvas-toolbar .field{max-width:440px}.layout-choices{margin-bottom:12px}.layout-choice{border-width:1px}.layout-choice.selected{box-shadow:inset 4px 0 0 var(--cyan)}
      .slot-editor>.section-block{display:flex;flex-direction:column}.slot-heading{min-height:44px;margin:0 0 8px;padding-bottom:7px;border-bottom:1px solid #17434a}.slot-heading label{min-width:0;flex:1;margin:0}.slot-heading label span{display:block;margin-bottom:3px;color:var(--muted);font-size:7px;text-align:left}.slot-heading label input{min-height:28px;padding:4px 6px;color:var(--cyan);font-size:10px}.region-add{width:28px;min-height:28px;padding:0;border-color:#267680;color:var(--cyan);font-size:18px}.panel-toolbar{display:flex;align-items:center;flex-wrap:wrap;gap:7px;margin:12px 0 4px;padding:9px;border:1px solid #143c42;background:#071014}.panel-toolbar strong{margin-right:4px;color:var(--cyan);font-size:9px}.panel-toolbar button{display:flex;align-items:center;gap:5px;min-height:32px;padding:5px 8px;font-size:8px}.panel-toolbar button ha-icon{--mdc-icon-size:15px}.panel-toolbar small{color:var(--muted);font-size:8px}.panel-controls{display:flex;gap:5px}.panel-controls button{min-height:28px;padding:3px 6px}.panel-height{display:flex;align-items:center;gap:4px;color:var(--muted);font-size:7px}.panel-height.selected{border-color:var(--cyan);color:var(--cyan);background:#0b2024}.panel-height ha-icon,.panel-controls .icon ha-icon{--mdc-icon-size:15px}.panel-controls .icon{width:28px}.empty-panels{display:grid;place-items:center;grid-column:1/-1;min-height:220px;color:var(--muted);border:1px dashed #28626a}
      .entity-canvas{flex:1}.entity-card{grid-template-columns:17px 28px minmax(0,1fr) auto auto 30px;padding:7px;gap:7px}.entity-card ha-icon{--mdc-icon-size:22px}.entity-copy strong{font-size:10px}.tap-mode{color:#73b7bb;font-size:7px;border:1px solid #245c63;padding:3px 5px}.card-settings,.live-toggle{display:grid;place-items:center;width:30px;min-height:30px;padding:0}.card-settings ha-icon,.live-toggle ha-icon{--mdc-icon-size:17px}.live-toggle.is-on{color:#021012;background:var(--cyan);border-color:var(--cyan)}.drop-empty{width:100%;min-height:92px;border:1px dashed #28626a;background:transparent;color:var(--muted);display:grid;place-items:center;align-content:center;gap:7px}.drop-empty ha-icon{color:var(--cyan);--mdc-icon-size:28px}.slot-camera_primary .drop-empty{min-height:180px}.slot-reactor .drop-empty,.slot-core .drop-empty{border-radius:50%;width:min(180px,80%);aspect-ratio:1;justify-self:center;align-self:center;background:radial-gradient(circle,rgba(69,232,232,.12),transparent 62%)}
      .editor-modal{position:fixed;inset:0;z-index:1000;display:grid;place-items:center;padding:24px;background:rgba(0,6,8,.78);backdrop-filter:blur(4px)}.editor-modal-card{width:min(540px,100%);max-height:calc(100vh - 48px);overflow:auto;background:#09171b;border:1px solid var(--cyan);box-shadow:0 18px 70px rgba(0,0,0,.55)}.editor-modal-card>header{display:flex;align-items:center;padding:16px;margin:0;border-bottom:1px solid var(--line)}.editor-modal-card>header h2{font-size:17px;margin:2px 0 0}.editor-modal-card>header button{margin-left:auto;width:36px;min-height:36px;padding:0}.dialog-title{display:flex;align-items:center;gap:11px}.dialog-title>ha-icon{color:var(--cyan);--mdc-icon-size:30px}.dialog-copy{padding:14px 16px;color:var(--muted);font-size:11px}.editor-modal-card>[data-picker-selector]{display:block;padding:0 16px 18px}.dialog-fields{display:grid;gap:14px;padding:18px}.dialog-fields label{font-size:9px}.dialog-fields input,.dialog-fields select{margin-top:6px}.editor-modal-card>footer{display:flex;justify-content:space-between;gap:10px;padding:14px 18px;border-top:1px solid var(--line)}
      .fixed-value{display:flex;align-items:center;min-height:38px;padding:8px 12px;border:1px solid var(--line);color:var(--cyan)}.home-mode-note{display:flex;align-items:center;gap:10px;margin:12px 0;padding:10px;border:1px solid #267680;background:#0a1d22}.home-mode-note ha-icon{color:var(--cyan)}.home-mode-note strong,.home-mode-note small{display:block}.home-mode-note strong{font-size:11px;color:var(--cyan)}.home-mode-note small{margin-top:3px;font-size:9px;color:var(--muted)}.page-render-settings{display:grid;grid-template-columns:repeat(4,minmax(130px,1fr));gap:10px;margin:12px 0;padding:12px;border:1px solid #143c42;background:#071014}.scale-field label span{float:right;color:var(--cyan)}.scale-field input{padding:0}.ha-cards-preview{display:grid;place-items:center;align-content:center;gap:10px;min-height:440px;border:1px dashed #267680;background:rgba(2,10,13,.82);text-align:center}.ha-cards-preview ha-icon{color:var(--cyan);--mdc-icon-size:58px}.ha-cards-preview strong{color:var(--cyan);font-size:16px}.ha-cards-preview span{color:#d8f7f7;font-size:12px}.ha-cards-preview small{max-width:420px;color:var(--muted);font-size:10px}.page-link-card{display:grid;grid-template-columns:28px minmax(0,1fr) auto;align-items:center;gap:8px;width:100%;padding:9px;text-align:left;border-color:#267680;background:#0a1d22}.page-link-card ha-icon{color:var(--cyan);--mdc-icon-size:21px}.page-link-card span{min-width:0}.page-link-card strong,.page-link-card small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.page-link-card strong{color:#d8f7f7;font-size:10px}.page-link-card small{margin-top:2px;color:var(--muted);font-size:7px}.page-link-card em{color:var(--cyan);font-size:7px;font-style:normal}.entity-picker-search{display:grid;grid-template-columns:24px minmax(0,1fr);align-items:center;gap:8px;margin:0 16px 8px;padding:0 10px;border:1px solid var(--line);background:#061014}.entity-picker-search:focus-within{border-color:var(--cyan)}.entity-picker-search ha-icon{color:var(--cyan);--mdc-icon-size:20px}.entity-picker-search input{min-height:44px;padding:8px 0;border:0;background:transparent;outline:0}.entity-picker-summary{padding:0 16px 8px;color:var(--muted);font-size:9px}.entity-picker-list{display:grid;max-height:min(480px,55vh);overflow:auto;border-top:1px solid #143c42}.entity-picker-option{display:grid;grid-template-columns:28px minmax(0,1fr) auto;align-items:center;gap:10px;width:100%;min-height:54px;padding:8px 16px;border:0;border-bottom:1px solid #143c42;text-align:left}.entity-picker-option:hover{background:#0b2024}.entity-picker-option[hidden]{display:none}.entity-picker-option ha-icon{color:var(--cyan);--mdc-icon-size:23px}.entity-picker-option span{min-width:0}.entity-picker-option strong,.entity-picker-option small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.entity-picker-option strong{font-size:11px}.entity-picker-option small{margin-top:3px;color:var(--muted);font-size:9px}.entity-picker-option em{max-width:110px;overflow:hidden;text-overflow:ellipsis;color:#82c8cc;font-size:9px;font-style:normal;white-space:nowrap}.entity-picker-empty{padding:28px 16px;text-align:center;color:var(--muted);font-size:11px}.entity-picker-empty[hidden]{display:none}
      @container(max-width:700px){.entity-card{grid-template-columns:15px 26px minmax(0,1fr) auto 30px}.tap-mode{display:none}.editor-modal{padding:10px}.screen-tabs{position:sticky;top:0;z-index:5;background:#050b0e}.entity-picker-option{grid-template-columns:26px minmax(0,1fr)}.entity-picker-option em{display:none}.page-render-settings{grid-template-columns:1fr}.ha-cards-preview{min-height:280px}}
      .preview-stage.radial_command_overview{grid-template-columns:1fr 1fr 1.6fr 1fr;grid-template-rows:1fr 1fr;grid-template-areas:"overview overview reactor media" "left_menu right_menu reactor events"}.preview-stage.radial_command_overview .slot-overview{grid-area:overview}.preview-stage.radial_command_overview .slot-left_menu{grid-area:left_menu}.preview-stage.radial_command_overview .slot-reactor{grid-area:reactor}.preview-stage.radial_command_overview .slot-right_menu{grid-area:right_menu}.preview-stage.radial_command_overview .slot-media{grid-area:media}.preview-stage.radial_command_overview .slot-events{grid-area:events}
      .page-header{margin-bottom:12px}.task-tabs{display:flex;gap:6px;max-width:100%;overflow-x:auto;margin-bottom:12px;padding-bottom:2px;border-bottom:1px solid var(--line)}.task-tab{display:flex;align-items:center;gap:7px;min-width:120px;border-bottom:3px solid transparent}.task-tab ha-icon{--mdc-icon-size:18px}.task-tab.selected{color:#021012;background:var(--cyan);border-color:var(--cyan)}.profile-context{display:grid;grid-template-columns:minmax(220px,420px) 1fr auto;align-items:end;gap:12px;min-width:0;margin-bottom:16px;padding:10px 12px;border:1px solid var(--line);background:#071014}.profile-context label{min-width:0;margin:0}.profile-context select{margin-top:5px}.profile-context span{align-self:center;color:var(--muted);font-size:10px}.task-workspace{min-width:0;max-width:100%;overflow:hidden}.settings-page,.assignments{min-width:0;padding:18px;border:1px solid var(--line);background:rgba(10,21,25,.94)}.settings-heading{display:flex;align-items:end;justify-content:space-between;gap:20px;margin-bottom:18px;padding-bottom:14px;border-bottom:1px solid #143c42}.settings-heading h2{margin:3px 0 5px;font-size:19px}.settings-heading p{color:var(--muted);font-size:10px}.profiles-layout{display:grid;grid-template-columns:minmax(220px,320px) minmax(0,1fr);gap:18px;min-width:0}.profile-list,.profile-settings,.advanced-grid article{min-width:0;padding:14px;border:1px solid #143c42;background:#071014}.profile-settings{display:grid;grid-template-columns:repeat(3,minmax(160px,1fr));gap:12px;align-items:end}.profile-delete{grid-column:1/-1;justify-self:start}.advanced-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;min-width:0}.advanced-grid article h2{margin:0 0 6px}.advanced-grid article p{min-height:32px;margin-bottom:12px;color:var(--muted);font-size:10px}.advanced-grid article>button{width:100%;margin-top:8px}.screen-workspace{display:grid;grid-template-columns:190px minmax(0,1fr);gap:14px;min-width:0}.screen-list,.screens,.screen-card{min-width:0;max-width:100%}.screen-list{align-self:start;padding:12px;border:1px solid var(--line);background:rgba(10,21,25,.94)}.screen-list-heading{display:flex;align-items:center;justify-content:space-between;margin-bottom:9px}.screen-list-heading label{margin:0}.screen-list .screen-tab{display:block;width:100%;margin-bottom:6px;text-align:left}.panel-picker{min-width:0;margin:12px 0;padding:10px;border:1px solid #143c42;background:#071014}.panel-picker-heading{display:flex;align-items:baseline;gap:9px;margin-bottom:8px}.panel-picker-heading strong{color:var(--cyan);font-size:9px}.panel-picker-heading small{color:var(--muted);font-size:8px}.panel-picker-list{display:flex;gap:7px;max-width:100%;overflow-x:auto;padding-bottom:2px}.panel-picker-item{display:grid;grid-template-columns:22px minmax(100px,1fr);grid-template-rows:auto auto;gap:2px 7px;min-width:150px;text-align:left}.panel-picker-item ha-icon{grid-row:1/3;align-self:center;color:var(--cyan);--mdc-icon-size:19px}.panel-picker-item span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.panel-picker-item small{color:var(--muted);font-size:7px}.panel-picker-item.selected{border-color:var(--cyan);background:#0b2024;color:var(--cyan)}.add-panel{min-width:0;margin-bottom:10px}.add-panel summary{cursor:pointer;color:var(--cyan);font-size:9px}.add-panel .panel-toolbar{margin-top:7px}.focused-panel-editor{min-width:0;min-height:420px;overflow:hidden;padding:12px;border:1px solid #143c42;background:rgba(2,10,13,.82)}.focused-panel-editor>.section-block{min-width:0;min-height:390px;border:1px solid var(--line);border-top:3px solid var(--cyan);padding:14px;background:rgba(7,17,21,.96)}.focused-panel-editor .slot-heading{align-items:end}.focused-panel-editor .entity-canvas{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:8px}.focused-panel-editor .drop-empty{grid-column:1/-1}.focused-panel-editor .quick-command-list{max-height:none}.focused-panel-editor .selected-entities{max-height:none}.backend-config{margin:0;padding:18px;border:1px solid var(--line);background:rgba(10,21,25,.94)}.backend-config h2{margin-top:0}
      @container(max-width:900px){.profiles-layout,.screen-workspace,.advanced-grid{grid-template-columns:minmax(0,1fr)}.screen-list{display:flex;gap:6px;width:100%;overflow-x:auto}.screen-list-heading{min-width:90px}.screen-list .screen-tab{min-width:130px;margin:0}.profile-settings{grid-template-columns:1fr}.profile-context{grid-template-columns:minmax(0,1fr) auto}.profile-context span{display:none}}
      @container(max-width:600px){.task-tab{min-width:auto;flex:1;justify-content:center}.task-tab ha-icon{display:none}.profile-context{grid-template-columns:1fr}.focused-panel-editor{padding:6px}.focused-panel-editor .entity-canvas{grid-template-columns:1fr}.settings-heading{align-items:stretch;flex-direction:column}.settings-heading .button-row{width:100%}}
    `;
  }
}

if (!customElements.get("biofects-butler-panel")) {
  customElements.define("biofects-butler-panel", BiofectsButlerPanel);
}

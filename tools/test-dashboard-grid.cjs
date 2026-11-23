const assert = require('node:assert/strict');
const {test} = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const registry = new Map();
const context = vm.createContext({HTMLElement: class {}, customElements: {get: k => registry.get(k), define: (k,v) => registry.set(k,v)}});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../custom_components/biofects_butler/frontend/biofects-butler-panel.js'), 'utf8'), context);
const pack = (screen, columns) => JSON.parse(JSON.stringify(context.dashboardGridPlacements(screen, columns)));
const prototype = registry.get('biofects-butler-panel').prototype;
const panel = (props = {}) => ({section_id:'panel', slot:'panel', column_span:2, row_span:1, ...props});
test('tall panels allow stacked neighbors', () => {
  assert.deepEqual(pack({sections:[panel({row_span:2}),panel(),panel()]}), [
    {column:0,row:0,width:2,height:2}, {column:2,row:0,width:2,height:1}, {column:2,row:1,width:2,height:1},
  ]);
});
test('pinned panels reserve cells before automatic panels', () => {
  const result = pack({sections:[panel(),panel({grid_column:1,grid_row:1})]});
  assert.equal(result[0].column,2); assert.equal(result[1].column,0);
});
test('collisions move down without overlap', () => {
  assert.deepEqual(pack({sections:[panel({row_span:2,grid_column:1,grid_row:1}),panel({grid_column:1,grid_row:1})]})[1], {column:0,row:2,width:2,height:1});
});
test('phone reflow removes gaps and preserves reading order', () => {
  assert.deepEqual(pack({grid_columns:12,sections:[panel({column_span:8,row_span:2,grid_column:5,grid_row:20}),panel({column_span:4,grid_column:1,grid_row:1})]},1), [
    {column:0,row:0,width:1,height:2}, {column:0,row:2,width:1,height:1},
  ]);
});
test('dense mixed layouts never overlap at any breakpoint', () => {
  const screen = {grid_columns:12, sections:Array.from({length:20}, (_,i) => panel({column_span:1+i%12,row_span:1+i%8,grid_column:1+i%12,grid_row:1+i%4}))};
  for (const columns of [1,6,12]) {
    const cells = new Set();
    for (const p of pack(screen,columns)) {
      assert.ok(p.column >= 0 && p.column+p.width <= columns);
      for (let y=p.row;y<p.row+p.height;y++) for (let x=p.column;x<p.column+p.width;x++) {
        assert.ok(!cells.has(`${x},${y}`)); cells.add(`${x},${y}`);
      }
    }
  }
});
test('presets feature the selected panel and retain controls', () => {
  for (const preset of ['hero','mosaic','wall','briefing']) {
    const sections = [panel({slot:'one',bindings:[{target_id:'light.kitchen'}]}),panel({slot:'two',actions:[{type:'navigate',target_id:'security'}]}),panel({slot:'three'}),panel({slot:'four'})];
    const screen = {composition:'freeform_grid',sections};
    const content = sections.map(({slot,bindings,actions}) => ({slot,bindings,actions}));
    const editor = Object.assign(Object.create(prototype), {_draft:{profile_id:"test",screens:[screen]},_activeSectionSlot:"two"});
    editor._applyGridPreset(0,preset);
    assert.deepEqual(sections.map(({slot,bindings,actions}) => ({slot,bindings,actions})),content);
    assert.equal(screen.grid_columns,12);
    if (preset !== 'wall') assert.equal(sections[1].grid_column,1);
    assert.equal(pack(screen).length,4);
  }
});

test('undo restores layout without losing subsequent entity edits', () => {
  const section = panel({section_id:'one',slot:'one',bindings:[]});
  const screen = {screen_id:'home',composition:'freeform_grid',sections:[section]};
  const editor = Object.assign(Object.create(prototype), {_draft:{profile_id:'test',screens:[screen]},_activeSectionSlot:'one'});
  editor._applyGridPreset(0,'hero');
  section.bindings.push({target_id:'light.kitchen'});
  editor._undoGridLayout(screen);
  assert.equal(section.column_span,2);
  assert.equal(section.grid_column,undefined);
  assert.equal(screen.grid_columns,undefined);
  assert.equal(section.bindings[0].target_id,'light.kitchen');
});
test('whole-home arrangement groups by purpose and undo restores reading order', () => {
  const types = ['media','events','assistant','quick_commands','weather','status_overview','cameras'];
  const sections = types.map((type,i)=>panel({section_id:`panel_${i}`,slot:`panel_${i}`,type,bindings:[{target_id:`sensor.${i}`}]}));
  const screen = {screen_id:'home',composition:'freeform_grid',sections};
  const editor = Object.assign(Object.create(prototype), {_draft:{profile_id:'test',screens:[screen]}});
  editor._applyGridPreset(0,'whole_home');
  assert.deepEqual(Array.from(screen.sections,s=>s.type), ['status_overview','assistant','weather','media','events','quick_commands','cameras']);
  assert.equal(screen.sections[0].column_span,12);
  assert.equal(screen.sections[1].row_span,4);
  assert.equal(screen.sections[1].grid_row,3);
  const cells = new Set();
  for (const p of pack(screen)) for(let y=p.row;y<p.row+p.height;y++) for(let x=p.column;x<p.column+p.width;x++) {
    assert.ok(!cells.has(`${x},${y}`)); cells.add(`${x},${y}`);
  }
  screen.sections[1].bindings.push({target_id:'light.kitchen'});
  editor._undoGridLayout(screen);
  assert.deepEqual(Array.from(screen.sections,s=>s.type),types);
  assert.equal(screen.sections[2].bindings[1].target_id,'light.kitchen');
});
test('whole-home arrangement handles sparse and unclassified panels', () => {
  for(const count of [0,1,2,6,20]) {
    const screen = {screen_id:'home',composition:'freeform_grid',sections:Array.from({length:count},(_,i)=>panel({section_id:`panel_${i}`,slot:`panel_${i}`,type:'form'}))};
    const editor = Object.assign(Object.create(prototype), {_draft:{profile_id:'test',screens:[screen]}});
    editor._applyGridPreset(0,'whole_home');
    assert.equal(screen.sections.length,count);
    assert.equal(new Set(screen.sections.map(s=>s.section_id)).size,count);
    assert.equal(pack(screen).length,count);
  }
});
function visualEditor(sections) {
  return Object.assign(Object.create(prototype), {_draft:{profile_id:'test',screens:[{screen_id:'home',composition:'freeform_grid',sections}]},_hass:{states:{'light.kitchen':{entity_id:'light.kitchen',state:'off',attributes:{friendly_name:'Kitchen'}}}},_render(){}});
}
test('adding an entity uses existing binding/action fields and rejects duplicates', () => {
  const section = {section_id:'one',slot:'one',type:'entity_controls',bindings:[],actions:[]};
  const editor = visualEditor([section]);
  editor._addCanvasEntity(0,0,'light.kitchen');
  editor._addCanvasEntity(0,0,'light.kitchen');
  assert.equal(section.bindings.length,1);
  assert.equal(section.bindings[0].display_mode,'tile');
  assert.equal(section.actions[0].type,'more_info');
});
test('moving a card retains settings, grouped entities, tap and custom hold actions', () => {
  const binding = {kind:'entity',target_id:'light.kitchen',entity_ids:['light.kitchen','light.dining'],name:'My lights',display_mode:'tile',card_width:3,card_height:2,card_shape:'rounded'};
  const tap={gesture:'tap',type:'toggle',target_id:'light.kitchen'};
  const hold={gesture:'hold',type:'call_service',source_id:'light.kitchen',domain:'script',service:'evening',data:{color:'warm'}};
  const from={section_id:'one',slot:'one',bindings:[binding],actions:[tap,hold]},to={section_id:'two',slot:'two',bindings:[],actions:[]};
  const editor=visualEditor([from,to]);
  assert.equal(editor._moveCanvasBinding({screen:0,section:0,binding:0},0,1),true);
  assert.equal(to.bindings[0],binding);assert.equal(from.bindings.length,0);assert.equal(from.actions.length,0);
  assert.equal(to.actions[0],tap);assert.equal(to.actions[1],hold);
});
test('a duplicate destination never removes the source card or actions', () => {
  const from={section_id:'one',slot:'one',bindings:[{target_id:'light.kitchen'}],actions:[{type:'toggle',target_id:'light.kitchen'}]};
  const to={section_id:'two',slot:'two',bindings:[{target_id:'light.kitchen'}],actions:[]};
  const editor=visualEditor([from,to]);
  assert.equal(editor._moveCanvasBinding({screen:0,section:0,binding:0},0,1),false);
  assert.equal(from.bindings.length,1);assert.equal(from.actions.length,1);assert.equal(to.bindings.length,1);
});
test('changing a tap action cannot truncate unrelated actions or activate a sensor', () => {
  const section={actions:Array.from({length:20},(_,i)=>({gesture:'tap',type:'toggle',target_id:`light.item_${i}`}))};
  const editor=visualEditor([]),original=JSON.stringify(section.actions);
  editor._setBindingTapAction(section,'light.kitchen','toggle');
  assert.equal(JSON.stringify(section.actions),original);
  editor._setBindingTapAction(section,'sensor.temperature','activate');
  assert.equal(JSON.stringify(section.actions),original);
});
test('dragging a nested card uses the binding payload instead of moving its panel', () => {
  const data={};
  const card={dataset:{screen:'0',section:'1',binding:'2'}};
  const editor=visualEditor([]);
  editor._onDragStart({target:{closest(selector){return selector==='[data-binding-card]'?card:selector==='[data-panel-drag]'?{dataset:{}}:null;}},dataTransfer:{setData(key,value){data[key]=value;}}});
  assert.ok(data['application/x-butler-binding']);assert.equal(data['application/x-butler-panel'],undefined);
});
test('new profiles start in the visual designer without modifying existing profiles', () => {
  const existing={profile_id:'existing',screens:[{screen_id:'home',composition:'radial_command_overview',sections:[]}]};
  const editor=visualEditor([]);editor._snapshot={profiles:[existing]};
  const before=JSON.stringify(existing);
  editor._new();
  assert.equal(editor._draft.screens[0].composition,'freeform_grid');
  assert.equal(editor._activeWorkspace,'screens');
  assert.equal(editor._draft.screens[0].sections.length,0);
  editor._addFreeformSection(0,'entity_controls');
  assert.equal(editor._draft.screens[0].sections[0].column_span,6);
  assert.equal(JSON.stringify(existing),before);
});

test('Home Assistant arrangement stays fixed across display themes', () => {
  for (const theme of ['butler_neon', 'holographic_interface', 'companion']) {
    const editor = {_layoutPreviewTheme: () => theme, _panelPreviewContent: () => '', _slotLabel: () => 'Assistant'};
    for (const layout of [undefined, 'theme_default', 'console', 'orbital', 'observatory', 'wings', 'companion']) {
      const html = prototype._layoutPreview.call(editor, {
        screen_id: 'home', composition: 'radial_command_overview', command_layout: layout,
        sections: [{section_id: 'assistant', slot: 'reactor'}],
      }, 0, null);
      const expected = !layout || layout === 'theme_default' ? 'orbital' : layout;
      assert.ok(html.includes(`arrangement-${expected}`));
      assert.ok(!html.includes('PREVIEW THEME'));
    }
  }
});

test('position buttons preserve panel content and undo restores geometry', () => {
  const sections = [panel({section_id:'one',slot:'one',grid_column:1,grid_row:1,bindings:[{target_id:'light.kitchen'}],actions:[{type:'toggle',target_id:'light.kitchen'}]}),panel({section_id:'two',slot:'two',grid_column:3,grid_row:1})];
  const screen = {screen_id:'home',composition:'freeform_grid',grid_columns:6,sections};
  const editor = {_draft:{profile_id:'test',screens:[screen]},_rememberGridLayout:prototype._rememberGridLayout};
  const content = JSON.stringify(sections.map(s=>({bindings:s.bindings,actions:s.actions})));
  prototype._adjustPanel.call(editor,0,0,'position','top_right');
  assert.equal(sections[0].grid_column,5);assert.equal(sections[0].grid_row,1);
  prototype._adjustPanel.call(editor,0,0,'column_span',4);
  assert.equal(sections[0].grid_column,3);assert.equal(sections[0].column_span,4);
  prototype._adjustPanel.call(editor,0,0,'nudge','down');
  assert.equal(sections[0].grid_row,2);
  prototype._undoGridLayout.call(editor,screen);
  assert.equal(sections[0].grid_row,1);
  prototype._undoGridLayout.call(editor,screen);
  prototype._undoGridLayout.call(editor,screen);
  assert.equal(sections[0].grid_column,1);assert.equal(sections[0].column_span,2);
  assert.equal(JSON.stringify(sections.map(s=>({bindings:s.bindings,actions:s.actions}))),content);
});

test('simple controls never convert fixed templates or lose commands', () => {
  const screen = {screen_id:'home',composition:'radial_command_overview',sections:[panel({slot:'media',type:'quick_commands',actions:[{type:'call_service',domain:'script',service:'good_night'}]})]};
  const before = JSON.stringify(screen);
  prototype._adjustPanel.call({_draft:{screens:[screen]}},0,0,'position','top_right');
  assert.equal(JSON.stringify(screen),before);
  const html=prototype._simplePanelControls.call({_slotLabel:()=> 'Quick Actions'},screen,0,screen.sections[0]);
  assert.ok(html.includes('data-quick-panel'));assert.ok(!html.includes('data-quick-position'));
});

test('Simpsons theme exposes character choices and sends display-only assignments', () => {
  for (const name of ['homer','marge','bart','lisa','maggie']) {
    const theme='simpsons_'+name;
    const editor={_snapshot:{assignments:{echo:'profile'},display_themes:{echo:theme}}};
    const html=prototype._displayAssignments.call(editor,[{display_id:'echo',name:'Echo Show',model:'Echo',viewport_class:'expanded'}],[{profile_id:'profile',name:'Home'}]);
    assert.ok(html.includes('data-display-character="echo"'));
    assert.ok(html.includes(`value="${theme}" selected`));
    let assignment;
    const handler={_draft:{},_snapshot:editor._snapshot,_assign:(...args)=>assignment=args};
    prototype._onChange.call(handler,{target:{dataset:{displayCharacter:'echo'},value:theme,hasAttribute:()=>false},composedPath:()=>[]});
    assert.deepEqual(assignment,['echo','profile',theme]);
  }
});

test('background and character selections preserve each other', () => {
  let assignment;
  const editor={_draft:{},_snapshot:{assignments:{echo:'profile'},display_themes:{echo:'simpsons_homer__house'}},_assign:(...args)=>assignment=args};
  const event=(dataset,value)=>({target:{dataset,value,hasAttribute:()=>false},composedPath:()=>[]});
  prototype._onChange.call(editor,event({displayCharacter:'echo'},'simpsons_bart'));
  assert.deepEqual(assignment,['echo','profile','simpsons_bart__house']);
  prototype._onChange.call(editor,event({displayBackground:'echo'},'kwik_e_mart'));
  assert.deepEqual(assignment,['echo','profile','simpsons_homer__kwik_e_mart']);
  prototype._onChange.call(editor,event({displayBackground:'echo'},'plain'));
  assert.deepEqual(assignment,['echo','profile','simpsons_homer']);
  const html=prototype._displayAssignments.call(editor,[{display_id:'echo',name:'Echo',model:'Echo',viewport_class:'expanded'}],[{profile_id:'profile',name:'Home'}]);
  assert.ok(html.includes('value="house" selected'));assert.ok(html.includes('value="simpsons_homer" selected'));
});

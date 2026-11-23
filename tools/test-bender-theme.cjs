const assert = require('node:assert/strict');
const {test} = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const registry = new Map();
const context = vm.createContext({HTMLElement: class {}, customElements: {get: k => registry.get(k), define: (k,v) => registry.set(k,v)}});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../custom_components/biofects_butler/frontend/biofects-butler-panel.js'), 'utf8'), context);
const prototype = registry.get('biofects-butler-panel').prototype;
const backgrounds = ['plain','planet_express','new_new_york','robot_bar'];
test('every Bender background remains selected and offers a Bender preview', () => {
  for (const background of backgrounds) {
    const theme = 'futurama_bender' + (background === 'plain' ? '' : `__${background}`);
    const editor = {_snapshot:{assignments:{echo:'shared'},display_themes:{echo:theme}}};
    const html = prototype._displayAssignments.call(editor, [{display_id:'echo',name:'Echo',model:'Echo Show 8',viewport_class:'expanded'}], [{profile_id:'shared',name:'Home'}]);
    assert(html.includes('value="futurama_bender" selected'));
    assert(html.includes(`value="${background}" selected`));
    assert(html.includes('data-display-bender-background="echo"'));
    const preview = prototype._panelPreviewContent.call(editor,{slot:'reactor'}, {composition:'radial_command_overview'},theme);
    assert(preview.includes('alt="Bender"'));
  }
});
test('background changes keep the display and dashboard; plain removes suffix', () => {
  const assigned=[];
  const editor = {_snapshot:{assignments:{echo:'shared'},display_themes:{echo:'futurama_bender__planet_express'}}, _assign:(...args)=>assigned.push(args)};
  const change = value => prototype._onChange.call(editor, {target:{hasAttribute:()=>false,dataset:{displayBenderBackground:'echo'},value},composedPath:()=>[]});
  change('robot_bar');
  change('plain');
  change('unknown');
  assert.deepEqual(assigned,[['echo','shared','futurama_bender__robot_bar'],['echo','shared','futurama_bender']]);
  editor._snapshot.display_themes.echo = 'simpsons_homer';
  change('new_new_york');
  assert.equal(assigned.length,2);
});

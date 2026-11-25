const {chromium} = require('playwright');
const fs = require('fs');
const path = require('path');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1500,height:1100}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.setContent('<html><body style="margin:0"></body></html>');
    await page.addScriptTag({content:fs.readFileSync(path.join(__dirname,'../custom_components/biofects_butler/frontend/biofects-butler-panel.js'),'utf8')});
    await page.evaluate(() => {
      const panel = document.createElement('biofects-butler-panel');
      panel._load = async () => {};
      panel._hass = {states:{'light.desk':{entity_id:'light.desk',state:'on',attributes:{friendly_name:'Desk light'}}},panels:{}};
      const sections = ['overview','left_menu','reactor','right_menu','media','events'].map(slot => ({section_id:slot,slot,type:'entity_controls',bindings:[],actions:[]}));
      sections[0].bindings = [{kind:'entity',target_id:'light.desk'}];
      sections[4].panel_height = 'full_height';
      const profile = {schema_version:1,profile_id:'shared',name:'Shared home',default_screen_id:'home',screens:[{screen_id:'home',title:'Home',composition:'radial_command_overview',command_layout:'companion',sections}]};
      panel._snapshot = {profiles:[profile],displays:[{display_id:'echo',name:'Echo Show'},{display_id:'tablet',name:'Tablet'}],assignments:{echo:'shared',tablet:'shared'},display_themes:{echo:'companion',tablet:'holographic_interface'}};
      panel._draft = structuredClone(profile);
      panel._loadedProfile = structuredClone(profile);
      panel._selectedId = 'shared';
      panel._editorDisplayId = 'echo';
      panel._activeScreenId = 'home';
      panel._activeWorkspace = 'screens';
      document.body.appendChild(panel);
    });
    await page.locator('.arrangement-companion').waitFor();
    assert.equal(await page.locator('[data-editor-display]').inputValue(), 'echo');
    assert.equal(await page.locator('.preview-robot-art').count(), 1);
    assert((await page.locator('.preview-content-list').first().textContent()).includes('Desk light'));
    assert((await page.locator('.shared-profile-note').textContent()).includes('Tablet'));
    const boxes = await page.locator('.arrangement-companion').evaluate(stage => ['overview','media','events','reactor'].map(slot => {const r=stage.querySelector('.slot-'+slot).getBoundingClientRect();return {x:r.x,w:r.width,h:r.height};}));
    assert(boxes[0].x < boxes[1].x && boxes[1].x < boxes[3].x);
    assert(Math.abs(boxes[0].w - boxes[1].w) < 2);
    assert(boxes[1].h > boxes[2].h * 2);
    await page.locator('[data-field="title"]').fill('My changed home');
    await page.locator('[data-field="title"]').press('Tab');
    await page.locator('[data-editor-display]').selectOption('tablet');
    await page.locator('.arrangement-companion').waitFor();
    assert.equal(await page.locator('[data-editor-display]').inputValue(), 'tablet');
    assert.equal(await page.locator('.preview-robot-art').count(), 0);
    assert.equal(await page.locator('[data-field="title"]').inputValue(),'My changed home');
    await page.locator('[data-editor-display]').selectOption('echo');
    await page.locator('.arrangement-companion').waitFor();
    await page.setViewportSize({width:390,height:844});
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= 392));
    assert.deepEqual(errors, []);
    console.log('Display preview passed: target theme, content, panel proportions, shared-profile notice, retained edits and mobile fit.');
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error);process.exitCode=1;});
